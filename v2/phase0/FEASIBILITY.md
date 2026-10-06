# Phase 0: feasibility

**Status:** free checks done (2026-10-05); paid spike not started. Budget ≈ ½ day, ≤ $10. Go/no-go for everything else (Task Brief 7, section 3).

## Plan

1. Install AutomationBench; run the Cheap agent on 20 "simple" tasks and 20 tasks from one business domain.
2. Measure cost and time per run, and the Cheap and Strong agents' pass rates.
3. Confirm we can: (a) run K independent candidates per task; (b) grade each one; (c) export a run summary with no assertion text; (d) plug in our own agent loop or wrap theirs.

## Free checks (2026-10-05, no model calls)

- **Source:** AutomationBench v1.0.6, downloaded manually to `v2/z-ignore/AutomationBench-main` (git-ignored). **Licence: MIT** (© 2026 Zapier, Inc.), which settles the brief's open licence question.
- **Setup:** `uv` is not installed, so the bench was installed with pip into `v2/.venv` (Python 3.13, git-ignored): `python3.13 -m venv .venv && .venv/bin/python -m pip install -e z-ignore/AutomationBench-main pytest pytest-asyncio`.
- **Bench's own tests:** 1,398 passed, run with API keys unset.
- **Do-nothing run, graded on every task:** all 800 tasks load and grade with no errors; a do-nothing run passes 0 and gets credit > 0 on 0 tasks in every domain. The grader drops checks that already pass in the starting state, so all credit comes from what the agent does.

| Domain | Tasks | Median checks per task |
|---|---|---|
| Sales | 100 | 10 |
| Marketing | 100 | 18 |
| Operations | 100 | 13 |
| Support | 100 | 32 |
| Finance | 100 | 7 |
| HR | 100 | 9 |
| Simple | 200 | 1 |

Note for the domain choice: Support has by far the most checks per task, so full passes will be rarer there while partial credit carries the most detail.
- **Item 3d, our own agent loop: yes.** `src/jevloop/bench.py` drives the bench's own pieces directly (the simulated `WorldState`, the default `api` toolset of `api_search` / `api_fetch` / `base64_encode`, and the bench's `partial_credit` grader) without `auto-bench`, so our cache, spend cap and logging stay in charge. Proof at $0: a hand-written solution to `simple:3001` scores 1.0 through the bench's grader; a do-nothing run scores 0.
- **Items 3a–3c at $0:** (a) K independent candidates per task, each in a fresh world (`runs.py`); (b) each graded by the bench (`partial_credit`, pass/fail); (c) a run summary with no grading-check text (`summary.py`; leak tests in `tests/test_summary.py`, including a canary check and a sweep of all 800 tasks). Paid confirmation of (a) needs a real agent: identical prompts must not replay one cached answer K times, so each candidate's index goes into the cache key.
- **Free check, rerunnable:** `.venv/bin/python scripts/phase0_free_check.py`.

## Numbers (paid spike, not run yet)

| Measure | Value |
|---|---|
| Cost per run (Cheap agent) | |
| Cost per run (Strong agent) | |
| Time per run | |
| Cheap agent pass rate | |
| Strong agent pass rate | |
| Share of tasks with mixed pass/fail across K | |
| Projected Phase 1 cost | |

## Go/no-go criteria

- [ ] The Cheap agent passes 20–80% of tasks (so selection has room to matter).
- [ ] Candidates differ: at least 30% of tasks have mixed pass/fail across K.
- [ ] The projected Phase 1 cost fits the cap.

Fallback if K-run generation is too expensive: the 200 "simple" tasks.

## Call

*Go / no-go, with date and reasoning.*

## Domains chosen

*Suggested: Support and Sales.*
