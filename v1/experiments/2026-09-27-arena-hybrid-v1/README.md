# Experiment 4: one LLM + Jev hybrid (stacked vote) — Results

**Completed:** 2026-09-27 · **Brief:** [`config/Task Brief 4_Hybrids.md`](config/Task%20Brief%204_Hybrids.md) · **Preregistered verdict:** **No meaningful gain**

## Headline

> Combining the best LLM harness with the best Jev harness in a fitted vote did not beat the LLM alone on 1,000 fresh Arena battles (75.6% vs 75.7%; 95% interval of the difference −0.9 to +0.7 points). The two disagreed on only 21% of pairs, and when they did, the fitted vote almost always sided with the LLM. In an exploratory cascade, letting Jev decide the half of pairs where it was most confident cost 0.5 points of accuracy (75.2%) and cut the decision cost roughly in half.

## Setup

- **A\*** (best LLM harness): experiment 2's final Loop A (`A-r1-c2`), Gemini 3.8 Flash.
- **J\*** (best Jev harness, by the brief's preregistered rule): experiment 3's B-plus final (`Bw-r4-c1`, six questions with fitted weights), Jev 1.13.
- **Hybrid:** logistic regression, no intercept, on A\*'s pick (±1), J\*'s six weighted per-question differences and J\*'s total; fitted on practice ∪ gate (1,999 pairs; one Gemini-refused pair left out); C = 10 by 5-fold CV. Frozen before the sealed stage ([`artifacts/hybrid_model.json`](artifacts/hybrid_model.json)).
- **Sealed-4:** 1,000 fresh pairs from the sealed prompt buckets, excluding all 3,000 pairs of experiments 2 and 3's sealed sets; no pair or prompt overlap with practice, gate or earlier sealed sets; winner first in exactly 50%. Evaluated once.

## Results (sealed-4, 1,000 pairs)

| System | Accuracy | 95% interval | Cost / 1,000 decisions |
|---|---:|---:|---:|
| LLM alone (A\*) | 75.7% | 73.0–78.3% | $1.510 |
| Jev alone (J\*) | 71.8% | — | $0.065 |
| **Hybrid (stacked vote)** | **75.6%** | 72.8–78.2% | $1.575 |
| Style code baseline | 62.2% | — | $0 |

- **Primary test, hybrid vs LLM:** 8 pairs better, 9 worse; McNemar p = 1.0. The 95% interval for (hybrid − LLM) is −0.9 to +0.7 points, inside the ±3-point margin → **no meaningful gain**.
- **Hybrid vs Jev:** hybrid better (114 vs 76, p 0.007). **LLM vs Jev:** LLM better (123 vs 84, p 0.008).
- **All three vs the style baseline:** all clearly better (p < 0.0001).
- **Agreement:** the LLM and Jev agreed on 79.3% of pairs. On the 20.7% where they disagreed, the hybrid sided with Jev only 8% of the time.
- **Refused pairs:** 1 pair refused by Gemini; the hybrid used Jev's pick (correct).
- **Memorization flag:** on (LLM at 75.7%).

## Exploratory: the cascade (not part of the verdict)

Jev decides every pair where its score margin is at least the threshold chosen on gate (0.608); the LLM decides the rest.

| | LLM share | Accuracy | Cost / 1,000 |
|---|---:|---:|---:|
| LLM alone | 100% | 75.7% | $1.51 |
| **Cascade (threshold from gate)** | **49%** | **75.2%** | **$0.80** |
| Jev alone | 0% | 71.8% | $0.065 |

Full curve (LLM share → accuracy): 0% 71.8 · 10% 73.0 · 20% 74.6 · 30% 75.5 · 40% 76.0 · 50% 75.2 · 60–100% 75.2–75.8. Most of the LLM's advantage comes from the ~30–40% of pairs where Jev is least sure. No significance test was preregistered for the cascade; treat it as a direction for the next experiment, not a result.

## Reading

- **The fitted vote learned to trust the LLM.** Where the LLM and Jev disagreed, the LLM was right more often, so the stacker mostly followed it. Jev's per-question signal carried little information the LLM's single pick did not already have.
- **The cost story is in routing, not voting.** The stacked vote needs both systems on every pair, so it can only win on accuracy, and it didn't. The cascade keeps most of the LLM's accuracy at about half its cost. That is the version worth a preregistered test.

## Run integrity and cost

- Design, code and tests committed before any paid call (`a199e47`); the model was fitted and frozen (`0419f0f`) before the sealed set was read.
- Fit: $0.00 (all practice/gate decisions replayed from cache). Sealed: $1.57. **Total: $1.57.**
- One sealed attempt, no errors requiring a retry.

## Limits

One task; LLM memorization flag on (every LLM-containing system inherits it); 1,000 pairs can only resolve differences of about 3 points or more; practice and gate reused from experiments 2 and 3 for fitting.

## Files

[`artifacts/sealed_complete.json`](artifacts/sealed_complete.json) (verdict, tests, agreement, cascade curve) · [`artifacts/hybrid_model.json`](artifacts/hybrid_model.json) (frozen model, CV scores, fit-set accuracy) · `config/` · `splits/` (sealed-4 IDs; practice and gate are experiment 2's) · `telemetry/`.
