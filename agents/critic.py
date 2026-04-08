"""
Critic Agent — LLM-as-a-Judge

Evaluates the report quality and decides whether to pass or
send back for refinement. Links to SecuRAG's LLM-as-a-Judge technique.
"""
from core.state import ResearchState, CriticFeedback
from core.llm import get_main_llm, call_llm_json
from prompts.critic_prompt import CRITIC_PROMPT
from config import CRITIC_SCORE_THRESHOLD


def critic_node(state: ResearchState) -> dict:
    """
    LangGraph node: Evaluate report and decide pass/refine.
    """
    print("\n" + "=" * 60)
    print("🧐 [评审器] 正在评估报告质量...")
    print("=" * 60)
    
    report = state.get("report_draft", "")
    if not report:
        print("[评审器] ⚠️ 无报告可评审")
        return {
            "critic_feedback": CriticFeedback(
                score=0, completeness=0, accuracy=0, coherence=0,
                missing_aspects=["未生成报告"],
                suggestions="请先生成报告。",
                verdict="refine",
            ),
            "status": "planning",
        }
    
    main_llm = get_main_llm(temperature=0.1)  # Low temp for consistent evaluation
    
    result = call_llm_json(main_llm, CRITIC_PROMPT.format(
        user_query=state["user_query"],
        report=report[:3000],  # Truncate to manage tokens
        threshold=CRITIC_SCORE_THRESHOLD,
    ))
    
    feedback = CriticFeedback(
        score=float(result.get("score", 5.0)),
        completeness=float(result.get("completeness", 5.0)),
        accuracy=float(result.get("accuracy", 5.0)),
        coherence=float(result.get("coherence", 5.0)),
        missing_aspects=result.get("missing_aspects", []),
        suggestions=result.get("suggestions", ""),
        verdict=result.get("verdict", "pass"),
    )
    
    print(f"  总分: {feedback.score}/10")
    print(f"  完整性: {feedback.completeness}/10")
    print(f"  准确性: {feedback.accuracy}/10")
    print(f"  连贯性: {feedback.coherence}/10")
    print(f"  判定: {feedback.verdict.upper()}")
    
    if feedback.missing_aspects:
        print(f"  缺失内容: {', '.join(feedback.missing_aspects)}")
    
    return {
        "critic_feedback": feedback,
    }
