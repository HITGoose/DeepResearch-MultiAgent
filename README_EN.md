# 🔬 DeepResearch-Agent: Multi-Agent Deep Research System

[中文](README.md) | English

A LangGraph-based multi-agent research system that produces cited research reports, using **Simulate-Before-Act** search planning and **Cross-Source NLI Verification**.

## Architecture

```
User Query → Planner → Searcher → Analyzer → Writer → Critic
               ↑                                        │
               └──── refine (when score < threshold) ───┘
```

### Agents

| Agent | Responsibility | Key technique |
|-------|----------------|---------------|
| **Planner** | Decomposes the question; generates and scores candidate search plans | Simulate-Before-Act |
| **Searcher** | Multi-source search (Web + ArXiv + Wikipedia), sub-queries run sequentially | Map-phase compression |
| **Analyzer** | Cross-verifies sources and detects contradictions | NLI contradiction detection |
| **Writer** | Writes the report with citations | Claim-level citation tracking |
| **Critic** | Scores the report and decides pass / refine | LLM-as-a-Judge |

### Key ideas

**1. Simulate-Before-Act search planning**

Instead of executing the first plan it writes, the Planner generates several candidate strategies, has a light LLM simulate each one's expected coverage, and runs the best one. Failed strategies are explicitly excluded in the next iteration.

> *Reference: Simulate Before Act (Gu et al., 2025)*

**2. Cross-Source NLI Verification**

The Analyzer uses an NLI model (`cross-encoder/nli-deberta-v3-base`) to detect contradictions between sources: each claim is compared against the other sources' summaries; model outputs are converted to probabilities with softmax, and entailment > 0.75 counts as support, contradiction > 0.9 as a contradiction. Each claim in the report carries a confidence marker:
- ✅ supported by multiple sources
- ⚠️ disputed (both sides noted)
- ❓ single source only

> *Targets: Explicit Summarization hallucinations in the PIES taxonomy (DeepHalluBench, 2026.01)*

### Context management (avoiding token blow-up)

| Strategy | How |
|----------|-----|
| Only compressed summaries between agents | State holds each result's summary and atomic claims, never the raw content |
| Map-Reduce over search results | Each result is compressed individually (Map), then the Analyzer synthesizes them (Reduce), with summaries capped at 3000 characters |
| Search results reset every round | `search_results` uses a custom reducer: a node returning `None` clears it, so State only holds the current round |
| File-as-Memory | All rounds of one research run share `outputs/memory/<run_id>/`: raw results and compressed summaries are stored per sub-query and read back when a later round repeats the sub-query; each round's analysis and sources are stored too and read back in the next round |
| Progressive Summarization | The Writer rewrites from scratch each round without accumulating drafts; the Analyzer reads back the previous round's analysis and merges it with new results, so filling a gap does not drop what was already covered |

## Results

### Earlier runs (before the NLI and context-management fixes)

4 queries of different difficulty, one run each (English reports):

| Query | Difficulty | Iterations | Final score | Time | ✅ High | ⚠️ Disputed | ❓ Unverified |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| What is MCP | Simple | 2 | 7.4/10 | 432s | 5 | 0 | 19 |
| LangGraph vs CrewAI | Medium | 3 | 7.0/10 | 724s | 4 | 0 | 19 |
| RAG vs Fine-tuning | Medium | 2 | 6.85/10 | 411s | 1 | 0 | 23 |
| LLM agent hallucination mitigation | Complex | 4 (max) | 5.4/10 | 819s | 0 | 0 | 22 |

- Scores are the system's own Critic (LLM-as-a-Judge, same model as the Writer), ranging 5.4–7.4; the complex query hit the iteration limit without reaching the 6.0 threshold
- NLI counts are from the final round; "⚠️ Disputed = 0" only means no contradiction was flagged

### NLI fix and evaluation

**Problem**: for multi-class models, `CrossEncoder.predict` returns logits by default (e.g. `[6.83, -3.73, -2.82]`). The old code compared these logits with the probability thresholds 0.75 / 0.9, so the thresholds never applied and the decision was just the top class. The fix applies softmax first and reads the label order from the model's `id2label`.

**Test set**: `evaluation/nli_testset.json`, 44 pairs (15 entailment / 15 contradiction / 14 neutral), labels checked by hand. Premises imitate the source summaries the Searcher produces, hypotheses are atomic claims from another source, and topics come from research questions this project has actually run (RAG vs fine-tuning, hallucination, LangGraph/AutoGen, MCP, RLHF/DPO, LoRA, ...). The decision rule matches `cross_verify_claims`.

| Configuration | Accuracy | Contradiction recall | Contradiction precision | Entailment recall | Neutral recall | False contradictions |
|---|---|---|---|---|---|---|
| Before (logits + thresholds) | 0.977 (43/44) | 1.000 | 1.000 | 0.933 | 1.000 | 0 |
| After (probabilities + thresholds) | 0.977 (43/44) | 1.000 | 1.000 | 0.933 | 1.000 | 0 |

- **No difference on this test set**: the model is confident on all 44 pairs (lowest top-class probability 0.984), so the thresholds never come into play. What the fix guarantees is that low-confidence cases (e.g. a top class at 0.6) fall back to neutral; this test set does not contain such cases.
- The only error is #7: the source says "reduced hallucination rates by about 40%", the claim says "lowered", and the model predicts neutral with 0.999.
- Run: `python -m evaluation.eval_nli`

