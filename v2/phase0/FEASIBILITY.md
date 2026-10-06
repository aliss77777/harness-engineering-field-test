# Phase 0: feasibility

**Status:** free checks done (2026-10-05); paid spike not started. Budget ≈ ½ day, ≤ $10. Go/no-go for everything else (Task Brief 7, section 3).

## Plan

1. Install AutomationBench; run the Cheap agent on 20 "simple" tasks and 20 tasks from one business domain.
   **First, pick the Cheap agent with a bake-off** (below): the agent's model is v2's biggest cost lever.
2. Measure cost and time per run, and the Cheap and Strong agents' pass rates.
3. Confirm we can: (a) run K independent candidates per task; (b) grade each one; (c) export a run summary with no assertion text; (d) plug in our own agent loop or wrap theirs.

## Cheap-agent bake-off (added 2026-10-05, Alexander)

**Why:** the Cheap agent's runs are most of v2's cost. Open-weight models on OpenRouter cost a small fraction of Gemini 3.8 Flash per token, and a cheaper agent also widens the gap the Router can exploit, provided the agent is good enough. Settle it with data instead of guessing.

**Candidates** (OpenRouter list prices on 2026-10-05, $ per million tokens, input / output):

| Model | Open weight? | Price | vs Gemini 3.8 Flash |
|---|---|---|---|
| `google/gemini-3.8-flash` (v1's model; reference) | No | $0.75 / $3.75 | — |
| `nvidia/nemotron-3-super-120b-a12b` | Yes | $0.08 / $0.45 | ≈ 8–9× cheaper |
| `openai/gpt-oss-120b` | Yes | $0.037 / $0.17 | ≈ 20× cheaper |

**Protocol:**
- The same 20 tasks for every model: 10 from "simple", 10 from the first business domain.
- One run each, with the same agent prompt, tool set and step cap.
- Run on the free Phase 0 harness (`src/jevloop/`), with caching, logging and a spend cap of **$5**.
- **Pin one provider per open-weight model** through OpenRouter (no fallbacks). v1's route check carries over: the run stops if a different model or host answers. Log the host used.

**Measure, per model:** pass rate, mean partial credit, cost per run (from the API's reported cost), time per run, steps per run, and tool-call errors (malformed calls, loops, step-cap hits).

**Selection rule (fixed before the bake-off runs):** pick the **cheapest model whose pass rate on the 20 tasks is between 20% and 80%** (room for selection to matter) **and whose tool-call error rate is under 10% of runs**. Tie or near-tie (within 5 points of pass rate): take the cheaper one. If no open-weight model qualifies, keep Gemini 3.8 Flash. Record the choice and the numbers here and in `PLAN.md` before any further paid run.

**Other notes:**
- **The editor** (few calls, quality matters) stays on a strong model regardless of the bake-off.
- **The Strong agent** is chosen separately (brief section 9, decision 3).
- **Cost of the bake-off:** about $2–3 (60 runs).

| Model | Host pinned | Pass rate | Mean credit | $ / run | s / run | Steps / run | Tool-call errors |
|---|---|---|---|---|---|---|---|
| Gemini 3.8 Flash | Google AI Studio | | | | | | |
| Nemotron 3 Super | | | | | | | |
| gpt-oss-120b | | | | | | | |

**Chosen Cheap agent:** *(fill in with date and reasoning)*

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
| Cheap agent model (from the bake-off) | |
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
