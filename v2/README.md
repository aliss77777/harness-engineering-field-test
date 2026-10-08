# v2: the winning harness on real business tasks

**Core question (revised 2026-10-07):** *can a self-learning harness make an open-weight agent learn from its own mistakes, with Jev learning when to trust it, so the system matches Gemini Flash on real back-office work, cheaper and faster?*

**Main focus (Alexander, 2026-10-06):** an **open-weight agent (MiniMax M3, adopted 2026-10-07) plus Jev**, improved by a self-learning harness, against **Gemini 3.8 Flash** on back-office business tasks (Finance and HR). The hoped-for result, as in v1: *as good as Gemini Flash, but cheaper and faster.*

**The learning story (2026-10-07):** two things learn, with **no help from Gemini**. In the **Agent skill loop**, MiniMax reads its own graded mistakes and rewrites its own playbook (Phase 0 showed it skips the policy emails and breaks the rules they set). In the **Jev rubric loop**, the checker learns what a correct MiniMax run looks like, so it knows when to trust MiniMax. MiniMax is the editor in both loops; Gemini is only the baseline and the fallback. A **cascade** then keeps MiniMax's runs Jev is confident in and hands the rest to Gemini. As both improve, fewer tasks need Gemini.

**This is the one page for tracking v2:** status, plan and progress, key results, and open decisions. Each row links to the file with the detail. [`PLAN.md`](PLAN.md) is the full dated log; [`Task Brief 7`](briefs/Task%20Brief%207_V2_Business.md) is the design.

## Status at a glance

*Updated 2026-10-07.*

