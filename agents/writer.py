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
    Passes actual source URLs to prevent URL fabrication.
    """
    print("\n" + "=" * 60)
    print("✍️  [撰写器] 正在生成研究报告...")
    print("=" * 60)
    
    main_llm = get_main_llm(temperature=0.4, max_tokens=8192)
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
    
    # Build actual source pool from search results
    # Build actual source pool from search results
    search_results = state.get("search_results", [])
    
    # 1. 确保取最新的结果，防止 Token 爆炸
    recent_results = search_results[-20:] 
    
    source_pool_lines = []
    seen_urls = set()
    
    # 2. ✅ 将这里改为遍历 recent_results！
    for r in recent_results: 
        if r.url and r.url not in seen_urls:
            seen_urls.add(r.url)
            source_pool_lines.append(f"- [{r.title}]: {r.url}")
            
    source_pool_text = "\n".join(source_pool_lines) if source_pool_lines else "无可用来源"
    
    print(f"  可用来源: {len(seen_urls)} 个")
    
    # Always write from scratch with latest analysis + feedback + source pool
    report = call_llm(main_llm, WRITE_REPORT_PROMPT.format(
        user_query=state["user_query"],
        analysis_summary=state.get("analysis_summary", "无分析结果。"),
        critic_feedback=critic_feedback_text,
        source_pool=source_pool_text,
    ))
    
    # Extract citations
    import re
    citations = []
    for block_match in re.finditer(r'\[(?:来源|Source):\s*([^\]]+)\]', report, re.IGNORECASE):
        urls_text = block_match.group(1)
        
        # 步骤 B：在块内部精准捕获合法的 URL
        # [^\s,，。；;]+ 表示：只要遇到空格、中英文逗号、句号、分号，URL 就立刻截断
        for url_match in re.finditer(r'https?://[^\s,，。；;]+', urls_text):
            # 去除末尾可能因为排版粘连的冗余符号（如 _ 或 .）
            clean_url = url_match.group(0).rstrip('._')
            
            # 去重并加入列表
            if {"url": clean_url} not in citations:
                citations.append({"url": clean_url})


    # ==========================================
    # 2. 完美修复报告中的 Markdown 渲染
    # ==========================================
    def format_markdown_links(match):
        raw_text = match.group(1)
        # 同样使用严格的正则提取该区块内的所有有效 URL
        urls = re.findall(r'https?://[^\s,，。；;]+', raw_text)
        
        if not urls:
            return match.group(0) # 没找到有效 URL，保持原样返回
        
        # 将多个 URL 规范化渲染为 [[来源](url1)] [[来源](url2)] 的严谨格式
        markdown_links = [f"[[来源]({u.rstrip('._')})]" for u in urls]
        return " ".join(markdown_links)

    # 执行替换：用自定义函数处理每一个匹配到的 [来源: ...] 区块
    
    report = re.sub(r'\[(?:来源|Source):\s*([^\]]+)\]', format_markdown_links, report, flags=re.IGNORECASE)
    
    # 打印成功日志（必须放在 return 前面）
    print(f"✅ [撰写器] 报告已生成（{len(report)} 字符, {len(citations)} 条引用）")
    
    # 最终的 Return：完美契合你的 LangGraph State
    return {
        "report": report,              # 兼容某些可能直接读 report 的逻辑
        "report_draft": report,        # 真正传给 Critic 的报告草稿
        "citations": citations,        # 提取出的引用列表
        "status": "critiquing",        # 推动状态机进入评审环节
    }