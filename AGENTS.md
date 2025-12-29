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

### 代码结构说明 (src/kuhn)

当前可视化应用主要由以下模块构成：

- **`calculate_alpha.py`**: CFR 训练 CLI 入口。
  - **职责**：
    - 执行指定次数 CFR 迭代并估算 alpha。
    - 支持 `--iterations` 与 `--log-every` 参数控制运行与日志。

- **`ui_tree.py`**: Streamlit 应用主入口。
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

- **`kuhn_poker.py`**: Kuhn Poker 规则与状态机实现。
  - **职责**：
    - 实现发牌、下注、终局判断与收益计算。
    - 提供轻量 `clone` 以支持 CFR 大量状态复制。
    - 通过 `KuhnConfig` 提供可选参数校验与配置管理。
