# v2: the winning harness on real business tasks

**This is the one page for tracking v2:** status, plan and progress, key results, and open decisions. Each row links to the file with the detail. [`PLAN.md`](PLAN.md) is the full dated log; [`Task Brief 7`](briefs/Task%20Brief%207_V2_Business.md) is the design.

## Status at a glance

*Updated 2026-10-06.*

| | |
|---|---|
| **Phase** | 0 — feasibility (gates everything else) |
| **Done** | AutomationBench installed and checked; free harness built (27 tests) |
| **Next** | Build the model-backed agent and its OpenRouter client (free), then a smoke test (cents) |
| **Waiting on Alexander** | Spend cap for the comparability check (after the smoke test); Strong agent shortlist; Phase 1 domains |
| **Spend so far** | $0 |

## Plan and progress

✅ done · ▶️ next · ⬜ not started

**Phase 0 — feasibility** · detail: [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md)

| Step | Status | Result / where |
|---|---|---|
| 0.1 Install AutomationBench; check its licence and tests | ✅ 2026-10-05 | MIT licence; its 1,398 tests pass; all 800 tasks load and grade |
| 0.2 Free harness: bench adapter, K runs per task, run summary, leak tests | ✅ 2026-10-05 | `src/jevloop/`; 27 tests; our own agent loop drives the bench |
| 0.3 Model-backed agent + tool-calling OpenRouter client, tested on fake responses | ▶️ | free |
| 0.4 Smoke test: 2 tasks per model | ⬜ | cents; measures tokens per run, then the check's cost |
| 0.5 Cheap-agent comparability check: Gemini 3.8 Flash vs Nemotron 3 Super, 50 tasks | ⬜ | [below](#cheap-agent-comparability-check); spend cap set after 0.4 |
| 0.6 Phase 0 spike: the Cheap agent with K runs per task, plus the Strong agent on the same tasks | ⬜ | budget set after 0.5 |
| 0.7 Go/no-go call (Alexander) | ⬜ | [criteria](phase0/FEASIBILITY.md#gono-go-criteria) |

**Phase 1 — experiments on business tasks** (preregistered in code before each paid run) · detail: [brief section 3](briefs/Task%20Brief%207_V2_Business.md)

| Experiment | Question | Status |
|---|---|---|
| V2-1 Controls | How much room is there (random pick → best of K; Cheap → Strong agent)? | ⬜ |
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
| A do-nothing agent scores | 0 on all 800 tasks (the grader drops checks already true at the start) | [FEASIBILITY](phase0/FEASIBILITY.md#free-checks-2026-10-05-no-model-calls) |
| Our own agent loop drives the bench | Yes: a hand-written solution scores 1.0 through the bench's grader | [FEASIBILITY](phase0/FEASIBILITY.md#free-checks-2026-10-05-no-model-calls) |
| Nemotron 3 Super comparable to Gemini 3.8 Flash? | *not run* | [below](#cheap-agent-comparability-check) |
| Cheap / Strong agent pass rates; share of tasks with mixed pass/fail | *not run* | Phase 0 spike |
| Go/no-go | *pending* | |

Once Phase 1 has results, the 3–5 numbered insights go here, copied verbatim from [`story/insights.yaml`](story/insights.yaml), each linked to its experiments.

## Open decisions

| Decision | Status |
|---|---|
| Repo layout | ✅ v2 is a folder in this repo (2026-10-05) |
| AutomationBench licence | ✅ MIT (2026-10-05) |
| Cheap agent | Decided by the comparability check (below) |
| Strong agent | Open: shortlist needed before step 0.6 |
| Phase 1 domains | Open: suggested Support + Sales (the comparability check uses those) |
| Spend caps | Open: the comparability check's cap after the smoke test; Phase 1 placeholder $60 |
[line omitted from the public copy]

## Cheap-agent comparability check

A **stability check, not a quality ranking or harness training**: can the open-weight **Nemotron 3 Super** (about 8–9× cheaper per token) stand in for **Gemini 3.8 Flash** as the Cheap agent? It replaces the earlier 20-task, three-model bake-off: 20 tasks can't separate models on quality, since one task is 5 points of pass rate.

- **Tasks:** 50 business tasks (25 Sales + 25 Support), fixed seed, IDs committed first. They stay out of Phase 1's sealed set.
- **Runs:** one per model per task; same prompt, tools, 50-step cap and temperature; Nemotron's provider pinned on OpenRouter.
- **Rule (fixed in advance):** Nemotron is comparable if its mean partial credit is **within 10 points** of Gemini's (paired, same tasks) **and under 10% of its runs fail**. Then it becomes the Cheap agent; otherwise Gemini stays. At n=50 the check can rule out a large gap, not prove the models equal.
- **Order:** build the agent (free) → smoke test, 2 tasks per model (cents) → Alexander sets the cap → run.

Full protocol and results table: [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md#cheap-agent-comparability-check-revised-2026-10-06-alexander).

## The question

v1 showed, on public benchmarks, that a learned yes/no rubric (the **Jev rubric loop**) learns from outcomes when an LLM doesn't, and that a **Router** gives LLM-level quality at less than half the cost. v2 asks whether that holds on real business work: the graded workflow tasks in Zapier's AutomationBench. Results from v1: [`../v1/RESULTS.md`](../v1/RESULTS.md).

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

> A cheap agent plus a learned checker matches a strong agent on real business tasks at half the cost.

That is the claim a business actually cares about.

*Terminology: in [Task Brief 7](briefs/Task%20Brief%207_V2_Business.md), **Phase 1** is the experiments on the new data and **Phase 2** is the Magic Patterns UI and tutorial.*
