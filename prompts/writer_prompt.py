"""Writer Agent Prompts — Citation-Tracked Report Generation"""

WRITE_REPORT_PROMPT = """你是一个专业的研究报告撰写专家（Research Report Writer）。请基于提供的信息，生成一份结构良好、带有严格引用的中文研究报告。

## 用户查询 (User Query)
{user_query}

## 分析摘要 (Analysis Summary)
{analysis_summary}

## 上一轮评审反馈 (Critic Feedback, 若有)
{critic_feedback}

## 撰写要求 (Instructions)
请撰写一份详尽的中文研究报告，必须严格满足以下条件：
1. 语言要求：必须使用全中文（简体）撰写最终报告。
2. 内容核心：直接且全面地回答用户的查询问题。
3. 结构布局：使用清晰的 Markdown 标题进行分节。
4. 引用规范：为每一个关键事实/声明提供来源引用，格式严格为：[来源: URL]。
5. 置信度标注：在关键声明后标注信息置信度：
   - ✅（多源一致，高可信）
   - ⚠️（来源存在争议，需标明各方立场）
   - ❓（仅单一来源，待验证）
6. 局限性：包含一个“局限性与信息空白 (Limitations & Gaps)”章节，说明哪些问题或细节未能完全查明或验证。
7. 总结：在报告末尾提供精炼的“核心结论 (Key Takeaways)”。

## 格式与约束 (Formatting Rules)
- 仅输出 Markdown 格式。
- 总字数控制在 2000 字以内。
- 【绝对规则】每一条事实性声明都必须有对应的引用。
- 如果提供了“上一轮评审反馈”，请在本次撰写中专门针对缺失或不足的部分进行补充。

## 输出 (Output)
请直接以 Markdown 格式输出完整的中文研究报告，不要包含任何无关的开头语或解释。
"""

REFINE_REPORT_PROMPT = """你正在根据评审人员的反馈，修改和完善一份已有的研究报告。

## 原始报告 (Original Report)
{previous_report}

## 评审反馈 (Critic Feedback)
得分: {score}/10
缺失部分: {missing_aspects}
修改建议: {suggestions}

## 新检索到的信息 (New Information from Additional Search)
{new_analysis}

## 修改要求 (Instructions)
请使用全中文（简体）对原报告进行深度修订，以彻底解决评审反馈中的问题。具体要求：
1. 补充内容：针对反馈中列出的“缺失部分 (missing aspects)”，逐一补充实质性的详细内容。
2. 整合新知：将新检索到的信息有机融入报告，并确保加上正确的引用（格式：[来源: URL]）和置信度标签（✅、⚠️、❓）。
3. 保留精华：【切勿】删除原有报告中已经有充分引用的高质量内容。
4. 保持一致：维持原有报告的结构和 Markdown 格式规范。

## 输出 (Output)
请直接输出完整的、修改后的中文研究报告，不要包含任何无关的开头语或过程解释。
"""