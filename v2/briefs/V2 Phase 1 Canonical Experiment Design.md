# V2 Phase 1: Canonical Experiment Design

Oct 9, 2026 · @Alexander Liss · rewritten Oct 10, 2026 to carry what Take 1 and Take 2 taught us. The sealed exam opened Oct 10, 18:25 UTC; its results are not in this memo yet.

## The question

Phase 1 tests whether a cheap open-weight model, working inside a harness we built, can come close to a premium model's score on real business workflows for a fraction of the cost.

**Where v1 left us.** On a simple task (which of two answers would people prefer?), Jev, a small checker, learned from its mistakes, and Gemini's own instructions barely improved. Routing through Jev matched Gemini's accuracy (76.2% vs 76.3%) at about half the cost.

**What v2 changes.** The task is AutomationBench: 200 Finance and HR workflows where an agent takes many steps and must follow rules hidden in policy emails. MiniMax M3 does the work and learns by rewriting its own playbook. Jev checks finished runs. Gemini redoes the runs Jev doubts. We compare that whole system with Gemini doing every task alone.

**Hypothesis.** MiniMax learns kind of like an RL model learning a policy, but without updating its weights. Jev's routing toggles between MiniMax and Gemini. Together, the harness and the Jev router deliver gains in speed and cost without a loss of quality, as we showed in v1.

**The story we can defend (Oct 10, before the sealed exam).** An open-weight model, with a harness that taught it from its own mistakes, got close to a premium model for a fraction of the cost, and a redesigned checker can find some of its failures. The router is the part that may or may not add value on top.

## How the harness learns

Every learner runs the same loop: try, study the mistakes, propose a change, keep it only if a fair test says it helped. No model is retrained; what changes is written text. The playbook is MiniMax's. Jev's questions are the checker's.

**In v1** the task was one decision repeated, every pair gave a clean right or wrong, and 1,000 to 1,500 held-out pairs could decide each change. **In v2** the unit is a whole workflow, every task differs, and credit is partial, so the loop changed:

1. **Learn patterns across tasks.** The playbook holds rules that carry from task to task ("read every policy email before changing a record"). Each failure is labeled by kind: broke a "must not" rule, skipped a required action, or wrote the wrong content.
2. **Aim each rule at one failure kind.** MiniMax studies its failure profile on practice tasks and proposes a rule naming its target kind. Rules over 1,200 characters, or too specific, are refused.
3. **Keep a rule only on a margin.** On the 60 test bench tasks the targeted failure kind must improve, overall credit must rise by at least 0.02, and fully passed tasks must not fall (the margin keep test).
4. **Jev has to see what it checks.** A generic checklist over a run summary cannot see wrong values or missed exclusions. Jev reads the request, the policy emails, the source records the run read and the writes in full, and answers questions written for that task.

**The checkpoint does not learn.** It is a fixed rule in the harness (action masking in reinforcement learning): before MiniMax changes any record it must have read every policy email, or the action is held (at most 3 times per run) and logged as a near-miss. It is a shield, not a teacher. Gemini gets none.

## The pipeline

Checkpoint on for MiniMax in every step; Gemini runs as it comes. One run per task throughout.

1. **Sort the 200 tasks.** Practice 60, test bench 60, sealed exam 80. The sealed exam stays closed until the end.
2. **Teach MiniMax.** Four rounds: 30 practice tasks, 2 candidate rules, each tried on all 60 test bench tasks and kept only if it passes the margin keep test; the best kept rule joins the playbook and the next round starts from it.
3. **Teach Jev.** The question writer's instructions are edited on development tasks (practice) and checked once on fresh runs. Fresh runs are new, independent draws of the final playbook.
4. **Set the cutoff.** Jev scores the fresh test bench runs; the cutoff is placed so the lowest 30% would go to Gemini, then frozen.
5. **Sit the sealed exam.** MiniMax does each of the 80 tasks once and Jev scores the run. At or above the cutoff, MiniMax's run stands; below it, Gemini redoes the task from scratch. We compare this router with Gemini alone.

