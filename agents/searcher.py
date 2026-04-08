"""
Searcher Agent — Multi-Source Parallel Search with Compression

Executes the selected plan's sub-queries across multiple sources,
then compresses each result into a summary to avoid token explosion.
"""
from core.state import ResearchState, SearchResult
from core.llm import get_light_llm, call_llm_json
from core.memory import MemoryStore
from tools.search import search


SUMMARIZE_PROMPT = """Summarize the following search result into key findings. Be concise but preserve specific facts, numbers, and claims.

Query: {query}
Source: {title}
Content: {content}

Output JSON:
{{
  "summary": "2-3 sentence summary of key findings",
  "key_claims": ["claim 1", "claim 2", ...]
}}
"""


def searcher_node(state: ResearchState) -> dict:
    """
    LangGraph node: Execute search queries and compress results.
    
    Context management:
    - Raw search results are saved to File-as-Memory
    - Only compressed summaries are passed in state
    """
    print("\n" + "=" * 60)
    print("🔍 [搜索器] 正在执行搜索查询...")
    print("=" * 60)
    
    selected_plan = state["selected_plan"]
    if selected_plan is None:
        print("[搜索器] ❌ 错误：未选中任何计划")
        return {"status": "analyzing"}
    
    memory = MemoryStore()
    light_llm = get_light_llm()
    search_results = []
    
    for i, sq in enumerate(selected_plan.sub_queries):
        print(f"  [{sq.source}] 搜索中: {sq.query}")
        
        # Execute search
        raw_results = search(query=sq.query, source=sq.source)
        
        if not raw_results:
            print(f"    → 未找到结果")
            continue
        
        # Save raw results to memory (NOT to state)
        memory.save(f"raw_search_{i}", raw_results)
        
        # Compress each result (Map phase)
        for result in raw_results[:3]:  # Top 3 per query
            try:
                summary_data = call_llm_json(light_llm, SUMMARIZE_PROMPT.format(
                    query=sq.query,
                    title=result.get("title", "Unknown"),
                    content=result.get("content", "")[:800],
                ))
                
                search_results.append(SearchResult(
                    query=sq.query,
                    source_type=sq.source,
                    title=result.get("title", "Unknown"),
                    url=result.get("url", ""),
                    summary=summary_data.get("summary", result.get("content", "")[:200]),
                    key_claims=summary_data.get("key_claims", []),
                ))
            except Exception as e:
                print(f"    → 压缩结果时出错: {e}")
                search_results.append(SearchResult(
                    query=sq.query,
                    source_type=sq.source,
                    title=result.get("title", "Unknown"),
                    url=result.get("url", ""),
                    summary=result.get("content", "")[:300],
                    key_claims=[],
                ))
        
        print(f"    → 找到 {len(raw_results)} 条结果，已压缩前 3 条")
    
    print(f"\n✅ [搜索器] 压缩后结果总数: {len(search_results)}")
    
    return {
        "search_results": search_results,
        "status": "analyzing",
    }
