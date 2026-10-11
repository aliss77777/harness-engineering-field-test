# Results: v2 Phase 1 (Take 2)

*A standalone mirror of the results in the canonical design ([`briefs/V2 Phase 1 Canonical Experiment Design.md`](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md)). If the two ever differ, the memo wins. Terms are the memo's "words we use". Last synced 2026-10-10 from the memo; derived numbers are produced by [`scripts/sealed_analysis.py`](scripts/sealed_analysis.py).*

## The hypothesis and the story we can defend

**Hypothesis.** MiniMax learns kind of like an RL model learning a policy, but without updating its weights. Jev's routing toggles between MiniMax and Gemini. Together, the harness and the Jev router deliver gains in speed and cost without a loss of quality, as we showed in v1.

**The story we can defend (Oct 10, after the sealed exam).** An open-weight model, taught by a harness from its own mistakes, got within about 6 points of a premium model's credit on unseen tasks at 15% of the cost. A redesigned checker improved on the original but did not show value as a router on this task: the router reached Gemini's credit by sending 45% of tasks to Gemini, not by choosing well.

## At a glance

| | Starting point | End point | Change |
| --- | --- | --- | --- |
| MiniMax credit on 80 unseen tasks | 0.573 | **0.755** | **+0.182** (95% interval +0.095 to +0.272) |
| MiniMax fully passed | 23 (29%) | 33 (41%) | +10 tasks |
| Gap to Gemini alone (0.811) | −0.238 | −0.056 | closed about three quarters |
| Cost per task, MiniMax vs Gemini | | $0.042 vs $0.273 | 15% |
| Router vs Gemini alone | | 0.804 vs 0.811 at 62% of the cost | credit within 3 points; cost not at most half |
| Jev as a router (same-playbook AUC) | 0.475 (original) | 0.566 on the exam | improved, below the 0.65 bar |

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
| Seven later candidates on top of the final playbook (rounds 3 and 4, replay) | 0.746 to 0.792; none kept | 19 to 26 | `phase1/run/take2/skill_history.json`, `skill_replay.json`, `replay_decision.json` |
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
