# Jev Learning Loop MVP

Local experiment comparing an LLM prompt-learning loop with a Jev rubric-learning loop on real Upworthy A/B tests.

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

Raw Upworthy files belong under `data/jd64p-osfstorage-archive/` and are never committed.

## Current local checks

```sh
.venv/bin/python -m pytest -q
.venv/bin/python prep.py
.venv/bin/python controls.py
.venv/bin/python access_check.py --gemini
.venv/bin/python access_check.py --openrouter-llm
.venv/bin/python access_check.py --jev
.venv/bin/python run.py --loop-a-smoke 10 --run-id loop-a-smoke-v0
.venv/bin/python run.py --loop-b-smoke 10 --run-id loop-b-smoke-v0
```

Use `controls.py --include-sealed` only for the registered final evaluation.

## Full-run sequence

```sh
.venv/bin/python editor.py --start --run-id EXPERIMENT_ID
.venv/bin/python learn.py --run-id EXPERIMENT_ID
.venv/bin/python sealed.py --run-id EXPERIMENT_ID-sealed
```

Afterward, package `results/` and `logs/` under a new immutable `experiments/YYYY-MM-DD-task-version/` folder before starting another experiment.
