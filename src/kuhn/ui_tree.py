import json
import time

import streamlit as st
import streamlit.components.v1 as components
from cfr_backend import CFRSolver
from kuhn_poker import KuhnPokerGame
from viz import NASH_INFO, make_svg_responsive, render_game_tree_svg

PLAY_DELAY_MS = 300

# --- 1. 页面配置与 CSS 注入 (去除留白) ---
st.set_page_config(layout="wide", page_title="Kuhn Poker CFR Visualizer")

# 使用 CSS 强制减少顶部空白，并将主区域背景设为白色
st.markdown(
    """
    <style>
        /* Reduce top padding - adjusted to clear the header */
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Adjust title size */
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.5rem !important;
        }
        /* Tighten main section spacing */
        .stMarkdown h4 {
            margin: 0.3rem 0 0.2rem 0 !important;
        }
        .stSlider {
            padding-top: 0.1rem !important;
            padding-bottom: 0.2rem !important;
        }
        [data-testid="stMetric"] {
            padding: 0.2rem 0.4rem !important;
        }
        /* Hide Streamlit default menu and footer to save space (optional) */
        #MainMenu {visibility: hidden;}
        /* header {visibility: hidden;} */
        footer {visibility: hidden;}

        /* Inject title into the header - Left Aligned */
        header[data-testid="stHeader"]::after {
            content: "Kuhn Poker CFR Visualizer";
            font-family: "Helvetica", sans-serif;
            font-size: 1.2rem;
            font-weight: bold;
            color: #31333F;
            position: absolute;
            left: 3.5rem; /* Space for the sidebar toggle icon */
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# --- 2. 核心逻辑：缓存训练数据 (先执行数据加载) ---
@st.cache_data
def run_training_session(iterations, interval):
    solver = CFRSolver()
    history = []
    history.append({"step": 0, "data": solver.get_snapshot()})

    # 进度条显示在侧边栏，以免占用主屏
    progress_bar = st.sidebar.progress(0)
    for i in range(1, iterations + 1):
        solver.train_step()
        if i % interval == 0:
            history.append({"step": i, "data": solver.get_snapshot()})
            progress_bar.progress(i / iterations)

    progress_bar.empty()
    return history


def trigger_rerun():
    st.rerun()


# --- 3. 侧边栏布局 (所有的控制都在这里) ---
with st.sidebar:
    st.title(":material/casino: Kuhn CFR")

    # --- A. 训练控制 ---
    with st.expander(":material/build: Training Settings", expanded=False):
        total_iterations = st.number_input("Total iterations", value=100, step=10)
        log_interval = st.number_input("Snapshot interval", value=1, step=1)
        start_btn = st.button("Start / Retrain", type="primary", use_container_width=True)

    # 触发训练
    training_triggered = start_btn or "cfr_history" not in st.session_state
    if training_triggered:
        with st.spinner("Training..."):
            st.session_state["cfr_history"] = run_training_session(total_iterations, log_interval)
        st.session_state["is_playing"] = False
        st.session_state["selected_step_index"] = max(len(st.session_state["cfr_history"]) - 1, 0)

    history = st.session_state["cfr_history"]
    steps = [h["step"] for h in history]
    if training_triggered and steps:
        st.session_state["step_value"] = steps[st.session_state["selected_step_index"]]

    st.divider()


# --- 4. 主界面：博弈树 (占据 95% 空间) ---

# st.title(":material/account_tree: Kuhn Poker CFR Visualizer")


# 数据提取辅助
def get_strat(infoset):
    return current_snapshot[infoset]["avg_strategy"] if infoset in current_snapshot else [0.0, 0.0]


# --- CSS 样式注入：仪表盘与指标卡片 ---
st.markdown(
    """
<style>
    .dashboard-header {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .metric-card {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        padding: 6px 10px;
        margin: 0 4px;
        min-width: 100px;
        font-family: "Helvetica", sans-serif;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #555;
        font-weight: 600;
        margin-bottom: 2px;
    }
    .metric-value {
        font-size: 1.1rem;
        font-weight: bold;
    }
    .p0-card { background-color: #E1F5FE; border: 1px solid #B3E5FC; color: #01579B; }
    .p1-card { background-color: #FCE4EC; border: 1px solid #F8BBD0; color: #880E4F; }

    /* 调整 Streamlit 默认按钮样式以匹配 */
    div.stButton > button {
        height: 2.2rem;
        padding: 0 0.5rem;
        font-size: 0.85rem;
    }

    /* 为 Payoff 按钮设置特殊样式 (紫色系) */
    div[data-testid="column"]:nth-of-type(4) button {
        background-color: #f3e5f5 !important;
        color: #7b1fa2 !important;
        border-color: #ce93d8 !important;
    }
    div[data-testid="column"]:nth-of-type(4) button:hover {
        background-color: #7b1fa2 !important;
        color: white !important;
        border-color: #7b1fa2 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- 仪表盘逻辑与布局 ---

# 控制逻辑预处理
if "is_playing" not in st.session_state:
    st.session_state["is_playing"] = False
if "selected_step_index" not in st.session_state:
    st.session_state["selected_step_index"] = len(steps) - 1
if "step_value" not in st.session_state:
    st.session_state["step_value"] = steps[st.session_state["selected_step_index"]] if steps else 0
if "show_payoff" not in st.session_state:
    st.session_state["show_payoff"] = False

# 布局容器
header_container = st.container()

with header_container:
    # 使用两列：左侧控制，右侧指标
    c_ctrl, c_metrics = st.columns([0.45, 0.55], vertical_alignment="center")

    with c_ctrl:
        # 第一行：播放按钮组
        b1, b2, b3, b4 = st.columns(4)
        play_clicked = b1.button("Play", icon=":material/play_arrow:", use_container_width=True)
        pause_clicked = b2.button("Pause", icon=":material/pause:", use_container_width=True)
        reset_clicked = b3.button("Reset", icon=":material/restart_alt:", use_container_width=True)

        payoff_label = "Hide Payoff" if st.session_state["show_payoff"] else "Show Payoff"
        payoff_icon = (
            ":material/visibility_off:"
            if st.session_state["show_payoff"]
            else ":material/visibility:"
        )
        # type="secondary" (default) but we can style it or leave it standard to differentiate
        # Streamlit doesn't support custom colors directly in button() without custom CSS or themes,
        # but using type="secondary" vs "primary" is the standard way.
        # "Play" is secondary, so we'll keep this secondary too, or make Play primary?
        # Let's just use the button.
        toggle_payoff = b4.button(payoff_label, icon=payoff_icon, use_container_width=True)

        if toggle_payoff:
            st.session_state["show_payoff"] = not st.session_state["show_payoff"]
            st.rerun()

        # 第二行：滑动条 (紧凑)
        selected_step_value = st.select_slider(
            "Iter",
            options=steps,
            value=st.session_state["step_value"],
            disabled=st.session_state["is_playing"],
            label_visibility="collapsed",
        )
        # 显示当前迭代数的小标签
        st.markdown(
            f"<div style='text-align: center; font-size: 0.8rem; color: #666; margin-top: -10px;'>Iteration: <b>{st.session_state['step_value']}</b></div>",
            unsafe_allow_html=True,
        )

    with c_metrics:
        # 获取当前数据
        current_snapshot = history[st.session_state["selected_step_index"]]["data"]
        s_0 = get_strat("0")
        s_2pb = get_strat("2pb")
        s_1p = get_strat("1p")
        s_1b = get_strat("1b")

        # 使用 HTML 渲染美化的指标卡片
        st.markdown(
            f"""
        <div style="display: flex; justify-content: flex-end; width: 100%;">
            <div class="metric-card p0-card" title="Bluff rate">
                <span class="metric-label">P0 Card0 (Bet)</span>
                <span class="metric-value">{s_0[1]:.2f}</span>
            </div>
            <div class="metric-card p0-card" title="Call rate (always wins)">
                <span class="metric-label">P0 Card2 (Call)</span>
                <span class="metric-value">{s_2pb[1]:.2f}</span>
            </div>
            <div class="metric-card p1-card">
                <span class="metric-label">P1 Card1 (Check)</span>
                <span class="metric-value">{s_1p[0]:.2f}</span>
            </div>
            <div class="metric-card p1-card">
                <span class="metric-label">P1 Card1 (Fold)</span>
                <span class="metric-value">{s_1b[0]:.2f}</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

# 状态更新逻辑 (放在布局之后以避免重绘问题，或者在回调中处理)
max_step_index = max(len(steps) - 1, 0)
if play_clicked:
    st.session_state["is_playing"] = True
    st.session_state["selected_step_index"] = 0
if pause_clicked:
    st.session_state["is_playing"] = False
if reset_clicked:
    st.session_state["selected_step_index"] = 0

step_to_index = {step: idx for idx, step in enumerate(steps)}

# 同步 Slider 值
if selected_step_value != st.session_state["step_value"]:
    st.session_state["step_value"] = selected_step_value
    st.session_state["selected_step_index"] = step_to_index.get(selected_step_value, 0)

# 自动播放逻辑
should_autoplay = False
if st.session_state["is_playing"]:
    next_index = st.session_state["selected_step_index"] + 1
    if next_index > max_step_index:
        st.session_state["selected_step_index"] = max_step_index
        st.session_state["is_playing"] = False
    else:
        st.session_state["selected_step_index"] = next_index
        st.session_state["step_value"] = steps[next_index]
    should_autoplay = st.session_state["is_playing"]

# 确保最新状态用于绘图
selected_step_index = st.session_state["selected_step_index"]
current_snapshot = history[selected_step_index]["data"]
current_step = steps[selected_step_index]


# 渲染 SVG
svg_content, tooltip_map = render_game_tree_svg(
    KuhnPokerGame(),
    current_snapshot,
    show_payoff=st.session_state["show_payoff"],
)
svg_content = make_svg_responsive(svg_content)
tooltip_json = json.dumps(tooltip_map)

# --- 5. SVG 容器与自定义 Tooltip 系统 (使用 iframe 组件确保脚本执行) ---

# 构建完整的 HTML 文档
html_content = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{
        margin: 0;
        padding: 0;
        font-family: "Helvetica", sans-serif;
        overflow: hidden; /* 让内部容器处理滚动 */
    }}
    .tree-wrapper {{
        width: 100%;
        height: 100vh; /* 占满 iframe 高度 */
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: white;
    }}
    svg {{
        width: 100%;
        height: 100%;
        display: block;
    }}

    /* Tooltip 样式 */
    #kuhn-tooltip {{
        position: fixed;
        display: none;
        background: white;
        border: 1px solid #ddd;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-radius: 8px;
        padding: 0;
        z-index: 999999;
        font-family: "Helvetica", sans-serif;
        font-size: 13px;
        pointer-events: none;
        max-width: 280px;
        min-width: 200px;
    }}
    .tt-header {{
        padding: 8px 12px;
        border-bottom: 2px solid #eee;
        font-size: 14px;
        font-weight: bold;
    }}
    .tt-section {{
        padding: 8px 12px 4px 12px;
        color: #333;
        font-size: 13px;
    }}
    .tt-divider {{
        height: 1px;
        background-color: #eee;
        margin: 6px 0;
    }}
    .tt-row {{
        display: flex;
        justify-content: space-between;
        padding: 2px 12px;
        color: #444;
    }}
    .tt-bar {{
        height: 6px;
        background-color: #f0f0f0;
        margin: 2px 12px 6px 12px;
        border-radius: 3px;
        overflow: hidden;
    }}
</style>
</head>
<body>

<div id="kuhn-tooltip"></div>

<div class="tree-wrapper">
    {svg_content}
</div>

<script>
    console.log("[Kuhn-CFR-Iframe] Script started.");

    try {{
        const tooltipData = {tooltip_json};
        const tooltip = document.getElementById('kuhn-tooltip');
        const svg = document.querySelector('svg'); // 直接获取 SVG

        if (svg) {{
            console.log("[Kuhn-CFR-Iframe] SVG found.");

            // Mouse Over
            svg.addEventListener('mouseover', function(e) {{
                const nodeGroup = e.target.closest('g[id^="node_"]');
                if (nodeGroup && tooltipData[nodeGroup.id]) {{
                    tooltip.innerHTML = tooltipData[nodeGroup.id];
                    tooltip.style.display = 'block';
                    tooltip.style.opacity = '1';
                }}
            }});

            // Mouse Move
            svg.addEventListener('mousemove', function(e) {{
                if (tooltip.style.display === 'block') {{
                    const xOffset = 15;
                    const yOffset = 15;
                    let left = e.clientX + xOffset;
                    let top = e.clientY + yOffset;

                    // 边界检测 (基于 iframe 窗口大小)
                    if (left + tooltip.offsetWidth > window.innerWidth) {{
                        left = e.clientX - tooltip.offsetWidth - 10;
                    }}
                    if (top + tooltip.offsetHeight > window.innerHeight) {{
                        top = e.clientY - tooltip.offsetHeight - 10;
                    }}

                    tooltip.style.left = left + 'px';
                    tooltip.style.top = top + 'px';
                }}
            }});

            // Mouse Out
            svg.addEventListener('mouseout', function(e) {{
                const nodeGroup = e.target.closest('g[id^="node_"]');
                if (nodeGroup) {{
                    tooltip.style.display = 'none';
                }}
            }});
        }} else {{
            console.error("[Kuhn-CFR-Iframe] SVG element not found!");
        }}
    }} catch (err) {{
        console.error("[Kuhn-CFR-Iframe] Error:", err);
    }}
</script>

</body>
</html>
"""

# 使用 components.html 渲染 (创建一个 iframe)
# height 设置为固定高度，因为 iframe 无法自动获取 calc(100vh)
components.html(html_content, height=1200, scrolling=False)

if should_autoplay:
    time.sleep(PLAY_DELAY_MS / 1000)
    trigger_rerun()
