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
        /* 移除顶部巨额 padding */
        .block-container {
            padding-top: 0.4rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* 调整标题大小 */
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.5rem !important;
        }
        /* 紧凑主区块间距 */
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
        /* 隐藏掉 Streamlit 默认的汉堡菜单和 footer 以争取更多空间 (可选) */
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
    with st.expander(":material/build: 训练配置", expanded=False):
        total_iterations = st.number_input("总迭代次数", value=5000, step=500)
        log_interval = st.number_input("记录间隔", value=100, step=100)
        start_btn = st.button("开始/重新训练", type="primary", use_container_width=True)

    # 触发训练
    training_triggered = start_btn or "cfr_history" not in st.session_state
    if training_triggered:
        with st.spinner("正在训练..."):
            st.session_state["cfr_history"] = run_training_session(total_iterations, log_interval)
        st.session_state["is_playing"] = False
        st.session_state["selected_step_index"] = max(len(st.session_state["cfr_history"]) - 1, 0)

    history = st.session_state["cfr_history"]
    steps = [h["step"] for h in history]
    if training_triggered and steps:
        st.session_state["step_value"] = steps[st.session_state["selected_step_index"]]

    st.divider()

    # --- B. 视图控制 ---
    st.header(":material/visibility: 视图设置")
    show_payoff = st.checkbox("显示 Payoff", value=False)

    st.divider()


# --- 4. 主界面：博弈树 (占据 95% 空间) ---

# 标题与控制区域占位
title_slot = st.empty()

# --- C. 播放控制 (移到主界面) ---
st.markdown("#### :material/gamepad: 进度回放")

if "is_playing" not in st.session_state:
    st.session_state["is_playing"] = False
if "selected_step_index" not in st.session_state:
    st.session_state["selected_step_index"] = len(steps) - 1
if "step_value" not in st.session_state:
    st.session_state["step_value"] = steps[st.session_state["selected_step_index"]] if steps else 0

max_step_index = max(len(steps) - 1, 0)
if st.session_state["selected_step_index"] > max_step_index:
    st.session_state["selected_step_index"] = max_step_index
    st.session_state["step_value"] = steps[max_step_index] if steps else 0

step_to_index = {step: idx for idx, step in enumerate(steps)}
if st.session_state["step_value"] not in step_to_index and steps:
    st.session_state["step_value"] = steps[st.session_state["selected_step_index"]]

# 优化布局：使用 3 列按钮 + 1 个占位列
play_col, pause_col, reset_col, _ = st.columns([0.8, 0.8, 0.8, 4.6], vertical_alignment="center")

play_clicked = play_col.button("播放", icon=":material/play_arrow:", use_container_width=True)
pause_clicked = pause_col.button("暂停", icon=":material/pause:", use_container_width=True)
reset_clicked = reset_col.button("重置", icon=":material/restart_alt:", use_container_width=True)

if play_clicked:
    st.session_state["is_playing"] = True
    st.session_state["selected_step_index"] = 0
    st.session_state["step_value"] = steps[0] if steps else 0
if pause_clicked:
    st.session_state["is_playing"] = False
if reset_clicked:
    st.session_state["selected_step_index"] = 0
    st.session_state["step_value"] = steps[0] if steps else 0

should_autoplay = False
if st.session_state["is_playing"]:
    next_index = st.session_state["selected_step_index"] + 1
    if next_index > max_step_index:
        st.session_state["selected_step_index"] = max_step_index
        st.session_state["step_value"] = steps[max_step_index] if steps else 0
        st.session_state["is_playing"] = False
    else:
        st.session_state["selected_step_index"] = next_index
        st.session_state["step_value"] = steps[next_index]
    should_autoplay = st.session_state["is_playing"]

selected_step_value = st.select_slider(
    "选择 Iteration:",
    options=steps,
    key="step_value",
    disabled=st.session_state["is_playing"],
)
st.caption("提示：播放按“记录间隔”的快照推进，若想逐步观察可把记录间隔设为 1。")

selected_step_index = step_to_index.get(selected_step_value, 0)
st.session_state["selected_step_index"] = selected_step_index

current_snapshot = history[selected_step_index]["data"]
current_step = steps[selected_step_index]

# 现在更新标题（位置在上方占位处）
title_slot.subheader(f"博弈树可视化 (Iteration {current_step})")

# --- D. 关键指标监控 (移到主界面) ---
st.markdown("#### :material/bar_chart: 关键指标")


# 数据提取辅助
def get_strat(infoset):
    return current_snapshot[infoset]["avg_strategy"] if infoset in current_snapshot else [0.0, 0.0]


