# V2 Phase 1: Canonical Experiment Design

Oct 9, 2026 · @Alexander Liss · rewritten Oct 10, 2026 to carry what Take 1 and Take 2 taught us. The sealed exam opened Oct 10, 18:25 UTC and finished 22:42 UTC; results are in "What the sealed exam showed".

## The question

Phase 1 tests whether a cheap open-weight model, working inside a harness we built, can come close to a premium model's score on real business workflows for a fraction of the cost.

**Where v1 left us.** On a simple task (which of two answers would people prefer?), Jev, a small checker, learned from its mistakes, and Gemini's own instructions barely improved. Routing through Jev matched Gemini's accuracy (76.2% vs 76.3%) at about half the cost.

**What v2 changes.** The task is AutomationBench: 200 Finance and HR workflows where an agent takes many steps and must follow rules hidden in policy emails. MiniMax M3 does the work and learns by rewriting its own playbook. Jev checks finished runs. Gemini redoes the runs Jev doubts. We compare that whole system with Gemini doing every task alone.

**Hypothesis.** MiniMax learns kind of like an RL model learning a policy, but without updating its weights. Jev's routing toggles between MiniMax and Gemini. Together, the harness and the Jev router deliver gains in speed and cost without a loss of quality, as we showed in v1.

**The story we can defend (Oct 10, after the sealed exam).** An open-weight model, taught by a harness from its own mistakes, got within about 6 points of a premium model's credit on unseen tasks at 15% of the cost. A redesigned checker improved on the original but did not show value as a router on this task: the router reached Gemini's credit by sending 45% of tasks to Gemini, not by choosing well.

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

## What the sealed exam showed (opened once, Oct 10; 80 tasks, one run each)

Every number below, with its source file, is in the Appendix.

| Question | Result |
| --- | --- |
| **2. Did MiniMax learn?** | **Yes.** Credit 0.573 to 0.755, **+0.182** (95% interval +0.095 to +0.272, p < 0.001). Fully passed 23 (29%) to 33 (41%). Closed about three quarters of the gap to Gemini (the starting playbook was −0.238 behind). |
| **MiniMax final vs Gemini alone** | 0.755 vs 0.811, **−0.056** (−0.131 to +0.020). Fully passed 33 vs 47 (41% vs 59%). Cost per task $0.042 vs $0.273 (**15%**). |
| **1. Router vs Gemini alone** (main comparison) | Credit **0.804 vs 0.811**, −0.007 (−0.061 to +0.053): within 3 points. Cost **$0.170 vs $0.273 (62%)**: not at most half. 45% of tasks escalated at the frozen cutoff 0.756. Fully passed 42 vs 47. Time 166 s vs 177 s. |
| **3. Is Jev a good checker?** | **No on the exam.** Redesigned Jev same-playbook AUC **0.566** [0.44, 0.70] against a bar of 0.65; lowest-30% gap 0.06 against 0.10. Original rubric: AUC 0.567, gap 0.21. Neither learned (starting vs final rubric accuracy 0.600 vs 0.625, p 0.34). |
| **4. What does the checkpoint add?** | **At exam time, little with the learned playbook; during learning, plausibly a lot.** Final playbook, checkpoint on vs off: credit 0.755 vs 0.775 (−0.020, interval −0.075 to +0.033); **fully passed 33 (41%) on vs 30 (37.5%) off**; broken "must not" rules per run 0.80 on vs 0.69 off; holds 0.19 per run. Unshielded, the read-policies-first habit rose from **31%** (starting playbook, test bench, V2-5a) to **84%** (final playbook, sealed), and the learned rule cites the checkpoint's holds. The checkpoint worked as a training scaffold. The counterfactual (learning with it off) was not run. |

**The router, decomposed.** Against random escalation at the same 45% share (expected 0.780) it gained **+0.024** (−0.021 to +0.071). Reviewing Jev's lowest 45% of runs finds 46% of the poor runs (chance 45%). A perfect detector would have added about +7 points (ceiling check).

