# v2: the winning harness on real business tasks

**Main focus (Alexander, 2026-10-06):** an **open-weight agent plus Jev**, improved by a self-learning harness, against **Gemini 3.8 Flash** on back-office business tasks (Finance and HR). The hoped-for result, as in v1: *as good as Gemini Flash, but cheaper and faster.*

**This is the one page for tracking v2:** status, plan and progress, key results, and open decisions. Each row links to the file with the detail. [`PLAN.md`](PLAN.md) is the full dated log; [`Task Brief 7`](briefs/Task%20Brief%207_V2_Business.md) is the design.

## Status at a glance

*Updated 2026-10-07.*

| | |
|---|---|
| **Phase** | 0 — feasibility (gates everything else); remaining steps approved 2026-10-06 |
| **Spend cap** | $10 for all of Phase 0, enforced in code |
| **Done** | AutomationBench installed and checked; free harness built; domain analysis; focus and models decided |
| **Now** | ⏸️ Nemotron screen **paused**: 18 of 200 runs done. The pinned host (DeepInfra via OpenRouter's shared capacity) rate-limits about half the calls, and the run stopped twice after retries ran out |
| **Waiting on Alexander** | How to unblock the screen: (1) add your own DeepInfra key to OpenRouter (recommended; settings unchanged), (2) switch to the fp8 host DekaLLM (a logged deviation), or (3) 2 runs per task instead of 4 |
| **Spend so far** | $0.52 of the $10 Phase 0 cap |

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
| 0.5 Nemotron screen: 4 runs on each of the 50 Finance + HR tasks (replaces the comparability check and the spike) | ⏸️ | 18/200 runs; paused on upstream rate limits; [why](#cheap-agent-comparability-moved-into-phase-1) |
| 0.6 ~~Spike~~ | merged into 0.5 | the Gemini comparison moves to Phase 1's sealed set |
| 0.7 Go/no-go call (Alexander) | ⬜ | [criteria](phase0/FEASIBILITY.md#gono-go-criteria) |

**Phase 1 — experiments on business tasks** (preregistered in code before each paid run) · detail: [brief section 3](briefs/Task%20Brief%207_V2_Business.md)

| Experiment | Question | Status |
|---|---|---|
| V2-1 Controls | How much room is there (random pick → best of K; Cheap → Strong agent)? Includes the **Nemotron vs Gemini comparability test** on the 80 sealed tasks | ⬜ |
| V2-2 Learning | Do the Jev rubric loop and the Agent skill loop learn on business tasks? | ⬜ |
| V2-3 Router (headline) | Does routing keep Strong-agent quality for less? | ⬜ |
| V2-4 Partial feedback (optional) | Does it still learn without an answer key? | ⬜ |

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
| Nemotron 3 Super: pass rate, failures, varied runs, best-of-4 on 50 tasks | *running* | [FEASIBILITY](phase0/FEASIBILITY.md#nemotron-screen-2026-10-07) |
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
| Cheap agent | Nemotron 3 Super (open weight), subject to the Phase 0 go/no-go; comparability with Gemini tested in Phase 1 |
| Strong agent, editor, escalation judge | ✅ Gemini 3.8 Flash, v1's model (2026-10-06). No frontier LLM |
| Phase 1 domains | ✅ **Finance + HR** ([analysis](phase0/DOMAINS.md), 2026-10-06) |
| Spend caps | ✅ Phase 0: $10 hard cap (2026-10-06). ✅ Lean budget ≈ $60 in total (2026-10-07). Phase 1 cap: set after Phase 0 (placeholder $60) |
| Agent skill loop in Phase 1 | Optional, as in the brief; not in the lean plan (+≈ $40 if added) |
[line omitted from the public copy]

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
| *Optional, not in the lean plan:* Agent skill loop | each candidate edit re-runs the agent (≈ 2,100 Nemotron runs) | +≈ $40 | +$21–84 |

- **Phase 0 cap: $10, enforced in code.** The screen projects to ≈ $4.
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
| **Cheap agent** | An open-weight LLM: Nemotron 3 Super, if the comparability check passes (otherwise Gemini 3.8 Flash) | Does each task K times, calling the tools |
| **Strong agent** | Gemini 3.8 Flash, v1's model (approved 2026-10-06; no frontier LLM) | New in v2. The baseline v2 must match ("as good as a strong agent, for less") and, under escalation option B, the fallback that re-does a task Jev isn't confident about. Under option A an LLM judge picks among the K runs instead, which is v1's exact escalation |
| **Jev** | The decision model from v1 (`typesafe/jev-1.13` via OpenRouter) | Answers the rubric's yes/no questions about each run's summary, so the runs can be scored. It never calls tools or does the task. |
| **Router** | Code | Keeps Jev's top-scoring run when Jev is confident; otherwise escalates to the Strong agent |
| **Editor** | An LLM; in v1, Gemini 3.8 Flash (few calls) | **Same role as in v1:** the learning step. After each practice round it reads the mistakes and proposes one edit, to the rubric (Jev rubric loop) or to the agent's skill file (Agent skill loop); the gate keeps or rejects it. Without it there is selection but no learning |

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
