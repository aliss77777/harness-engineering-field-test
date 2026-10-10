# V2 Phase 1: Canonical Experiment Design

Oct 9, 2026 · @Alexander Liss · updated Oct 10, 2026: Take 2, margin keep test (see Takes)

## The question

Phase 1 tests whether a cheap open-weight model, working inside a harness we built, can come close to a premium model's score on real business workflows for about half the cost.

**Where v1 left us.** On a simple task (which of two answers would people prefer?), Jev, a small checker, learned from its mistakes, and Gemini's own instructions barely improved. Routing through Jev matched Gemini's accuracy (76.2% vs 76.3%) at about half the cost.

**What v2 changes.** The task is now AutomationBench: 200 Finance and HR workflows where an agent takes many steps and must follow rules hidden in policy emails. MiniMax M3 does the work and learns by rewriting its own playbook. Jev learns to check finished runs. Gemini redoes the runs Jev doubts. We compare that whole system with Gemini doing every task alone.

**Hypothesis.** MiniMax learns kind of like an RL model learning a policy, but without updating its weights. Jev's routing toggles between MiniMax and Gemini. Together, the harness and the Jev router deliver gains in speed and cost without a loss of quality, as we showed in v1.

## How the harness learns

Every learner here runs the same loop: try, study the mistakes, propose a change, and keep the change only if a fair test says it helped. No model is retrained: what changes is written text, a playbook for MiniMax and a rubric for Jev.

**In v1** the task was one decision repeated over and over: which of two answers would people prefer? An editor studied the mistakes and proposed a change, either to Gemini's instructions or to Jev's rubric. The change was tried on 1,000 to 1,500 held-out pairs and kept only if it scored clearly better. It worked because every pair gave a clean right or wrong. Jev's rubric learned; Gemini's instructions barely moved.

**In v2** the unit is a whole workflow: many steps, scored hidden check by hidden check, and every task is different. So the loop changes in four ways.

1. **Learn patterns across tasks, not one task repeated.** The playbook holds rules that carry from task to task, such as "read every policy email before changing a record." Each failure is labeled by kind: broke a "must not" rule, skipped a required action, or wrote the wrong content.
2. **Aim each proposed rule at one kind of failure.** MiniMax studies its failure profile on the practice tasks and proposes a rule that names the kind it targets. Rules over 1,200 characters, or too specific, are refused (the limit was 600 through Take 2 round 4; see Takes).
3. **Keep a rule only if it helps what it claims, by a margin, at no cost.** On the 60 test-bench tasks, the targeted failure kind must improve, overall credit must rise by at least 0.02, and the rule must not lose fully passed tasks. This is the margin keep test (Take 2). Take 1 asked for a clear drop in the targeted failure kind (p < 0.10) and no fall in credit, and kept nothing in two rounds; 60 tasks at one run each could not show that.
4. **Jev's rubric learns the same way,** from finished runs. A change to its yes/no questions is kept only if the rubric then separates good runs from bad ones better on the test bench.

**The checkpoint is the part that does not learn.** It is a fixed rule in the harness, called action masking in reinforcement learning. Before MiniMax changes any record, it must have read every policy email. If not, the action is held (at most 3 times per run) and MiniMax is told what to read. It is a shield, not a teacher: it blocks one known mistake as it happens and logs each hold as a near-miss. The playbook editor sees those near-misses, so learning effort goes to the mistakes the checkpoint cannot catch.

## The pipeline

Five steps, with the checkpoint on in every one, learning and final exam alike. Gemini never learns.

