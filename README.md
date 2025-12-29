# CFR Lab（Kuhn Poker）

基于 Kuhn Poker 的 CFR（Counterfactual Regret Minimization）算法可视化小工具，提供交互式训练与博弈树可视化，帮助理解策略如何收敛到纳什均衡。

## 功能概览

- 交互式 CFR 训练：可配置迭代次数与快照间隔
- 动态博弈树可视化：Chance / 玩家 / 终局节点一体展示
- 富文本 Tooltip：显示平均策略、当前策略与 Regret
- 播放控制：自动播放、暂停、重置、拖拽回溯

## 快速开始

1. 安装依赖（uv）：

```bash
uv sync
```

2. 运行 CFR 训练并估算 alpha（正式入口）：

```bash
uv run python src/kuhn/calculate_alpha.py
```

参数示例：

```bash
uv run python src/kuhn/calculate_alpha.py --iterations 1000000 --log-every 100000
```

默认 `--iterations=200000`，`--log-every=0`（不输出进度）。

3. 启动可视化界面（Streamlit）：

```bash
uv run streamlit run src/kuhn/ui_tree.py
```

## 目录结构

- `src/kuhn/kuhn_poker.py`：Kuhn Poker 游戏逻辑（高性能实现，带可选参数校验）
- `src/kuhn/cfr_backend.py`：CFR 训练与快照生成
- `src/kuhn/viz.py`：Graphviz 博弈树渲染与 Tooltip 生成
- `src/kuhn/ui_tree.py`：Streamlit 可视化应用入口
- `docs/README.md`：文档索引（规则与纳什均衡参考）

## 注意事项

- `graphviz` Python 包依赖系统的 Graphviz 可执行文件（`dot`）。如遇渲染错误，请先安装系统 Graphviz。

## License

MIT License
