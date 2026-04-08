"""
Evaluation — Report quality metrics and batch testing.

Provides utilities for:
1. Single report evaluation via LLM-as-a-Judge
2. Batch evaluation across example queries
3. Comparison between iterations (did refinement help?)
"""
import json
from core.llm import get_main_llm, call_llm_json


EVAL_PROMPT = """Evaluate this research report on a scale of 0-10 for each dimension.

## Query
{query}

## Report
{report}

## Dimensions
1. **Relevance**: Does it answer the query directly?
2. **Completeness**: Are all aspects covered?
3. **Accuracy**: Are claims well-supported with citations?
4. **Clarity**: Is it well-written and organized?
5. **Citation Quality**: Are sources credible and properly attributed?

Output JSON:
{{
  "relevance": 0-10,
  "completeness": 0-10,
  "accuracy": 0-10,
  "clarity": 0-10,
  "citation_quality": 0-10,
  "overall": 0-10,
  "comments": "brief assessment"
}}
"""


def evaluate_report(query: str, report: str) -> dict:
    """Evaluate a single report using LLM-as-a-Judge."""
    llm = get_main_llm(temperature=0.1)
    result = call_llm_json(llm, EVAL_PROMPT.format(
        query=query,
        report=report[:3000],
    ))
    return result


def batch_evaluate(results: list[dict]) -> dict:
    """
    Evaluate multiple query-report pairs.
    
    Args:
        results: [{"query": str, "report": str}, ...]
    
    Returns:
        {"individual": [...], "average": {...}}
    """
    evaluations = []
    for item in results:
        eval_result = evaluate_report(item["query"], item["report"])
        eval_result["query"] = item["query"]
        evaluations.append(eval_result)
    
    # Compute averages
    metrics = ["relevance", "completeness", "accuracy", "clarity", "citation_quality", "overall"]
    averages = {}
    for m in metrics:
        values = [e.get(m, 0) for e in evaluations if isinstance(e.get(m), (int, float))]
        averages[m] = sum(values) / len(values) if values else 0
    
    return {"individual": evaluations, "average": averages}
