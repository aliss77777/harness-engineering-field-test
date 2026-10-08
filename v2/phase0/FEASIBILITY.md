# Phase 0: feasibility

**Status:** free checks done (2026-10-05); remaining steps approved 2026-10-06 within a **$10 hard cap**, enforced in code. Go/no-go for everything else (Task Brief 7, section 3).

## Plan

1. Install AutomationBench; run the Cheap agent on 20 "simple" tasks and 20 tasks from one business domain.
   **First, the cheap-agent comparability check** (below): can open-weight Nemotron 3 Super stand in for Gemini 3.8 Flash?
2. Measure cost and time per run, and the Cheap and Strong agents' pass rates.
3. Confirm we can: (a) run K independent candidates per task; (b) grade each one; (c) export a run summary with no assertion text; (d) plug in our own agent loop or wrap theirs.

## Nemotron screen (2026-10-07)

*Replaces the comparability check below and the Phase 0 spike (Alexander, 2026-10-07). The Gemini comparison moves to Phase 1, where Gemini runs on the 80 sealed tasks anyway; the same preregistered rule applies there.*

**What runs:** Nemotron 3 Super only, **4 runs on each of the 50 Finance + HR tasks** in `comparability_task_ids.txt` (still kept out of Phase 1's sealed set), with the committed settings (`config_phase0.yaml`). The smoke test's `finance:4001` run is reused as that task's run 0. Projected ≈ $4 (range $2–8) at the smoke rate; the script refuses to start if spend + 1.5 × projection would pass the $10 cap.

**Measures (all from the same 200 runs):**
- first-run pass rate and mean partial credit;
- random pick of 4 and best-of-4 (oracle) pass rate and credit: the room selection has;
- share of tasks whose 4 runs mix pass and fail;
- run-failure rate (step cap, unparseable tool call, error);
- cost, model time and steps per run; projected Phase 1 cost.

**Go/no-go (unchanged rule):** pass rate 20–80%; at least 30% of tasks with mixed pass/fail; projected Phase 1 cost within the Phase 1 cap (placeholder $60). Also reported: Nemotron's failure rate against the 10% limit of the Phase 1 comparability rule.

Results so far: paused at 19 of 200 runs on upstream rate limits (0 passes; mean credit 0.19).

### Gemini reference on the screened tasks (2026-10-07, $1.67)

Nemotron's screen had reached 6 Finance tasks (20 runs including the smoke run). Gemini 3.8 Flash ran once on each, same settings. Data: `reference_results.json`.

| Task | Gemini 3.8 Flash | Nemotron 3 Super (each run) |
|---|---|---|
| finance:4001 | 0.50 | 0, 0, 0.17, 0.17 |
| finance:4009 | **1.00 pass** | 0, 0.29, 0.29, 0.50 |
| finance:4010 | **1.00 pass** | 0, 0.33, 0.33, 0.50 |
| finance:4011 | **1.00 pass** | 0, 0, 0 |
| finance:4012 | 0 (hit the 50-step cap) | 0, 0, 0, 0.60 |
| finance:4028 | 0.20 | 0.40 |
| **Pass rate** | **3 of 6** | **0 of 20** |
| **Mean credit** | **0.62** | 0.20 (best of its runs: 0.36) |
| **Cost per run** | $0.36 | $0.033 (≈ 11× cheaper) |

**Reading it:** the setup is not the problem. Gemini passes half the tasks in our harness, inside the 20–80% band the go/no-go wants. Nemotron 3 Super trails by about 42 points of credit, far beyond the 10-point comparability margin, and even the best of its attempts per task (0.36) stays well below Gemini. On this evidence Nemotron 3 Super is not a viable Cheap agent for these tasks. Caveat: 6 tasks, all Finance; directional, not conclusive.


## Three-model comparison (2026-10-07)

One run on each of 20 tasks (first 10 Finance + first 10 HR of `comparability_task_ids.txt`; `compare_task_ids.txt`), same settings. Data: `compare_results.json`.

| | Gemini 3.8 Flash | MiniMax M3 | DeepSeek V4 Pro |
|---|---|---|---|
| Host (pinned) | Google AI Studio | Minimax (fp8) | StreamLake (fp8) |
| Pass rate | 45% | 20% | 5% |
| Finance / HR pass rate | 30% / 60% | 10% / 30% | 0% / 10% |
| Mean credit | 0.66 | 0.58 | 0.21 |
| Credit vs Gemini, 95% paired bootstrap | — | −0.08 [−0.29, +0.14] | −0.44 [−0.59, −0.30] |
| Run failures | 4/20 | 1/20 | 8/20 |
| $ / run | 0.319 | 0.062 | 0.048 |
| Model s / run | 266 | 129 | 443 |
| Steps / run | 34.0 | 20.3 | 38.0 |
| Comparability rule | reference | comparable | not comparable |

MiniMax M3 meets the preregistered comparability rule; DeepSeek V4 Pro does not. Directional at n=20 (wide interval). MiniMax's pass rate (20%) sits exactly at the bottom of the go/no-go band.

## Cheap-agent comparability check (revised 2026-10-06, Alexander; superseded 2026-10-07 — moved into Phase 1)

*Replaces the 2026-10-05 three-model bake-off (20 tasks; Gemini 3.8 Flash, Nemotron 3 Super, gpt-oss-120b). Revised because 20 tasks with one run each can't separate models on quality: each task is 5 points of pass rate. gpt-oss-120b is dropped.*

**What it is:** a stability check, not a quality ranking and not harness training. Question: **does the open-weight Nemotron 3 Super perform comparably to Gemini 3.8 Flash as the Cheap agent?** If yes, v2 runs on the much cheaper model.

**Models** (OpenRouter list prices on 2026-10-05, $ per million tokens, input / output):

| Model | Role | Open weight? | Price |
|---|---|---|---|
| `google/gemini-3.8-flash` | Reference (v1's model) | No | $0.75 / $3.75 |
| `nvidia/nemotron-3-super-120b-a12b` | Candidate | Yes | $0.08 / $0.45 (≈ 8–9× cheaper) |

**Protocol (fixed before any paid run):**
- **Tasks:** 50 business tasks, 25 Finance + 25 HR (the Phase 1 domains, adopted 2026-10-06; see `DOMAINS.md`), drawn with a fixed seed. The task IDs are committed to `phase0/comparability_task_ids.txt` before the run. These 50 tasks must not go into Phase 1's sealed set; they may go into practice or gate.
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
3. Project the check's cost from the smoke test. It runs within the **$10 hard cap for all of Phase 0** (Alexander, 2026-10-06); if the projection goes over, stop and ask.
4. Run the check, fill in the table, apply the rule, and record the choice here and in `PLAN.md` before any further paid run.

**Other notes:** the editor makes few calls and stays on Gemini 3.8 Flash, as in v1. **Gemini 3.8 Flash is also the Strong agent** (approved 2026-10-06); no frontier model.

### Smoke test (2026-10-06, $0.52 spent)

Both models, one run each, on `simple:3001` and `finance:4001` (the first Finance task of the check). Settings as committed in `config_phase0.yaml`.

| Model (host) | Task | Credit | Pass | Steps | Input tokens | Cost | Model time |
|---|---|---|---|---|---|---|---|
| Gemini 3.8 Flash (Google AI Studio) | simple:3001 | 1.00 | ✅ | 9 | 35k | $0.013 | 95 s |
| Gemini 3.8 Flash | finance:4001 | 0.50 | ❌ | 45 | 1.79M | **$0.484** | 548 s |
| Nemotron 3 Super (DeepInfra bf16) | simple:3001 | 1.00 | ✅ | 9 | 44k | $0.004 | 27 s |
| Nemotron 3 Super | finance:4001 | 0.00 | ❌ | 21 | 203k | **$0.019** | 101 s |

What it showed:
- **The plumbing works:** tool calls parse, the pinned hosts served every call, and costs are reported.
- **Bug found and fixed:** Gemini sometimes returns an empty reply (`finish_reason=error`). The first version treated that as the agent finishing and scored it 0. Now it is retried, and if it persists the run stops loudly.
- **Nemotron's 0 on finance:4001 is a real failure:** it logged invoices the AP guidelines say to hold, shifted the spreadsheet columns, and reported the wrong total. Gemini got half the checks.
- **Cost:** on this business task Gemini cost about **25× more** than Nemotron and took 5× longer, mostly because it ran 45 steps and each step re-sends the whole conversation (1.79M input tokens in total).
- **Projection:** at the smoke rate, the 50-task check costs about **$24 on Gemini + $1 on Nemotron ≈ $25**, over the $10 Phase 0 cap. **Stopped here, as agreed; waiting on Alexander.** The projection rests on one business task per model, so it is rough.
- **Cache replays are partial:** the simulator stamps clock times and random IDs into tool results, so a rerun can't replay model calls past the first write. Fix: resume by whole runs (finished runs are reloaded from the log; only missing tasks run).

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

## Numbers (Phase 0, 2026-10-07)

From the 3-model comparison (20 Finance + HR tasks, one run each) and the free failure diagnosis.

| Measure | Value |
|---|---|
| Cheap agent | **MiniMax M3** (adopted 2026-10-07) |
| Cost per run: Cheap / Strong agent | $0.062 / $0.32 (≈ 1/5) |
| Model time per run: Cheap / Strong agent | 129 s / 266 s (≈ 2× faster) |
| Pass rate: Cheap / Strong agent | 20% / 45% |
| Mean partial credit: Cheap / Strong agent | 0.58 / 0.66 (−0.08, 95% interval −0.29 to +0.14) |
| Cheap agent run failures | 1 of 20 (5%) |
| Cheap agent's failures systematic? | Yes: skips policy emails (read all in 4 of 13 runs) and breaks ≈ 3× more "must not" rules |
| Share of tasks with mixed pass/fail across K | not measured: the cascade design runs each task once, so best-of-K no longer applies |
| Projected Phase 1 cost | ≈ $80 (range $55–115); see `briefs/Phase 1 design.md` |
| Phase 0 spend | $9.41 of the $25 cap |

## Go/no-go criteria

The original criteria assumed best-of-K selection. For the cascade (`briefs/Phase 1 design.md`) they become:

- [x] **The tasks are passable in our setup:** the Strong agent passes 20–80% (Gemini 45%).
- [x] **The Cheap agent is comparable on credit:** within 10 points of the Strong agent, under 10% failed runs (MiniMax −8 points, 5%).
- [x] **The Cheap agent is much cheaper:** ≤ ⅓ of the Strong agent's cost per run, so the cascade can reach half cost (MiniMax ≈ ⅕).
- [x] **There is something to learn:** the Cheap agent's failures are systematic, not random (policy emails skipped, rules broken).
- [x] **The Cheap agent passes some tasks on its own:** pass rate ≥ 20% (MiniMax 20%, at the boundary).
- [ ] **The projected Phase 1 cost fits the Phase 1 cap:** ≈ $80 against a proposed $100 cap. Needs Alexander to set the cap.
- *Retired:* "at least 30% of tasks with mixed pass/fail across K" (a best-of-K criterion).

Caveats: 20 tasks, one run each; wide intervals; MiniMax's pass rate is exactly at the floor.

## Call

**Recommendation (Claude, 2026-10-07): GO**, with MiniMax M3 as the Cheap agent and the cascade design, if Alexander sets a Phase 1 cap of about $100.

*Decision (Alexander):* pending.

## Domains chosen

*Suggested: Support and Sales.*
