# Task #4 brief: LLM + Jev hybrids

**Written:** 2026-09-26 · **Owner:** Alexander · **Status:** design only, not scheduled · **Builds on:** experiments 2 (Arena) and 3 (decision trace). The harness, logging, gate, spend cap, content-block rule and telemetry are unchanged unless stated here. · **Repo:** same repo, new config/task pair (`config_arena4.yaml`, `task_arena4.yaml`).

## 1. Why this experiment

Experiments 1–3 raced an LLM decider (Loop A) against a Jev rubric (Loop B and its variants). But Jev is designed to work *alongside* an LLM. The Arena results so far point to a clear division of labour: the LLM is more accurate (≈77% vs ≈70–72% on gate), and Jev is about 20× cheaper per decision, reads every text without content blocks, and gives a readable per-question trace.

**The question:** does combining them beat either one alone, on accuracy or on accuracy per dollar?

> **Chef's kiss:** a hybrid that is significantly more accurate than the LLM alone, or matches it at half the cost or less.

## 2. The components (chosen before this experiment's sealed set is touched)

- **A\*** = experiment 2's final Loop A instructions (unchanged).
- **J\*** = the Jev arm with the highest accuracy on **experiment 3's fresh sealed set**, among experiment 2's B final, B-prime final and B-plus final. Experiment 3's sealed set acts as this experiment's *selection* set; this experiment gets its own new sealed set (section 4), so selecting on experiment 3's results is not peeking.
- **Style baseline** (experiment 2's six features), as a reference line.

No component is re-learned here. This experiment tests *combination*, not learning.

## 3. The hybrids (three, fixed)

| # | Name | How it decides | Cost per decision | Tuned on |
|---|---|---|---|---|
| H1 | **Cascade** | J\* decides when its score margin is large; the LLM (A\*) decides only the close calls | Jev on every pair + LLM on the routed share | Margin threshold τ, on gate |
| H2 | **Stacked vote** | A small logistic regression combines A\*'s pick (±1) with J\*'s per-question signed differences | Jev + LLM on every pair | Weights, on practice ∪ gate |
| H3 | **Jev-informed LLM** | The LLM sees the request, both responses, **and J\*'s per-question P(yes) table for each**, then decides | Jev + LLM (larger prompt) on every pair | Nothing tuned; one fixed instruction |

Details:

- **H1 threshold rule (preregistered):** on the gate set, choose the τ with the highest accuracy among thresholds that send **at most 50%** of pairs to the LLM. Ties go to the lower LLM share. Report the full accuracy-vs-LLM-share curve.
- **H2 model:** no intercept (X/Y order is arbitrary), L2 regularization chosen by 5-fold cross-validation on practice ∪ gate (2,000 pairs). Features: A\*'s pick, J\*'s signed per-question differences, and J\*'s total score. Report the fitted weights, so we can see how much the stack trusts each part.
- **H3 instruction:** A\*'s instructions, plus one fixed paragraph: *"For each response you also get a checklist scored by a separate model: the probability that each statement is true. Use it as evidence, not as the answer."* Verified once on gate before sealed; no iteration on sealed.
- **Content blocks:** when Gemini refuses a pair, H1–H3 fall back to J\*'s pick (the LLM-only system still uses the coin flip). This is a genuine advantage of combining them and is reported as its own line: accuracy on blocked pairs.

## 4. Data

- Practice and gate: the same files as experiments 2 and 3 (tuning only).
- **New sealed set ("sealed-4"):** **1,000 pairs** (Alexander, 2026-09-26: future experiments use 1,000 pairs per set instead of 1,500, for speed) from the same prompt-hash buckets, excluding every pair used in experiment 2's and experiment 3's sealed sets (≈10,800 remain). Winner shown first in exactly 50%. At 1,000 pairs a real gain of about 3–4 points is needed to show up clearly; smaller hybrid gains may read as inconclusive.
- Every system (A\*, J\*, H1–H3, baseline) is scored once on sealed-4, on the same pairs.

## 5. Preregistered analysis

**Primary (two-sided McNemar on sealed-4, Holm-corrected across the three hybrids):** each hybrid vs A\*, the stronger single system.

**Apply the first row that matches:**

| Result | Verdict |
|---|---|
| No hybrid differs from A\* and none meets the cost row | **No hybrid gain** |
| A hybrid beats A\* (significant after Holm) | **Hybrid beats the LLM** (chef's kiss). Name it; also report it vs J\* |
| H1 is within ±3 points of A\* (95% interval of the paired difference) **and** costs ≤ ½ of A\* per decision | **Same quality, half the cost** (chef's kiss, cost version) |
| A hybrid is significantly *worse* than A\* | **Combination hurts** (report which, and why) |
| Anything else | **Inconclusive** |

**Also reported:** each hybrid vs J\*; accuracy on the LLM-routed vs Jev-decided pairs (H1); H2's weights; the H1 cost curve; accuracy on blocked pairs; each system vs the style baseline; cost per 1,000 decisions for all systems; the memorization flag (A\* or any LLM-containing hybrid above 70%).

## 6. Cost and time (estimate)

| Item | Pairs | Estimate |
|---|---|---|
| A\* on sealed-4 | 1,000 | ≈ $1.60 |
| J\* on sealed-4 (and on gate/practice for H1/H2 features, mostly cached) | 1,000 (+cache) | ≈ $0.10 |
| H3 on gate (one check) + sealed-4 | 2,500 | ≈ $5–6 (larger prompt) |
| H1 and H2 | computed from A\* and J\* decisions | ≈ $0 |
| **Total** | | **≈ $7–8**, cap $15 |

Time: under an hour if the Gemini rate limit is lifted (see section 8), about 2 hours at the current 3 workers.

## 7. Honest limits

- **Memorization carries over.** If A\* partly recalls Arena, every hybrid that includes it inherits the edge. Say so in the headline.
- **Tuning data reuse.** Practice and gate have been used in experiments 2 and 3; sealed-4 is the only clean test.
- **One task.** A hybrid win on Arena is still one task (the story-arc caveat from the MVP brief).
- **Stacking needs both calls.** H2 can't be cheaper than A\*; its only possible win is accuracy.

## 8. Before running

1. **Speed:** OpenRouter BYOK with the Google AI Studio key is **enabled** (2026-09-26). Checked: served provider still "Google AI Studio"; reported cost still equals tokens × reference price. Keep OpenRouter's shared-capacity fallback on, so throttling on the BYOK quota overflows to shared capacity.
2. Experiment 3's sealed verdict must exist (it selects J\*).
3. Commit this design, the analysis code and its tests before any paid call, as in experiments 2 and 3.

## 9. Build (≈ half a day)

1. `prep_arena4.py`: sealed-4 draw with overlap checks.
2. `hybrids.py`: H1 threshold selection, H2 stacker, H3 prompt (the H3 prompt is a new decider view that adds J\*'s table per response).
3. `verdict_hybrid.py`: rows above, with Holm; tests for every row.
4. `sealed_hybrid.py`: guarded, single run on sealed-4; writes `results/arena4/sealed_complete.json`; live telemetry as before.
5. Fake-client dry run end to end, then smoke test on 20 practice pairs, then cost estimate vs cap.

## 10. Out of scope

Re-learning either component inside the hybrid; a learned router; multi-turn Arena; a second task (the natural next step if a hybrid wins).
