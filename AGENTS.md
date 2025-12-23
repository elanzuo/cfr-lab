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
