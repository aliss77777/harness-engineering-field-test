# Jev + LLM learning loops: results summary

**As of:** 2026-09-27 · Five experiments, all preregistered, all scored on sealed sets that no system saw during learning. Details: `experiments/COMPARISON.md` and each experiment's report.

## Bottom line

A Jev rubric that learns its criteria from real outcomes decides at about **1/23 of an LLM's cost**. On its own it is 3–7 points less accurate. **Routed together**, with Jev deciding the cases it is confident about and the LLM only the close calls, they **matched the LLM's accuracy (76.2% vs 76.3%) at 43% of the cost and a third less latency** (experiment 5).

## Labels used below

| Label | What it is |
|---|---|
| **LLM loop** | Gemini 3.8 Flash deciding from prose instructions; an LLM editor rewrites the instructions |
| **Jev loop** | Jev 1.13 answering a yes/no rubric per item; code sums the answers; an LLM editor rewrites the rubric |
| **Jev (weighted)** | The Jev loop with per-question weights fitted by code |
| **Style baseline** | Six simple text features and a logistic regression, with no LLM |
| **Learned?** | Final version beats its starting version on the sealed set (paired McNemar, p < 0.05) |

## Results

| # | Task | Question | LLM loop | Jev loop | Verdict |
|---|---|---|---|---|---|
| **1** | Upworthy headlines (500 sealed pairs) | Does the Jev loop learn better or cheaper than the LLM loop? | 73.8% → 73.8%, not learned | 61.2% → 61.2%, not learned | **Hypothesis weakened**: neither learned; LLM more accurate |
| **2** | Chatbot Arena responses (1,500) | Same question, rebuilt harness | 72.9% → 73.3%, not learned (p 0.50) | 66.7% → **70.1%**, **learned** (p 0.00002) | **Only the Jev loop learned**; LLM still more accurate; Jev ≈ 23× cheaper |
| **3** | Arena, fresh set (1,500) | Do decision traces or fitted weights help the Jev loop? | 73.6% → 75.3% (same versions as exp. 2) | Traces 67.9% (no gain) · **Jev (weighted) 67.5% → 69.8%, learned** (p 0.002) | **Traces: no difference. Weights: help** (p 0.011) |
| **4** | Arena, fresh set (1,000) | Does a fitted vote of LLM + Jev beat the LLM? | 75.7% | 71.8% (weighted) | **No meaningful gain**: vote 75.6% |
| **5** | Arena, fresh set (1,000) | Does routing (Jev first, LLM on close calls) keep LLM quality for less? | 76.3%, $1.48 / 1k | 72.7%, $0.065 / 1k | **Same quality, half the cost**: router **76.2%, $0.63 / 1k** |

Style baseline across Arena sets: 59.9–62.2%. Every LLM and Jev system beat it.

## What the harness taught us

1. **Test one edit at a time.** Bundled edits kept 0 of 8; single edits started learning.
2. **Show the editor its rejected edits.** Otherwise it resubmits the same idea every round.
3. **Validate on held-out data, confirm on a sealed set.** The sealed set caught an edit that looked good only on the gate.
4. **Weight the criteria rather than explain the mistakes.** Fitted weights helped; decision traces did not.
5. **Route, don't vote.** Voting added nothing; routing halved the cost at the same accuracy.
6. **Preregister, fail loudly, resume from cache.** Rate limits, content blocks and spend limits never corrupted a result.

## Caveats

- **One LLM, two datasets.** The LLM's starting accuracy exceeded the memorization threshold (70%) every time, so part of its lead may be recall.
- **This was supervised learning with text parameters.** Every pair came with its answer. Experiment 6 (designed) moves to partial feedback, a contextual bandit.
- **"Jev" vs "a yes/no rubric":** a headline claim about Jev specifically needs Loop C (the same rubric answered by an LLM), not yet run.

## Spend

Experiments 1–5: ≈ $52 in paid API calls ($1.92 + $37.09 + $9.10 + $1.57 + $1.54, plus checks).

## Next

- **Experiment 6 (designed):** learning from partial feedback on Upworthy. `Task Brief 6_Bandit.md`.
- The experiment 5 router on a second task with no memorization risk.
- Loop C.