1. **Sort the 200 tasks.** Practice 60, test bench 60, sealed exam 80. The sealed exam stays locked until the end.
2. **Teach MiniMax.** Four rounds. In each, MiniMax does 30 of the practice tasks, studies its mistakes, and proposes 2 candidate rules. Each candidate runs on all 60 test-bench tasks and is kept only if it passes the keep-or-reject test. The best kept rule joins the playbook, and the next round starts from it. Each task is run once.
3. **Teach Jev.** Jev's rubric, a list of yes/no questions about a finished run, is edited the same way. A change is kept only if the rubric then separates good runs from bad ones better on the test bench.
4. **Set the cutoff.** Jev scores every test-bench run. The cutoff is placed so the lowest-scoring 30% would go to Gemini, then frozen.
5. **Sit the sealed exam.** MiniMax does each of the 80 tasks once and Jev scores the finished run. At or above the cutoff, MiniMax's run stands. Below it, Gemini redoes the task from scratch. We compare this router with Gemini doing all 80 alone.

## The words we use

Each term means one thing everywhere. The last column lists code names and retired words.

| Word | Means | Code name / retired |
| --- | --- | --- |
| MiniMax M3 | Cheap open-weight agent. The only model that learns. |  |
| Gemini Flash | Premium yardstick and backup. Never learns. |  |
| Jev | The checker. Scores a finished run with its rubric. Also learns. |  |
| Grader | AutomationBench's hidden end-state checks, run in code. Produces the credit. | Not Gemini, not Jev |
| Harness | The code around the models: both learning loops, checkpoint, keep-or-reject test, router. |  |
| Playbook | Written rules MiniMax edits for itself. | Code: skill |
| Rubric | Jev's yes/no questions about a finished run. |  |
| Checkpoint | Holds record-changing actions until the policy emails are read; max 3 holds per run. RL name: action masking. | Retired: gate, prevention layer |
| Router | MiniMax does the task, Jev checks it, Gemini redoes what Jev doubts. | Code: cascade |
| Cutoff | Jev score below which a task goes to Gemini; 30% of test-bench runs fall below it. | Code: tau (τ) |
| Practice / test bench / sealed exam | 60 / 60 / 80 tasks. Learn on practice; keep-or-reject and cutoff on the test bench; sealed exam opened once. | Files named gate = test bench |
| Keep-or-reject test | Decides whether a playbook or rubric change stays. For the playbook it is the margin keep test in Take 2 and the p-value keep test in Take 1. | Retired: gate |
| Take 1 / Take 2 | An attempt at Phase 1. Take 1: 2026-10-09, p-value keep test, stopped after round 2, no rule kept ($16.15). Take 2: 2026-10-10, margin keep test, starting from round 1. | Not "run" (a run is one task execution) |
| P-value keep test | Take 1's playbook test: targeted failure kind clearly drops (p < 0.10) and overall credit does not fall. | Code: `keep_test: p_value` |
| Jev refit | Re-estimating how much each rubric question counts, on about 1,050 labelled runs, tested on tasks held out of fitting. | Stage B1 (retired) |
| Jev redesign, first / second attempt | Jev changed from a generic checklist over a run summary to a checker that sees the source data, policy emails and the agent's writes, with questions written per task. First attempt: one question set, learned instructions. Second attempt: variants 1 to 4 (more question sets, a compliance set, a per-write check) on fresh runs. | D, D2, verifier (retired) |
| AUC | Of all good-run / poor-run pairs, the share where the good run scored higher. 0.5 is chance, 1.0 is perfect. Good = credit 0.8 or more. | |
| Same-playbook comparison | AUC computed only between runs made with the same playbook version, so Jev is not credited for telling playbooks apart. | Code: within-playbook |
| Margin keep test | Take 2's playbook test: targeted failure kind improves, overall credit up by at least 0.02, fully passed tasks not lower; no p-value. | Code: `keep_test: margin` |
| Credit | The grader's partial score for one run, 0 to 1. |  |
| Main comparison | Router vs Gemini alone on the sealed exam, checkpoint on. | Retired: headline |

## Takes

Phase 1 is run in numbered takes so results are never mixed up. Always cite "Take N, round M" and name the keep test.

