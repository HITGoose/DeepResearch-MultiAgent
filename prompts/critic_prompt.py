"""Critic Agent Prompts — LLM-as-a-Judge"""

CRITIC_PROMPT = """你是一个严谨的研究报告评审专家（Research Report Critic）。请评估以下研究报告的质量。

## 用户查询 (User Query)
{user_query}

## 待评估报告 (Report to Evaluate)
{report}

## 评估标准 (Evaluation Criteria)
请为以下各个维度打分（0-10分）：

1. **完整性 (Completeness)** (0-10): 报告是否涵盖了用户查询的所有核心方面？是否存在明显的逻辑断层或信息遗漏？
2. **准确性 (Accuracy)** (0-10): 报告中的事实性声明是否有充分的来源引用支持？置信度标记（✅⚠️❓）的使用是否准确恰当？
3. **连贯性 (Coherence)** (0-10): 报告的结构是否清晰，逻辑是否有条理，语言表达是否流畅易读？

然后提供以下综合评估结果：
- **总分 (score)**: 加权平均分计算（完整性 40%，准确性 35%，连贯性 25%）。保留一位小数。
- **缺失部分 (missing_aspects)**: 列出报告中未能涵盖或探讨不够深入的具体主题与维度。
- **修改建议 (suggestions)**: 为下一轮修订提供具体、可操作的改进建议。
- **最终裁决 (verdict)**: 如果总分 >= {threshold}，则输出 "pass"；否则输出 "refine"。

## 输出格式 (Output Format)
【绝对要求】必须仅输出合法的 JSON 格式，不要包含任何 Markdown 标记 (如 ```json) 或其他多余文本，确保能被直接解析。使用以下结构：

{{
  "completeness": 0.0,
  "accuracy": 0.0,
  "coherence": 0.0,
  "score": 0.0,
  "missing_aspects": ["缺失的维度1", "缺失的维度2"],
  "suggestions": "详细的修改与改进建议...",
  "verdict": "pass 或 refine"
}}
"""