import re

import graphviz
from kuhn_poker import KuhnPokerGame

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
    dot.attr(nodesep="1.0")  # Increase horizontal spacing
    dot.attr(ranksep="1.2")  # Increase vertical spacing
    dot.attr(fontname="Helvetica")

    # --- Global Node/Edge Attributes ---
    dot.attr("node", fontname="Helvetica", fontsize="16", penwidth="2.0")
    dot.attr("edge", fontname="Helvetica", fontsize="14", penwidth="1.5", arrowsize="0.9")

    def visit(state, parent_id=None, edge_label=None):
        history_str = "".join(map(str, state.history))
        node_id = f"node_{history_str}"

        # Default Node Style
        label = ""
        fillcolor = "white"
        color = "#333333"
        shape = "box"
        style = "filled,rounded"
        width = "1.8"
        height = "1.2"
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
                width = "1.5"
                height = "0.8"

                # Tooltip for terminal
                tooltip_map[node_id] = (
                    f"<div class='tt-header' style='border-bottom-color: {color}'>Terminal Node</div>"
                    f"<div class='tt-row'><span>Payoff P0:</span> <b>{p0_ret:+.1f}</b></div>"
                    f"<div class='tt-row'><span>Payoff P1:</span> <b>{-p0_ret:+.1f}</b></div>"
                )

        elif state.is_chance_node():
            # Chance Node
            deal_to = "P0" if len(state.history) == 0 else "P1"
            label = f"Deal\n{deal_to}"
            fillcolor = "#FFF9C4"  # Light Yellow
            color = "#FBC02D"
            shape = "circle"
            width = "1.0"
            height = "1.0"
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
                    f'<TR><TD BGCOLOR="{header_bg}"><FONT POINT-SIZE="16"><B>P{player}</B></FONT> <FONT POINT-SIZE="14">({info_set})</FONT></TD></TR>'
                    f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="16">Pass: <B>{avg_strat[0]:.1%}</B></FONT></TD></TR>'
                    f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="16">Bet:  <B>{avg_strat[1]:.1%}</B></FONT></TD></TR>'
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
    cleaned = re.sub(r'\s(width|height)="[^" ]+"', "", svg_text, count=2)

    # 2. Inject ID and responsive style
    cleaned = cleaned.replace(
        "<svg ",
        'id="game-tree-svg" style="display:block; width:100%; height:100%;" preserveAspectRatio="xMidYMid meet" ',
        1,
    )

    # 3. CRITICAL: Remove all <title> tags to prevent native browser tooltips
    # Graphviz automatically adds <title> tags with node IDs.
    cleaned = re.sub(r"<title>.*?</title>", "", cleaned, flags=re.DOTALL)

    return cleaned
