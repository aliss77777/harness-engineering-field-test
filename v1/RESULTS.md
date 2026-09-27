# Jev + LLM learning loops: results summary

**As of:** 2026-09-27 · Six experiments, all preregistered, all scored on sealed sets that no system saw during learning. Details: `experiments/COMPARISON.md` and each experiment's report.

## Bottom line

A Jev rubric that learns its criteria from real outcomes decides at about **1/23 of an LLM's cost**. On its own it is 3–7 points less accurate. **Routed together**, with Jev deciding the cases it is confident about and the LLM only the close calls, they **matched the LLM's accuracy (76.2% vs 76.3%) at 43% of the cost and a third less latency** (experiment 5). **Without an answer key** (experiment 6: each policy saw only its own choices' click rates), the Jev rubric still learned (p 0.02), and the router kept ~84% of the LLM's gain at 46% of the cost, within the preregistered margin.

## Chef's kiss scorecard

"Chef's kiss" means a Jev + LLM combination that is **as good as the LLM alone at half the cost or less**, confirmed on a sealed set.

| Criterion | Exp 4: stacked vote | **Exp 5: router, labelled data** | Exp 6: router, partial feedback |
|---|---|---|---|
| As accurate as the LLM | ✅ 75.6% vs 75.7% | ✅ **76.2% vs 76.3%**; difference −1.8 to +1.6 points, centred on zero | ⚠️ Within the ±5 margin, but −2.1 lift points (interval −4.0 to −0.1, excludes zero) |
| At ≤ ½ the LLM's cost | ❌ 104% (runs both on every decision) | ✅ **43%** | ✅ 46% |
| Faster than the LLM | ❌ | ✅ **874 ms vs 1,285 ms** (−32%) | ≈ same (1,278 vs 1,302 ms) |
| Learned without an answer key | — | — (labelled data) | ✅ Jev-only learned (p 0.02) · ❌ the router itself did not |
| **Verdict** | No meaningful gain | **✅ Clear chef's kiss** | **Win with an asterisk** |

**Why experiment 5 is the clear winner:**
- **No measurable accuracy loss.** Every accuracy check came out even:
  - The router beat the LLM on 36 decisions and lost on 37.
  - The interval for the difference sits evenly around zero.
- **Less than half the cost, and faster:** 43% of the LLM's cost, about a third faster.
- **It shows the mechanism, not just an average.** On the 62% of cases where Jev was confident, it was as accurate as the LLM (81.6% vs 81.7% on the same cases). Paying for the LLM there bought nothing. The LLM earned its cost only on the close calls.
- **Preregistered and fresh:** the routing threshold was frozen on the gate set before a new, never-seen test set was scored.

**Why experiment 6 carries an asterisk:**
- The router met the preregistered rule, but kept about 84% of the LLM's gain rather than all of it.
- Its own learning was not significant.
- The standout result there is different: **the Jev rubric learned with no answer key.**

**Caveats that apply to experiment 5:**
- Arena is labelled data.
- The LLM's memorization flag was on.
- The 40% routing budget was informed by experiment 4's exploratory curve. This is disclosed, and the test set was new.

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
| **6** | Upworthy, partial feedback only (1,000 tests; click lift over a random pick) | Can the router learn with no answer key and stay at LLM quality for less? | +13.0, $1.45 / 1k; kept 0 edits | +5.6 → **+7.7, learned** (p 0.02) | **Same quality, half the cost** (preregistered ±5): router **+10.9, $0.66 / 1k**. Nuance: −2.1 pts vs LLM (interval −4.0 to −0.1) |

Style baseline across Arena sets: 59.9–62.2%. Every LLM and Jev system beat it.

## Learning: start → final, LLM vs Jev

All numbers are on unseen (sealed) data. ✅ = passed the preregistered learning test (final beats its own start, p < 0.05). Experiments 4 and 5 had no training rounds; they combined components already learned in experiments 2 and 3.

| Exp | Setting (metric) | LLM: start → final | LLM change | Jev: start → final | Jev change |
|---|---|---|---|---|---|
| **1** | Upworthy headlines (accuracy) | 73.8% → 73.8% | 0 (no edits kept) | 61.2% → 61.2% | 0 (no edits kept) |
| **2** | Arena responses (accuracy) | 72.9% → 73.3% | +0.4 (p 0.50) | 66.7% → **70.1%** | **+3.4 ✅** (p 0.00002) |
| **3** | Arena, fresh set (accuracy) | 73.6% → 75.3%, re-scoring exp. 2's versions | +1.7 (p 0.009; replication, not preregistered) | Plain B, exp. 2's versions re-scored: 66.5% → 69.0% · B′ (decision trace): 66.5% → 67.9% · **B+ (fitted weights): 67.5% → 69.8%** | B: +2.5 (replication) · B′: +1.4 (p 0.11) · **B+: +2.3 ✅** (p 0.002) |
| **4** | Arena (accuracy), stacked vote | 75.7% (fixed) | — | 71.8% (B+, fixed) | — |
| **5** | Arena (accuracy), router | 76.3% (fixed) | — | 72.7% (B+, fixed) | — |
| **6** | Upworthy, no answer key (click lift over a random pick) | +13.0 → +13.0 | 0 (no edits kept) | Jev only: +5.6 → **+7.7** · router's Jev: +10.2 → +10.9 | **Jev only: +2.1 ✅** (p 0.02) · router: +0.7 (p 0.21) |

**Combined systems (no learning of their own):**

| Exp | System | Accuracy vs LLM alone | Cost vs LLM |
|---|---|---|---|
| 4 | Stacked vote | 75.6% vs 75.7% | 104% |
| **5** | **Router** | **76.2% vs 76.3%** | **43%** (32% faster) |
| 6 | Router, no answer key | +10.9 vs +13.0 lift points | 46% |

**Reading it:** Jev passed a preregistered learning test three times (experiments 2, 3, 6). The LLM never did; its only significant gain (+1.7) was a replication on a second set. B+ started 1 point above plain B because of the fitted weights alone.

## What went into the experiment 5 chef's kiss

Experiment 5 had no training of its own. It routed between two pieces learned earlier:

| Piece | Where it was learned | What it was |
|---|---|---|
| **LLM (A\*)** | Experiment 2, 4 rounds | Gemini 3.8 Flash with its learned instructions (one kept edit: "don't disqualify a response for minor truncation; users appreciate elaboration") |
| **Jev (J\* = B+ final)** | Experiment 3, 4 rounds | Six yes/no questions answered by Jev, with **code-fitted weights**, including one kept edit (a reworded "fulfils the user's request" question). This is the B+ result above (+2.3 ✅) |
| **Routing rule** | Set once on the gate set in experiment 5 | Jev decides when its weighted score is decisive; the 40% least-decisive cases go to the LLM |

## What the harness taught us

1. **Test one edit at a time.** Bundled edits kept 0 of 8; single edits started learning.
2. **Show the editor its rejected edits.** Otherwise it resubmits the same idea every round.
3. **Validate on held-out data, confirm on a sealed set.** The sealed set caught an edit that looked good only on the gate.
4. **Weight the criteria rather than explain the mistakes.** Fitted weights helped; decision traces did not.
5. **Route, don't vote.** Voting added nothing; routing halved the cost at the same accuracy.
6. **Preregister, fail loudly, resume from cache.** Rate limits, content blocks and spend limits never corrupted a result.

## Caveats

- **One LLM, two datasets.** The LLM's starting accuracy exceeded the memorization threshold (70%) in experiments 1–5, so part of its lead there may be recall (the flag was off in experiment 6, where its best-headline hit rate was 34%).
- **Experiments 1–5 were supervised learning with text parameters** (every pair came with its answer). **Experiment 6 used partial feedback** (a contextual bandit on replayed randomized tests), the first RL-style step; it is replay, not live traffic.
- **"Jev" vs "a yes/no rubric":** a headline claim about Jev specifically needs Loop C (the same rubric answered by an LLM), not yet run.

## Spend

Experiments 1–6: ≈ $78 in paid API calls ($1.92 + $37.09 + $9.10 + $1.57 + $1.54 + $25.86, plus checks).

## Next

- The router on a second task with no memorization risk, with partial feedback.
- Let the router's LLM part learn too, and tighten the equivalence margin.
- Loop C.
