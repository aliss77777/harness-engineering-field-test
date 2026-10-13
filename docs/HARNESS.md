# The harness

What was built to make "can a cheap model learn on the job, and can we tell?" a testable question. Code is in [`v2/src/jevloop`](../v2/src/jevloop) (about 2,400 lines, 93 tests); the run orchestration is [`v2/scripts/phase1_run.py`](../v2/scripts/phase1_run.py).

## The problem it solves

AutomationBench tasks are multi-step: read an email, look up records, apply a policy, write to the right systems. A task is graded by assertions on the final state of the simulated company, so partial work earns partial credit and one wrong write can fail the whole task.

Three things make learning on this hard to measure honestly:

1. **One run is noisy.** Temperature 0 is not repeatable for this model: 0 of 10 repeated runs were identical, with scores differing by up to 0.26. A single run per task moves about 3 points.
2. **Fixes are chosen on the data that judges them.** Pick the best of several candidate rules on 60 tasks and the winner looks better than it is.
3. **Paid runs are easy to lose.** Rate limits, credit errors and spend limits interrupt long runs and can silently corrupt a result.

## The pipeline

Five stages, each resumable, each writing machine-readable output under `v2/phase1/run/`.

| Stage | What it does |
|---|---|
| `skill` | The learning loop: practice, propose rules, keep or reject each on the test bench |
| `jevdata` | Run the final playbook on all practice tasks to give the checker data |
| `rubric` | Learn and refit the checker's question weights, tested on held-out tasks |
| `tau` | Set the checker's escalation cutoff before the exam (later frozen on fresh validation runs) |
| `sealed` | The exam: starting playbook, final playbook (checkpoint on and off), Gemini alone, router |

Plus `replay-refused`, `ceiling` and `fresh`: a replay of rules that were refused for length, a check of how much a perfect detector could add, and fresh draws to separate luck from effect.

## The learning loop

Each round: the agent does 30 practice tasks with the current playbook; the editor (the same open-weight model) reads its own graded mistakes and proposes two candidate rules; each candidate runs on all 60 test bench tasks; the best one that passes the keep test joins the playbook. At most four rules. The editor sees the current playbook, the mistakes it still makes, and every rejected rule, so it does not resubmit them. A stronger model is never in the loop: Gemini is the yardstick, not the teacher.

**The keep test** went through two designs, and the change is on the record:

| | Take 1 | Take 2 |
|---|---|---|
| Rule | p-value: the targeted failure kind clearly drops (p < 0.10), credit does not fall | margin: targeted failure improves, credit up at least 0.02, fully passed tasks not lower |
| Outcome | four candidates, none kept | R1a and R2x kept |
| Status | preregistered | adopted after seeing Take 1, recorded as post hoc |

At 60 tasks and one run each, the p-value test was too blunt to see a few points. The margin test accepts that some useless rules will be kept; the sealed exam is what makes that safe.

## The checkpoint

Before the agent changes any record, the harness confirms it has read every policy email. If not, the action is held, the agent is told which emails to read, and the hold is logged as a near-miss. It is a shield (a veto after an action is proposed), not removal from the action set. Built first as a replay over 236 logged runs, then run live off against on.

It worked as a training scaffold: holds per run fell from 0.82 with the starting playbook to 0.19 with the learned one, as the playbook absorbed the habit. At exam time the shield added little.

## The checker and the router

The checker (Jev, a third-party model) answers yes/no questions about a run and returns a probability for each. The generic rubric over a run summary stayed near chance. A redesign that shows it the source records, policy emails and the agent's writes, with questions written per task, roughly doubled the signal: AUC 0.666 on fresh runs against a bar of 0.65, cutoff frozen at 0.756. On the exam it scored 0.566. The router keeps a run whose score clears the cutoff and sends the rest to Gemini.

## Guardrails

- **Spend caps in code**, per stage, and paid runs wait for `run.approved: true` in the config.
- **One exam, one opening.** The sealed stage needs `--release-confirmed`. A 403 (key spend limit) and a 402 (OpenRouter's in-flight budget, not an empty balance) halted runs mid-exam; both were diagnosed, the harness now retries the 402, and the exam resumed from cache without a second opening.
- **No peeking.** The checker and the editor never see the grader's checks.
- **Everything is cached and logged.** Reloaded runs cost nothing, which is how Take 2 reused Take 1's first round.
- **Terms are fixed.** One name per concept ([`v2/GLOSSARY.md`](../v2/GLOSSARY.md)); "gate" had drifted to mean three things and was renamed.

## What it measures with

Paired bootstrap intervals for differences; one-sided Wilcoxon for "did it learn"; AUC within a playbook version and cluster bootstrap by task for the checker ([`evalstats.py`](../v2/src/jevloop/evalstats.py)); the router compared against random escalation at the same share, so credit that comes from sending more tasks to Gemini is not mistaken for good choosing.
