"""
DeepResearch-Agent — Streamlit 前端终极优化版
包含：居中布局、思考动画、长链接换行修复、isatty报错修复、思考过程历史留存
"""
import streamlit as st
import time
import sys
import traceback
from datetime import datetime

st.set_page_config(
    page_title="DeepResearch-Agent",
    page_icon="🔬",
    layout="centered", 
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
.stApp { font-family: 'Noto Sans SC', sans-serif; background: #f7f7f8; }
#MainMenu, footer, header { visibility: hidden; }

.welcome { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:55vh; text-align:center; }
.welcome-icon { font-size:3.2rem; margin-bottom:0.8rem; }
.welcome-title { font-size:1.9rem; font-weight:700; color:#1a1a1a; }
.welcome-sub { font-size:0.9rem; color:#9ca3af; margin-top:0.4rem; line-height:1.6; }
.welcome-tags { display:flex; gap:8px; margin-top:1.2rem; flex-wrap:wrap; justify-content:center; }
.wtag { padding:5px 13px; background:#fff; border:1px solid #e5e7eb; border-radius:20px; font-size:0.76rem; color:#6b7280; }

.u-msg { 
    background:#2563eb; color:#fff; border-radius:18px 18px 4px 18px; 
    padding:10px 16px; margin:8px 0 8px auto; max-width:85%; 
    width: fit-content; 
    font-size:0.92rem; line-height:1.5; 
}

.a-msg { 
    background:#fff; border:1px solid #e5e7eb; border-radius:18px 18px 18px 4px; 
    padding:12px 16px; margin:8px 0; max-width:100%; 
    width: fit-content;
    font-size:0.92rem; color:#374151; line-height:1.6; 
}
.a-label { font-size:0.7rem; color:#9ca3af; margin-bottom:4px; font-weight:500; }

.thinking-text { font-size:0.85rem; color:#2563eb; font-weight:600; display:flex; align-items:center; margin-bottom: 8px; }
.loader { 
    border: 2px solid #e5e7eb; border-top: 2px solid #2563eb; 
    border-radius: 50%; width: 14px; height: 14px; 
    animation: spin 1s linear infinite; display: inline-block; 
    margin-right: 8px; vertical-align: middle; 
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.sp { display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:14px; font-size:0.73rem; font-family:'JetBrains Mono',monospace; margin:2px 3px 2px 0; }
.sp-run { background:#dbeafe; color:#2563eb; border:1px solid #93c5fd; }
.sp-done { background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; }
.sp-wait { background:#f9fafb; color:#d1d5db; border:1px solid #e5e7eb; }

.mrow { display:flex; gap:1rem; margin-top:6px; font-size:0.76rem; color:#6b7280; font-family:'JetBrains Mono',monospace; }
.mv { font-weight:600; color:#374151; }

.detail-line { font-size:0.78rem; color:#6b7280; margin:6px 0 2px 0; padding-left:4px; font-family:'JetBrains Mono',monospace; }

details.log-dropdown { margin-top: 8px; border-top: 1px dashed #e5e7eb; padding-top: 4px; }
details.log-dropdown summary { text-align: right; font-size: 0.75rem; color: #9ca3af; cursor: pointer; list-style: none; outline: none; }
details.log-dropdown summary::-webkit-details-marker { display: none; }
details.log-dropdown summary:hover { color: #2563eb; }
.log-content { background: #ffffff; border: 1px solid #000000; padding: 8px 10px; border-radius: 6px; font-size: 0.72rem; color: #4b5563; max-height: 200px; overflow-y: auto; white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; text-align: left; margin-top: 6px; }

/* 修复长链接/长文本撑破容器的问题 */
div[data-testid="stExpander"] p, div[data-testid="stExpander"] a, .stMarkdown p, .stMarkdown a {
    word-wrap: break-word; overflow-wrap: break-word; word-break: break-all; white-space: normal;
}
div[data-testid="stExpander"] { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; margin-top: 10px; }
/* --- 修复输入框选中时的红色边框，改为科技浅蓝 --- */
div[data-testid="stChatInput"] > div:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 1px #3b82f6 !important;
}
</style>
""", unsafe_allow_html=True)

# ===== State =====
for key, default in [
    ("msgs", []), ("running", False), ("report", None),
    ("rmeta", {}), ("pending", None)
]:
    if key not in st.session_state:
        st.session_state[key] = default

STEPS = [
    ("planner",  "🧠", "规划"),
    ("searcher", "🔍", "搜索"),
    ("analyzer", "🔬", "分析"),
    ("writer",   "✍️", "撰写"),
    ("critic",   "🧐", "评审"),
]

STEP_KEYWORDS = {
    "规划器": "planner",
    "搜索器": "searcher",
    "分析器": "analyzer",
    "撰写器": "writer",
    "评审器": "critic",
}

def build_progress(current_step: str, done_steps: set, detail: str = "", iteration: int = 0, all_logs: list = []):
    """动态运行时的进度条生成器"""
    pills = ""
    if current_step:
        for key, icon, name in STEPS:
            if key in done_steps:
                pills += f'<span class="sp sp-done">{icon} {name} ✓</span>'
            elif key == current_step:
                pills += f'<span class="sp sp-run">{icon} {name} ⟳</span>'
            else:
                pills += f'<span class="sp sp-wait">{icon} {name}</span>'

    iter_label = f" · 第{iteration+1}轮" if iteration > 0 else ""
    detail_html = f'<div class="detail-line">➤ {detail}</div>' if detail else ""
    
    logs_html = ""
    if all_logs:
        joined_logs = "\n".join(all_logs).replace("<", "&lt;").replace(">", "&gt;")
        logs_html = (
            f'<details class="log-dropdown">'
            f'<summary>🔽 展开实时日志</summary>'
            f'<div class="log-content">{joined_logs}</div>'
            f'</details>'
        )

    return (
        f'<div class="a-msg">'
        f'<div class="a-label">🔬 DeepResearch-Agent{iter_label}</div>'
        f'<div class="thinking-text"><span class="loader"></span> <span>Thinking...</span></div>'
        f'<div>{pills}</div>'
        f'{detail_html}{logs_html}'
        f'</div>'
    )


def do_research(query):
    progress = st.empty()
    progress.markdown(
        build_progress(current_step=None, done_steps=set(), detail="正在分配计算资源与建立通信...", iteration=0, all_logs=[]),
        unsafe_allow_html=True
    )

    from core.graph import compile_graph
    from core.state import ResearchState

    init: ResearchState = {
        "user_query": query,
        "candidate_plans": [], "selected_plan": None,
        "search_results": [], "verified_claims": [],
        "analysis_summary": "", "report_draft": "",
        "citations": [], "critic_feedback": None,
        "current_iteration": 0, "failed_strategies": [],
        "status": "planning",
    }

    t0 = time.time()
    old_stdout = sys.stdout

    current_step = "planner"
    done_steps = set()
    last_detail = "系统已启动，正在规划研究路径..."
    iteration = 0
    all_logs = [] 

    class ProgressCapture:
        def __init__(self):
            self.terminal = old_stdout

        # 【修复点 1】：加入 isatty 修复 NLI 验证器 tqdm 进度条报错
        def isatty(self):
            return hasattr(self.terminal, 'isatty') and self.terminal.isatty()

        def write(self, msg):
            nonlocal current_step, done_steps, last_detail, iteration, all_logs
            self.terminal.write(msg)

            if not msg.strip():
                return
            
            all_logs.append(msg.strip())

            for keyword, step_key in STEP_KEYWORDS.items():
                if keyword in msg and "正在" in msg:
                    if current_step and current_step != step_key:
                        done_steps.add(current_step)
                    current_step = step_key
                    break

            line = msg.strip()
            if line.startswith("[web]") or line.startswith("[arxiv]"):
                last_detail = line[:60] + "..." if len(line)>60 else line
            elif "搜索中:" in line:
                last_detail = line.split("搜索中:")[-1].strip()[:50]
            elif "压缩后结果总数" in line:
                last_detail = line
            elif "验证范围" in line or "NLI" in line:
                last_detail = line.strip()
            elif "覆盖度=" in line:
                last_detail = line.strip()[:60]
            elif "总分:" in line or "判定:" in line:
                last_detail = line.strip()
            elif "第" in line and "轮迭代" in line:
                iteration += 1
                done_steps = set() 
                current_step = "planner"
            elif "报告已生成" in line:
                last_detail = line.strip()

            progress.markdown(
                build_progress(current_step, done_steps, last_detail, iteration, all_logs),
                unsafe_allow_html=True,
            )

        def flush(self):
            self.terminal.flush()

    try:
        sys.stdout = ProgressCapture()
        graph = compile_graph()
        final = graph.invoke(init)
        sys.stdout = old_stdout

        dt = time.time() - t0
        rpt = final.get("report_draft", "")
        fb = final.get("critic_feedback")
        it = final.get("current_iteration", 0) + 1
        sc = fb.score if fb and hasattr(fb, 'score') else 0
        
        st.session_state.report = rpt
        st.session_state.rmeta = {"score": sc, "iters": it, "time": dt, "chars": len(rpt)}
        
        progress.empty()
        # 【修复点 2】：把 all_logs 塞进历史消息里留存
        st.session_state.msgs.append({
            "role": "assistant",
            "content": f"研究完成！得分 {sc:.1f}/10，耗时 {dt:.0f}s，{it} 轮迭代。",
            "time": datetime.now().strftime("%H:%M"),
            "logs": all_logs  # 保存思考过程
        })

    except Exception as e:
        sys.stdout = old_stdout
        progress.empty()
        st.error(f"❌ 运行异常: {e}")
        st.code(traceback.format_exc())
    finally:
        sys.stdout = old_stdout
        st.session_state.running = False
        st.session_state.pending = None


# ===== Layout =====
has_msgs = len(st.session_state.msgs) > 0

if not has_msgs and not st.session_state.running:
    st.markdown("""
    <div class="welcome">
        <div class="welcome-icon">🔬</div>
        <div class="welcome-title">DeepResearch-Agent</div>
        <div class="welcome-sub">多智能体协作深度研究系统<br>输入研究问题，AI 自动搜索、验证、分析并生成带引用的研究报告</div>
        <div class="welcome-tags">
            <span class="wtag">🧠 Simulate-Before-Act</span>
            <span class="wtag">🔬 NLI 交叉验证</span>
            <span class="wtag">🧐 LLM-as-a-Judge</span>
            <span class="wtag">📄 自动引用追踪</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if has_msgs:
    for m in st.session_state.msgs:
        if m["role"] == "user":
            st.markdown(f'<div class="u-msg">{m["content"]}</div>', unsafe_allow_html=True)
        else:
            # 【修复点 3】：渲染历史消息时，如果带有日志，就渲染出一个折叠面板
            logs_html = ""
            if "logs" in m and m["logs"]:
                joined_logs = "\n".join(m["logs"]).replace("<", "&lt;").replace(">", "&gt;")
                logs_html = (
                    f'<details class="log-dropdown">'
                    f'<summary>🔽 展开思考与验证日志</summary>'
                    f'<div class="log-content">{joined_logs}</div>'
                    f'</details>'
                )
            
            # 渲染所有的步骤为绿色的“完成”状态，代表这是历史记录
            pills = ""
            for key, icon, name in STEPS:
                pills += f'<span class="sp sp-done">{icon} {name} ✓</span>'
                
            st.markdown(
                f'<div class="a-msg"><div class="a-label">🔬 DeepResearch-Agent · {m["time"]}</div>'
                f'<div>{pills}</div>'
                f'<div class="detail-line" style="margin-top:8px;">➤ {m["content"]}</div>'
                f'{logs_html}</div>', unsafe_allow_html=True)

if st.session_state.report and not st.session_state.running:
    rm = st.session_state.rmeta
    expander_title = f"📄 点击查看完整研究报告 ({rm.get('chars',0):,} 字 | 评分 {rm.get('score',0):.1f}/10)"
    
    with st.expander(expander_title, expanded=True):
        st.markdown(st.session_state.report)
        st.divider()
        st.download_button(
            label="📥 下载 Markdown 报告", 
            data=st.session_state.report,
            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown", 
            use_container_width=True
        )

if st.session_state.running and st.session_state.pending:
    do_research(st.session_state.pending)
    st.rerun()

query = st.chat_input("输入你的研究问题...")
if query:
    st.session_state.msgs.append({"role": "user", "content": query, "time": datetime.now().strftime("%H:%M")})
    st.session_state.running = True
    st.session_state.report = None
    st.session_state.rmeta = {}
    st.session_state.pending = query
    st.rerun()