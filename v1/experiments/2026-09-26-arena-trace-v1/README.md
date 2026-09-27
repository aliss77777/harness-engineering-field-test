# Experiment 3: Arena, decision-trace learning for the Jev loop — Results

**Completed:** 2026-09-27 00:17 MDT · **Design:** "Experiment 3" section of `MVP Project Plan.md` (committed before any paid call, `cd8f701`) · **Preregistered answers:** decision trace → **no detectable difference**; fitted weights → **help**

## Headline

> Giving the Jev loop's editor a per-question decision trace did not make it learn better than plain feedback (67.9% vs 69.0% on 1,500 fresh unseen battles, p = 0.16). Letting code fit a weight for each rubric question did help (69.8% vs 67.9%, p = 0.011), and that weighted loop learned significantly (67.5% → 69.8%, p = 0.002) — at about 4% of the LLM's cost per decision. The LLM loop (experiment 2's Loop A) was still more accurate on this set (75.3%).

## Question and arms

Experiment 2's Loop B learned one edit and then stalled. Its editor never saw *why* a pair was missed. Two new arms, both starting from experiment 2's version 0 rubric, same practice/gate sets, gate rule and limits:

- **B-prime (decision trace):** the editor sees, for each sampled mistake, which questions pushed the pick toward the loser and by how much; plus per-question error totals, win rate by probability gap, and question overlap. The editor proposes up to 8 edits; each is scored on practice with Jev (≈7¢) and the best 3 with a net practice gain go to the gate. Unweighted sum, as in B.
- **B-plus (trace + weights):** the same, but each version's per-question weights are fitted on practice (logistic regression, no intercept).

Loop A was not rerun; experiment 2's Loop A (version 0 and final) is the comparison.

## Fresh sealed set

1,500 pairs drawn from the same prompt-hash buckets as experiment 2's sealed set, excluding all of experiment 2's sealed pairs: no shared pair with experiment 2's sealed set, no prompt shared with practice or gate, winner first in exactly 50%. Evaluated once.

## Results (fresh sealed set, 1,500 pairs)

| System | Accuracy | Cost / 1,000 decisions |
|---|---:|---:|
| Loop A version 0 (experiment 2) | 73.6% | — |
| **Loop A final (experiment 2)** | **75.3%** | $1.563 |
| Loop B version 0 (= B-prime v0) | 66.5% | — |
| Loop B final (experiment 2) | 69.0% | — |
| **B-prime final** (trace) | 67.9% | $0.063 |
| B-plus version 0 (v0 rubric + fitted weights) | 67.5% | — |
| **B-plus final** (trace + weights) | **69.8%** | $0.065 |
| Style code baseline | 60.3% | $0 |

**Primary tests** (two-sided McNemar, Holm-corrected across the two):

| Question | Comparison | b / c | p | Answer |
|---|---|---|---:|---|
| P1: does the trace help? | B-prime final vs B final | 57 / 74 | 0.16 | **No detectable difference** (B-prime numerically lower) |
| P2: do weights help? | B-plus final vs B-prime final | 75 / 46 | 0.011 | **Helps** (significant after Holm) |

**Learning checks:** B-prime final vs version 0: 82 / 62, p 0.11 → did not learn. B-plus final vs its version 0: 78 / 43, **p 0.002 → learned** (+2.3 points).

**Headline verdict vs Loop A** (`arena_v2` rows, reported, not primary): with B-prime as "B" → *hypothesis weakened* (A higher by 7.5 points, p < 0.0001); with B-plus → *hypothesis weakened* (A higher by 5.5 points, p < 0.0001). Both Jev arms clearly beat the style baseline (p < 0.0001). Cost ratio ≈ 0.04 (≈ 24–25× cheaper). Memorization flag: on (Loop A version 0 at 73.6%).

## What each arm learned

| Arm | Proposed | Pre-screened out | Failed question check | Gated and rejected | Kept |
|---|---:|---:|---:|---:|---:|
| B-prime | 31 | 15 | 7 | 7 | **2**: r1 drop `directly_answers_without_filler` (gate p 0.040); r3 reword `contains_factual_or_logical_errors` to severe errors only (p 0.028) |
| B-plus | 32 | 15 | 5 | 11 | **1**: r4 reword `satisfies_explicit_instructions` to "effectively fulfil the user's primary request and intended goal" (p 0.028) |

B-plus's final fitted weights: instruction-following 2.27 · formatting 1.18 · task left incomplete 0.66 · filler 0.28 · unnecessary refusal 0.22 · factual errors 0.14. The data says users reward following the request and clean formatting far more than the absence of factual errors.

**Reading:** with traces, the editor made surgical edits (drops and rewordings) instead of adding questions, but it never found experiment 2's single big win (adding a "depth/explanation" question), and its two gate-passing edits did not add up on unseen data. The weights did the heavy lifting: the same six questions, weighted by practice data, were worth +1 point before any edit and supported a real learned edit.

## Run integrity

- Learning ran in parallel with experiment 2 (Alexander's decision, 19:20); the sealed stage was guarded to run only after experiment 2's verdict (it did, 23:22 → 00:17).
- Learning launch 1 stopped on OpenRouter 402 (out of credit) before any candidate was gated; launch 2 completed. Sealed attempts 1–2 failed on a Gemini response block (fixed: treated like a request block after three identical refusals); attempt 3 crashed at the last step because one response is the literal text "N/A", which the CSV reader turned into a missing value (fixed: pair files read as text; the deciders had been shown "nan" for that pair). Attempt 4 completed; all earlier work replayed from cache. No attempt wrote a verdict before the final one.
- 4 fresh-sealed pairs refused by Gemini (Loop A coin flip, flagged). No sensitivity rerun was preregistered for experiment 3.
- Paid spend: learning $4.09; total experiment 3 **$9.10** (most of it Loop A scoring the fresh sealed set).

## Caveats

- **Experiment 3 was designed after seeing experiment 2's gate results** (not its sealed results). The fresh sealed set protects the verdict; the design choice is disclosed.
- **Loop A on the fresh set:** its final beat version 0 here (73.6% → 75.3%, p 0.009), unlike on experiment 2's sealed set (p 0.50). Experiment 2's preregistered verdict stands as run; the two sets together suggest Loop A's edit had a small real effect (+0.4 and +1.7 points). See `experiments/COMPARISON.md`.
- **Pre-screen asymmetry:** only the Jev arms could afford to pre-screen 8 candidates per round; that is part of the claim, not a flaw, but it means B-prime/B-plus searched harder than Loop A.
- **One task, one dataset; memorization flag on for the LLM.**

## Files

- [`artifacts/sealed_complete.json`](artifacts/sealed_complete.json) — primary tests, learning checks, headline verdicts, costs.
- [`artifacts/final_versions.json`](artifacts/final_versions.json) — both arms' final rubrics, B-plus weights, full candidate/pre-screen/gate history.
- `config/`, `splits/` (fresh sealed IDs; practice/gate are experiment 2's), `telemetry/` (compressed JSONL of every launch and sealed attempt; `supervisor.log`).
