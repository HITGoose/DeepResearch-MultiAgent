# 🔬 DeepResearch-Agent MultiAgent深度研究系统

中文 | [English](README_EN.md)

基于 LangGraph 的多 Agent 协作深度研究系统，通过 **Simulate-Before-Act** 搜索规划和 **Cross-Source NLI Verification** 机制，生成带引用的高质量研究报告。

## 架构

```
User Query → 规划器 → 搜索器 → 分析器 → 撰写器 → 评审器
               ↑                                      │
               └──── 迭代改进（得分 < 阈值时触发）────┘
```

### Agents

| Agent | 职责 | 核心技术 |
|-------|------|----------|
| **规划器 (Planner)** | 分解问题，生成并评估候选搜索计划 | Simulate-Before-Act |
| **搜索器 (Searcher)** | 多源搜索 (Web + ArXiv + Wikipedia)，按子查询依次执行 | Map-phase 压缩 |
| **分析器 (Analyzer)** | 交叉验证多源信息，检测矛盾 | NLI 矛盾检测 |
| **撰写器 (Writer)** | 生成带引用的研究报告 | Claim-level 引用追踪 |
| **评审器 (Critic)** | 评估报告质量，决定通过/迭代 | LLM-as-a-Judge |

### 核心创新点

**1. Simulate-Before-Act 搜索规划**

规划器不直接执行搜索，而是先生成多个候选策略，用轻量 LLM 模拟每个策略的预期覆盖度，选择最优方案再执行。失败的策略在下一轮迭代中被显式排除。

> *参考论文: Simulate Before Act (Gu et al., 2025)*

**2. Cross-Source NLI Verification 多源冲突消解**

分析器使用 NLI 模型 (`cross-encoder/nli-deberta-v3-base`) 检测不同来源间的矛盾：把每条声明和其他来源的摘要逐一比较，模型输出经 softmax 转成概率后，支持概率 > 0.75 记为支持、矛盾概率 > 0.9 记为矛盾。报告中每条声明标注置信度：
- ✅ 多源一致（高可信）
- ⚠️ 来源有争议（标注各方立场）
- ❓ 仅单一来源（待验证）

> *解决问题: PIES 分类法中的 Explicit Summarization 幻觉 (DeepHalluBench, 2026.01)*

### Context 管理（解决 Token 爆炸）

| 策略 | 做法 |
|------|------|
| Agent 间只传压缩摘要 | State 中只保存每条结果的摘要和原子声明，不保存原文 |
| Map-Reduce 检索处理 | 每条搜索结果先单独压缩（Map），再由分析器统一综合（Reduce），综合时摘要截断至 3000 字符 |
| 每轮清空搜索结果 | `search_results` 使用自定义 reducer：节点返回 `None` 时清空，State 中只保留本轮结果 |
| File-as-Memory 外挂存储 | 一次研究的所有轮次共用 `outputs/memory/<run_id>/`：原文和压缩摘要按子查询存储，后续轮次遇到相同子查询直接读回；每轮的分析和来源也存入其中，下一轮读回 |
| Progressive Summarization | 撰写器每轮从头撰写，不累积历史草稿；分析器会读回上一轮的分析并与本轮结果合并，避免补上缺口的同时丢掉已覆盖的内容 |

## 实验结果

### 早期运行记录（修复 NLI 和上下文管理之前的版本）

4 个不同难度的查询，各运行一次（英文报告）：

| 查询任务 | 难度 | 迭代次数 | 最终得分 | 耗时 | ✅ 高可信 | ⚠️ 争议 | ❓ 待验证 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MCP 是什么 | 简单 | 2 | 7.4/10 | 432s | 5 | 0 | 19 |
| LangGraph vs CrewAI | 中等 | 3 | 7.0/10 | 724s | 4 | 0 | 19 |
| RAG vs Fine-tuning | 中等 | 2 | 6.85/10 | 411s | 1 | 0 | 23 |
| LLM Agent 幻觉缓解 | 复杂 | 4(max) | 5.4/10 | 819s | 0 | 0 | 22 |