| | Take 1 | Take 2 |
| --- | --- | --- |
| Started | 2026-10-09 | 2026-10-10 |
| Playbook keep test | P-value keep test | Jev refit | Re-estimating how much each rubric question counts, on about 1,050 labelled runs, tested on tasks held out of fitting. | Stage B1 (retired) |
| Jev redesign, first / second attempt | Jev changed from a generic checklist over a run summary to a checker that sees the source data, policy emails and the agent's writes, with questions written per task. First attempt: one question set, learned instructions. Second attempt: variants 1 to 4 (more question sets, a compliance set, a per-write check) on fresh runs. | D, D2, verifier (retired) |
| AUC | Of all good-run / poor-run pairs, the share where the good run scored higher. 0.5 is chance, 1.0 is perfect. Good = credit 0.8 or more. | |
| Same-playbook comparison | AUC computed only between runs made with the same playbook version, so Jev is not credited for telling playbooks apart. | Code: within-playbook |
| Margin keep test |
| Rubric keep test | McNemar, p < 0.10 | Unchanged |
| Rounds 1 and 2 | Four candidate rules, none kept; starting playbook 0.62 credit on the test bench | Round 1 reuses Take 1's logged runs (same runs, new test); round 2 onward starts from the playbook Take 2 keeps |
| Files | `phase1/run/take1/`, `logs/phase1_run/take1/` | `phase1/run/take2/` |

**Rule length limit (2026-10-10, Alexander):** raised from 600 to 1,200 characters after Take 2's rounds 3 and 4. The editor's drafts ran 627 to 1,073 characters; most refused ideas came back shortened and were tested, but one (a verbatim checklist for wrong content) never was. The rules refused for length are replayed against the final playbook as written, post hoc, and nothing changes in the playbook without Alexander's OK.

**Jev refit (2026-10-10, Alexander; written before any refit result).** In plain words: re-estimate how much each of the old rubric's questions counts, using about 1,050 labelled runs instead of 60. The Jev stage as built (8 questions, weights fitted on 60 practice runs, edits tested on 60 test bench runs) did not transfer: AUC 0.73 on the runs it was fitted on and 0.475 on the test bench. About 990 more labelled MiniMax runs exist from the skill loop and replay. The refit uses them, in two stages, and the sealed exam waits for it.

- **The refit, weights only (primary).** Take 2's final rubric, its 8 questions as they stand, with weights refit by L2 logistic regression (C = 1.0) on all labelled runs (checkpoint on; good = credit 0.8 or more; Jev's answers are the ones already computed). No new questions.
- **Validation.** 5-fold cross-validation grouped by task (120 tasks, fixed seed): a run is scored only by a model that never saw its task, so the same task under different playbooks cannot leak. The test runs are the final playbook's run on each held-out task, one per task, 120 in all.
- **The bar, fixed here:** AUC of at least 0.65 with a bootstrap 95% lower bound above 0.5, **and** the lowest-scoring 30% of those runs averaging at least 0.10 credit below the rest. Both must hold for "Jev learned".
- **Reported beside it, not part of the bar:** the starting rubric refit the same way, the rubrics as they were, and C of 0.1 and 10.
- **Cutoff.** Set from the held-out scores of the 120 final-playbook runs (lowest 30% below), then frozen. The sealed exam uses the refit rubric only if the bar is met, with weights fitted on all 120 tasks.
- **A second option, editing the questions on the pooled data,** only with Alexander's OK, and only if the refit misses the bar. If both miss, Jev as built (a run summary as input) has not shown skill, and the sealed exam reports MiniMax against Gemini without a router claim.

**Jev redesign, first attempt (2026-10-10, Alexander; written before any result).** In plain words: Jev is redesigned to check work against the source data, with questions written for each task. The refit missed its bar (AUC 0.525 against 0.65): eight generic questions over a run summary cannot see wrong values or missed exclusions, and the summary leaves out what the agent read. The redesign makes Jev a verifier:

