import re
import time

import graphviz
import streamlit as st
import streamlit.components.v1 as components
from cfr_backend import CFRSolver
from kuhn_poker import KuhnPokerGame

PLAY_DELAY_MS = 300

# --- 1. 页面配置与 CSS 注入 (去除留白) ---
st.set_page_config(layout="wide", page_title="Kuhn Poker CFR Visualizer")

# 使用 CSS 强制减少顶部空白，并将主区域背景设为白色
st.markdown(
    """
    <style>
        /* Reduce top padding */
        .block-container {
            padding-top: 0.4rem !important;
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
        header {visibility: hidden;}
        footer {visibility: hidden;}
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
        total_iterations = st.number_input("Total iterations", value=5000, step=500)
        log_interval = st.number_input("Snapshot interval", value=100, step=100)
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

    # --- B. 视图控制 ---
    st.header(":material/visibility: View Settings")
    show_payoff = st.checkbox("Show Payoff", value=False)

    st.divider()


# --- 4. 主界面：博弈树 (占据 95% 空间) ---

st.title(":material/account_tree: Kuhn Poker CFR Visualizer")


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

# 布局容器
header_container = st.container()

with header_container:
    # 使用两列：左侧控制，右侧指标
    c_ctrl, c_metrics = st.columns([0.35, 0.65], vertical_alignment="center")

    with c_ctrl:
        # 第一行：播放按钮组
        b1, b2, b3 = st.columns(3)
        play_clicked = b1.button("Play", icon=":material/play_arrow:", use_container_width=True)
        pause_clicked = b2.button("Pause", icon=":material/pause:", use_container_width=True)
        reset_clicked = b3.button("Reset", icon=":material/restart_alt:", use_container_width=True)

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


# 纳什均衡理论值参考
NASH_INFO = {
    "0": "Nash Bet: [0.00, 0.33] (alpha)",
    "1": "Nash Pass: 100%",
    "2": "Nash Bet: 3 * alpha",
    "0p": "Nash Bet: 33.3%",
    "1p": "Nash Pass: 100%",
    "2p": "Nash Bet: 100%",
    "0b": "Nash Fold: 100%",
    "1b": "Nash Call: 33.3%",
    "2b": "Nash Call: 100%",
    "0pb": "Nash Fold: 100%",
    "1pb": "Nash Call: alpha + 33.3%",
    "2pb": "Nash Call: 100%",
}


# 绘图逻辑
def render_game_tree_svg(game, snapshot_data, show_payoff=True):
    dot = graphviz.Digraph(comment="Kuhn Poker")
    tooltip_map = {}  # Store HTML content for custom tooltips

    # --- Global Graph Attributes ---
    dot.attr(bgcolor="transparent")
    dot.attr(rankdir="TB")
    dot.attr(splines="true")  # "true" for curved lines, "ortho" for right angles
    dot.attr(nodesep="0.6")  # Increase horizontal spacing
    dot.attr(ranksep="0.6")  # Increase vertical spacing
    dot.attr(fontname="Helvetica")

    # --- Global Node/Edge Attributes ---
    dot.attr("node", fontname="Helvetica", fontsize="12", penwidth="1.5")
    dot.attr("edge", fontname="Helvetica", fontsize="10", penwidth="1.2", arrowsize="0.7")

    def visit(state, parent_id=None, edge_label=None):
        history_str = "".join(map(str, state.history))
        node_id = f"node_{history_str}"

        # Default Node Style
        label = ""
        fillcolor = "white"
        color = "#333333"
        shape = "box"
        style = "filled,rounded"
        width = "1.2"
        height = "0.8"
        node_data = None
        # Note: We no longer set the 'tooltip' attribute on the node directly
        # to avoid the default browser tooltip behavior.

        if state.is_terminal():
            if not show_payoff:
                label = ""
                shape = "point"
                width = "0.1"
                style = "invis"
            else:
                returns = state.returns()
                p0_ret = returns[0]
                # Color-code payoffs
                if p0_ret > 0:
                    fillcolor = "#E8F5E9"  # Light Green
                    color = "#4CAF50"
                elif p0_ret < 0:
                    fillcolor = "#FFEBEE"  # Light Red
                    color = "#EF5350"
                else:
                    fillcolor = "#F5F5F5"
                    color = "#9E9E9E"

                label = f"Payoff\nP0: {p0_ret:+.1f}"
                shape = "box"
                style = "filled,rounded"
                width = "0.9"
                height = "0.5"

                # Tooltip for terminal
                tooltip_map[node_id] = (
                    f"<div class='tt-header' style='border-bottom-color: {color}'>Terminal Node</div>"
                    f"<div class='tt-row'><span>Payoff P0:</span> <b>{p0_ret:+.1f}</b></div>"
                    f"<div class='tt-row'><span>Payoff P1:</span> <b>{-p0_ret:+.1f}</b></div>"
                )

        elif state.is_chance_node():
            # Chance Node
            deal_to = "P0" if len(state.history) == 0 else "P1"
            label = f"Deal\\n{deal_to}"
            fillcolor = "#FFF9C4"  # Light Yellow
            color = "#FBC02D"
            shape = "circle"
            width = "0.7"
            height = "0.7"
            style = "filled"

            tooltip_map[node_id] = (
                f"<div class='tt-header' style='border-bottom-color: {color}'>Chance Node</div>"
                f"<div class='tt-row'>Action: Dealing card to <b>{deal_to}</b></div>"
            )

        else:  # Player Node
            player = state.current_player()
            info_set = state.information_state_string()

            # Player-specific themes
            if player == 0:
                header_bg = "#B3E5FC"  # Blue Header
                fillcolor = "#E1F5FE"  # Light Blue Body
                border_color = "#0277BD"  # Dark Blue Border
                player_color = "#0277BD"
            else:
                header_bg = "#F8BBD0"  # Pink Header
                fillcolor = "#FCE4EC"  # Light Pink Body
                border_color = "#C2185B"  # Dark Pink Border
                player_color = "#C2185B"

            node_data = snapshot_data.get(info_set)

            if node_data:
                avg_strat = node_data["avg_strategy"]
                regret = node_data.get("regret")
                current_strat = node_data.get("current_strategy")

                # --- Build Rich HTML Tooltip ---
                tt_html = f"<div class='tt-header' style='background-color: {header_bg}; color: {player_color};'><b>P{player}</b> &nbsp; InfoSet: {info_set}</div>"

                # Strategy Section
                tt_html += "<div class='tt-section'><b>Average Strategy</b></div>"
                tt_html += (
                    f"<div class='tt-row'><span>Pass:</span> <span>{avg_strat[0]:.1%}</span></div>"
                )
                tt_html += f"<div class='tt-bar'><div style='width:{avg_strat[0] * 100}%; background:#1976D2;'></div></div>"
                tt_html += (
                    f"<div class='tt-row'><span>Bet:</span> <span>{avg_strat[1]:.1%}</span></div>"
                )
                tt_html += f"<div class='tt-bar'><div style='width:{avg_strat[1] * 100}%; background:#D32F2F;'></div></div>"

                # Nash Section
                nash_desc = NASH_INFO.get(info_set)
                if nash_desc:
                    tt_html += f"<div class='tt-section' style='margin-top:8px; color:#555;'><b>Nash Equilibrium</b><br/><small>{nash_desc}</small></div>"

                # Stats Section (Regret/Current)
                if regret is not None or current_strat is not None:
                    tt_html += "<div class='tt-divider'></div>"
                    if current_strat is not None:
                        tt_html += f"<div class='tt-row'><small>Curr Strat:</small> <small>[{current_strat[0]:.2f}, {current_strat[1]:.2f}]</small></div>"
                    if regret is not None:
                        tt_html += f"<div class='tt-row'><small>Regret:</small> <small>[{regret[0]:.3f}, {regret[1]:.3f}]</small></div>"

                tooltip_map[node_id] = tt_html

                # HTML Label Table for Node
                label = (
                    f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" COLOR="{border_color}" BGCOLOR="{fillcolor}">'
                    f'<TR><TD BGCOLOR="{header_bg}"><B>P{player}</B> <FONT POINT-SIZE="10">({info_set})</FONT></TD></TR>'
                    f'<TR><TD ALIGN="LEFT">Pass: <B>{avg_strat[0]:.1%}</B></TD></TR>'
                    f'<TR><TD ALIGN="LEFT">Bet:  <B>{avg_strat[1]:.1%}</B></TD></TR>'
                    f"</TABLE>>"
                )
                shape = "plain"  # Let HTML table define shape
            else:
                label = f"P{player}: {info_set}"
                # If no data, fall back to standard box
                color = border_color
                style = "filled,rounded"
                tooltip_map[node_id] = (
                    f"<div class='tt-header'>P{player}: {info_set}</div><div>No data available</div>"
                )

        node_kwargs = dict(
            shape=shape,
            style=style if shape != "plain" else "",
            fillcolor=fillcolor if shape != "plain" else "",
            color=color if shape != "plain" else "",
            width=width,
            height=height,
            id=node_id,  # Critical: Assign ID for JS mapping
        )
        # Removed 'tooltip' key to prevent native browser tooltip

        dot.node(node_id, label, **node_kwargs)

        if parent_id:
            # Edge Styling
            edge_style_attr = "solid"
            edge_color_attr = "#616161"
            font_color_attr = "#424242"

            if state.is_terminal() and not show_payoff:
                edge_style_attr = "invis"

            # Action-specific styling
            if edge_label == "Pass":
                edge_color_attr = "#1976D2"  # Blue
                font_color_attr = "#1565C0"
            elif edge_label == "Bet":
                edge_color_attr = "#D32F2F"  # Red
                font_color_attr = "#C62828"
            elif edge_label and "Card" in edge_label:
                edge_color_attr = "#FBC02D"  # Yellow/Orange
                edge_style_attr = "dashed"
                font_color_attr = "#EF6C00"
                # Simplify label: "Card to Px: K" -> "K"
                if ":" in edge_label:
                    edge_label = edge_label.split(":")[1].strip()

            dot.edge(
                parent_id,
                node_id,
                label=edge_label,
                color=edge_color_attr,
                style=edge_style_attr,
                fontcolor=font_color_attr,
            )

        if not state.is_terminal():
            if state.is_chance_node():
                deal_to = "P0" if len(state.history) == 0 else "P1"
                for card in state.legal_actions():
                    next_s = state.clone()
                    next_s.apply_action(card)
                    visit(next_s, node_id, f"Card to {deal_to}: {card}")
            else:
                actions = [0, 1]
                names = ["Pass", "Bet"]
                for i, action in enumerate(actions):
                    next_s = state.clone()
                    next_s.apply_action(action)
                    visit(next_s, node_id, names[i])

    root = KuhnPokerGame().new_initial_state()
    visit(root)
    return dot.pipe(format="svg").decode("utf-8"), tooltip_map


# 让 SVG 自适应容器尺寸，确保树完整可见
def make_svg_responsive(svg_text: str) -> str:
    if "<svg" not in svg_text:
        return svg_text

    # 1. Remove hardcoded width/height attributes from <svg> tag
    cleaned = re.sub(r'\s(width|height)="[^"]+"', "", svg_text, count=2)

    # 2. Inject ID and responsive style
    cleaned = cleaned.replace(
        "<svg ",
        '<svg id="game-tree-svg" style="display:block; width:100%; height:100%;" preserveAspectRatio="xMidYMid meet" ',
        1,
    )

    # 3. CRITICAL: Remove all <title> tags to prevent native browser tooltips
    # Graphviz automatically adds <title> tags with node IDs.
    cleaned = re.sub(r"<title>.*?</title>", "", cleaned, flags=re.DOTALL)

    return cleaned


import json

# 渲染 SVG
svg_content, tooltip_map = render_game_tree_svg(
    KuhnPokerGame(),
    current_snapshot,
    show_payoff=show_payoff,
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
components.html(html_content, height=800, scrolling=False)

if should_autoplay:
    time.sleep(PLAY_DELAY_MS / 1000)
    trigger_rerun()