| | |
|---|---|
| **Phase** | 0 — feasibility: **done; go/no-go call pending** (recommendation: GO). Phase 1 designed: [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md) |
| **Spend cap** | $25 for all of Phase 0, enforced in code (raised from $10 on 2026-10-07 for the 3-model comparison) |
| **Done** | AutomationBench installed and checked; free harness built; domain analysis; focus and models decided |
| **Nemotron screen** | ⏸️ Stopped at 19/200 runs (upstream rate limits); superseded: Nemotron is out (0/20 passes) |
| **Latest** | 3-model comparison done: **MiniMax M3 is comparable to Gemini 3.8 Flash** (credit 0.58 vs 0.66, at ≈ 1/5 the cost and 2× the speed), but passes 4 of 20 vs Gemini's 9. DeepSeek V4 Pro and Nemotron 3 Super are out ([results](#phase-0-results-so-far)) |
| **Latest** | Free diagnosis: **MiniMax's failures are systematic**: it skips the policy emails (read all of them in 4 of 13 runs vs Gemini's 12 of 12) and breaks ~3× more "must not" rules. Teachable, so it supports bringing back the Agent skill loop ([details](#phase-0-results-so-far)) |
| **Waiting on Alexander** | The go/no-go call (0.7) and the Phase 1 cap (proposed $100; Phase 1 projects to ≈ $80) |
| **Spend so far** | $9.41 of the $25 Phase 0 cap |

## Plan and progress

✅ done · ▶️ next · ⏸️ paused · ⬜ not started

**Phase 0 — feasibility** · detail: [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md)

| Step | Status | Result / where |
|---|---|---|
| 0.1 Install AutomationBench; check its licence and tests | ✅ 2026-10-05 | MIT licence; its 1,398 tests pass; all 800 tasks load and grade |
| 0.2 Free harness: bench adapter, K runs per task, run summary, leak tests | ✅ 2026-10-05 | `src/jevloop/`; 27 tests; our own agent loop drives the bench |
| 0.2b Domain analysis: anatomy of a task; which tasks fit back-office work | ✅ 2026-10-06 | [`phase0/DOMAINS.md`](phase0/DOMAINS.md): **Finance + HR adopted** |
| 0.3 Model-backed agent + tool-calling OpenRouter client, tested on fake responses | ✅ 2026-10-06 | `src/jevloop/openrouter.py`, `llm_agent.py`; 42 tests |
| 0.4 Smoke test: 2 tasks per model | ✅ 2026-10-06 | $0.52. Both pass the simple task; one business task cost $0.48 on Gemini vs $0.019 on Nemotron. [Results](phase0/FEASIBILITY.md#smoke-test-2026-10-06-052-spent) |
| 0.5 Nemotron screen | ⏹️ stopped at 19/200 (rate limits); Nemotron out (0/20 passes) | [results](#phase-0-results-so-far) |
| 0.5b 3-model comparison: Gemini vs MiniMax M3 vs DeepSeek V4 Pro, 20 tasks | ✅ 2026-10-07 | MiniMax comparable at ≈ 1/5 the cost; [results](#phase-0-results-so-far) |
| 0.5c Free failure diagnosis | ✅ 2026-10-07 | MiniMax's failures are systematic and teachable |
| 0.5d Phase 1 design (cascade + two learning loops) | ✅ 2026-10-07 | [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md) |
| 0.6 ~~Spike~~ | merged into 0.5 | the Gemini comparison moves to Phase 1's sealed set |
| 0.7 Go/no-go call (Alexander) | ▶️ recommendation: GO | [criteria and numbers](phase0/FEASIBILITY.md#gono-go-criteria) |

**Phase 1 — experiments on business tasks** (verdict rules preregistered in code before each paid run) · design: [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md)

| Experiment | Question | Status |
|---|---|---|
| V2-1 Controls | Where do we start? MiniMax (v0 skill) vs Gemini on the 80 sealed tasks | ⬜ |
| V2-2a Agent skill loop | Does MiniMax learn its playbook? (final skill vs v0 on sealed) | ⬜ |
| V2-2b Jev rubric loop | Does the checker learn what a correct MiniMax run looks like? | ⬜ |
| V2-3 Router (headline) | Cascade: MiniMax once → Jev keeps or escalates to Gemini. As good as Gemini (±3 points), at ≤ ½ the cost, and faster? | ⬜ |
| V2-4 Partial feedback | not run (out of budget) | — |

**Phase 2 — Magic Patterns UI and tutorial**

| Step | Status | Where |
|---|---|---|
| 2a Harden the story: insights, experiment template, generated `ui-data/` | ⬜ (scaffold ready) | [`story/insights.yaml`](story/insights.yaml), [`experiments/_TEMPLATE.md`](experiments/_TEMPLATE.md) |
| 2b Build the UI with Magic Patterns (minimum bar: [`v1/ui-demo-2`](../v1/ui-demo-2/README.md)) | ⬜ | |
| 2c Tutorial chapters | ⬜ (stubs) | [`tutorial/`](tutorial/) |

## Key results

| Result | Value | Where |
|---|---|---|
| Best-fit domains for back-office work | Finance + HR, adopted (Operations in reserve) | [DOMAINS](phase0/DOMAINS.md) |
| A do-nothing agent scores | 0 on all 800 tasks (the grader drops checks already true at the start) | [FEASIBILITY](phase0/FEASIBILITY.md#free-checks-2026-10-05-no-model-calls) |
| Our own agent loop drives the bench | Yes: a hand-written solution scores 1.0 through the bench's grader | [FEASIBILITY](phase0/FEASIBILITY.md#free-checks-2026-10-05-no-model-calls) |
| Cost per business-task run, smoke test (one task) | Gemini 3.8 Flash $0.48 vs Nemotron 3 Super $0.019 (≈ 25× cheaper, 5× faster on that task) | [FEASIBILITY](phase0/FEASIBILITY.md#smoke-test-2026-10-06-052-spent) |
| **Gemini vs MiniMax M3 vs DeepSeek V4 Pro, 20 tasks** | Credit 0.66 / **0.58** / 0.21; passes 9 / 4 / 1; $0.32 / **$0.062** / $0.048 per run. MiniMax comparable under the preregistered rule | [results](#phase-0-results-so-far) |
| Gemini vs Nemotron on 6 Finance tasks (directional) | Gemini **3/6 passes, credit 0.62, $0.36/run**; Nemotron **0/20, credit 0.20, $0.033/run**. Nemotron trails by ≈ 42 points | [FEASIBILITY](phase0/FEASIBILITY.md#gemini-reference-on-the-screened-tasks-2026-10-07-167) |
| Nemotron 3 Super comparable to Gemini 3.8 Flash? | *Phase 1 (V2-1, sealed set)* | [below](#cheap-agent-comparability-moved-into-phase-1) |
| Cheap / Strong agent pass rates; share of tasks with mixed pass/fail | *not run* | Phase 0 spike |
| Go/no-go | *pending* | |

Once Phase 1 has results, the 3–5 numbered insights go here, copied verbatim from [`story/insights.yaml`](story/insights.yaml), each linked to its experiments.

## Open decisions

| Decision | Status |
|---|---|
| Repo layout | ✅ v2 is a folder in this repo (2026-10-05) |
| AutomationBench licence | ✅ MIT (2026-10-05) |
| Experiment focus | ✅ Open-weight agent + Jev vs Gemini 3.8 Flash (2026-10-06) |
| Cheap agent | ✅ **MiniMax M3** (open weight; comparable to Gemini on 20 tasks; adopted by Alexander 2026-10-07). Nemotron 3 Super and DeepSeek V4 Pro out |
| Strong agent, editor, escalation judge | ✅ Gemini 3.8 Flash, v1's model (2026-10-06). No frontier LLM |
| Phase 1 domains | ✅ **Finance + HR** ([analysis](phase0/DOMAINS.md), 2026-10-06) |
| Spend caps | ✅ Phase 0: $10 hard cap (2026-10-06). ✅ Lean budget ≈ $60 in total (2026-10-07). Phase 1 cap: set after Phase 0 (placeholder $60) |
| Agent skill loop in Phase 1 | ✅ **Back in, lean version** (Alexander, 2026-10-07), supported by the failure diagnosis. MiniMax learns only from its own graded outcomes, **never from Gemini's runs** |
| Router design | ✅ **Cascade**, not best-of-K (2026-10-07) |
| Editor for both loops | ✅ **MiniMax M3** (2026-10-07): no Gemini judgement inside the loops |
| Core question | ✅ Revised 2026-10-07 (top of this page) |
| Phase 1 cap | Open: proposed $100 (Phase 1 projects to ≈ $80) |
[line omitted from the public copy]

## Phase 0 results so far

*Updated 2026-10-07. Phase 0 spend: $9.41 of the $25 cap.*

**1. Our harness works on business tasks.** In the smoke test both models solved a simple task end to end, and the grader, tool calls, pinned hosts and cost logging all behaved. Two bugs were found and fixed on the way: empty provider replies were briefly scored as "agent finished" (now retried), and reruns couldn't replay cached calls because the simulator stamps clock times and random IDs (now resumed by whole runs).

**2. Gemini 3.8 Flash vs Nemotron 3 Super on 6 Finance tasks:**

| Task | Gemini 3.8 Flash | Nemotron 3 Super (each run) |
|---|---|---|
| finance:4001 | 0.50 | 0, 0, 0.17, 0.17 |
| finance:4009 | **1.00 pass** | 0, 0.29, 0.29, 0.50 |
| finance:4010 | **1.00 pass** | 0, 0.33, 0.33, 0.50 |
| finance:4011 | **1.00 pass** | 0, 0, 0 |
| finance:4012 | 0 (hit the 50-step cap) | 0, 0, 0, 0.60 |
| finance:4028 | 0.20 | 0.40 |
| **Pass rate** | **3 of 6** | **0 of 20** |
| **Mean partial credit** | **0.62** | 0.20 (best of its runs per task: 0.36) |
| **Cost per run** | $0.36 | $0.033 (≈ 11× cheaper) |

- **The tasks are passable in our setup:** Gemini passes half, inside the 20–80% band the go/no-go wants.
- **Nemotron 3 Super is not a viable Cheap agent here:** it trails by about 42 points of credit, far past the 10-point margin, and even its best attempt per task stays well below Gemini. Cheaper doesn't help if it can't do the work.
- **Why only 6 of the 50 tasks:** the screen was meant to run all 50 tasks × 4 attempts. It worked task by task (all 4 attempts on one task before the next), and upstream rate limits at Nemotron's host stopped it after the first 6 Finance tasks. The other 44 tasks (19 Finance, all 25 HR) were never reached, so this result is **directional, not conclusive**, and says nothing yet about HR. Lesson applied: future runs go **breadth first** (attempt 1 on every task before attempt 2).

**3. Three models, one run on each of 20 tasks (10 Finance, 10 HR), 2026-10-07:**

| | **Gemini 3.8 Flash** | **MiniMax M3** (open weight) | DeepSeek V4 Pro (open weight) |
|---|---|---|---|
| Pass rate (all 20) | **45%** (9) | 20% (4) | 5% (1) |
| Pass rate: Finance / HR | 30% / 60% | 10% / 30% | 0% / 10% |
| Mean partial credit | **0.66** | **0.58** | 0.21 |
| Credit vs Gemini (paired, 95% interval) | — | **−0.08** [−0.29, +0.14] | −0.44 [−0.59, −0.30] |
| Run failures (step cap, unparseable call, error) | 4 of 20 (all step cap) | **1 of 20** | 8 of 20 |
| Cost per run | $0.32 | **$0.062 (≈ 1/5 of Gemini)** | $0.048 |
| Model time per run | 266 s | **129 s (≈ 2× faster)** | 443 s |
| Steps per run | 34 | 20 | 38 |
| **Preregistered comparability rule** (credit within 10 points, failures under 10%) | reference | **✅ comparable** | ❌ not comparable |

- **MiniMax M3 passes the comparability rule:** 8 points of credit below Gemini, at about a fifth of the cost and twice the speed, with fewer failed runs than Gemini itself. On HR it nearly matches Gemini on credit (0.67 vs 0.70).
- **But it passes fewer tasks outright:** 4 against Gemini's 9. Partial credit is close; finishing every check is where it falls short. Closing exactly that gap is the job v2 gives the Jev rubric and the Router: pick MiniMax's best attempt, escalate the rest.
- **DeepSeek V4 Pro is out:** it often wanders until the 50-step cap (8 of 20 runs).
- **Caveats:** 20 tasks, one run each, so the interval is wide (−29 to +14 points). This is a directional read, not proof of equivalence. Gemini's own 4 step-cap hits show the 50-step limit binds on the longest tasks.

**4. Nemotron 3 Super** (6 Finance tasks, above) is out: 0 passes in 20 runs.

**5. Why MiniMax misses checks: a free diagnosis (2026-10-07, $0).** Each recorded run was replayed through a fresh copy of its world and graded check by check (`scripts/diagnose_failures.py`; all 20 MiniMax runs reproduced their scores exactly).

| | Gemini 3.8 Flash | MiniMax M3 | DeepSeek V4 Pro |
|---|---|---|---|
| Missed checks (20 tasks) | 39 | 52 | 106 |
| Of which: required action never taken | 51% | 35% | 62% |
| Of which: action taken, required values missing | 31% | 29% | 16% |
| Of which: **broke a "must not" rule** | 18% (7) | **37% (19)** | 22% (23) |
| Read every policy email (tasks that have one) | **12 of 12** | **4 of 13** | 7 of 13 |
| Steps per run | 33 | 20 | 38 |

| MiniMax, tasks with policy emails | Runs | Mean credit | Broken "must not" rules | Passes |
|---|---|---|---|---|
| Read every policy email | 4 | 0.55 | 2 | 1 |
| **Skipped at least one** | 9 | 0.41 | **11** | 0 |

- **MiniMax's failures are systematic: it acts before reading the rules.** It often stops early (its worst runs are 8–13 steps), skips the policy emails, and then breaks the rules those emails set. Gemini reads every policy email and breaks far fewer rules.
- **That is teachable.** It is a behaviour fix ("read every policy email and reference sheet before acting; handle every item"), exactly what the Agent skill loop edits. So the diagnosis supports bringing the skill loop back.
- **DeepSeek's problem is different:** it reads but gets lost and runs out of steps, consistent with dropping it.
- **Caveats:** 13 tasks with policy emails; "policy email" is detected by keywords in the subject and opening lines, so it is approximate; and correlation is not proof (skipped tasks might also be harder, though Gemini read and did well on the same tasks).

<details><summary>Plan for the three-model comparison, as approved</summary>

**Approved 2026-10-07: one run on each of 20 tasks for three models**: Gemini 3.8 Flash vs two open-weight candidates, **DeepSeek V4 Pro** (pinned to StreamLake, fp8) and **MiniMax M3** (pinned to MiniMax's own host, fp8). The 20 tasks are the first 10 Finance and first 10 HR of the committed list (`phase0/compare_task_ids.txt`), including the 6 Gemini has already run (reused). Same settings as before. Estimated ≈ $8–18; **Phase 0 cap raised to $25** (Alexander, 2026-10-07). Read: each model's pass rate and credit across Finance and HR, cost and time per run, and the paired gap to Gemini under the preregistered comparability rule (directional at 20 tasks).

</details>

## Budget

*Approved 2026-10-07 (Alexander): the lean plan, with the comparability check folded into Phase 1. Estimates from the smoke test (one business task per model: Gemini 3.8 Flash $0.48 per run, Nemotron 3 Super $0.019), so they are rough.*

| Step | What runs | Central | Range |
|---|---|---|---|
| Phase 0, spent | smoke test | $0.52 | — |
| Phase 0, Nemotron screen | 4 runs × 50 Finance + HR tasks = 200 Nemotron runs | ≈ $4 | $2–8 |
| Phase 1, Nemotron runs | 4 runs × 200 tasks = 800 runs (the Jev rubric loop re-scores these; no new agent runs per round) | ≈ $15 | $8–32 |
| Phase 1, Gemini baseline | 1 run × 80 sealed tasks (also the paired comparability test) | ≈ $38 | $20–48 |
| Phase 1, Jev + editor + escalation judge | small calls | ≈ $3 | $2–5 |
| **Total, lean plan** | | **≈ $60** | **$33–93** |
| *Superseded:* the plan above assumed Nemotron and best-of-4. Phase 1 is now the cascade with both learning loops: **≈ $80** (range $55–115), [design](briefs/Phase%201%20design.md#budget) | | | |

- **Phase 0 cap: $25, enforced in code** (raised from $10 on 2026-10-07 for the 3-model, 20-task comparison).
- **Phase 1 cap: placeholder $60**, to be set after Phase 0 (the lean plan's Phase 1 is ≈ $56).
- **The Agent skill loop is optional** (as in the brief): not in the lean plan; it runs only if Alexander adds it later (+≈ $40).
- **Not adopted** (Alexander, 2026-10-07): Gemini's half-price flex tier (its timings would not fairly test "faster"); reusing Gemini's sealed runs as option-B escalations.

## Cheap-agent comparability: moved into Phase 1

*Revised 2026-10-07.* Comparing Nemotron 3 Super with Gemini 3.8 Flash on 50 Phase 0 tasks would have cost ≈ $25, mostly Gemini, and Phase 1 runs the same comparison anyway: Gemini on the 80 sealed tasks against Nemotron's runs. So the comparison happens there, on more tasks, with the same preregistered rule (Nemotron comparable if its mean partial credit is within 10 points of Gemini's, paired, and under 10% of its runs fail).

**Phase 0 instead screens Nemotron alone** on the same 50 Finance + HR tasks (`phase0/comparability_task_ids.txt`, kept out of the sealed set), 4 runs each, for the go/no-go numbers: its pass rate, run failures, the share of tasks where its runs differ, best-of-4, and cost per run. The trade-off: if Nemotron turns out far behind Gemini, we learn it in Phase 1, after its ≈ $15 of runs, rather than before. Details: [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md#nemotron-screen-2026-10-07).

## The question

v1 showed, on public benchmarks, that a learned yes/no rubric (the **Jev rubric loop**) learns from outcomes when an LLM doesn't, and that a **Router** gives LLM-level quality at less than half the cost. v2 asks whether that holds on real back-office work (the Finance and HR tasks in Zapier's AutomationBench) with a cheaper worker: **can an open-weight agent plus Jev, improved by a self-learning harness, be as good as Gemini 3.8 Flash, but cheaper and faster?** Results from v1: [`../v1/RESULTS.md`](../v1/RESULTS.md).

## Where things are

| | |
|---|---|
| [`STORY.md`](STORY.md) | The narrative: question → approach → insights → caveats → next |
| [`story/insights.yaml`](story/insights.yaml) | Single source of truth for headline sentences and key numbers |
| [`RESULTS.md`](RESULTS.md) | One page: scorecard + learning table |
| [`GLOSSARY.md`](GLOSSARY.md) | One name per concept |
| [`PLAN.md`](PLAN.md) | Dated log of every decision, deviation and fix |
| [`briefs/`](briefs/) | One brief per experiment, preregistration included |
| [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md) | Feasibility numbers and the go/no-go call |
| [`phase0/DOMAINS.md`](phase0/DOMAINS.md) | Anatomy of a task (the atomic unit) and which domains fit back-office work |
| [`experiments/`](experiments/) | One folder per experiment, README from [`_TEMPLATE.md`](experiments/_TEMPLATE.md) |
| [`ui-data/`](ui-data/) | Generated by `scripts/export_ui_data.py`; never hand-edited |
| `scripts/` `src/` `tests/` | Harness code (ported from v1), tests, supervisor |
[line omitted from the public copy]

## How to run

Everything runs from inside this folder (`cd v2`). Python 3.13 (AutomationBench requires it).

1. Download AutomationBench into `z-ignore/AutomationBench-main` (git-ignored).
2. `python3.13 -m venv .venv && .venv/bin/python -m pip install -e z-ignore/AutomationBench-main -r requirements.txt`
3. Tests: `.venv/bin/python -m pytest -q`
4. Free end-to-end check (no model calls): `.venv/bin/python scripts/phase0_free_check.py`
5. Regenerate UI data: `.venv/bin/python scripts/export_ui_data.py`

Harness code is in `src/jevloop/` (`bench.py` is the only module that touches AutomationBench). Model-backed agents come after the Phase 0 model choice.

## Methodology appendix: what changes from v1, and why

> "this is exponentially more complicated than the harness experiment in v1; but it seems like the appropriate jump in difficulty, from a lab experiment to a real world task."
>
> — Alexander, 2026-10-06, on seeing the anatomy of an AutomationBench task ([`phase0/DOMAINS.md`](phase0/DOMAINS.md#anatomy-of-a-task-the-experiments-atomic-unit))

### Who does what: agents do the work, Jev checks it

| Role | What it is | What it does |
|---|---|---|
| **Cheap agent** | An open-weight LLM: **MiniMax M3** (adopted 2026-10-07 after Phase 0's comparison) | Does each task K times, calling the tools |
| **Strong agent** | Gemini 3.8 Flash, v1's model (approved 2026-10-06; no frontier LLM). Baseline and fallback only; never an editor or teacher | New in v2. The baseline v2 must match ("as good as a strong agent, for less") and, under escalation option B, the fallback that re-does a task Jev isn't confident about. Under option A an LLM judge picks among the K runs instead, which is v1's exact escalation |
| **Jev** | The decision model from v1 (`typesafe/jev-1.13` via OpenRouter) | Answers the rubric's yes/no questions about each run's summary, so the runs can be scored. It never calls tools or does the task. |
| **Router** | Code | **A cascade** (2026-10-07): MiniMax runs the task once; if Jev is confident the run is right, it is kept; otherwise Gemini does the task |
| **Editor** | **MiniMax M3, editing its own playbook and Jev's rubric** (2026-10-07; in v1 the model edited its own instructions) | **Same role as in v1:** the learning step. After each practice round it reads the mistakes and proposes one edit, to the rubric (Jev rubric loop) or to the agent's skill file (Agent skill loop); the gate keeps or rejects it. Without it there is selection but no learning |

Jev enters in Phase 1. Phase 0 only measures the agents.

### Does v1's improvement loop carry over?

The mechanics carry over unchanged: practice → mistakes → one edit → held-out gate → keep or reject. Whether it still *learns* here is what V2-2 tests. What changes:

- **For the rubric, the hard part shrinks back to v1's problem.** Two runs of the same task, one passing and one failing, are a v1-style pair with a known winner. The editor compares their summaries, and the difference is visible (for example, one run emailed the customer on a payment plan). This is the strongest reason to expect the rubric loop to keep learning.
- **It only works when runs differ.** If all K runs fail, there is nothing to pick between; only escalation helps. That is why the go/no-go needs at least 30% of tasks with mixed pass/fail.
- **Credit assignment is harder for the agent's skill file.** A failed run is up to 50 steps, and the editor has to find the step that went wrong. Agent runs are also noisy, so the gate needs several runs per task to tell a real improvement from luck, which makes this loop expensive.
- **Lessons must transfer across workflows.** v1's items were all the same kind (headline pairs, response pairs). Here every task is a different workflow, so a kept edit has to be general ("Did it apply the policy it found in the inbox?") rather than specific. The held-out gate enforces this, but it may reject more edits, so learning could be slower.
- **Less data, richer signal.** About 200 tasks instead of thousands of pairs, so less statistical power; but partial credit is a much denser signal than v1's single right/wrong per item.


**Short version:** the harness barely changes. What changes is *what the system is doing*, and that is the point of v2.

### v1 predicted a judgment; v2 does the work

- **v1: predicting a judgment.** We gave the system two existing responses or headlines and asked it to predict which one a human preferred. The outcome was someone else's vote or click. That was useful for proving the learning loop works. But in a business you rarely need to guess which of two finished things a stranger liked.
- **v2: doing the work and being graded on whether it worked.** In AutomationBench an agent actually performs a business task: update the CRM, route the ticket, file the expense. The grade is whether the systems end up in the correct state, checked automatically against the task's assertions. That is much closer to production: **the reward is "did the job get done correctly"**, not a human's taste.

### What stays the same: the harness

- **A policy written as text, learning in batches.** Each round runs practice, grading, and one edit at a time. A held-out gate decides whether an edit is kept. A sealed set is used once, at the end.
- **The Jev rubric loop**, with code-fitted weights.
- **The Router.** Jev handles the confident cases; the more expensive model handles the hard ones.
- **Every lesson from v1:** preregistration, single edits, memory of rejected edits, the spend cap, and the supervisor that resumes from cache (see [`../v1/RESULTS.md`](../v1/RESULTS.md), "What the harness taught us").

### The one real adaptation: the agent produces the candidates

In v1 the two candidates were given; in v2 the agent has to produce them. So the **Cheap agent** runs each task a few times (K runs):

1. The Jev rubric checks each run, e.g. "Did it update the right record?"
2. If Jev is confident, its best run is kept.
3. If not, the task escalates to the **Strong agent** (or an LLM judge chooses among the runs).

It is the same select-or-escalate **Router** as v1's experiment 5. It now works on the agent's own attempts instead of someone else's responses.

### What gets learned shifts, in a business-relevant way

- **The Jev rubric loop** learns what a correct run looks like in each business domain.
- **The Agent skill loop** learns how to do the task: the agent's skill file, effectively the company's playbook for the agent, improving from graded outcomes.

*Note (2026-10-07): Phase 0 replaced best-of-K with a **cascade** (MiniMax runs once; Jev keeps confident runs; Gemini does the rest), because at MiniMax's price four runs plus escalation cost more than Gemini alone. Both learning loops below still apply. See [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md).*

### Best-of-K is the picking step; the v1 learning loop still runs on top

Two things learn, round by round.

**1. The Jev rubric (the checker).** Same loop as v1:
- **Practice:** Jev scores the agent's K runs on practice tasks, and we see which runs actually passed.
- **Mistakes:** the editor sees the runs Jev ranked wrong and proposes one edit. For example, *add "Did it notify the account owner?"*, or drop or reword a question.
- **Gate:** the edit is kept only if picks improve on held-out tasks.
- **Weights:** refit from the graders' partial credit, as in v1's B+.
- **Over rounds:** the rubric learns what "done correctly" means in each business domain.

**2. The agent's skill file (its playbook).** Mirrors v1's LLM loop:
- **Failures:** the editor sees failed runs and which grading checks were missed. For example, *"forgot to update the ticket status."*
- **Edit:** one targeted fix to the instructions. For example, *"Always close the ticket after replying."*
- **Gate:** kept only if the pass rate improves on held-out tasks.
- **Cost note:** this is the expensive part (every candidate edit re-runs the agent), so it is optional in the lean plan.

**Same v1 rules throughout:** single edits, memory of rejected edits, fresh mistakes each round, the held-out gate, a sealed set used once, and preregistration.

**Net effect over time:**
- The agent makes better attempts.
- The checker picks better among them.
- The Router escalates less as Jev's confidence becomes trustworthy.

All three show up as accuracy gains or cost cuts on the sealed set.

### The claim v2 can make, if it works

> An open-weight agent plus a learned checker (Jev) matches Gemini Flash on real back-office tasks, cheaper and faster.

That is the claim a business actually cares about.

*Terminology: in [Task Brief 7](briefs/Task%20Brief%207_V2_Business.md), **Phase 1** is the experiments on the new data and **Phase 2** is the Magic Patterns UI and tutorial.*
