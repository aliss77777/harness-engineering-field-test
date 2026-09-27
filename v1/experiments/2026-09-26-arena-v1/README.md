# Experiment 2: Chatbot Arena, long responses — Results

**Completed:** 2026-09-26 23:22 MDT · **Brief:** [`config/Task Brief 2_Arena.md`](config/Task%20Brief%202_Arena.md) · **Preregistered verdict:** **Only the Jev loop learned**

## Headline

> On real Chatbot Arena votes, a Jev rubric that learned its criteria from outcomes improved significantly on 1,500 unseen battles (66.7% → 70.1%, p = 0.00002), while an LLM that learned from its own reasoning did not (72.9% → 73.3%, p = 0.50). The LLM stayed more accurate (73.3% vs 70.1%), but the Jev loop decided at 4.4% of the cost (≈23× cheaper), and it clearly beat a style-only baseline (61.8%).

Wording rules from the MVP brief: "learned" applies to the Jev loop only; "Jev" (rather than "a yes/no rubric") needs Loop C, which was not run. Scope: one decision task, 2023–2024 Arena single-turn battles.

## Task and data

Given a real user request and two model responses, predict which one the user voted for. `lmarena-ai/arena-human-preference-55k` (Apache 2.0), single-turn, no ties, both responses ≤ 1,500 words, model names hidden. 57,477 rows → 34,267 usable battles. Split by **prompt hash** so no prompt appears in two sets: practice 500, gate 1,500, sealed 1,500. Winner shown first in exactly 50% of each set (balanced seeded order). Full counts: [`artifacts/prep_report.json`](artifacts/prep_report.json).

## Sealed results (1,500 unseen pairs, evaluated once)

| System | Version 0 | Final | 95% interval (final) | Learned? | Cost / 1,000 decisions |
|---|---:|---:|---:|---|---:|
| Loop A — Gemini 3.8 Flash, prose instructions | 72.9% | 73.3% | 71.0–75.5% | No (b 43 / c 36, p 0.50) | $1.526 |
| Loop B — Jev 1.13, yes/no rubric | 66.7% | **70.1%** | 67.7–72.3% | **Yes** (b 95 / c 44, p 0.00002) | **$0.066** |
| Style code baseline (6 features) | — | 61.8% | — | — | $0 |

- **A vs B:** A higher by 3.2 points (paired 95% interval for B − A: −5.6 to −0.9; McNemar p = 0.008). Not within the ±3-point "same quality" margin.
- **B vs style baseline:** B better (b 341 / c 217, p < 0.0001). The rubric learned more than length and formatting.
- **Cost ratio:** B / A = 0.044 (**≈23× cheaper per decision**).
- **Memorization flag: on.** Loop A's version 0 scored 72.9% (> 70%). Arena data (2023–24) may be in Gemini's training data; Loop A's lead may partly reflect that.
- **Sensitivity (not the verdict):** excluding the 3 pairs Gemini refused to read, the verdict is unchanged.

Verdict rows (`arena_v2`, applied in order): no signal → neither learned → B learned and better → B learned, same quality and ≤ ⅕ cost → **B learned, A didn't** ← matched here → A better → inconclusive.

## What each loop learned

Both loops learned the same lesson in round 1, then nothing else passed the gate.

| | Kept edit (round 1) | Gate | Sealed |
|---|---|---|---|
| **Loop A** | Appended: *"Do not automatically disqualify a response due to minor truncation … users often appreciate helpful elaboration, context, and examples even when brief answers were requested."* | 75.3% → 77.1% (p 0.003) | 72.9% → 73.3% — **did not hold** |
| **Loop B** | Added question `provides_helpful_explanation_and_depth` (helps): *"Does the response provide thorough explanation, relevant background context, or educational breakdown beyond a bare-minimum answer?"* | 67.6% → 72.0% (p < 0.0001) | 66.7% → 70.1% — **held** |

Edit statistics (single-edit gate, one-sided sign test p < 0.05, at most one kept per round, 4 rounds):

| | Proposed | Kept | Passed but not best | Rejected | Failed question check |
|---|---:|---:|---:|---:|---:|
| Loop A | 12 | 1 | 2 | 9 | — |
| Loop B | 12 | 1 | 0 | 10 | 1 |

All three of Loop A's round-1 candidates passed the gate; the gate kept the one with the largest net gain. Loop A's closest later miss was round 4 (77.8% vs 77.1%, p 0.10).

## Harness changes vs experiment 1 (all adopted before the run)

Single-edit gating; structured edits applied by code; rejected edits shown to the editor, near-copies refused; a fresh seeded sample of mistakes each round; spend cap in code; concurrent calls with order-independent results; Loop A batch 5 (was 20); code-baseline per-pair predictions for a paired test; Jev tested on the longest responses first.

## Run integrity

- Verdict rules (`arena_v2`) committed before any paid Arena call (`b18f99b`). Sealed set evaluated once, after final versions were frozen.
- **Seven learning launches**, all resuming from cache (same prompts → same answers), so later launches reproduce earlier work exactly. Reasons: Gemini 429 rate limits at 8 workers (→ 3); a provider error body mistaken for a model change (→ retried); Gemini content-policy blocks (→ rule below); OpenRouter credit ran out (→ 402 made fatal, editor failures stop the run instead of skipping a round); a rate-limited batch exhausting retries at 5 workers (→ back to 3, capped backoff, fail-fast pool). Every change was operational; none depended on a result. Details and times: `MVP Project Plan.md`.
- **Gemini refusals:** 3 of 1,500 sealed pairs (and a handful in learning) were refused by Gemini's content policy. Rule (set 2026-09-26 18:40, before any sealed call): a refused pair gets a seeded coin flip in Loop A and is flagged `blocked`; Jev read every pair. Refused pairs were excluded from the editor's mistake samples.
- Position balance: winner first in exactly 50% of every set; Loop A picked the first response 53–55% of the time on practice and sealed.
- Fake decider through the real pipeline: 48.6–51.2% on every set.
- Models: `google/gemini-3.8-flash` via OpenRouter (provider Google AI Studio; BYOK enabled from 21:25 — same provider and pricing); `typesafe/jev-1.13-20260917`. Served model/provider checked on every call.

## Cost

| Stage | Paid spend |
|---|---:|
| Version 0, smoke test, checks | ≈ $0.2 |
| Learning (both loops, 4 rounds) | $32.41 |
| Sealed evaluation | ≈ $4.5 |
| **Total** | **$37.09** |

Almost all of it is Loop A: the Jev loop's entire learning run cost well under $1.

## Honest limits

- **Memorization:** see above; Loop A's accuracy may be inflated.
- **Noisy labels:** one user vote per battle; accuracy in the 70s may be near the ceiling.
- **Gate optimism:** Loop A's kept edit looked +1.8 on gate and was +0.4 on sealed — the gate (1,500 pairs, three candidates per round) selects some lucky edits. The sealed set caught it; that is its job.
- **One task, one dataset.**

## Files

- [`artifacts/sealed_complete.json`](artifacts/sealed_complete.json) — verdict, all tests, intervals, costs, sensitivity check.
- [`artifacts/final_versions.json`](artifacts/final_versions.json) — version 0, final versions, full candidate and gate history.
- [`artifacts/wip_summary.json`](artifacts/wip_summary.json) — every evaluation, candidate and gate decision of the final launch.
- `config/` — exact config, task file and brief. `config_arena.yaml` shows the final operational settings (3 Gemini workers, 12 retries).
- `splits/` — registered practice, gate and sealed pair IDs.
- `telemetry/` — compressed JSONL of every launch, smoke test and the sealed stage; `supervisor.log`.
