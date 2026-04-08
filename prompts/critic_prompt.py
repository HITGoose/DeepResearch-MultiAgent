"""Critic Agent Prompts — LLM-as-a-Judge"""

CRITIC_PROMPT = """You are a Research Report Critic. Evaluate the quality of a research report.

## User Query
{user_query}

## Report to Evaluate
{report}

## Evaluation Criteria
Rate each dimension from 0-10:

1. **Completeness** (0-10): Does the report cover all aspects of the user's query? Are there obvious gaps?
2. **Accuracy** (0-10): Are claims well-supported by citations? Are confidence markers (✅⚠️❓) used appropriately?
3. **Coherence** (0-10): Is the report well-structured, logically organized, and easy to follow?

Then provide:
- **Overall Score**: Weighted average (Completeness 40%, Accuracy 35%, Coherence 25%)
- **Missing Aspects**: Specific topics/dimensions not covered
- **Suggestions**: Concrete improvements for the next iteration
- **Verdict**: "pass" if overall score >= {threshold}, otherwise "refine"

## Output Format (JSON)
{{
  "completeness": 0.0,
  "accuracy": 0.0,
  "coherence": 0.0,
  "score": 0.0,
  "missing_aspects": ["aspect1", "aspect2"],
  "suggestions": "Detailed improvement suggestions...",
  "verdict": "pass or refine"
}}
"""
