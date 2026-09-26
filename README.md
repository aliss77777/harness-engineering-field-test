# Jev Learning Loop MVP

Local experiment comparing an LLM prompt-learning loop with a Jev rubric-learning loop on real Upworthy A/B tests.

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
.venv/bin/python access_check.py --jev
.venv/bin/python run.py --loop-a-smoke 10 --run-id loop-a-smoke-v0
.venv/bin/python run.py --loop-b-smoke 10 --run-id loop-b-smoke-v0
```

Use `controls.py --include-sealed` only for the registered final evaluation.