### Context management: before vs after

**Problems**:
1. `search_results` used the `operator.add` reducer, so `prepare_iteration` returning `[]` only produced "old + []" and results accumulated across rounds;
2. File-as-Memory was write-only, and every round created a new directory.

See the context-management table above for the fixes.

**Method**: 3 fixed questions, one run each before and after the fix (DeepSeek `deepseek-chat` + Tavily). Both versions get identical search results for identical queries (cached). Tokens are input + output of all LLM calls in the round. "Critic" is the system's final Critic score; "Judge" is the overall score from `evaluation/judge.py` (also DeepSeek).

| Question | Version | Rounds | Tokens per round | Total tokens | Results in State | Critic | Judge |
|---|---|---|---|---|---|---|---|
| What is MCP | Before | 1 | 18.3k | 18.3k | 15 | 7.1 | 7 |
| | After | 1 | 18.8k | 18.8k | 15 | 6.6 | 7 |
| LangGraph vs AutoGen vs CrewAI | Before | 2 | 19.1k / 20.5k | 39.5k | 15 → 30 | 6.35 | 5 |
| | After | 1 | 18.6k | 18.6k | 15 | 7.2 | 7 |
| Hallucination (training vs prompting) | Before | 4 (not passed) | 18.0k / 20.6k / 19.5k / 22.5k | 80.5k | 15 → 30 → 45 → 63 | 5.9 | 5 |
| | After | 4 (passed in round 4) | 19.3k / 21.6k / 19.0k / 21.4k | 81.4k | 15 / 15 / 15 / 15 | 6.2 | 6 |

- **Confirmed effect**: search results no longer accumulate in State (63 → 15 per round on the complex query).
- **Tokens per round are essentially unchanged**: the Analyzer and Writer already passed only the latest 15 / 20 results to the LLM, so accumulated results stayed in State without all being sent to the model; the real harm of accumulation was the Writer's source pool mixing in previous rounds' results. Reading back the previous analysis adds about 700 tokens per round to the Analyzer; on the complex query, one memory hit saved 1 search and 3 summarization calls.
- **Score differences cannot be attributed to the fixes**:
  - After the fix, the first two questions passed in round 1, so the fixed code never ran.
  - On the second question both versions used identical search results, yet their round-1 reports scored 5.3 and 7.2, i.e. single-run noise is about ±2 points.
  - Only the complex query went through several rounds, and it was run once.

### Known limitations

- **NLI is English-only**: the test set is entirely English, and `nli-deberta-v3-base` only supports English; if the Searcher produces Chinese summaries, cross-verification largely stops working, which this test set cannot detect.
- **The NLI test set is easy**: model confidence is ≥ 0.984 on every pair, so ambiguous low-confidence cases are not covered.
- **Scores are subject to LLM variance**: both the Critic and the judge are LLMs using the same model as the Writer; each configuration ran once and single-run noise is about ±2 points, so the score differences above are not statistically meaningful — multiple runs per question are needed.
- **Judging only sees the first 3000 characters**: the Critic and `judge.py` both truncate the report, so the rest is not scored.
- **Complex queries do not converge**: the Critic repeatedly flags the same gaps (e.g. CoVe, Reflexion, RLHF/DPO) and search fails to find sources for them; this is unrelated to the two fixes above.

## Quick start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/DeepResearch-Agent.git
cd DeepResearch-Agent

# 2. Install
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# edit .env and fill in the DeepSeek and Tavily API keys

# 4. Run
python main.py "Compare LangGraph and CrewAI for multi-agent development"
```

## Tech stack

| Component | Choice |
|-----------|--------|
| Agent orchestration | LangGraph (StateGraph) |
| LLM | DeepSeek API / OpenAI API (configurable) |
| Web search | Tavily API |
| NLI model | cross-encoder/nli-deberta-v3-base |
| Frontend | Streamlit (optional) |

## Project structure

```
DeepResearch-Agent/
├── main.py                  # CLI entry point
├── config.py                # Global configuration
├── agents/
│   ├── planner.py           # Simulate-Before-Act planning
│   ├── searcher.py          # Multi-source search + compression
│   ├── analyzer.py          # NLI cross-verification
│   ├── writer.py            # Cited report generation
│   └── critic.py            # LLM-as-a-Judge
├── core/
│   ├── state.py             # LangGraph State definition
│   ├── graph.py             # StateGraph construction
│   ├── llm.py               # LLM call helpers
│   ├── memory.py            # File-as-Memory
│   └── nli_verifier.py      # NLI contradiction detection
├── tools/
│   └── search.py            # Search API wrappers
├── prompts/                 # Agent prompts
├── evaluation/
│   ├── judge.py             # LLM-as-a-Judge report scoring
│   ├── eval_nli.py          # NLI evaluation (before vs after)
│   └── nli_testset.json     # 44-pair NLI test set
└── examples/                # Example queries and reports
```

## References

- [DeepHalluBench](https://arxiv.org/abs/2601.22984) — PIES taxonomy for Deep Research Agent hallucinations
- [Simulate Before Act](https://arxiv.org/html/2508.12752v1) — simulation-based agent planning
- [DeerFlow](https://github.com/bytedance/deer-flow) — ByteDance's multi-agent research framework
- [Deep Research Agents: A Systematic Examination](https://arxiv.org/abs/2506.18096) — DR agent survey

## License

MIT
