"""
Example research queries for testing DeepResearch-Agent.

These cover different complexity levels and domains.
"""

EXAMPLES = {
    # Simple: single-topic factual research
    "simple": [
        "What is Model Context Protocol (MCP) and how does it work?",
        "What are the key features of LangGraph for multi-agent orchestration?",
    ],
    
    # Medium: comparison / multi-dimensional analysis
    "medium": [
        "Compare Milvus, Pinecone, Weaviate, and Qdrant vector databases in terms of performance, pricing, and use cases",
        "What are the pros and cons of using DeepSeek vs OpenAI API for building AI agents in 2025?",
        "Compare LangGraph, AutoGen, and CrewAI for multi-agent system development",
    ],
    
    # Complex: multi-hop reasoning / synthesis across domains
    "complex": [
        "Analyze the current state of Agentic RAG systems: what are the main architectural approaches, their trade-offs, and which open-source frameworks are most mature?",
        "What are the key techniques for reducing hallucination in Deep Research Agents, and how do training-based vs prompt-based approaches compare?",
    ],
    
    # Domain-specific
    "domain": [
        "What are the latest advances in reinforcement learning for LLM agent training (2025-2026)?",
        "How are multi-agent systems being applied in software engineering automation?",
    ],
}


if __name__ == "__main__":
    for category, queries in EXAMPLES.items():
        print(f"\n{'=' * 40}")
        print(f"Category: {category}")
        print(f"{'=' * 40}")
        for q in queries:
            print(f"  • {q}")
