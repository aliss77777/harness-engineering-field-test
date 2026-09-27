# Experiments 1–5 compared

**Written:** 2026-09-27 · Each experiment's own report is the source of truth; this page lines them up. All accuracies are on sealed sets that no loop, editor or baseline saw during learning, evaluated once.

## One-line answers

| # | Question | Preregistered answer |
|---|---|---|
| 1 | Upworthy headlines: does a Jev rubric loop learn better or cheaper than an LLM loop? | **Hypothesis weakened.** Neither loop learned (no edit passed the gate); the LLM was more accurate. |
| 2 | Arena responses, with a rebuilt harness: same question | **Only the Jev loop learned.** Jev: 66.7% → 70.1% (p 0.00002). LLM: 72.9% → 73.3% (p 0.50). LLM still more accurate; Jev ≈23× cheaper. |
| 3 | Arena: does a decision trace help the Jev loop? Do fitted weights? | **Trace: no detectable difference. Weights: help** (+1.9 over the trace arm, p 0.011); the weighted loop learned (p 0.002). |
| 5 | Arena: can Jev decide the confident cases and the LLM the rest, at the LLM's quality for half the cost? | **Same quality, half the cost.** Router 76.2% vs LLM 76.3% (interval −1.8 to +1.6) at 43% of the cost; Jev decided 62% of pairs. |
| 4 | Arena: does a fitted vote of the best LLM and best Jev harness beat the LLM alone? | **No meaningful gain** (75.6% vs 75.7%, interval −0.9 to +0.7). Exploratory cascade: Jev decides half the pairs → 75.2% at about half the cost. |

## The numbers side by side