## The words we use

Each term means one thing everywhere. The last column lists code names and retired words.

| Word | Means | Code name / retired |
| --- | --- | --- |
| MiniMax M3 | Cheap open-weight agent. The only model whose playbook learns. | |
| Gemini Flash | Premium yardstick and backup. Never learns. | |
| Jev | The checker. Scores a finished run. | |
| Grader | AutomationBench's hidden end-state checks, run in code. Produces the credit. | Not Gemini, not Jev |
| Harness | The code around the models: learning loops, checkpoint, keep tests, router. | |
| Playbook | Written rules MiniMax edits for itself. | Code: skill |
| Rubric | The original 8 generic yes/no questions Jev answered about a run summary. | |
| Checkpoint | Holds record-changing actions until the policy emails are read; max 3 holds per run. | RL: action masking. Retired: gate |
| Router | MiniMax does the task, Jev checks it, Gemini redoes what Jev doubts. | Code: cascade |
| Cutoff | Jev score below which a task goes to Gemini; 30% of fresh test bench runs fall below it. | Code: tau (τ) |
| Practice / test bench / sealed exam | 60 / 60 / 80 tasks. Learn on practice; keep tests and cutoff on the test bench; sealed exam opened once. | File name gate = test bench |
| Credit | The grader's partial score for one run, 0 to 1. "Good" = credit 0.8 or more. | |
| Margin keep test | Playbook change stays if the targeted failure kind improves, credit rises by at least 0.02, and fully passed tasks do not fall. Take 2. | `keep_test: margin` |
| P-value keep test | Playbook change stays if the targeted failure kind clearly drops (p < 0.10) and credit does not fall. Take 1. | `keep_test: p_value` |
| Take 1 / Take 2 | Attempts at Phase 1. Take 1: Oct 9, p-value keep test, stopped after round 2. Take 2: Oct 10, margin keep test. | Not "run" (a run is one task execution) |
| Jev refit | Re-estimating how much each rubric question counts, on about 1,050 labelled runs, tested on held-out tasks. | Retired: stage B1 |
| Jev redesign, first / second attempt | Jev as a checker that sees the source data, policy emails and writes, with questions written per task. First: one question set, learned instructions. Second: variants 1 to 4 on fresh runs. | Retired: D, D2, verifier |
| Variant 1 to 4 | Second-attempt versions: 1 the first attempt; 2 averages 3 question sets; 3 adds compliance questions; 4 adds a per-write check. | V1 to V4 |
| AUC | Of all pairs of one good run and one poor run, the share where the good run scored higher. 0.5 is chance. | |
| Same-playbook comparison | AUC computed only between runs of the same playbook version. | Code: within-playbook |
| Fresh runs | New, independent draws of a playbook on tasks already run. | |
| Opened once | A set scored a single time, after every design choice is frozen. | |
| Main comparison | Router vs Gemini alone on the sealed exam. | Retired: headline |

## Takes and Jev attempts, with their bars

Cite "Take N, round M" and name the keep test. Bars were fixed before each result.

