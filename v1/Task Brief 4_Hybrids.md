# Task #4 brief: one LLM + Jev hybrid

**Written:** 2026-09-26 · **Revised:** 2026-09-26 (single hybrid: the stacked vote; cascade kept only as a free, exploratory add-on; 1,000-pair sets) · **Owner:** Alexander · **Status:** built and preregistered 2026-09-27 (code: `prep_arena4.py`, `hybrid.py`, `fit_hybrid.py`, `sealed_hybrid.py`, `verdict_hybrid.py`) · **Builds on:** experiments 2 (Arena) and 3 (decision trace). The harness, logging, spend cap, content-block rule and telemetry are unchanged unless stated here. · **Repo:** same repo, new config/task pair (`config_arena4.yaml`, `task_arena4.yaml`).

## 1. Why this experiment

Experiments 1–3 raced an LLM decider (Loop A) against a Jev rubric (Loop B and its variants). But Jev is designed to work *alongside* an LLM. The Arena results so far point to a clear division of labour: the LLM is more accurate (≈77% vs ≈70–72% on gate), and Jev is about 20× cheaper per decision, reads every text without content blocks, and gives a readable per-question signal.

**The question:** does combining the best LLM harness and the best Jev harness beat the LLM alone?

> **Chef's kiss:** the hybrid is significantly more accurate than the LLM alone on a sealed set neither component has seen.

One hybrid, one preregistered comparison: no multiple-testing correction, and a one-line headline.

## 2. The components (fixed before this experiment's sealed set is touched)

- **A\*** = experiment 2's final Loop A instructions: the best LLM harness.
- **J\*** = the best Jev harness: whichever of experiment 2's B final, experiment 3's B-prime final and experiment 3's B-plus final has the highest accuracy on **experiment 3's fresh sealed set**. **Resolved 2026-09-27: B-plus final** (69.8%, vs B 69.0% and B-prime 67.9%). That set is this experiment's *selection* set; this experiment gets its own new sealed set (section 4), so choosing J\* there is not peeking.
- **Style baseline** (experiment 2's six features), as a reference line.

No component is re-learned here. This experiment tests *combination*, not learning.

## 3. The hybrid: stacked vote

A small logistic regression decides each pair from both components' outputs:

- **Features:** A\*'s pick (+1 for X, −1 for Y), J\*'s signed per-question differences (direction × (P_X(yes) − P_Y(yes)), times J\*'s weights if it is B-plus), and J\*'s total score.
- **Model:** no intercept (X/Y order is arbitrary); L2 regularization strength chosen by 5-fold cross-validation.
- **Fitted on:** practice ∪ gate (500 + 1,500 = 2,000 pairs, the same files as experiments 2 and 3; pairs Gemini refused are left out of the fit). The final weights are reported, so the write-up can say how much the hybrid trusts the LLM vs each Jev question.
- **Content blocks:** when Gemini refuses a pair, A\*'s pick is unknown; the hybrid then uses J\*'s pick alone (the LLM-only system still uses its coin flip). This is a genuine advantage of combining them and is reported as its own line: accuracy on blocked pairs.

**Why this hybrid:** it is the one most likely to beat the LLM, because it uses both signals on every pair and learns how much to trust each. Its cost is Jev + LLM on every pair, so it can only win on accuracy, not cost.

## 4. Data

- Practice and gate: the same files as experiments 2 and 3 (fitting only).
- **New sealed set ("sealed-4"): 1,000 pairs** (Alexander, 2026-09-26: future experiments use 1,000 pairs per set) from the same prompt-hash buckets, excluding every pair used in experiment 2's and experiment 3's sealed sets (≈10,800 remain). Winner shown first in exactly 50%.
- A\*, J\*, the hybrid and the baseline are all scored once on sealed-4, on the same pairs.

## 5. Preregistered analysis

**Primary:** hybrid vs A\* on sealed-4, two-sided McNemar (exact when discordant pairs are few), α = 0.05.

**Apply the first row that matches:**

| Result | Verdict |
|---|---|
| Hybrid significantly more accurate than A\* | **Hybrid beats the LLM** (chef's kiss). Also report it vs J\* |
| Hybrid significantly less accurate than A\* | **Combination hurts.** Report the stack's weights and why |
| 95% interval of (hybrid − A\*) within ±3 points | **No meaningful gain:** the LLM already carries the signal Jev adds |
| Anything else | **Inconclusive** (a gain may exist but is too small for 1,000 pairs) |

**Also reported:** hybrid vs J\* (McNemar); the stack's weights; accuracy on blocked pairs; each system vs the style baseline; cost per 1,000 decisions for every system; the memorization flag (A\* or the hybrid above 70%).

**Exploratory add-on (not part of the verdict): the cascade.** From the *same* logged decisions (no extra calls, no extra look at sealed-4), compute what happens if J\* decides every pair where its score margin is large and A\* only the rest: the accuracy-vs-LLM-share curve, and the point that sends at most 50% of pairs to the LLM (threshold chosen on gate). This answers "can Jev take the easy half, at half the LLM cost?" and is labelled exploratory in the write-up.

## 6. Cost and time (estimate)

| Item | Pairs | Estimate |
|---|---|---|
| A\* on sealed-4 | 1,000 | ≈ $1.60 |
| J\* on sealed-4 | 1,000 | ≈ $0.10 |
| A\* on practice and gate (stacker features) | 2,000 | ≈ $0 (cached from experiment 2) |
| J\* on practice and gate | 2,000 | ≈ $0 (cached from experiments 2/3) |
| Stacked vote and cascade | computed from the above | $0 |
| **Total** | | **≈ $2–3**, cap $10 |

Time: about 20–30 minutes with BYOK.

## 7. Honest limits

- **Memorization carries over.** If A\* partly recalls Arena, the hybrid inherits the edge. Say so in the headline.
- **Power.** At 1,000 pairs a real gain of about 3–4 points is needed to show up clearly; a smaller gain reads as inconclusive.
- **Fitting data reuse.** Practice and gate were used in experiments 2 and 3; sealed-4 is the only clean test.
- **One task.** A hybrid win on Arena is still one task (the story-arc caveat from the MVP brief).
- **Not cheaper.** The stacked vote needs both calls on every pair; the cost story lives in the exploratory cascade.

## 8. Before running

1. OpenRouter BYOK with the Google AI Studio key is **enabled** (2026-09-26). Checked: served provider still "Google AI Studio"; reported cost still equals tokens × reference price. Keep OpenRouter's shared-capacity fallback on.
2. Experiment 3's sealed verdict must exist (it selects J\*).
3. Commit this design, the analysis code and its tests before any paid call, as in experiments 2 and 3.

## 9. Build (≈ 2–3 hours)

1. `prep_arena4.py`: sealed-4 draw with overlap checks.
2. `hybrid.py`: feature builder, stacker fit (cross-validated), prediction with the blocked-pair fallback; cascade curve (exploratory).
3. `verdict_hybrid.py`: rows above; tests for every row.
4. `sealed_hybrid.py`: guarded, single run on sealed-4; writes `results/arena4/sealed_complete.json`; live telemetry as before.
5. Fake-client dry run end to end, then cost estimate vs cap.

## 10. Out of scope

Other hybrids (Jev-informed LLM, a learned router); re-learning either component inside the hybrid; multi-turn Arena; a second task (the natural next step if the hybrid wins).
