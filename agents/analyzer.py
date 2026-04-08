"""
Analyzer Agent — Cross-Source Verification

Innovation Point #2:
Uses NLI-based verification to detect contradictions between sources,
then synthesizes a verified analysis with confidence markers.
"""
from core.state import ResearchState, ClaimVerification
from core.llm import get_main_llm, call_llm
from core.nli_verifier import NLIVerifier
from prompts.analyzer_prompt import ANALYZE_AND_SYNTHESIZE_PROMPT


def analyzer_node(state: ResearchState) -> dict:
    """
    LangGraph node: Verify claims across sources and synthesize analysis.
    
    Flow:
    1. Collect claims from all search results (grouped by source)
    2. Run NLI cross-verification to detect contradictions
    3. Synthesize a verified analysis summary for the Writer
    """
    print("\n" + "=" * 60)
    print("🔬 [分析器] 交叉验证 & 信息综合中...")
    print("=" * 60)
    
    search_results = state.get("search_results", [])
    
    if not search_results:
        print("[分析器] ⚠️ 无搜索结果可分析")
        return {
            "verified_claims": [],
            "analysis_summary": "无可用搜索结果。",
            "status": "writing",
        }
    
    # --- Step 1: Group claims by source (only latest 15 results) ---
    recent_results = search_results[-15:]  # Avoid accumulated results from previous iterations
    claims_by_source: dict[str, list[str]] = {}
    for result in recent_results:
        source_key = result.url or result.title
        if result.key_claims:
            claims_by_source[source_key] = result.key_claims
    
    print(f"  分析 {len(recent_results)} 条搜索结果，{len(claims_by_source)} 个有声明的来源")
    
    # --- Step 2: NLI Cross-Source Verification ---
    verified_claims = []
    
    if len(claims_by_source) >= 2:
        print(f"  正在验证 {len(claims_by_source)} 个来源的声明一致性...")
        verifier = NLIVerifier()
        
        try:
            raw_verifications = verifier.cross_verify_claims(claims_by_source)
            
            for v in raw_verifications:
                verified_claims.append(ClaimVerification(
                    claim=v["claim"],
                    confidence=v["confidence"],
                    supporting_sources=v["supporting_sources"],
                    contradicting_sources=v["contradicting_sources"],
                    resolution="",
                ))
            
            # Stats
            high = sum(1 for c in verified_claims if c.confidence == "high")
            disputed = sum(1 for c in verified_claims if c.confidence == "disputed")
            unverified = sum(1 for c in verified_claims if c.confidence == "unverified")
            print(f"  ✅ 高可信度: {high}")
            print(f"  ⚠️ 有争议: {disputed}")
            print(f"  ❓ 待验证: {unverified}")
            
        except Exception as e:
            print(f"  [分析器] NLI 验证失败: {e}，回退到 LLM 综合分析")
    else:
        print("  仅 1 个来源，跳过交叉验证")
    
    # --- Step 3: Synthesize analysis ---
    print("  正在综合分析...")
    main_llm = get_main_llm()
    
    # Build verified claims text
    verified_claims_text = ""
    if verified_claims:
        for c in verified_claims:
            marker = {"high": "✅", "disputed": "⚠️", "unverified": "❓"}.get(c.confidence, "❓")
            verified_claims_text += f"{marker} {c.claim}\n"
            if c.confidence == "disputed":
                verified_claims_text += f"   Contradicted by: {', '.join(c.contradicting_sources[:2])}\n"
    else:
        verified_claims_text = "No cross-verification performed."
    
    # Build search summaries text
    search_summaries_text = ""
    for r in recent_results:
        search_summaries_text += f"\n### {r.title} [{r.source_type}]\nURL: {r.url}\n{r.summary}\n"
    
    analysis = call_llm(main_llm, ANALYZE_AND_SYNTHESIZE_PROMPT.format(
        user_query=state["user_query"],
        verified_claims_text=verified_claims_text,
        search_summaries_text=search_summaries_text[:3000],  # Cap to prevent token explosion
    ))
    
    print(f"✅ [分析器] 分析完成（{len(analysis)} 字符）")
    
    return {
        "verified_claims": verified_claims,
        "analysis_summary": analysis,
        "status": "writing",
    }
