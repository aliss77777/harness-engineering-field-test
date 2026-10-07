# Phase 0: feasibility

**Status:** free checks done (2026-10-05); paid spike not started. Budget ≈ ½ day, ≤ $10. Go/no-go for everything else (Task Brief 7, section 3).

## Plan

1. Install AutomationBench; run the Cheap agent on 20 "simple" tasks and 20 tasks from one business domain.
   **First, the cheap-agent comparability check** (below): can open-weight Nemotron 3 Super stand in for Gemini 3.8 Flash?
2. Measure cost and time per run, and the Cheap and Strong agents' pass rates.
3. Confirm we can: (a) run K independent candidates per task; (b) grade each one; (c) export a run summary with no assertion text; (d) plug in our own agent loop or wrap theirs.

## Cheap-agent comparability check (revised 2026-10-06, Alexander)

*Replaces the 2026-10-05 three-model bake-off (20 tasks; Gemini 3.8 Flash, Nemotron 3 Super, gpt-oss-120b). Revised because 20 tasks with one run each can't separate models on quality: each task is 5 points of pass rate. gpt-oss-120b is dropped.*

**What it is:** a stability check, not a quality ranking and not harness training. Question: **does the open-weight Nemotron 3 Super perform comparably to Gemini 3.8 Flash as the Cheap agent?** If yes, v2 runs on the much cheaper model.

**Models** (OpenRouter list prices on 2026-10-05, $ per million tokens, input / output):

| Model | Role | Open weight? | Price |
|---|---|---|---|
| `google/gemini-3.8-flash` | Reference (v1's model) | No | $0.75 / $3.75 |
| `nvidia/nemotron-3-super-120b-a12b` | Candidate | Yes | $0.08 / $0.45 (≈ 8–9× cheaper) |

**Protocol (fixed before any paid run):**
- **Tasks:** 50 business tasks, 25 Sales + 25 Support (the suggested Phase 1 domains), drawn with a fixed seed. The task IDs are committed to `phase0/comparability_task_ids.txt` before the run. These 50 tasks must not go into Phase 1's sealed set; they may go into practice or gate.
- **Runs:** one per model per task (100 in total). Both models get the same agent prompt (the bench's own system prompt), the same `api` tools, the same 50-step cap, and the same temperature (the value Phase 1 will use, proposed 0.7). Reasoning effort is fixed per model and recorded.
- **Hosting:** Nemotron runs through one pinned OpenRouter provider (no fallbacks), and Gemini on Google AI Studio. v1's route check carries over: the run stops if a different model or host answers. The host is logged.
- **Harness:** the free Phase 0 harness (`src/jevloop/`), with caching, logging and a spend cap in code.

**Measures, per model:**
- **Primary:** mean partial credit, and the **paired difference** (Nemotron − Gemini) on the same 50 tasks, with a 95% paired bootstrap interval.
- **Also:** pass rate, run failures, cost per run (from the API's reported cost), time per run, and steps per run.
- **Run failure:** the run hits the step cap, makes a tool call our client can't parse, or ends on an API error. Errors returned by the simulated apps don't count; agents hit those normally while exploring.

**Comparability rule (fixed before the run):** Nemotron 3 Super is **comparable** if both hold:
1. its mean partial credit is **no more than 10 points below** Gemini's (paired point estimate);
2. its run-failure rate is **under 10%** (at most 4 of 50 runs).

If comparable, Nemotron 3 Super becomes the Cheap agent. If not, Gemini 3.8 Flash stays. The interval is reported either way. At n=50 it will be wide, so the check can rule out a large gap but cannot prove the models are equal.

**Order of work:**
1. Build the model-backed agent and a tool-calling OpenRouter client (free; tested on fake responses).
2. **Smoke test:** 2 tasks per model (cents). It confirms tool calls parse, route pinning holds and costs are logged, and it measures real tokens per run.
3. Estimate the check's cost from the smoke test. Alexander sets the spend cap.
4. Run the check, fill in the table, apply the rule, and record the choice here and in `PLAN.md` before any further paid run.

**Other notes:** the editor (few calls, quality matters) stays on a strong model whatever the outcome. The Strong agent is chosen separately (brief section 9, decision 3).

| Model | Host pinned | Mean credit | Pass rate | Run failures | $ / run | s / run | Steps / run |
|---|---|---|---|---|---|---|---|
| Gemini 3.8 Flash | Google AI Studio | | | | | | |
| Nemotron 3 Super | | | | | | | |
| **Difference (N − G)** | | *(95% interval)* | | | | | |

**Outcome:** *(comparable / not comparable, with date and the chosen Cheap agent)*

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
| Cheap agent model (from the comparability check) | |
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
