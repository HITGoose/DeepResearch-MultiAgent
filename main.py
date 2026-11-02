"""
DeepResearch-Agent — Main Entry Point

A multi-agent deep research system with:
- Simulate-Before-Act search planning
- Cross-Source NLI verification
- LLM-as-a-Judge iterative refinement
"""
import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from core.graph import compile_graph
from core.state import ResearchState
from core.memory import new_run_id

console = Console()


def run_research(query: str, verbose: bool = True) -> str:
    """
    Run a full deep research workflow for the given query.
    
    Args:
        query: The research question to investigate
        verbose: Whether to print progress
    
    Returns:
        The final research report as a string
    """
    console.print(Panel(
        f"[bold cyan]{query}[/bold cyan]",
        title="🔬 DeepResearch-Agent",
        subtitle="多智能体深度研究系统",
    ))
    
    # Initialize state
    initial_state: ResearchState = {
        "user_query": query,
        "run_id": new_run_id(),
        "candidate_plans": [],
        "selected_plan": None,
        "search_results": [],
        "verified_claims": [],
        "analysis_summary": "",
        "report_draft": "",
        "citations": [],
        "critic_feedback": None,
        "current_iteration": 0,
        "failed_strategies": [],
        "status": "planning",
    }
    
    # Compile and run graph
    start_time = time.time()
    graph = compile_graph()
    
    try:
        final_state = graph.invoke(initial_state)
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断了研究。[/yellow]")
        return ""
    except Exception as e:
        console.print(f"\n[red]研究过程出错: {e}[/red]")
        raise
    
    elapsed = time.time() - start_time
    
    # Display results
    report = final_state.get("report_draft", "未生成报告。")
    feedback = final_state.get("critic_feedback")
    iterations = final_state.get("current_iteration", 0)
    
    console.print(f"\n{'=' * 60}")
    console.print(f"[bold green]✅ 研究完成[/bold green]")
    console.print(f"  耗时: {elapsed:.1f}秒")
    console.print(f"  迭代次数: {iterations + 1}")
    if feedback:
        console.print(f"  最终得分: {feedback.score}/10")
    console.print(f"  报告长度: {len(report)} 字符")
    console.print(f"{'=' * 60}\n")
    
    # Print report
    console.print(Panel(Markdown(report), title="📄 研究报告"))
    
    return report


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        console.print("[bold]DeepResearch-Agent[/bold] — 多智能体深度研究系统\n")
        console.print("请输入你的研究问题（输入 'quit' 退出）:\n")
        query = input("🔍 问题: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            return
    
    if not query:
        console.print("[red]请提供一个研究问题。[/red]")
        return
    
    run_research(query)


if __name__ == "__main__":
    main()