- 得分为系统内评审器（LLM-as-a-Judge，与撰写器使用同一模型）的自评分，范围 5.4–7.4；复杂查询达到迭代上限仍未通过阈值（6.0）
- NLI 统计为最后一轮的交叉验证结果；"⚠️ 争议 = 0"只说明未标出矛盾

### NLI 修复与测评

**问题**：`CrossEncoder.predict` 对多分类模型默认返回 logits（如 `[6.83, -3.73, -2.82]`），原代码直接拿 logits 和概率阈值 0.75 / 0.9 比较，阈值实际不起作用，等于只取最高类。修复后先做 softmax，标签顺序从模型的 `id2label` 读取。

**测试集**：`evaluation/nli_testset.json`，44 对（支持 15 / 矛盾 15 / 中立 14），已人工核对标签。前提是模拟搜索器生成的来源摘要，假设是另一来源的原子声明，主题取自项目实际运行过的研究问题（RAG vs 微调、幻觉、LangGraph/AutoGen、MCP、RLHF/DPO、LoRA 等）。判定规则与 `cross_verify_claims` 一致。

| 配置 | 准确率 | 矛盾召回 | 矛盾精确率 | 支持召回 | 中立召回 | 误判为矛盾 |
|---|---|---|---|---|---|---|
| 修复前（logits + 阈值） | 0.977 (43/44) | 1.000 | 1.000 | 0.933 | 1.000 | 0 |
| 修复后（概率 + 阈值） | 0.977 (43/44) | 1.000 | 1.000 | 0.933 | 1.000 | 0 |

- **修复前后在这个测试集上没有差别**：模型对全部 44 对都很确定（最高类概率最低 0.984），阈值从未起作用。修复保证的是模型没把握时（如最高类只有 0.6）会正确地判为中立，这类情况本测试集没有覆盖。
- 唯一错误是 #7：原文 "reduced hallucination rates by about 40%"，声明换成 "lowered"，模型以 0.999 判为中立。
- 运行：`python -m evaluation.eval_nli`

### 上下文管理修复前后对比

**问题**：
1. `search_results` 用 `operator.add` reducer，`prepare_iteration` 返回 `[]` 只是"旧值 + []"，结果跨轮累积；
2. File-as-Memory 只写不读，且每轮新建目录。

修复方式见上文 Context 管理表。

**对比方法**：3 个固定问题，修复前后各运行 1 次（DeepSeek `deepseek-chat` + Tavily）。两个版本遇到相同查询时使用相同的搜索结果（缓存）。token 为该轮所有 LLM 调用的输入 + 输出。"终评分"是系统内评审器的最终分，"独立评审"是 `evaluation/judge.py` 的总分（同为 DeepSeek）。

| 问题 | 版本 | 轮数 | 每轮 token | 总 token | State 中结果条数 | 终评分 | 独立评审 |
|---|---|---|---|---|---|---|---|
| MCP 是什么 | 修复前 | 1 | 18.3k | 18.3k | 15 | 7.1 | 7 |
| | 修复后 | 1 | 18.8k | 18.8k | 15 | 6.6 | 7 |
| LangGraph vs AutoGen vs CrewAI | 修复前 | 2 | 19.1k / 20.5k | 39.5k | 15 → 30 | 6.35 | 5 |
| | 修复后 | 1 | 18.6k | 18.6k | 15 | 7.2 | 7 |
| 幻觉缓解（训练 vs 提示） | 修复前 | 4（未通过） | 18.0k / 20.6k / 19.5k / 22.5k | 80.5k | 15 → 30 → 45 → 63 | 5.9 | 5 |
| | 修复后 | 4（第 4 轮通过） | 19.3k / 21.6k / 19.0k / 21.4k | 81.4k | 15 / 15 / 15 / 15 | 6.2 | 6 |

