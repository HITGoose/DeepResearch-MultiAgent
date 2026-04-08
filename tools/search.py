"""Search tool wrappers: Tavily (web), ArXiv, Wikipedia."""

from config import TAVILY_API_KEY, MAX_SEARCH_RESULTS_PER_QUERY


def search_web(query: str, max_results: int = MAX_SEARCH_RESULTS_PER_QUERY) -> list[dict]:
    """
    Web search via Tavily API.
    Returns: [{"title": str, "url": str, "content": str}]
    """
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query=query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:1000],  # Truncate to save tokens
            }
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return []


def search_arxiv(query: str, max_results: int = 3) -> list[dict]:
    """
    Academic paper search via ArXiv API.
    Returns: [{"title": str, "url": str, "content": str}]
    """
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        results = []
        for paper in client.results(search):
            results.append({
                "title": paper.title,
                "url": paper.entry_id,
                "content": paper.summary[:1000],
            })
        return results
    except Exception as e:
        print(f"[ArXivSearch] Error: {e}")
        return []


def search_wikipedia(query: str) -> list[dict]:
    """
    Wikipedia search for background knowledge.
    Returns: [{"title": str, "url": str, "content": str}]
    """
    try:
        import wikipediaapi
        wiki = wikipediaapi.Wikipedia("DeepResearchAgent/1.0", "en")
        page = wiki.page(query)
        if page.exists():
            return [{
                "title": page.title,
                "url": page.fullurl,
                "content": page.summary[:1000],
            }]
        return []
    except Exception as e:
        print(f"[WikiSearch] Error: {e}")
        return []


def search(query: str, source: str = "web", max_results: int = MAX_SEARCH_RESULTS_PER_QUERY) -> list[dict]:
    """Unified search interface. Routes to the appropriate source."""
    if source == "arxiv":
        return search_arxiv(query, max_results=min(max_results, 3))
    elif source == "wiki":
        return search_wikipedia(query)
    else:
        return search_web(query, max_results=max_results)
