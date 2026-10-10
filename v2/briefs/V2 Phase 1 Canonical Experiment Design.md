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
| Margin keep test | Take 2's playbook test: targeted failure kind improves, overall credit up by at least 0.02, fully passed tasks not lower; no p-value. | Code: `keep_test: margin` |
| Credit | The grader's partial score for one run, 0 to 1. |  |
| Main comparison | Router vs Gemini alone on the sealed exam, checkpoint on. | Retired: headline |

## Takes

Phase 1 is run in numbered takes so results are never mixed up. Always cite "Take N, round M" and name the keep test.

| | Take 1 | Take 2 |
| --- | --- | --- |
| Started | 2026-10-09 | 2026-10-10 |
| Playbook keep test | P-value keep test | Margin keep test |
| Rubric keep test | McNemar, p < 0.10 | Unchanged |
| Rounds 1 and 2 | Four candidate rules, none kept; starting playbook 0.62 credit on the test bench | Round 1 reuses Take 1's logged runs (same runs, new test); round 2 onward starts from the playbook Take 2 keeps |
| Files | `phase1/run/take1/`, `logs/phase1_run/take1/` | `phase1/run/take2/` |

**Rule length limit (2026-10-10, Alexander):** raised from 600 to 1,200 characters after Take 2's rounds 3 and 4. The editor's drafts ran 627 to 1,073 characters; most refused ideas came back shortened and were tested, but one (a verbatim checklist for wrong content) never was. The rules refused for length are replayed against the final playbook as written, post hoc, and nothing changes in the playbook without Alexander's OK.

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
