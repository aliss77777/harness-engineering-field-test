# Task #5 brief: route between Jev and the LLM (cascade)

**Written:** 2026-09-27 · **Owner:** Alexander · **Status:** design only, not scheduled · **Builds on:** experiment 4 (stacked vote: no meaningful gain; exploratory cascade: ≈ same accuracy at about half the cost). Harness, logging, spend cap, content-block rule and telemetry unchanged. · **Repo:** new config/task pair (`config_arena5.yaml`, `task_arena5.yaml`).

## 1. Why this experiment

Experiment 4 showed that *voting* the two systems together adds nothing: where they disagree, the LLM is usually right. But its exploratory cascade suggested *routing* works: let Jev decide the pairs it is confident about and send only the rest to the LLM. On sealed-4 that kept 75.2% accuracy (LLM alone 75.7%) at $0.80 instead of $1.51 per 1,000 decisions. That result was not preregistered, and the same data suggested the best LLM share. This experiment tests it properly.

> **Chef's kiss:** the router is within ±3 points of the LLM alone **and** costs at most half as much per decision — on a sealed set nobody has seen.

This is the enterprise pattern: a cheap, readable decider handles the easy majority; the expensive model handles the hard cases.

## 2. Components (fixed, not re-learned)

- **LLM (A\*):** experiment 2's final Loop A (`A-r1-c2`).
- **Jev (J\*):** experiment 3's B-plus final (`Bw-r4-c1`, six questions with fitted weights).
- **Confidence signal:** J\*'s absolute score margin, |Σ weighted signed per-question differences|. Large margin = the two responses differ clearly on the rubric.

## 3. The router (one, preregistered)

1. Jev scores every pair.
2. If the margin is **at least τ**, Jev's pick is final.
3. Otherwise the pair goes to the LLM, whose pick is final. If Gemini refuses a routed pair, Jev's pick is used.

**Choosing τ (preregistered rule):** τ is set on the **gate set** so that **40% of gate pairs go to the LLM** (the 40th percentile of J\*'s gate margins). It is a fixed budget, not tuned for accuracy on any set, to limit overfitting. The 40% figure comes from experiment 4's exploratory curve on sealed-4 (30–40% looked best). Sealed-4 is not reused here, so choosing the figure from it is disclosed, not peeking.

## 4. Data

- Gate (for τ only): experiment 2's gate set (1,500 pairs; Jev decisions replay from cache).
- **Sealed-5:** **1,000 fresh pairs** from the same prompt-hash buckets, excluding all 4,000 pairs of the sealed sets of experiments 2, 3 and 4 (≈ 9,800 remain). No pair or prompt overlap with practice, gate or any earlier sealed set; winner shown first in exactly 50%; text read as text.
- **Power:** the router differs from the LLM only on Jev-decided pairs where the two disagree (≈ 8–10% of pairs, from experiment 4). At 1,000 pairs the 95% interval of the difference is about ±2 points, tight enough to test the ±3 margin.

## 5. What is scored

On sealed-5, once each: **LLM alone** on every pair (needed for the paired test); **Jev alone** on every pair; the **router**, built from those decisions with τ frozen from gate; the style baseline.

**Cost accounting:** the router's cost = Jev on every pair + the LLM's cost on routed pairs only (per-pair share of each batch, as before). A deployment would batch only routed pairs; the difference is small and noted.

## 6. Preregistered analysis

Primary comparison: router vs LLM alone on sealed-5 (paired). Two-sided McNemar, α = 0.05; 95% interval of (router − LLM).

**Apply the first row that matches:**

| Result | Verdict |
|---|---|
| Router significantly more accurate than the LLM | **Router beats the LLM** (and is cheaper) |
| Interval of (router − LLM) within ±3 points **and** router cost ≤ ½ of the LLM's | **Same quality, half the cost** (chef's kiss) |
| Router significantly less accurate **and** interval's lower end below −3 points | **Routing costs real accuracy** |
| Interval within ±3 but cost > ½ | **Same quality, not cheap enough** (report the share actually routed) |
| Anything else | **Inconclusive** |

**Also reported:**
- The actual LLM share on sealed-5, and the full accuracy-vs-LLM-share curve.
- Accuracy on the Jev-decided vs LLM-decided pairs.
- Router vs Jev alone.
- Each system vs the style baseline.
- Cost per 1,000 decisions for all systems, and an average-latency estimate from the logs.
- Blocked pairs, and the memorization flag (LLM above 70%).

## 7. Cost and time

| Item | Estimate |
|---|---:|
| LLM on sealed-5 (1,000 pairs) | ≈ $1.55 |
| Jev on sealed-5 | ≈ $0.07 |
| Gate (τ) | $0 (cache) |
| **Total** | **≈ $1.6–2**, cap $5 |

About 15 minutes with BYOK.

## 8. Honest limits

- **Memorization:** the LLM's accuracy may be inflated; the router inherits it on routed pairs.
- **Tuning reuse:** τ is set on a gate set used in experiments 2–4; the LLM share (40%) was informed by sealed-4.
- **One task.** A win here is a strong pattern on Arena only.
- **The equivalence margin (±3 points) is a stated choice**, as in the MVP brief. A buyer may care about 1 point.

## 9. Build (≈ 1–2 hours; mostly reuses experiment 4)

1. `prep_arena5.py`: sealed-5 draw with overlap checks (generalize `prep_arena4.py`'s exclusion list).
2. `router.py`: τ from gate at the preregistered share; routing, blocked fallback, cost split, curve.
3. `verdict_router.py`: rows above; tests for every row.
4. `sealed_router.py`: guarded single run on sealed-5; `results/arena5/sealed_complete.json`; live telemetry.
5. Fake-client dry run, then commit before any paid call.

## 10. Out of scope

A learned router, since one fitted router input (J\*'s margin) is enough to test the idea. Also out: routing on the LLM's confidence, re-learning either component, and other tasks. The natural next step after a win is the same router on a second task.