Jev's AUC on validation (0.666) did not replicate on the exam (0.566), so the honest level of the redesigned Jev is lower than the 0.60 to 0.65 estimated before.

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
- **The checkpoint worked as a training scaffold.** Rule R2x cut checkpoint holds from 0.75 to 0.15 per run on the test bench, and unshielded the read-policies-first habit rose from 31% to 84%. At exam time the learned playbook did not need the shield (credit 0.755 on vs 0.775 off; fully passed 33 vs 30). Whether the checkpoint was *necessary* for the playbook to learn the habit was not tested.
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

## Limits of these results

- **Small sample.** 80 tasks: a pass rate is good to about ±11 points, a credit difference to about ±6.
- **One domain subset.** Finance and HR only. Published models are scored on 600+ tasks across all domains; Zapier's best fully passes 51% (v1.0.6) while our Gemini Flash passes 59% on our subset, so our subset is probably easier. "In the same range" is as far as that comparison goes.
- **The yardstick is Gemini 3.8 Flash as it comes** (no playbook, no checkpoint), not a frontier-tier model. Whether the harness helps a premium model was not tested.
- **Selection luck.** The margin keep test was adopted after seeing Take 1, and the test bench numbers (0.62 to 0.78) were optimistic; the exam shows 0.755.
- **Jev's estimates moved.** Validation 0.666, exam 0.566; both intervals overlap the 0.65 bar, so the fair level is about 0.6, not proven either way.
- **The cutoff did not transfer as a share.** Set for 30%, it escalated 45% on the exam.
- **One run per task,** so every difference carries run-to-run noise (about 0.02 on a 60-task mean).
- **The checkpoint's training-time role is untested:** no learning loop was run with it off.
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
- Oct 10 (evening): sealed exam finished 22:42 UTC. Results, the corrected checkpoint reading (training scaffold) and a sourced appendix added; derived numbers saved as `scripts/sealed_analysis.py`.

## Appendix: the results with their sources

Paths are relative to `v2/`. Derived numbers come from `scripts/sealed_analysis.py` (no model calls), which writes `phase1/run/take2/sealed_analysis.json`. "Results" below means `phase1/run/take2/sealed_results.json`.

### A. Sealed exam arms (80 tasks, one run each)

| Measure | Value | Source |
| --- | --- | --- |
| MiniMax starting playbook, checkpoint on | credit 0.573; fully passed 23 (29%); $0.044/run; holds 0.82; reads all policies first 64% | `logs/phase1_run/minimax-p1-v0-cp-sealed.jsonl`; `sealed_analysis.json` |
| MiniMax final playbook, checkpoint on | 0.755; 33 (41%); $0.042; holds 0.19; 98% | `…/minimax-p1-s78766c8a-cp-sealed.jsonl` |
| MiniMax final playbook, checkpoint **off** | 0.775; 30 (37.5%); $0.037; holds 0; 84% | `…/minimax-p1-s78766c8a-nocp-sealed.jsonl` |
| Gemini 3.8 Flash alone (no playbook, no checkpoint) | 0.811; 47 (59%); $0.273; reads policies first 96% | `…/gemini-p1-v0-nocp-sealed.jsonl` |
| Gemini redo on the 36 escalated tasks | credit 0.824 (Gemini alone on the same tasks 0.795) | `…/gemini-p1-v0-nocp-sealed-redo.jsonl`; `sealed_analysis.json` |

### B. Sealed exam questions

