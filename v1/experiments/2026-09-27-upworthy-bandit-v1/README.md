# Experiment 6: the Jev + LLM router learning from partial feedback — Results

**Completed:** 2026-09-27 13:16 MDT · **Brief:** [`config/Task Brief 6_Bandit.md`](config/Task%20Brief%206_Bandit.md) (see its addendum) · **Preregistered verdict:** **Same quality, half the cost** — with the nuance below

## Headline

> With no answer key — each policy saw only the click rate of the headline it chose — the Jev + LLM router kept within the preregistered margin of the LLM-only policy on 1,000 unseen Upworthy tests (+10.9 vs +13.0 points of click lift over a random pick) at 46% of the cost. The Jev-only policy measurably learned from partial feedback alone (+5.6 → +7.7, p = 0.02); the LLM-only policy kept no edit.

**Read the verdict with this nuance:** the router gave up about **2 lift points** against the LLM (95% interval −4.0 to −0.1). That is inside the preregistered ±5-point margin and not significant by the preregistered Wilcoxon test (p = 0.09), so the rule says *same quality*. But the interval excludes zero, so the fair plain-English summary is: **the router captured about 84% of the LLM's lift at 46% of its cost.** In experiment 5 (labelled data) the router lost essentially nothing.

## Setup

- **Task:** pick the headline that will get the most clicks from 3–8 headlines tested for the same story (median 4). Reward = the chosen headline's real click rate from Upworthy's randomized tests; nothing about the other headlines is ever shown to a learner (enforced by a test).
- **Policies (all from experiment 1's version 0):** **R**, the Jev + LLM router (Jev picks when its top-vs-second margin ≥ τ, else the LLM with fixed version-0 instructions; τ is the label-free quantile sending 40% to the LLM; **the rubric learns**); **L**, LLM only (**instructions learn**); **J**, Jev only (**rubric learns**); **C**, Thompson sampling on six surface features.
- **Learning:** 4 rounds × 300 new practice tests; 15% seeded exploration; editors see only chosen headlines and their observed click rates; gate on 1,000 tests compares each policy's own greedy picks (sign test, p < 0.05).
- **Evaluation:** 1,000 sealed tests, once, greedy picks. **Lift** = chosen click rate ÷ the test's mean click rate − 1, in points (random pick = 0; always picking the best = +40.1 on this set).

## Results (sealed set, 1,000 tests)

| Policy | Click lift vs random pick | Best-headline hit rate | Cost / 1,000 decisions | Avg latency |
|---|---:|---:|---:|---:|
| Random pick (reference) | 0.0 | 22.4% | — | — |
| **LLM only (L)** — final = version 0 | **+13.0** | 34.2% | $1.452 | 1,302 ms |
| **Router (R)** — version 0 → final | +10.2 → **+10.9** | 32.2% | **$0.662** | 1,278 ms |
| **Jev only (J)** — version 0 → final | +5.6 → **+7.7** | 29.0% | $0.091 | 761 ms |
| Thompson sampling on surface features (C) | +2.2 | 25.0% | $0 | — |
| Best headline (reference) | +40.1 | 100% | — | — |

**Primary (R final vs L final):** mean difference −2.07 lift points; 95% bootstrap interval **−3.99 to −0.06**; Wilcoxon p = 0.087 (423 tests where picks differed); cost ratio **0.46**. Interval within ±5 and cost ≤ ½ → **Same quality, half the cost** (`bandit_v1` row 3).

**Signal:** all three learned policies beat a random pick (R +9.0 to +12.9; L +11.1 to +14.9; J +5.7 to +9.7).

**Did each policy learn from partial feedback?** (final vs version 0, preregistered)

| Policy | Edits kept (of 12) | Change in lift | p | Learned? |
|---|---:|---:|---:|---|
| Jev only (J) | 2 | **+2.1** | **0.020** | **Yes** |
| Router (R) | 1 | +0.7 | 0.21 | No (the edit only affects the 60% of tests Jev decides) |
| LLM only (L) | 0 | 0.0 | — | No (all 12 candidates rejected at the gate) |

**Secondary:** J vs L −5.3 (p 0.0001); R vs J +3.2 (p 0.0006) — routing to the LLM adds real value over Jev alone; C vs L −10.8 (p < 0.0001) — the textbook bandit on surface features learned little. Router with both components learned = router (L kept no edit). Memorization flag: off (LLM best-headline hit rate 34%).

## What the Jev policies learned without an answer key

| Policy | Kept edit | Gate |
|---|---|---|
| Router (R), round 1 | Drop `uses_second_person` ("you/your" does not earn clicks) | p 0.00004 |
| Jev only (J), round 1 | Drop `uses_second_person` | p 0.00001 |
| Jev only (J), round 3 | Add `references_third_person_protagonist` (helps): *"Does the headline refer to an individual person using third-person pronouns such as 'he', 'she', 'him', or 'her'?"* | p 0.05 |

Both Jev policies reached the same first conclusion independently, from their own picks' click rates alone. Experiment 1's editor, which had full labels, flagged the same question (48.5% win rate).

## Reading

- **Learning without an answer key works for the Jev rubric.** The cheap Jev policy found and kept edits that held up on unseen tests (+2.1 points, p = 0.02), guided only by the click rates of its own picks and a bandit evidence table.
- **The LLM policy did not learn**, as in experiments 1–2 on Upworthy: none of its 12 candidate rewrites beat version 0 at the gate.
- **The router still pays off**, but less cleanly than on labelled Arena data: it keeps ~84% of the LLM's lift at 46% of the cost, and clearly beats Jev alone.
- **The router's own learning was diluted:** the rubric edit only changes the ~60% of tests Jev decides, and the LLM part was fixed by design.

## Run integrity and cost

- Design, code and tests (88, incl. a strict no-leak test) committed before the paid run (`948ec90`); supervisor `b6d9e4e`. One learning attempt and one sealed attempt; 1,597 rate-limit/server retries in learning, all recovered.
- Arms L and R requested the same version-0 LLM picks at the start, so some early calls were paid twice (≈ $1–2).
- **Paid spend: $25.86** (cap $40).

## Limits

Replay of past randomized tests, not live traffic; one reward per test (noisy); story baselines differ; the ±5-point equivalence margin is wide relative to the LLM's +13 lift (stated before the run, but a tighter margin would not have been met); public archive (memorization flag off here); Jev-only and router share the rubric search space; the LLM part of the router was deliberately fixed.

## Files

[`artifacts/sealed_complete.json`](artifacts/sealed_complete.json) (verdict, all tests, per-policy metrics) · [`artifacts/final_versions.json`](artifacts/final_versions.json) (versions, full edit history, Thompson state) · [`artifacts/wip_summary.json`](artifacts/wip_summary.json) · `config/` · `splits/` · `telemetry/`.
