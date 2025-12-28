# Repository Guidelines

## 重要指令

- 先分析，再给答案和行动
- 如果你有任何不清楚的地方，请向我提问

## 语言约定

- 所有文档与说明统一使用**简体中文**。
- 在仓库内协作交流（包括提交信息、讨论、回答）亦请使用简体中文。

## 项目描述

基于 Kuhn Poker 的 CFR（Counterfactual Regret Minimization）算法可视化工具，用于理解 CFR 如何收敛到纳什均衡，Vibe coding by GPT-5.2.

### 开发命令

使用 UV 进行依赖管理和项目执行：

- `uv sync` — 安装依赖
- `uv run python <module>` — 运行 Python 模块
- `uv run pytest` — 运行测试套件
- `uv add <package>` — 添加依赖

### Python 规范工具链

- `uvx basedpyright .`: 静态类型检查
- `uvx ruff format`: 代码自动格式化
- `uvx ruff check --fix`: 代码质量审计与自动修复

## 代码结构说明 (src/kuhn/gemini)

当前可视化应用主要由以下模块构成：

- **`app.py`**: Streamlit 应用主入口。
  - **职责**：
    - 页面布局与 CSS 样式注入（自定义 Header、按钮样式）。
    - 侧边栏训练控制（CFR 迭代次数、日志间隔）。
    - 核心 Session State 管理（训练数据、播放状态、当前步数）。
    - 控制栏交互（播放/暂停/重置/切换 Payoff 视图）。
    - 关键指标仪表盘渲染（主要 InfoSet 的策略概率）。
    - `iframe` 容器管理，用于嵌入 SVG 并注入自定义 Tooltip 脚本。
  - **依赖**：`viz.py` (绘图), `cfr_backend` (算法), `kuhn_poker` (规则)。

- **`viz.py`**: 可视化渲染模块。
  - **职责**：
    - `render_game_tree_svg`: 使用 Graphviz 生成博弈树 SVG。
      - 节点样式：根据玩家（P0/P1/Chance/Terminal）定制颜色和形状。
      - 节点内容：嵌入 HTML 表格显示详细策略数据（Pass/Bet 概率）。
      - HTML Tooltip 数据生成：构建富文本 Tooltip（包含 Nash 参考值、Regret 值）。
    - `make_svg_responsive`: 后处理 SVG 字符串，使其适配 Web 容器并清理冗余标签。
    - `NASH_INFO`: 纳什均衡理论参考数据常量。

- **`cfr_backend.py`**: CFR 算法核心实现。
  - **职责**：执行 CFR 迭代、累积 Regret 和策略、生成训练快照。

## 已实现功能

1.  **交互式 CFR 训练**：用户可在侧边栏配置迭代次数并实时触发训练，进度条显示训练状态。
2.  **动态博弈树可视化**：
    - 展示完整的 Kuhn Poker 博弈树（Chance -> P0 -> P1 -> Terminal）。
    - 节点大小与字体优化，清晰展示策略概率。
    - **Show/Hide Payoff**：一键切换是否显示终端节点的收益值，按钮使用紫色系高亮区分。
3.  **富文本交互 Tooltip**：
    - 鼠标悬停节点时显示详细信息浮层。
    - 内容包括：平均策略条形图、当前策略、Regret 值、纳什均衡理论参考值。
4.  **播放控制系统**：
    - 支持自动播放、暂停、重置训练过程。
    - 进度条拖拽回溯历史迭代步数。
5.  **关键指标仪表盘**：
    - 实时显示关键 InfoSet（如 P0 Card0 Bet, P1 Card1 Check 等）的策略概率。
    - 使用不同颜色的卡片区分 P0（蓝色）和 P1（粉色）。
6.  **UI/UX 优化**：
    - 自定义 Header：标题移至顶部导航栏左侧，节省主屏空间。
    - 响应式布局：SVG 高度自适应，防止遮挡。
    - 颜色编码：P0（蓝）、P1（粉）、Chance（黄）、Terminal（红/绿）统一配色体系。
