# Checking this work

Four levels, from reading to re-running. Each one needs more than the last.

| Level | What you get | Needs | Cost |
|---|---|---|---|
| 0. Read | The story, the numbers, their sources | A browser | free |
| 1. Re-derive | The sealed-exam headline numbers recomputed from the committed per-run table | Python 3.9+ | free |
| 2. Test | Both harnesses' test suites (no model calls) | Python, dependencies | free |
| 3. Re-run | The experiments themselves | API keys, benchmark data | paid |

## 0. Read

[`README.md`](../README.md), then [`v2/README.md`](../v2/README.md) (history and setbacks), [`v2/RESULTS.md`](../v2/RESULTS.md) (every number with its source), [`docs/CLAIMS.md`](CLAIMS.md) (what is and is not supported), and [`v2/PLAN.md`](../v2/PLAN.md) (a dated log of every decision and deviation).

## 1. Re-derive

```bash
python3 v2/scripts/rederive_sealed.py
```

Standard library only; no logs, cache, API key or network. It reads [`v2/phase1/run/take2/sealed_runs.csv`](../v2/phase1/run/take2/sealed_runs.csv) (one row per exam run: credit, passed, cost, steps, checker score) and recomputes the learning gain, its p-value, the router's credit and cost, and the escalation share, then compares each with the published [`sealed_results.json`](../v2/phase1/run/take2/sealed_results.json). It exits non-zero on any mismatch. Point estimates must agree to 1e-6; bootstrap intervals are seeded and compared at 0.01.

The table is produced from the raw run logs by [`v2/scripts/export_sealed_runs.py`](../v2/scripts/export_sealed_runs.py). The raw logs (about 200 MB of full agent transcripts) are not published.

## 2. Test

No model calls; nothing leaves your machine.

```bash
# v1 (Python 3.11 or later)
cd v1 && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q          # 88 pass; 1 is skipped unless the raw Arena data is present

# v2 (Python 3.13, which AutomationBench requires)
git clone https://github.com/zapier/AutomationBench && git -C AutomationBench checkout 4a8e1061254004d9dac807054eed33fad7d1ff14
cd v2 && python3.13 -m venv .venv
.venv/bin/python -m pip install -e ../AutomationBench -r requirements.txt -c requirements-lock.txt
.venv/bin/python -m pytest -q          # 93 pass
```

The pinned AutomationBench commit is version 1.0.6, the version the experiments used. `requirements-lock.txt` pins every package to the version the experiments ran against; without it, newer releases of AutomationBench's dependencies can drop `datasets`, which AutomationBench imports but does not declare.

## 3. Re-run

Paid. Read [`v2/PLAN.md`](../v2/PLAN.md) and the spend notes first: the sealed exam was about $42, the whole of Phase 1 about $118 against a $130 cap.

1. Put `OPENROUTER_KEY=...` in `v2/.env` (v1 also accepts `GEMINI_API_KEY`).
2. Paid stages refuse to run until `run.approved: true` in [`v2/phase1/config_phase1.yaml`](../v2/phase1/config_phase1.yaml).
3. Run the stages in order: `scripts/phase1_run.py skill`, then `jevdata`, `rubric`, `tau`, and last `sealed --release-confirmed`.

Model behaviour drifts. Expect different numbers: the point of the sealed set and the intervals is that the conclusions, not the third decimal, should hold. v1's raw datasets are not committed; the dataset sources and hashes are in [`v1/PLAN.md`](../v1/PLAN.md) and [`NOTICE.md`](../NOTICE.md), and the registered split ids are in `v1/data/*/splits/`.
