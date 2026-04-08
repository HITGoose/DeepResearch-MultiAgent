"""
Writer Agent — Citation-Tracked Report Generation

Generates a structured research report with claim-level citations
and confidence markers based on the Analyzer's verified output.
"""
from core.state import ResearchState
from core.llm import get_main_llm, call_llm
from prompts.writer_prompt import WRITE_REPORT_PROMPT, REFINE_REPORT_PROMPT


def writer_node(state: ResearchState) -> dict:
    """
    LangGraph node: Generate or refine the research report.
    
    Strategy: Always write from scratch using the latest analysis,
    but incorporate Critic feedback as additional constraints.
    This avoids the "degrading refinement" problem.
    """
    print("\n" + "=" * 60)
    print("✍️  [撰写器] 正在生成研究报告...")
    print("=" * 60)
    
    main_llm = get_main_llm(temperature=0.4, max_tokens=4096)
    iteration = state.get("current_iteration", 0)
    feedback = state.get("critic_feedback")
    
    # Build critic feedback text
    if feedback and iteration > 0:
        critic_feedback_text = (
            f"上一版得分: {feedback.score}/10\n"
            f"缺失内容: {', '.join(feedback.missing_aspects)}\n"
            f"改进建议: {feedback.suggestions}\n"
            f"请务必在本次报告中覆盖以上缺失内容。"
        )
        print(f"  第 {iteration+1} 次撰写，需覆盖: {', '.join(feedback.missing_aspects[:3])}...")
    else:
        critic_feedback_text = "无（首次撰写）"
    
    # Always write from scratch with latest analysis + feedback constraints
    report = call_llm(main_llm, WRITE_REPORT_PROMPT.format(
        user_query=state["user_query"],
        analysis_summary=state.get("analysis_summary", "无分析结果。"),
        critic_feedback=critic_feedback_text,
    ))
    
    # Extract citations
    import re
    citations = []
    for match in re.finditer(r'\[Source:\s*(https?://[^\]]+)\]', report):
        citations.append({"url": match.group(1)})
    
    print(f"✅ [撰写器] 报告已生成（{len(report)} 字符, {len(citations)} 条引用）")
    
    return {
        "report_draft": report,
        "citations": citations,
        "status": "critiquing",
    }