- **Input (the state Jev reads):** the request; the inbox's policy emails (by the harness's detector); the source records the run read (read results only, not API search results); the run's writes with their full content; and the diff of the records. Never the grader's checks or any detail derived from them (the existing no-peeking rule).
- **Questions:** written per task, once, by MiniMax from the request and the policy emails only (not the run, never the grader's checks), 6 to 10 yes/no questions phrased so that yes means the work was correct. The score of a run is the mean probability of yes. No weights are fitted.
- **Learning:** the question writer's instructions are the learned object. MiniMax edits them from runs Jev ranked wrongly on **development** tasks; an edit is kept if development AUC rises by at least 0.02. At most 3 rounds, 2 candidates each.
- **Splits:** development = the 60 practice tasks' logged runs; **validation = the 60 test bench tasks' logged runs, opened once** with the instructions frozen. The sealed exam is untouched.
- **Primary metric:** within-playbook AUC (comparisons only between runs of the same playbook version, good = credit 0.8 or more), with a bootstrap over tasks, on the validation runs. **Bar: AUC at least 0.65 with a 95% lower bound above 0.5, and the lowest 30% of runs (within a playbook) averaging at least 0.10 credit below the rest.** Reported beside it: the final playbook's 60 runs alone, within-task AUC, the generic rubric on the same runs.
- **If the bar is met,** the cutoff is re-set on the final playbook's validation scores and frozen, and the sealed exam uses it. **If not,** the router claim is dropped and Jev is reported as not having shown skill, with the sealed exam reporting MiniMax against Gemini.
- **Result (2026-10-10; validation opened once):** development AUC 0.650 with the starting instructions and 0.677 after one kept edit (2 rounds more kept nothing). **Validation, 840 test bench runs of 14 playbook versions: within-playbook AUC 0.612 [0.514, 0.719]; lowest 30% averaged 0.598 against 0.763 for the rest (gap 0.166). The bar (AUC at least 0.65) was not met.** On the same runs the generic rubric scored 0.51 (gap 0.06). On the final playbook's own 60 runs the AUC was 0.482 [0.327, 0.640]. Per failure kind, a low score flagged skipped actions (0.67) and wrong content (0.66) but not broken rules (0.48); discrimination fell as playbooks improved (0.70 for the starting playbook, 0.48 for the final one).
- **Value check:** a router's quality upside is bounded by how much better Gemini does on the tasks MiniMax fails. On 20 tasks with Gemini runs, a perfect detector escalating the worst 30% reached 0.699 against 0.713 for MiniMax alone (indicative). The Gemini ceiling check below should settle this.

**Jev redesign, second attempt (2026-10-10, Alexander approved; written before any result).** The first attempt reached AUC 0.612 on validation (bar 0.65) and 0.48 on the final playbook's own runs. The second attempt tries to close that gap on fresh data:

- **Fresh data.** Two more independent runs of the final playbook on every practice and test bench task (about 240 runs, about $11), checkpoint on. The test bench validation used by the first verifier is not reused as the proof.
- **Variants, chosen on development only** (practice tasks; all final-playbook runs on them): variant 1 the first attempt as frozen; variant 2 the mean over 3 independent question sets per task; variant 3 variant 2 plus a separate policy-compliance question set aimed at forbidden actions; variant 4 variant 3 plus a per-write check (each record-changing call judged on its own against the request, policies and source, the run scored by its worst write). The variant with the highest development AUC (within final-playbook runs) is chosen; if none beats variant 1 by 0.02 or more, variant 1 stays.
- **Validation, opened once:** the fresh test bench runs of the final playbook (120 runs, 60 tasks), never scored by any version of Jev before. **Bar: AUC at least 0.65 with a bootstrap 95% lower bound (by task) above 0.5, and the lowest 30% averaging at least 0.10 below the rest.** Reported beside it: variant 1 on the same runs, the generic rubric, per failure kind.
- **Caveat recorded in advance:** the test bench tasks (not their fresh runs) were seen by the first validation, and the second attempt's variants were motivated by its findings.
- **If the bar is met,** the cutoff is set on the fresh validation scores (lowest 30% below) and frozen for the sealed exam. If not, the sealed exam reports MiniMax against Gemini without a router claim.
- **Result (2026-10-10, validation opened once): bar met.** Variant 3 was chosen on development (AUC 0.648). On the 120 fresh test bench runs of the final playbook: **AUC 0.666 [0.548, 0.784]**, lowest 30% averaging 0.587 against 0.781 for the rest (gap 0.194, interval 0.07 to 0.33). Beside it: variant 1 (the first attempt) 0.663, variant 2 0.655, variant 4 0.588. By failure kind, a low score flagged wrong content (0.72), skipped actions (0.61) and, barely, rules broken (0.53). **Read with care:** variant 3 beat variant 1 by only 0.003 here; on the final playbook's other runs the first attempt scored 0.48 (60 runs) and 0.61 (180 development runs), so the honest level is about 0.6 to 0.65. The cutoff is frozen at 0.756 (30th percentile of variant 3 scores on these 120 runs; `phase1/run/take2/jev_cutoff_second_attempt.json`); the sealed stage is not yet wired to use it.

**Gemini ceiling check (approved to run, 2026-10-10).** Gemini (no playbook, no checkpoint, temperature 0) on every practice and test bench task where the final playbook's MiniMax run scored under 0.8 (about 54 tasks, about $17, no sealed tasks). Reported: Gemini's credit on those tasks, and the credit of a router with a perfect failure detector escalating all failures and the worst 30% of tasks, against MiniMax alone and Gemini alone.

## Follow-ups

**Ceiling check result (2026-10-10).** 54 of the 120 practice and test bench tasks scored under 0.8 with the final playbook. On those 54, MiniMax scored 0.528 and Gemini 0.696 (20 of 54 fully passed). MiniMax alone over all 120 scored 0.753. A router with a *perfect* failure detector would reach 0.828 escalating all 54 (45% of tasks) and 0.820 escalating the worst 30% (+6.7 points over MiniMax alone), at about $0.28 per Gemini run. This supersedes the earlier indicative 20-task check (perfect router 0.699). Caveat: the failed runs are partly bad luck, so against a fresh MiniMax draw on the same tasks the gap is smaller; the fresh runs now running will measure it.

- **Gemini ceiling check (Alexander, 2026-10-10; DONE 2026-10-10: see result below).** Run Gemini on the practice and test bench tasks where the final playbook's MiniMax run scored under 0.8 (about 54 tasks, about $17, no sealed tasks). It gives a firm number for what a perfect router could gain, so we know how much a better Jev can be worth and whether its role is routing or flagging runs for human review. Needs Alexander's go to spend.

Why Take 2: the p-value keep test could not see 2 to 5 point gains at 60 tasks and one run each (one run moves about 3 points on its own). The change was adopted after seeing Take 1's rounds 1 and 2, with Alexander's OK, and is recorded that way in PLAN.md. The sealed exam is the judge either way: final vs starting playbook.

## What we measure

The main comparison comes first. All four are measured on the 80 sealed tasks, one run per task, checkpoint on unless stated.

| Question | What is compared | How we read it |
| --- | --- | --- |
| 1. Does the router come close to Gemini for less? (main comparison) | Router vs Gemini alone: credit and cost per task | Reference lines: within 3 points of Gemini's credit, at most half its cost. Directional; we report the numbers and how close they land. |
| 2. Did MiniMax learn? | Final playbook vs starting playbook (no rules) | A real gain on unseen tasks. The starting playbook against Gemini is the starting line. |
| 3. Did Jev learn? | Final rubric vs starting rubric | Better at telling good runs from bad ones, on the sealed exam runs. |
| 4. What does the checkpoint add? | Final playbook, checkpoint off vs on | Reported on its own, as an extra. The off runs exist only for this. |

## What Phase 0 already showed

These findings stand whatever Phase 1 shows: a cheap open-weight model can come close to Gemini on real workflows, the gap is one identifiable habit, and a simple checkpoint appears to narrow it. The big bet, that the harness can teach the model, is still open.

**Known from Phase 0 and the first checkpoint test:**

- **Open-weight models are not interchangeable.** Nemotron 3 Super and DeepSeek V4 Pro fell far short of Gemini (credit about 0.2 against 0.6 to 0.7; 0% and 5% of tasks fully passed). MiniMax M3 came close: on 20 tasks, 0.62 credit against Gemini's 0.70 (range −0.21 to +0.06), at about $0.057 a run against $0.299.
- **MiniMax's gap is one habit: acting before reading the policy emails.** It read every policy email in 4 of 13 diagnosed runs, Gemini in 12 of 12. Across 236 runs, MiniMax broke a "must not" rule in 63% of runs that acted before reading, against 43% overall.
- **A simple checkpoint appears to help.** With it on, on the 60 test-bench tasks, broken rules fell from 0.88 to 0.67 per run and credit rose from 0.57 to 0.65. Both ranges just touch zero: promising, not proof.
- **The pilot's three candidate rules all cut rule-breaking** (from 0.90 to between 0.50 and 0.70 per run), but none passed a test too small to see a few points. That is why the learning loop was redesigned.
- **Runs are noisy.** Even at temperature 0 the same task shifts about 0.26 in credit between repeats.

**Unproven, and what Phase 1 exists to test:**

- That MiniMax's playbook improves on unseen tasks.
- That Jev's rubric improves on this kind of task.
- That the router comes close to Gemini's score at about half the cost.

## What could go wrong

Phase 1 is far bigger than v1: more moving parts, noisier scores, and roughly $110 of planned spend ($32 spent to date). Watch for:

- **Too little signal.** 60 test-bench tasks with one run each is thin. A real gain can be missed and a lucky rule can be kept. "No gain" would mean not detected at this size.
- **MiniMax may ignore the checkpoint.** In the first test only 75% of runs read the policies before writing (bar: 90%). In most shortfalls it ignored three holds in a row and was let through.
- **The policy-email detector is rough.** Half of what it flags is not policy, and it misses about a quarter of the real policy emails.
- **Jev sees a summary, not the whole run,** so it can miss what the summary leaves out.
- **The cost win is thin.** With 30% of tasks going to Gemini, cost lands near half of Gemini's, and a cutoff set on 60 tasks has to hold on the sealed 80.
- **The sealed exam is small.** 80 tasks give about six points of wiggle: enough to show "close", not "within 3 points".

## Ideas for later (noted, not adopted)

Each of these is a design change: it goes into this memo with Alexander's OK before any code.

- **Stack more than one passing rule per round.** Today only the best rule that passes the keep test joins the playbook. A rule that passes but is not the best (Take 2, round 1: R1b, +2.1 points, 17 vs 11 passes) is shown to the editor as rejected and does not come back. Stacking passing rules, or letting the runner-up retry against the new playbook in the next round, would capture more of what was learned. Noted 2026-10-10 (Alexander).

## Fixed rules of the run

- **One run per task,** in learning, on the test bench and on the sealed exam, as in v1.
- **The sealed exam opens once,** only after Alexander signs the release note. Nothing is tuned on it afterwards.
- **No peeking.** MiniMax may read a task's company data, never the grader's checks or any detail derived from them.
- **Gemini runs as it comes:** no playbook, no checkpoint, no learning.
- **Paid runs wait for `run.approved: true`.** The spend cap is a safety stop Alexander sets. Cost goals are directional.

## Standing rule for the coding agent

This memo is the source of truth for the design and its words. It outranks any older brief, README line or config comment.

1. **Use the terms in "The words we use" exactly,** in docs, reports, comments and commit messages. Code names stay as they are; writing uses the plain word.
2. **Do not rename, merge or invent terms.** If you need a new one, stop and ask Alexander, then add it to the table in the same commit.
3. **Do not change the design in passing.** A design change goes into this memo first, with Alexander's OK, and gets a dated line in PLAN.md.
4. **Nothing in the pipeline is optional.** Anything outside it needs a one-line scope note and Alexander's OK before work starts.
5. **Keep one status table,** updated in the same commit as the work it describes.

## Changes to make now

Done, 2026-10-09, commit `fb265a4`.

Done, 2026-10-10: Takes and the margin keep test added (this memo, config, `keep_rule`, tests, PLAN.md).
