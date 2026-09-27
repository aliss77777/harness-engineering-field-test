# Jev Learning Loop MVP

Experiments testing whether a decision model (Jev) helps an AI agent learn its own decision criteria from real outcomes, compared with an LLM that learns from its own reasoning.

| # | Task | Status | Where |
|---|---|---|---|
| 1 | Upworthy headline A/B tests | Complete: *hypothesis weakened* | [`experiments/2026-09-26-upworthy-v1`](experiments/2026-09-26-upworthy-v1/README.md); code at tag `exp1-upworthy-v1` |
| 2 | Chatbot Arena long responses | Complete: *only the Jev loop learned* | [`experiments/2026-09-26-arena-v1`](experiments/2026-09-26-arena-v1/README.md) |
| 3 | Arena, decision-trace Jev loop (B-prime, B-plus) | Complete: *trace no detectable difference; weights help* | [`experiments/2026-09-26-arena-trace-v1`](experiments/2026-09-26-arena-trace-v1/README.md) |
| 4 | Arena, one LLM + Jev hybrid (stacked vote) | Complete: *no meaningful gain* | [`experiments/2026-09-27-arena-hybrid-v1`](experiments/2026-09-27-arena-hybrid-v1/README.md) |
| 5 | Arena, route between Jev and the LLM (cascade) | Designed, not scheduled | brief: `Task Brief 5_Routing.md` |

Side-by-side results and lessons: [`experiments/COMPARISON.md`](experiments/COMPARISON.md). The full, dated record of every decision, deviation and result is in [`MVP Project Plan.md`](MVP%20Project%20Plan.md).

## Repository layout

- `experiments/` — completed, immutable experiment packages.
- `data/splits/` — registered pair IDs shared by the Upworthy experiment.
- Root Python files — reusable experiment harness.
- `results/`, `logs/`, and `cache/` — ignored working directories for the next run.

Completed experiments are named `YYYY-MM-DD-task-version`. Each package contains its report, machine-readable artifacts, configuration snapshot, split IDs, and compressed telemetry. Do not modify a completed package; create a new one for the next experiment.

See [`experiments/README.md`](experiments/README.md) for the experiment index.

## Setup

1. Create `.env` from `.env.example` and add API keys.
2. Create the environment: `python3 -m venv .venv`
3. Install dependencies: `.venv/bin/python -m pip install -r requirements.txt`

Raw data is never committed: Upworthy under `data/jd64p-osfstorage-archive/`; Arena `train.csv` (Hugging Face `lmarena-ai/arena-human-preference-55k`, Apache 2.0) under `data/arena/raw/`. Registered pair IDs are committed under `data/*/splits/`.

## Checks

```sh
.venv/bin/python -m pytest -q
.venv/bin/python access_check.py --openrouter-llm
.venv/bin/python access_check.py --jev
```

## Experiment 2 (Arena) sequence

```sh
.venv/bin/python prep_arena.py                       # filters, prompt-hash split, saved IDs
.venv/bin/python baseline_arena.py                   # style code baseline (practice-trained)
.venv/bin/python run.py --fake                       # seeded random clients through the real pipeline
.venv/bin/python editor.py --start --run-id arena-v0 --config config_arena.yaml --task task_arena.yaml
.venv/bin/python run.py --smoke 20 && .venv/bin/python run.py --estimate
.venv/bin/python learn.py --run-id RUN_ID            # both loops in parallel; no sealed data
.venv/bin/python sealed.py --run-id RUN_ID-sealed    # once, guarded
```

Live while running: `results/arena/run_status.json` (current stage per loop, ETA, spend), `results/arena/wip_summary.json` (every finished evaluation, candidate edit and gate decision), and `.venv/bin/python monitor.py --run-id RUN_ID` (read-only health check). Spend is capped in code (`budget.spend_cap_usd`).

## Experiment 3 (merged into `main`)

```sh
.venv/bin/python prep_arena3.py                      # fresh sealed set; practice/gate copied from experiment 2
.venv/bin/python learn_trace.py --run-id RUN_ID      # B-prime and B-plus in parallel
.venv/bin/python sealed_trace.py --run-id RUN_ID-sealed   # refuses until experiment 2's verdict exists
```

## Experiment 4 (hybrid)

```sh
.venv/bin/python prep_arena4.py                      # sealed-4 (1,000 fresh pairs); practice/gate copied
.venv/bin/python fit_hybrid.py --run-id RUN_ID       # fit + freeze the stacked vote on practice + gate
.venv/bin/python sealed_hybrid.py --run-id RUN_ID-sealed  # once, guarded
```

Experiment 1's commands (`prep.py`, `controls.py`, the old `run.py` smoke modes) are at tag `exp1-upworthy-v1`.

Afterward, package `results/` and `logs/` under a new immutable `experiments/YYYY-MM-DD-task-version/` folder before starting another experiment.