| Question | Value | Interval / test | Source |
| --- | --- | --- | --- |
| Starting line: starting playbook vs Gemini | −0.238 | −0.341 to −0.132 | Results → `V2-1_starting_line` |
| Q2 final vs starting playbook | +0.182 | +0.095 to +0.272; p = 8.9e−5 | Results → `V2-2a_did_minimax_learn` |
| MiniMax final vs Gemini alone | −0.056 | −0.131 to +0.020 | Results → `minimax_final_vs_gemini_alone` |
| Q1 router vs Gemini: credit | 0.804 vs 0.811 (−0.007) | −0.061 to +0.053 | Results → `V2-3_main_comparison` |
| Router cost per task; ratio | $0.170 vs $0.273; 0.622 | — | same |
| Router time per task | 166 s vs 177 s | — | same |
| Router fully passed | 42 vs Gemini 47 | — | `sealed_analysis.json` → `sealed.router_fully_passed` |
| Escalated at cutoff 0.7563 | 36 of 80 (45%); planned 30% | — | Results → `router_jev` |
| Router vs random escalation, same share | +0.024 (0.804 vs 0.780) | −0.021 to +0.071 | `sealed_analysis.json` → `sealed.router_minus_random_escalation` |
| Review queue: poor runs (<0.8) found in Jev's lowest 20 / 30 / 45 / 60% | 9 / 10 / 16 / 22 of 35 (chance 7 / 10.5 / 15.8 / 21) | — | `sealed_analysis.json` → `sealed.review_queue` |
| Q3 redesigned Jev: AUC; gap | 0.566; 0.060 | AUC 0.436 to 0.696; gap −0.079 to +0.263 | Results → `jev_on_sealed.redesign_second_attempt` |
| Q3 original rubric: AUC; gap | 0.567; 0.210 | 0.440 to 0.693; 0.065 to 0.390 | Results → `jev_on_sealed.original_rubric` |
| Q3 original rubric learning: accuracy starting vs final | 0.600 vs 0.625 (4 better, 2 worse) | p = 0.344 (McNemar) | Results → `V2-2b_did_jev_learn` |
| Q4 credit on vs off | 0.755 vs 0.775 (−0.020) | −0.075 to +0.033 | Results → `V2-5_checkpoint_extra.guard_credit` |
| Q4 fully passed on vs off | 33 (0.4125) vs 30 (0.375) | not tested | Results → `…pass_rate` |
| Q4 broken "must not" rules per run, on vs off | 0.80 vs 0.6875 (+0.1125) | −0.05 to +0.29 | Results → `…primary_broken_must_not_per_run` |
| Q4 silent-wrong / caught-wrong, on (off) | 0.525 / 0.0625 (0.625 / 0) | — | Results → `…silent_and_caught_wrong` |
| Read policies first, final playbook, checkpoint on (bar 0.90) | 0.982 | — | Results → `…sanity_read_policies_before_first_write` |

### C. Learning path before the exam (test bench, 60 tasks, one run each)

| Step | Credit | Fully passed | Source |
| --- | --- | --- | --- |
| Starting playbook (checkpoint on) | 0.620 | 11 | `logs/phase1_run/minimax-p1-v0-cp-bench.jsonl`; `sealed_analysis.json` → `test_bench` |
| + R1a ("do every required write") | 0.675 | 14 | `…-sc9e21881-cp-bench.jsonl` |
| + R2x ("read policy emails before any write"), the final playbook | 0.778 | 21 | `…-s78766c8a-cp-bench.jsonl` |
| Eight later candidates (rounds 3 and 4, replay) | 0.746 to 0.792; none kept | 19 to 26 | `phase1/run/take2/skill_history.json`, `skill_replay.json`, `replay_decision.json` |
| Seven neighbouring playbooks | mean 0.764, SD 0.020 | — | `sealed_analysis.json` → `test_bench.seven_neighbour_playbooks` |
| Practice cross-check, 45 shared tasks (final vs starting) | 0.633 → 0.756 (+0.123) | — (interval +0.008 to +0.240) | `sealed_analysis.json` → `practice_cross_check` |
| Take 1 (p-value keep test) | 4 candidates, none kept in 2 rounds | — | `phase1/run/take1/skill_history.json` |
| V2-5a, starting playbook, checkpoint off vs on | 0.572 vs 0.649 (+0.077); reads policies first 31% (11/36) vs 75% (27/36); broken rules 0.88 to 0.67 | interval −0.02 to +0.17 | `action_masking/v2_5a/REPORT.md`; `logs/v2_5a/gate-off.jsonl`, `gate-on.jsonl` |

