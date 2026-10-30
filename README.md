# 🔬 DeepResearch-Agent MultiAgent深度研究系统

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
| **搜索器 (Searcher)** | 多源并行搜索 (Web + ArXiv + Wikipedia) | Map-phase 压缩 |
| **分析器 (Analyzer)** | 交叉验证多源信息，检测矛盾 | NLI 矛盾检测 |
| **撰写器 (Writer)** | 生成带引用的研究报告 | Claim-level 引用追踪 |
| **评审器 (Critic)** | 评估报告质量，决定通过/迭代 | LLM-as-a-Judge |

### 核心创新点

**1. Simulate-Before-Act 搜索规划**

规划器不直接执行搜索，而是先生成多个候选策略，用轻量 LLM 模拟每个策略的预期覆盖度，选择最优方案再执行。失败的策略在下一轮迭代中被显式排除。

> *参考论文: Simulate Before Act (Gu et al., 2025)*

**2. Cross-Source NLI Verification 多源冲突消解**

分析器使用 NLI 模型 (`cross-encoder/nli-deberta-v3-base`) 检测不同来源间的矛盾。报告中每条声明标注置信度：
- ✅ 多源一致（高可信）
- ⚠️ 来源有争议（标注各方立场）
- ❓ 仅单一来源（待验证）

> *解决问题: PIES 分类法中的 Explicit Summarization 幻觉 (DeepHalluBench, 2026.01)*

### Context 管理（解决 Token 爆炸）

| 策略 | 做法 |
|------|------|
| Agent 间只传压缩摘要 | State 中只保存每条结果的摘要和原子声明，不保存原文 |
| Map-Reduce 检索处理 | 每条搜索结果先单独压缩（Map），再由分析器统一综合（Reduce），综合时摘要截断至 3000 字符 |
| File-as-Memory 外挂存储 | 原始搜索结果写入 `outputs/memory/`，不进入 State |
| Progressive Summarization | 撰写器每轮基于最新分析从头撰写，不累积历史草稿 |

## 实验结果

4 个不同难度的查询，各运行一次（英文报告）：

| 查询任务 | 难度 | 迭代次数 | 最终得分 | 耗时 | ✅ 高可信 | ⚠️ 争议 | ❓ 待验证 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MCP 是什么 | 简单 | 2 | 7.4/10 | 432s | 5 | 0 | 19 |
| LangGraph vs CrewAI | 中等 | 3 | 7.0/10 | 724s | 4 | 0 | 19 |
| RAG vs Fine-tuning | 中等 | 2 | 6.85/10 | 411s | 1 | 0 | 23 |
| LLM Agent 幻觉缓解 | 复杂 | 4(max) | 5.4/10 | 819s | 0 | 0 | 22 |

- 得分为系统内评审器（LLM-as-a-Judge，与撰写器使用同一模型）的自评分，范围 5.4–7.4；复杂查询达到迭代上限仍未通过阈值（6.0）
- NLI 统计为最后一轮的交叉验证结果；"⚠️ 争议 = 0"只说明未标出矛盾，尚无标注数据评估矛盾检测的准确率

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
├── evaluation/              # 评估脚本
└── examples/                # 示例查询与报告
```

## 参考文献

- [DeepHalluBench](https://arxiv.org/abs/2601.22984) — Deep Research Agent 幻觉评估的 PIES 分类法
- [Simulate Before Act](https://arxiv.org/html/2508.12752v1) — 基于模拟的 Agent 规划策略
- [DeerFlow](https://github.com/bytedance/deer-flow) — 字节跳动多 Agent 研究框架
- [Deep Research Agents: A Systematic Examination](https://arxiv.org/abs/2506.18096) — DR Agent 综述

## License

MIT
