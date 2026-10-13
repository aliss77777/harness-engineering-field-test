# Methodology: what changes from v1, and why

*Moved here from the README on 2026-10-07. The current design is [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md); where this page describes the earlier best-of-K plan, a note says so. The story of how the design changed is in [`JOURNEY.md`](JOURNEY.md).*

> "this is exponentially more complicated than the harness experiment in v1; but it seems like the appropriate jump in difficulty, from a lab experiment to a real world task."
>
> — Alexander, 2026-10-06, on seeing the anatomy of an AutomationBench task ([`phase0/DOMAINS.md`](phase0/DOMAINS.md#anatomy-of-a-task-the-experiments-atomic-unit))

### Who does what: agents do the work, Jev checks it

| Role | What it is | What it does |
|---|---|---|
| **Cheap agent** | An open-weight LLM: **MiniMax M3** (adopted 2026-10-07 after Phase 0's comparison) | Does each task **once** (the cascade), calling the tools; learns from its own mistakes in the Agent skill loop |
| **Strong agent** | Gemini 3.8 Flash, v1's model (approved 2026-10-06; no frontier LLM). Baseline and fallback only; never an editor or teacher | New in v2. The baseline v2 must match ("as good as Gemini, for less") and the cascade's fallback: it does the task when Jev isn't confident in MiniMax's run |
| **Jev** | The decision model from v1 (`typesafe/jev-1.13` via OpenRouter) | Answers the rubric's yes/no questions about each run's summary, so the runs can be scored. It never calls tools or does the task. |
| **Router** | Code | **A cascade** (2026-10-07): MiniMax runs the task once; if Jev is confident the run is right, it is kept; otherwise Gemini does the task |
| **Editor** | **MiniMax M3, editing its own playbook and Jev's rubric** (2026-10-07; in v1 the model edited its own instructions) | **Same role as in v1:** the learning step. After each practice round it reads the mistakes and proposes one edit, to the rubric (Jev rubric loop) or to the agent's skill file (Agent skill loop); the keep-or-reject test keeps or rejects it. Without it there is selection but no learning |

Jev enters in Phase 1. Phase 0 only measured the agents.

### Does v1's improvement loop carry over?

The mechanics carry over unchanged: practice → mistakes → one edit → held-out keep-or-reject test → keep or reject. Whether it still *learns* here is what V2-2 tests. What changes:

- **For the rubric, the hard part shrinks back to v1's problem.** Two runs of the same task, one passing and one failing, are a v1-style pair with a known winner. The editor compares their summaries, and the difference is visible (for example, one run emailed the customer on a payment plan). This is the strongest reason to expect the rubric loop to keep learning.
- ~~**It only works when runs differ.**~~ *Superseded 2026-10-07: the cascade runs each task once, so this best-of-K condition no longer applies.*
- **Credit assignment is harder for the agent's skill file.** A failed run is up to 50 steps, and the editor has to find the step that went wrong. Agent runs are also noisy, so a single run per test bench task can mistake luck for improvement. In v2 the editor sees the exact missed checks, which helps, and behaviour measures (did it read the policy emails?) give a second signal.
- **Lessons must transfer across workflows.** v1's items were all the same kind (headline pairs, response pairs). Here every task is a different workflow, so a kept edit has to be general ("Did it apply the policy it found in the inbox?") rather than specific. The held-out keep-or-reject test enforces this, but it may reject more edits, so learning could be slower.
- **Less data, richer signal.** About 200 tasks instead of thousands of pairs, so less statistical power; but partial credit is a much denser signal than v1's single right/wrong per item.


**Short version:** the harness barely changes. What changes is *what the system is doing*, and that is the point of v2.

### v1 predicted a judgment; v2 does the work

- **v1: predicting a judgment.** We gave the system two existing responses or headlines and asked it to predict which one a human preferred. The outcome was someone else's vote or click. That was useful for proving the learning loop works. But in a business you rarely need to guess which of two finished things a stranger liked.
- **v2: doing the work and being graded on whether it worked.** In AutomationBench an agent actually performs a business task: update the CRM, route the ticket, file the expense. The grade is whether the systems end up in the correct state, checked automatically against the task's assertions. That is much closer to production: **the reward is "did the job get done correctly"**, not a human's taste.

### What stays the same: the harness

- **A policy written as text, learning in batches.** Each round runs practice, grading, and one edit at a time. A held-out keep-or-reject test decides whether an edit is kept. A sealed set is used once, at the end.
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
- **Keep-or-reject test:** the edit is kept only if picks improve on held-out tasks.
- **Weights:** refit from the graders' partial credit, as in v1's B+.
- **Over rounds:** the rubric learns what "done correctly" means in each business domain.

**2. The agent's skill file (its playbook).** Mirrors v1's LLM loop:
- **Failures:** the editor sees failed runs and which grading checks were missed. For example, *"forgot to update the ticket status."*
- **Edit:** one targeted fix to the instructions. For example, *"Always close the ticket after replying."*
- **Keep-or-reject test:** kept only if the pass rate improves on held-out tasks.
- **Cost note:** this is the expensive part (every candidate edit re-runs the agent), so it is optional in the lean plan.

**Same v1 rules throughout:** single edits, memory of rejected edits, fresh mistakes each round, the held-out keep-or-reject test, a sealed set used once, and preregistration.

**Net effect over time:**
- The agent makes better attempts.
- The checker picks better among them.
- The Router escalates less as Jev's confidence becomes trustworthy.

All three show up as accuracy gains or cost cuts on the sealed set.

### The claim v2 can make, if it works

> An open-weight agent plus a learned checker (Jev) matches Gemini Flash on real back-office tasks, cheaper and faster.

That is the claim a business actually cares about.

*Terminology: in [Task Brief 7](briefs/Task%20Brief%207_V2_Business.md), **Phase 1** is the experiments on the new data and **Phase 2** was a planned UI and tutorial, not part of the experiments.*