### D. Jev designs, each against the bar (AUC at least 0.65 with lower bound above 0.5, gap at least 0.10)

| Design | AUC [95%] | Gap | Data | Source |
| --- | --- | --- | --- | --- |
| Original rubric, as fitted | 0.73 practice; **0.475** test bench | — | 60 + 60 runs | `phase1/run/take2/rubric_final.json`, `rubric_history.json` |
| Refit (weights only), cross-validated by task | **0.525** [0.421, 0.629] | 0.081 | 1,052 runs, 120 tasks | `phase1/run/take2/jev_refit.json` |
| Redesign, first attempt: development | 0.650 to 0.677 after one kept edit | 0.343 to 0.373 | 212 practice runs | `verifier_baseline.json`, `verifier_learning.json` |
| Redesign, first attempt: validation (opened once) | **0.612** [0.514, 0.719]; final playbook alone 0.482 [0.327, 0.640] | 0.166 | 840 runs, 14 playbooks | `verifier_validation.json` |
| Second attempt: development, variants 1 / 2 / 3 / 4 | 0.608 / 0.596 / **0.648** / 0.602 | 0.128 / 0.086 / 0.125 / 0.090 | 180 runs | `verifier_d2_development.json` |
| Second attempt: validation (opened once), variant 3 | **0.666** [0.548, 0.784]; variants 1 / 2 / 4: 0.663 / 0.655 / 0.588 | 0.194 [0.067, 0.327] | 120 fresh runs | `verifier_d2_validation.json` |
| Same design on the sealed exam | **0.566** [0.436, 0.696] | 0.060 | 80 runs | Results → `jev_on_sealed` |
| Learned vs starting question-writer instructions, fresh runs | 0.663 vs 0.615: +0.048 | −0.027 to +0.129 | 120 runs | `verifier_instructions_check.json` |
| By failure kind (second attempt, validation): wrong content / skipped actions / rules broken | 0.716 / 0.607 / 0.532 | — | 120 runs | `verifier_d2_validation.json` → `per_kind` |
| Frozen cutoff | 0.7563 (30th percentile of variant 3 scores) | — | 120 fresh runs | `jev_cutoff_second_attempt.json` |

### E. What a better Jev could be worth (ceiling check)

| Measure | Value | Source |
| --- | --- | --- |
| Tasks the final playbook failed (<0.8), practice and test bench | 54 of 120 | `phase1/run/take2/ceiling.json` |
| On those 54: MiniMax; Gemini | 0.528; 0.696 (20 of 54 fully passed) | same |
| On those 54: fresh MiniMax draws (2 per task) | 0.628 | `sealed_analysis.json` → `ceiling_extras` |
| MiniMax alone, all 120 | 0.753 | `ceiling.json` |
| Perfect detector: escalate all failures; worst 30% | 0.828; 0.820 | `ceiling.json` |
| Perfect detector against the fresh-draw baseline | about +0.03 | `sealed_analysis.json` → `ceiling_extras` |
| Re-run MiniMax when the first run failed | +0.045 at $0.045 | same |
| Gemini cost per run on those tasks | $0.278 | `ceiling.json` |

### F. Published context (not comparable one to one)

| Source | Figure | Metric |
| --- | --- | --- |
| Zapier leaderboard v1.0.6 (private set, 600+ tasks, all domains) | Gemini 4 Argon (High) 51.3%; Claude Sonnet 5.5 44.8% | share of tasks fully passed |
| Artificial Analysis AutomationBench-AA (July 2026) | Claude Fable 5 48.6% (about 73% raw objective completion) | objectives met without a guardrail violation |

### G. Spend

| Item | Amount | Source |
| --- | --- | --- |
| Phase 1 on the tracker at the end | $117.7 of the $130 cap | `results/phase1_run/spend.json` |
| Ceiling check; fresh runs; sealed exam | $15.30; $11.11; about $42.4 | `spend_ceiling.json`, `spend_fresh.json`, tracker deltas |