- **确认的效果**：State 中的搜索结果不再跨轮累积（复杂查询 63 条 → 每轮 15 条）。
- **每轮 token 基本不变**：分析器和撰写器原本就只截取最近 15 / 20 条交给 LLM，累积的结果留在 State 里，并没有全部发给模型；累积的实际危害是撰写器的来源池混入上一轮结果。读回上一轮分析使分析器每轮多用约 700 token；复杂查询中命中 1 次记忆，省掉 1 次搜索和 3 次摘要调用。
- **评分差异不能归因于修复**：
  - 前两个问题修复后都在第 1 轮通过，修复的代码没有执行到。
  - 第二个问题两个版本使用相同的搜索结果，第 1 轮报告仍分别得到 5.3 和 7.2 分，单次运行的评分波动约 ±2 分。
  - 只有复杂查询走完了多轮，但样本只有 1 次。

### 已知局限

- **NLI 只覆盖英文**：测试集全部是英文，NLI 模型 `nli-deberta-v3-base` 也只支持英文；如果搜索器生成中文摘要，交叉验证基本失效，本测试集测不出这一点。
- **NLI 测试集偏简单**：模型置信度全部 ≥ 0.984，没有覆盖模型没把握的模糊情况。
- **评分受 LLM 波动影响**：评审器和独立评审都是 LLM，且与撰写器使用同一模型；每个配置只运行 1 次，单次波动约 ±2 分，上表的评分差异不具统计意义，需要每个问题多次运行取平均。
- **评审只看报告前 3000 字符**：评审器和 `judge.py` 都会截断报告，后半部分内容不参与评分。
- **复杂查询不收敛**：评审器多轮反复指出相同缺口（如 CoVe、Reflexion、RLHF/DPO），搜索未能找到相关来源，这与上述两个修复无关。

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/DeepResearch-Agent.git
cd DeepResearch-Agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DeepSeek 和 Tavily 的 API Key

# 4. 运行
python main.py "Compare LangGraph and CrewAI for multi-agent development"
```

## 技术栈

| 组件 | 选型 |
|------|------|
| Agent 编排 | LangGraph (StateGraph) |
| LLM | DeepSeek API / OpenAI API（可配置） |
| Web 搜索 | Tavily API |
| NLI 模型 | cross-encoder/nli-deberta-v3-base |
| 前端 | Streamlit（可选） |

## 项目结构

```
DeepResearch-Agent/
├── main.py                  # CLI 入口
├── config.py                # 全局配置
├── agents/
│   ├── planner.py           # Simulate-Before-Act 规划
│   ├── searcher.py          # 多源搜索 + 压缩
│   ├── analyzer.py          # NLI 交叉验证
│   ├── writer.py            # 带引用的报告生成
│   └── critic.py            # LLM-as-a-Judge 评审
├── core/
│   ├── state.py             # LangGraph State 定义
│   ├── graph.py             # StateGraph 构建
│   ├── llm.py               # LLM 调用工具
│   ├── memory.py            # File-as-Memory
│   └── nli_verifier.py      # NLI 矛盾检测
├── tools/
│   └── search.py            # 搜索 API 封装
├── prompts/                 # Agent Prompts
├── evaluation/
│   ├── judge.py             # LLM-as-a-Judge 报告评分
│   ├── eval_nli.py          # NLI 测评（修复前后对比）
│   └── nli_testset.json     # 44 对 NLI 测试集
└── examples/                # 示例查询与报告
```

## 参考文献

- [DeepHalluBench](https://arxiv.org/abs/2601.22984) — Deep Research Agent 幻觉评估的 PIES 分类法
- [Simulate Before Act](https://arxiv.org/html/2508.12752v1) — 基于模拟的 Agent 规划策略
- [DeerFlow](https://github.com/bytedance/deer-flow) — 字节跳动多 Agent 研究框架
- [Deep Research Agents: A Systematic Examination](https://arxiv.org/abs/2506.18096) — DR Agent 综述

## License

MIT
