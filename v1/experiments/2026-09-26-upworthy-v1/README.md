# Jev Learning Loop MVP — Results

**Completed:** 2026-09-26 17:37 MDT  
**Preregistered verdict:** **Hypothesis weakened**

## Headline result

| System | Version 0 | Final | 95% interval | Cost / 1,000 decisions |
|---|---:|---:|---:|---:|
| Loop A — Gemini instructions | 73.8% | 73.8% | 69.8%–77.5% | $0.7134 |
| Loop B — Jev rubric | 61.2% | 61.2% | 56.9%–65.4% | $0.0378 |
| Registered code baseline | — | 58.0% | — | $0 |

Both loops found signal, but none of the eight proposed changes passed the gate. Therefore neither loop improved beyond version 0. Loop A beat Loop B by 12.6 points; the paired comparison was statistically clear (p = 0.0000036). Loop B cost 5.3% as much per decision—about 18.9× cheaper—but was not within the preregistered ±3-point quality margin.

Loop A's 73.8% version-0 score triggered the preregistered memorization warning (>70%). The Upworthy dataset is public, so this result may partly reflect training-data familiarity and should not be treated as clean evidence of general reasoning ability.

## Learning gates

No edit was kept.

| Round | Loop A p | Loop B p |
|---:|---:|---:|
| 1 | 0.121 | 0.145 |
| 2 | 0.555 | 0.133 |
| 3 | 0.500 | 0.367 |
| 4 | 0.655 | 0.939 |

The gate required one-sided p < 0.10 and more improvements than regressions.

## Run integrity and cost

- Practice/gate/sealed sizes: 300/300/500.
- The sealed set was evaluated once after final versions were frozen.
- Loop A used 20 pairs per call and `reasoning_effort: medium`; reasoning tokens count toward cost.
- Version 0 was originally generated with Gemini 3.8 Flash through Google directly. All learning, decision, and editor calls in this run used OpenRouter.
- Jev's initial repeat test had zero binary disagreements; new questions used the two-rewording consistency check.
- Served model/provider checks passed throughout. Three transient Jev transport/server failures retried successfully.
- Learning-run paid cost: $1.5443. Sealed-run paid cost: $0.3754. Total for these two stages: **$1.9196**.

Full machine-readable results are in `artifacts/sealed_complete.json`; historical events are in compressed JSONL files under `telemetry/`. The exact run configuration and registered split IDs are included alongside them.
