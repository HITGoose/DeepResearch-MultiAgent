"""
DeepResearch-Agent — Streamlit 前端

实时展示多 Agent 协作过程，支持交互式研究查询。
"""
import streamlit as st
import time
import os
import sys
import json
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout

# Page config
st.set_page_config(
    page_title="DeepResearch-Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Custom CSS =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Sans+SC:wght@300;400;600;700&display=swap');

/* Global */
.stApp {
    font-family: 'Noto Sans SC', sans-serif;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0d2137 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(100, 200, 255, 0.15);
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 20% 50%, rgba(56, 189, 248, 0.08) 0%, transparent 70%);
    pointer-events: none;
}
.main-header h1 {
    color: #e2e8f0;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.02em;
}
.main-header p {
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 0;
}

/* Agent status cards */
.agent-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(100, 200, 255, 0.12);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    backdrop-filter: blur(8px);
    transition: border-color 0.3s;
}
.agent-card.active {
    border-color: rgba(56, 189, 248, 0.5);
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.1);
}
.agent-card.done {
    border-color: rgba(74, 222, 128, 0.4);
}
.agent-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    color: #38bdf8;
    margin-bottom: 0.3rem;
}
.agent-status {
    font-size: 0.8rem;
    color: #94a3b8;
}

/* Metric cards */
.metric-row {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
}
.metric-card {
    flex: 1;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(100, 200, 255, 0.1);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e2e8f0;
}
.metric-label {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Log area */
.log-container {
    background: #0a0a1a;
    border: 1px solid rgba(100, 200, 255, 0.08);
    border-radius: 10px;
    padding: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #a0aec0;
    max-height: 400px;
    overflow-y: auto;
    line-height: 1.6;
}

/* Score badge */
.score-badge {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 0.9rem;
}
.score-high { background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
.score-mid { background: rgba(250, 204, 21, 0.15); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.3); }
.score-low { background: rgba(248, 113, 113, 0.15); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>🔬 DeepResearch-Agent</h1>
        <p>多智能体协作深度研究系统 · Simulate-Before-Act · Cross-Source NLI Verification</p>
    </div>
    """, unsafe_allow_html=True)


def render_agent_pipeline(current_agent: str = ""):
    """Render the agent pipeline status in sidebar."""
    agents = [
        ("🧠", "规划器 Planner", "Simulate-Before-Act 搜索规划"),
        ("🔍", "搜索器 Searcher", "多源并行搜索 + 压缩"),
        ("🔬", "分析器 Analyzer", "NLI 交叉验证"),
        ("✍️", "撰写器 Writer", "带引用报告生成"),
        ("🧐", "评审器 Critic", "LLM-as-a-Judge"),
    ]

    st.sidebar.markdown("### 🔄 Agent Pipeline")

    for icon, name, desc in agents:
        short_name = name.split()[0]
        if short_name in current_agent:
            status_class = "active"
            status_text = "⚡ 运行中..."
        elif agents.index((icon, name, desc)) < next(
            (i for i, (_, n, _) in enumerate(agents) if n.split()[0] in current_agent), len(agents)
        ):
            status_class = "done"
            status_text = "✅ 完成"
        else:
            status_class = ""
            status_text = "⏳ 等待中"

        st.sidebar.markdown(f"""
        <div class="agent-card {status_class}">
            <div class="agent-name">{icon} {name}</div>
            <div class="agent-status">{desc}<br/>{status_text}</div>
        </div>
        """, unsafe_allow_html=True)


def render_metrics(iterations: int, score: float, elapsed: float, report_len: int):
    """Render metric cards."""
    score_class = "score-high" if score >= 7 else "score-mid" if score >= 5 else "score-low"

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-value">{iterations}</div>
            <div class="metric-label">迭代次数</div>
        </div>
        <div class="metric-card">
            <div class="metric-value"><span class="score-badge {score_class}">{score:.1f}/10</span></div>
            <div class="metric-label">最终得分</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{elapsed:.0f}s</div>
            <div class="metric-label">总耗时</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report_len:,}</div>
            <div class="metric-label">报告字符数</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def run_research_ui(query: str):
    """Run the research pipeline with real-time UI updates."""
    from core.graph import compile_graph
    from core.state import ResearchState

    # Initialize state
    initial_state: ResearchState = {
        "user_query": query,
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

    # UI placeholders
    status_placeholder = st.empty()
    log_placeholder = st.empty()
    metrics_placeholder = st.empty()
    report_placeholder = st.empty()

    # Capture stdout for live log
    log_lines = []

    class LogCapture:
        def __init__(self):
            self.terminal = sys.stdout

        def write(self, msg):
            if msg.strip():
                log_lines.append(msg.rstrip())
                # Update log display
                log_html = "<br>".join(log_lines[-30:])  # Show last 30 lines
                log_placeholder.markdown(
                    f'<div class="log-container">{log_html}</div>',
                    unsafe_allow_html=True,
                )
            self.terminal.write(msg)

        def flush(self):
            self.terminal.flush()

    # Run
    start_time = time.time()
    old_stdout = sys.stdout
    sys.stdout = LogCapture()

    try:
        status_placeholder.info("🚀 研究进行中... 请耐心等待（预计 3-10 分钟）")
        graph = compile_graph()
        final_state = graph.invoke(initial_state)

        elapsed = time.time() - start_time
        report = final_state.get("report_draft", "")
        feedback = final_state.get("critic_feedback")
        iterations = final_state.get("current_iteration", 0) + 1
        score = feedback.score if feedback else 0

        # Success status
        status_placeholder.success(f"✅ 研究完成！耗时 {elapsed:.0f} 秒，迭代 {iterations} 轮")

        # Metrics
        with metrics_placeholder.container():
            render_metrics(iterations, score, elapsed, len(report))

        # Report
        with report_placeholder.container():
            st.markdown("---")
            st.markdown("### 📄 研究报告")
            st.markdown(report)

            # Download button
            st.download_button(
                label="📥 下载报告 (Markdown)",
                data=report,
                file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
            )

        # NLI stats in sidebar
        verified = final_state.get("verified_claims", [])
        if verified:
            st.sidebar.markdown("### 📊 NLI 验证统计")
            high = sum(1 for c in verified if c.confidence == "high")
            disputed = sum(1 for c in verified if c.confidence == "disputed")
            unverified = sum(1 for c in verified if c.confidence == "unverified")
            st.sidebar.metric("✅ 高可信度", high)
            st.sidebar.metric("⚠️ 有争议", disputed)
            st.sidebar.metric("❓ 待验证", unverified)

    except Exception as e:
        status_placeholder.error(f"❌ 研究出错: {str(e)}")
        st.exception(e)
    finally:
        sys.stdout = old_stdout


# ===== Main App =====
render_header()

# Sidebar config
st.sidebar.markdown("### ⚙️ 配置")
st.sidebar.caption("模型和搜索 API 通过 .env 文件配置")

# Example queries
EXAMPLES = [
    "What is Model Context Protocol (MCP) and how does it work?",
    "Compare LangGraph and CrewAI for multi-agent development",
    "Compare RAG and fine-tuning for adapting LLMs to domain-specific tasks",
    "What are the key techniques for reducing hallucination in LLM-based agents?",
]

st.sidebar.markdown("### 📝 示例查询")
selected_example = st.sidebar.selectbox(
    "选择一个示例：",
    ["自定义输入..."] + EXAMPLES,
)

# Main input area
col1, col2 = st.columns([5, 1])
with col1:
    if selected_example == "自定义输入...":
        query = st.text_input(
            "🔍 输入你的研究问题",
            placeholder="例如：Compare LangGraph and CrewAI for multi-agent development",
        )
    else:
        query = st.text_input("🔍 输入你的研究问题", value=selected_example)

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_button = st.button("🚀 开始研究", type="primary", use_container_width=True)

# Pipeline visualization in sidebar
render_agent_pipeline("")

# Run research
if run_button and query:
    run_research_ui(query)
elif run_button and not query:
    st.warning("请输入一个研究问题。")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#64748b; font-size:0.8rem;'>"
    "DeepResearch-Agent · Simulate-Before-Act · Cross-Source NLI Verification · LLM-as-a-Judge"
    "</div>",
    unsafe_allow_html=True,
)