| | Exp 1 (Upworthy) | Exp 2 (Arena) | Exp 3 (Arena, fresh sealed set) |
|---|---|---|---|
| Sealed pairs | 500 | 1,500 | 1,500 |
| **LLM loop** (Gemini 3.8 Flash) v0 → final | 73.8% → 73.8% | 72.9% → 73.3% | 73.6% → 75.3% (exp 2's versions) |
| **Jev loop** v0 → final | 61.2% → 61.2% | 66.7% → **70.1%** | B 66.5% → 69.0% · B-prime → 67.9% · **B-plus 67.5% → 69.8%** |
| Code baseline | 58.0% | 61.8% | 60.3% |
| Edits kept (LLM / Jev) | 0 / 0 of 4+4 bundles | 1 / 1 of 12 + 12 | — / 2 (B-prime) and 1 (B-plus) of ~31 each |
| Cost per 1,000 decisions (LLM / Jev) | $0.71 / $0.038 | $1.53 / $0.066 | $1.56 / $0.063–0.065 |
| Jev cost as share of LLM | 5.3% (≈19×) | 4.4% (≈23×) | ≈4% (≈24–25×) |
| Memorization flag (LLM v0 > 70%) | On | On | On |
| Paid spend | $1.92 | $37.09 | $9.10 |

## What changed between experiments, and what it did

| Change | Introduced | Effect |
|---|---|---|
| Single-edit gating (each edit tested alone; best passing one kept) | Exp 2 | Exp 1's bundles: 0 of 8 kept. Exp 2: both loops kept a round-1 edit; all three of the LLM's round-1 edits passed on their own. |
| Rejected edits shown to the editor; near-copies refused | Exp 2 | Exp 1's editors resubmitted near-identical edits for 4 rounds; in exp 2 they moved on (still converging on themes). |
| Fresh seeded mistake sample each round | Exp 2 | Removes "same 20 mistakes → same diagnosis". |
| Structured edits applied by code | Exp 2 | "One change" is true by construction; every change is auditable. |
| Bigger gate (1,500) and sealed (1,500) sets | Exp 2 | Enough power to confirm 3–5 point edits; also caught a lucky gate pass (the LLM's edit: +1.8 on gate, +0.4 on sealed). |
| Decision trace for the Jev editor | Exp 3 | Changed *what* the editor tried (drops and rewordings instead of piling on questions) but did not improve the result on unseen data. |
| Cheap practice pre-screen (8 candidates per round) | Exp 3 | Stopped ~half of all candidates before the gate for ≈7¢ each. Search got cheaper, not smarter. |
| Fitted question weights (B-plus) | Exp 3 | The clearest gain in experiment 3: same questions, +1 point from weights alone, and a real learned edit on top. |

## Replication note: the LLM's learned edit

Experiment 2's LLM edit ("don't disqualify for minor truncation; users appreciate elaboration") did not pass the learning test on experiment 2's sealed set (+0.4 points, p 0.50) but did on experiment 3's fresh set (+1.7 points, p 0.009). Experiment 2's preregistered verdict stands as run. Read together, the edit probably has a small real effect (≈ +1 point) that one 1,500-pair set cannot reliably detect. The Jev loop's edit replicated on both sets (+3.4 and +2.5 points).

## What the three experiments support

1. **A rubric loop can learn its criteria from real outcomes, cheaply, with an honest gate.** Experiment 2's Jev loop learned a readable criterion (answer depth) that held on two independent unseen sets, at ≈ 1/23 of the LLM's decision cost.
2. **On accuracy, the LLM still wins**: by 3–7 points on Arena, 12.6 on Upworthy, with the caveat that its version 0 scored above the memorization threshold every time.
3. **The harness matters more than the learner.** Single-edit gating, memory of rejected edits and bigger held-out sets turned "nothing learned" (exp 1) into "learning" (exp 2) with the same models.
4. **For the Jev loop, weighting beat richer feedback.** Telling the editor *why* it erred (the trace) did not help; letting code weight the questions did.
5. **Both loops independently found the same lesson** on Arena: users reward thorough, elaborated answers. Only the rubric's version held up everywhere.

## Limits that apply to all three

One decision step, two datasets, one LLM (Gemini 3.8 Flash) as decider and editor; the LLM's version 0 exceeded the memorization threshold every time; Arena labels are single user votes; experiments 2 and 3 share practice and gate sets, and experiment 3 was designed after seeing experiment 2's gate (not sealed) results. The wording rules from the MVP brief apply: say "a yes/no rubric" rather than "Jev" until Loop C (the same rubric answered by an LLM) is run.

## Experiment 4: LLM + Jev together

On 1,000 fresh pairs, a fitted vote of the best LLM harness (75.7% alone) and the best Jev harness (71.8% alone) scored 75.6%: **no meaningful gain**. The two agreed on 79% of pairs; where they disagreed, the vote followed the LLM 92% of the time. The promising direction is routing instead of voting: in an exploratory cascade, Jev decided the 51% of pairs where it was most confident and the LLM the rest, for **75.2% at $0.80 per 1,000 decisions vs $1.51** — within half a point of the LLM at about half the cost. That was not preregistered, so it is a lead, not a result.

## Experiment 5: routing, preregistered

The cascade idea from experiment 4, preregistered with the threshold frozen on gate (40% of pairs to the LLM) and tested on a fifth, fresh sealed set: **router 76.2% vs LLM 76.3%** (95% interval of the difference −1.8 to +1.6 points), at **$0.63 vs $1.48 per 1,000 decisions** (43%) and about a third less latency. The reason is clean: on the 62% of pairs where the rubric was confident, it was as accurate as the LLM (81.6% vs 81.7% on the same pairs); the LLM only earned its cost on the close calls. This is the strongest result of the series and the one that fits how Jev is meant to be used: a cheap, readable decider for most decisions, the LLM for the hard ones.

## Next

- **Replicate the router on a second task** where the LLM cannot have memorized the answers; that is the step that turns experiment 5 into a general claim.
- **From supervised to RL-style learning (designed: `Task Brief 6_Bandit.md`):** Upworthy as a contextual bandit — the policy picks one of 3+ headlines and sees only that headline's click rate; same harness, with exploration and a gate that compares policies by their own picks.
- **Rerun experiment 1 (Upworthy) with the experiment 2 harness**, to separate "better harness" from "easier task".
- **Loop C** (rubric answered by an LLM) to earn the word "Jev" in the headline.
- A second task where the LLM cannot have memorized the answers.
