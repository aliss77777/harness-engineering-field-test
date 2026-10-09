# Phase 1 pilot: 2 rounds of the Agent skill loop (2026-10-07)

**Question:** is MiniMax M3 learning from its own mistakes? **Spend:** $8.97 of a $20 cap. Practice and test bench tasks only; the sealed set was not touched. Settings: [`../config_phase1.yaml`](../config_phase1.yaml). Data: `round_1.json`, `round_2.json`, `summary.json`.

## Result: no fix was kept, but every candidate moved behaviour the right way

Each round, MiniMax ran 30 practice tasks, read its own failures, and proposed fixes to its playbook. Each fix was tested against the current version on the same 40 test bench tasks (one run each) and kept only if credit rose with one-sided Wilcoxon p < 0.10.

| On the 40 test bench tasks | Mean credit | Pass rate | Read every policy email | Broken "must not" checks per run | Keep-or-reject verdict |
|---|---|---|---|---|---|
| **Version 0** (the bench's prompt) | 0.522 | 15% | 6 of 23 | 0.90 | — |
| Round 1, fix A: *"After gathering source data and policy context, switch to acting; don't keep searching"* | **0.589** (+6.7) | **25%** | 9 of 23 | 0.60 | rejected: 13 better, 10 worse, p 0.17 |
| Round 1, fix B: *"Copy source values verbatim, character for character"* | 0.559 (+3.7) | 12% | 9 of 23 | 0.70 | rejected: 13 better, 9 worse, p 0.18 |
| Round 2, fix C: *"Check every item against the request's filters and scope before writing; exclude anything that doesn't clearly pass"* | 0.503 (−1.9) | 18% | 7 of 23 | **0.50** | rejected: 13 better, 12 worse, p 0.66 |

## What it tells us

1. **MiniMax can diagnose itself.** Its fixes target real failure patterns from Phase 0 (stopping early, paraphrasing values, letting excluded items through), and all three reduced broken "must not" checks (0.90 → 0.50–0.70 per run). Two of three also raised policy-email reading (6 → 9 of 23).
2. **The keep-or-reject test is underpowered.** Fix A's +6.7 points (and +10 points of pass rate) is the size of effect we hope for, but with one run on each of 40 tasks it can't reach p < 0.10. At this design, real improvements of a few points will usually be rejected.
3. **The harness wasted proposals.** 4 of the 5 refused proposals were refused only for being longer than 400 characters (MiniMax writes long rules); one named a specific detail. Round 2 tested a single fix instead of two.
4. **Run-to-run noise is still unmeasured.** 16 practice tasks ran with version 0 in both rounds, but 15 gave identical scores: the cache replayed most of each run, so they are not independent repeats.
5. **MiniMax was cheaper than estimated:** $0.028–0.055 per run (Phase 0 estimate: $0.062).

## Options before Phase 1 (for Alexander)

- **More power for the keep-or-reject test:** all 60 test bench tasks instead of 40, and/or 2 runs per task for each version (bypassing the cache, so repeats are independent). Roughly doubles the per-round cost (≈ $8–15 per round at the measured price).
- **Fix the length filter:** allow longer rules or ask the editor to shorten them, so each round tests two real candidates.
- **A cheap follow-up on fix A** (exploratory, labelled as post hoc): run it and version 0 on the other 20 test bench tasks (≈ $2) to see whether its +6.7 holds on all 60.
