"""
LangGraph StateGraph — Multi-Agent Orchestration

This is the core workflow graph that connects all agents:

    Planner → Searcher → Analyzer → Writer → Critic
                                                 │
                                          pass ──┴── refine
                                           │            │
                                         Done    Back to Planner
                                                (with feedback)
"""
from langgraph.graph import StateGraph, END

from core.state import ResearchState
from agents.planner import planner_node
from agents.searcher import searcher_node
from agents.analyzer import analyzer_node
from agents.writer import writer_node
from agents.critic import critic_node
from config import MAX_ITERATIONS


def should_continue(state: ResearchState) -> str:
    """
    Conditional edge after Critic: decide whether to iterate or finish.
    
    Returns:
    - "done": report passes quality threshold
    - "iterate": needs refinement (back to Planner with feedback)
    """
    feedback = state.get("critic_feedback")
    iteration = state.get("current_iteration", 0)
    
    # Force done if max iterations reached
    if iteration >= MAX_ITERATIONS:
        print(f"\n⚠️ 已达最大迭代次数（{MAX_ITERATIONS}），最终定稿。")
        return "done"
    
    # Check verdict
    if feedback and feedback.verdict == "pass":
        print(f"\n🎉 报告通过质量检查！（得分: {feedback.score}/10）")
        return "done"
    
    print(f"\n🔄 第 {iteration + 1} 轮迭代：报告需要改进。")
    return "iterate"


def prepare_iteration(state: ResearchState) -> dict:
    """
    Node between Critic → Planner on refinement loops.
    Updates iteration counter and records failed strategies.
    """
    iteration = state.get("current_iteration", 0)
    failed = list(state.get("failed_strategies", []))
    
    # Record the failed plan's strategy so Planner avoids it next time
    selected_plan = state.get("selected_plan")
    if selected_plan:
        failed.append(selected_plan.strategy)
    
    # Clear search results to avoid accumulation
    # 必须返回 None：reducer 是追加型的，返回 [] 只是"旧值 + []"，清不掉
    # 上一轮的结果已经存进 File-as-Memory，需要时由 Analyzer / Writer 读回
    return {
        "current_iteration": iteration + 1,
        "failed_strategies": failed,
        "search_results": None,  # Reset for fresh search
        "status": "planning",
    }


def finalize(state: ResearchState) -> dict:
    """Final node: mark status as done and save report."""
    import os
    from config import OUTPUT_DIR
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    report = state.get("report_draft", "No report generated.")
    
    # Save report to file
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(OUTPUT_DIR, f"report_{timestamp}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n{'=' * 60}")
    print(f"📄 报告已保存至: {filepath}")
    print(f"{'=' * 60}")
    
    return {"status": "done"}


def build_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for the DeepResearch workflow.
    
    Graph structure:
        planner → searcher → analyzer → writer → critic
                                                    │
                                            ┌───────┴───────┐
                                          done          iterate
                                            │               │
                                        finalize    prepare_iteration
                                            │               │
                                           END          → planner
    """
    graph = StateGraph(ResearchState)
    
    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("prepare_iteration", prepare_iteration)
    graph.add_node("finalize", finalize)
    
    # Linear flow: planner → searcher → analyzer → writer → critic
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "analyzer")
    graph.add_edge("analyzer", "writer")
    graph.add_edge("writer", "critic")
    
    # Conditional: critic → done or iterate
    graph.add_conditional_edges(
        "critic",
        should_continue,
        {
            "done": "finalize",
            "iterate": "prepare_iteration",
        }
    )
    
    # Iteration loop back to planner
    graph.add_edge("prepare_iteration", "planner")
    
    # Finalize → END
    graph.add_edge("finalize", END)
    
    # Entry point
    graph.set_entry_point("planner")
    
    return graph


def compile_graph():
    """Build and compile the graph, ready to invoke."""
    graph = build_graph()
    return graph.compile()