# 单行布局展示 4 个指标
c1, c2, c3, c4 = st.columns(4)
s_0 = get_strat("0")
c1.metric("P0 Card0 (Bet)", f"{s_0[1]:.2f}", delta_color="off", help="诈唬概率 (Bluff)")
s_2pb = get_strat("2pb")
c2.metric("P0 Card2 (Call)", f"{s_2pb[1]:.2f}", delta_color="off", help="跟注概率 (必胜)")
s_1p = get_strat("1p")
c3.metric("P1 Card1 (Check)", f"{s_1p[0]:.2f}", delta_color="off")
s_1b = get_strat("1b")
c4.metric("P1 Card1 (Fold)", f"{s_1b[0]:.2f}", delta_color="off")


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
    dot.attr(rankdir="TB")
    dot.attr(splines="polyline")
    dot.attr(nodesep="0.4")
    dot.attr(ranksep="0.8")

    def visit(state, parent_id=None, edge_label=None):
        history_str = "".join(map(str, state.history))
        node_id = f"node_{history_str}"

        # 样式设置
        label = ""
        fillcolor = "white"
        shape = "ellipse"
        fontsize = "13"
        width = "1.2"
        height = "0.8"
        style = "filled"
        node_data = None
        tooltip = None

        if state.is_terminal():
            if not show_payoff:
                label = ""
                shape = "box"
                fillcolor = "white"
                width = "1.0"
                height = "0.6"
                style = "invis"
                fixedsize = "true"
            else:
                returns = state.returns()
                p0_ret = returns[0]
                color_code = "#d9f7be" if p0_ret > 0 else "#ffa39e"
                label = f"Payoff\nP0: {p0_ret:+.1f}"
                shape = "box"
                fillcolor = color_code
                width = "1.0"
                height = "0.6"
                fixedsize = "true"

        elif state.is_chance_node():
            deal_to = "P0" if len(state.history) == 0 else "P1"
            label = f"{deal_to} 发牌"
            fillcolor = "#fff1b8"
            shape = "circle"
            width = "0.8"
            height = "0.8"

        else:  # 玩家节点
            player = state.current_player()
            info_set = state.information_state_string()
            fillcolor = "#bae7ff" if player == 0 else "#ffccc7"
            node_data = snapshot_data.get(info_set)

            if node_data:
                avg_strat = node_data["avg_strategy"]
                regret = node_data.get("regret")
                current_strat = node_data.get("current_strategy")

                # SVG tooltip: 显示完整策略与后悔值，便于悬浮查看
                tooltip_lines = [
                    f"avg_strategy: [{avg_strat[0]:.3f}, {avg_strat[1]:.3f}]",
                ]

                nash_desc = NASH_INFO.get(info_set)
                if nash_desc:
                    tooltip_lines.append(nash_desc)

                if regret is not None:
                    tooltip_lines.append(f"regret: [{regret[0]:.3f}, {regret[1]:.3f}]")
                if current_strat is not None:
                    tooltip_lines.append(
                        f"current_strategy: [{current_strat[0]:.3f}, {current_strat[1]:.3f}]"
                    )
                tooltip = "\n".join(tooltip_lines)
                label = (
                    f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'
                    f"<TR><TD><B>P{player} ({info_set})</B></TD></TR>"
                    f"<TR><TD>Pass: {avg_strat[0]:.1%}</TD></TR>"
                    f"<TR><TD>Bet:  {avg_strat[1]:.1%}</TD></TR>"
                    f"</TABLE>>"
                )
            else:
                label = f"P{player}: {info_set}"

        node_kwargs = dict(
            shape=shape,
            style=style,
            fillcolor=fillcolor,
            color="black",
            penwidth="1.0",
            fontname="Helvetica",
            fontsize=fontsize,
            width=width,
            height=height,
        )
        if node_data and tooltip:
            node_kwargs["tooltip"] = tooltip
            # 设置 URL 以确保浏览器对 tooltip 生效（生成可悬浮的 <a>） -> 移除 URL，直接利用 SVG <title>
            # node_kwargs["URL"] = "#"
        if state.is_terminal():
            node_kwargs["fixedsize"] = fixedsize
        dot.node(node_id, label, **node_kwargs)

        if parent_id:
            edge_style = "invis" if (state.is_terminal() and not show_payoff) else "solid"
            edge_label = "" if edge_style == "invis" else edge_label
            dot.edge(
                parent_id,
                node_id,
                label=edge_label,
                fontsize="14",
                arrowsize="0.6",
                style=edge_style,
            )

        if not state.is_terminal():
            if state.is_chance_node():
                deal_to = "P0" if len(state.history) == 0 else "P1"
                for card in state.legal_actions():
                    next_s = state.clone()
                    next_s.apply_action(card)
                    visit(next_s, node_id, f"{deal_to}牌值: {card}")
            else:
                actions = [0, 1]
                names = ["Pass", "Bet"]
                for i, action in enumerate(actions):
                    next_s = state.clone()
                    next_s.apply_action(action)
                    visit(next_s, node_id, names[i])

    root = KuhnPokerGame().new_initial_state()
    visit(root)
    return dot.pipe(format="svg").decode("utf-8")


# 让 SVG 自适应容器尺寸，确保树完整可见
def make_svg_responsive(svg_text: str) -> str:
    if "<svg" not in svg_text:
        return svg_text
    cleaned = re.sub(r'\s(width|height)="[^"]+"', "", svg_text, count=2)
    return cleaned.replace(
        "<svg ",
        '<svg id="game-tree-svg" style="display:block; width:100%; height:100%;" preserveAspectRatio="xMidYMid meet" ',
        1,
    )


# 渲染 SVG
svg_content = render_game_tree_svg(
    KuhnPokerGame(),
    current_snapshot,
    show_payoff=show_payoff,
)
svg_content = make_svg_responsive(svg_content)

# --- 5. SVG 容器 (改为 st.markdown 直接渲染以避免 iframe 闪烁) ---
html_container = f"""
<style>
    .tree-wrapper {{
        width: 100%;
        height: 820px;
        overflow: hidden;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 6px;
        text-align: center;
        background-color: white;
        box-sizing: border-box;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .tree-wrapper svg {{
        display: block;
        width: 100%;
        height: 100%;
    }}
</style>
<div class="tree-wrapper">
    {svg_content}
</div>
"""

st.markdown(html_container, unsafe_allow_html=True)

if should_autoplay:
    time.sleep(PLAY_DELAY_MS / 1000)
    trigger_rerun()