| | Take 1 | Take 2 |
| --- | --- | --- |
| Started | Oct 9 | Oct 10 (round 1 reuses Take 1's logged runs; new test) |
| Playbook keep test | P-value keep test | Margin keep test (adopted after seeing Take 1; post hoc) |
| Outcome | 4 candidates, none kept in 2 rounds | R1a and R2x kept; rounds 3 and 4 and a replay of the 4 length-refused rules kept nothing |
| Files | `phase1/run/take1/` | `phase1/run/take2/` |

| Jev design | Bar (fixed in advance) | Result |
| --- | --- | --- |
| Original rubric, fitted on 60 runs | | AUC 0.73 on practice, **0.475** on test bench |
| Jev refit, 1,052 runs, 5-fold by task | AUC 0.65 (lower bound above 0.5), lowest 30% at least 0.10 below the rest | **0.525** [0.42, 0.63]; missed |
| Redesign, first attempt, 840 test bench runs of 14 playbooks, opened once | same | **0.612** [0.51, 0.72], gap 0.166; missed. Final playbook alone 0.48 |
| Redesign, second attempt, variant 3 chosen on development, 120 fresh test bench runs, opened once | same | **0.666** [0.55, 0.78], gap 0.194; **met** |

## What we measure

All four are measured on the 80 sealed tasks, one run per task, checkpoint on unless stated.

| Question | What is compared | How we read it |
| --- | --- | --- |
| 1. Does the router come close to Gemini for less? (main comparison) | Router vs Gemini alone: credit and cost per task | Reference lines: within 3 points of Gemini's credit, at most half its cost. Directional. |
| 2. Did MiniMax learn? | Final vs starting playbook | A real gain on unseen tasks. |
| 3. Is Jev a good checker, and did it learn? | Redesigned Jev's same-playbook AUC and gap on the sealed runs against the bar; the original rubric's final vs starting accuracy | AUC 0.65 with a lower bound above 0.5, gap 0.10. Whether it *learned* is a separate, weaker claim (see below). |
| 4. What does the checkpoint add? | Final playbook, checkpoint off vs on | An extra; also a like-for-like MiniMax vs Gemini. |

Also reported from the same runs, no extra cost: MiniMax final alone against Gemini alone.

## What Phase 0 showed

Open-weight models are not interchangeable (Nemotron 3 Super and DeepSeek V4 Pro fell far short; MiniMax M3 came close at about $0.057 a run against $0.30). MiniMax's gap was one habit: acting before reading the policy emails. A simple checkpoint appeared to narrow it. Runs are noisy: even at temperature 0 the same task moves about 0.26 in credit between repeats.

## What we learned (Take 1 and Take 2, before the sealed exam)

**MiniMax and the playbook**
- **The harness learns.** From its own graded mistakes, with no Gemini, MiniMax went from 0.62 to 0.78 credit and from 11 to 21 of 60 fully passed on the test bench; about +13 points is the fair reading, with +12 on practice tasks the rules were not chosen on. The two rules that stuck match the Phase 0 diagnosis: finish every required write, and read the policy emails before any write.
- **Two rules look like a plateau.** Eight more candidates, including longer versions let through by the higher limit, landed between 0.746 and 0.792 against 0.778: noise. Prompt rules fix habits (order, finishing the job), not accuracy of values: wrong content stayed the largest failure.
- **Noise is about 0.02 on a 60-task mean** (SD of near-identical playbooks), smaller than the 0.03 we assumed. One run per task moves 3 points; the keep test has to be a margin, not a p-value, at this size.
- **The playbook absorbs the checkpoint.** Rule R2x cut checkpoint holds from 0.75 to 0.15 per run, so question 4 may come out small without the checkpoint having failed.
- **The gain costs nothing per run** (about $0.045 throughout), unlike extra samples.

**Jev and the router**
- **Seeing the right things beat learning.** The original rubric and the refit stayed near chance (0.475, 0.525); showing Jev the source, policy emails and writes, with questions written per task, roughly doubled the signal (0.61, then 0.67). The first attempt's design carried the gain; variants 2 and 3 added only 0.003 on fresh runs, and the first attempt's own level on the final playbook has varied from 0.48 to 0.66, so the honest level is **about 0.60 to 0.65**.
- **It flags some failures, not all.** A low score flags wrong content (0.72) and skipped actions (0.61), and barely rules broken (0.53). Judging each write alone and taking the worst (variant 4) hurt.
- **Jev's signal fades as the agent improves** (0.70 for the starting playbook, 0.48 to 0.66 for the final one): what is left to find is subtle.
- **Learning from outcomes is not shown for Jev.** Learned question-writer instructions gained +0.048 AUC on fresh runs, interval −0.03 to +0.13. Jev improved by design.
- **The prize is real and bounded.** On the 54 of 120 tasks MiniMax's final playbook scored under 0.8, Gemini scored 0.696 against MiniMax's 0.528 (0.628 on fresh MiniMax draws). A perfect failure detector would lift credit from 0.753 to about 0.82 (+7 points per run; about +3 against fresh draws). Re-running MiniMax on failures recovers about +4.5 at $0.045 against $0.28 for Gemini. A rough estimate for this Jev: about +3 points at about $0.13 a task.

**Method**
- **Pre-register the bar, then open each set once.** It caught three misses (refit, redesign first attempt, and the original rubric) that would otherwise have been argued away.
- **Fresh runs are the honest validation set.** The test bench was reused every round, so its numbers are optimistic by a few points.
- **Report the caveats with the numbers.** The margin keep test was adopted after seeing Take 1; the test bench tasks were seen by earlier validations.

## What could go wrong at the sealed exam

- **Small sample.** 80 tasks give about ±6 points: enough to show "close", not "within 3".
- **Jev at 0.60 to 0.65.** The router may add little over MiniMax alone, and the cutoff set on 120 runs has to hold on 80 new tasks. Roughly a third of tasks will go to Gemini.
- **Selection luck.** The playbook's test bench gain is optimistic; the sealed exam is the judge.
- **The checkpoint is part of the harness for MiniMax and Gemini gets none.** The off arm and the MiniMax vs Gemini comparison exist to keep that visible.
- **The policy-email detector is rough** (half of what it flags is not policy; it misses about a quarter).

## Ideas for later (noted, not adopted)

Each is a design change: it goes into this memo with Alexander's OK before any code.

- **Stack passing rules, or let a runner-up retry.** Today only the best passing rule per round joins the playbook.
- **A re-run fallback.** On a flagged run, re-run MiniMax (cheap) before escalating to Gemini.
- **Test Jev's learning properly.** Enough labelled runs and a held-out design to show learning from outcomes, not design.
- **A different lever for wrong content.** Prompt rules did not move it.
- **Does a rule need the one before it?** MiniMax with R2x alone on the test bench (about $3), the only test of "cascade" as opposed to "two good rules".

## Fixed rules of the run

- **One run per task,** in learning, on the test bench and on the sealed exam.
- **The sealed exam opens once,** only after Alexander signs the release note (`phase1/SEALED_RELEASE.md`). Nothing is tuned on it afterwards.
- **No peeking.** MiniMax and Jev may read a task's company data, never the grader's checks or any detail derived from them.
- **Gemini runs as it comes:** no playbook, no checkpoint, no learning.
- **Paid runs wait for `run.approved: true`.** The spend cap is a safety stop Alexander sets ($130 for the sealed exam). Cost goals are directional.

## Standing rule for the coding agent

This memo is the source of truth for the design and its words. It outranks any older brief, README line or config comment.

1. **Use the terms in "The words we use" exactly,** in docs, reports, comments and commit messages. Code names stay as they are; writing uses the plain word.
2. **Do not rename, merge or invent terms.** If you need a new one, stop and ask Alexander, then add it to the table in the same commit.
3. **Do not change the design in passing.** A design change goes into this memo first, with Alexander's OK, and gets a dated line in PLAN.md.
4. **Nothing in the pipeline is optional.** Anything outside it needs a one-line scope note and Alexander's OK before work starts.
5. **Keep one status table,** updated in the same commit as the work it describes.

## Change log

- Oct 9: canonical design adopted; checkpoint on for the final test too (`fb265a4`).
- Oct 10: margin keep test (Take 2); rule limit 600 to 1,200 characters; Jev refit, then Jev redesign (first, second attempt) pre-registered before each result; Gemini ceiling check; sealed stage wired to variant 3 and the frozen cutoff 0.756; cap $130; sealed exam released and started 18:25 UTC. Memo rewritten for concision with the learnings above.
