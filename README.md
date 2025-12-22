# CFR Lab (Kuhn Poker)

This repo provides a tiny CFR trainer and a Streamlit UI to visualize Kuhn poker information sets.

## Quick start

1. Install deps (uv):

```bash
uv sync
```

2. Train and export JSON snapshots:

```bash
uv run src/train_kuhn.py --iterations 5000 --checkpoint-every 500
```

3. Launch the UI:

```bash
uv run streamlit run src/streamlit_app.py
```

The UI reads `artifacts/kuhn_cfr.json` by default. Use the sidebar to select a checkpoint and switch between average/current strategies.

## Notes

- The Python `graphviz` package relies on the Graphviz system binary (`dot`). Install it if you see rendering errors.
