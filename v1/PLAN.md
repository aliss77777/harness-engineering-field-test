# MVP Project Plan (v1 — formerly `MVP Project Plan.md`)

Updated as work progresses. The experiment rules in [`briefs/MVP-BRIEF-jev-learning-loop-v2_5.md`](briefs/MVP-BRIEF-jev-learning-loop-v2_5.md) stay fixed.

## Two-hour target

- [x] Create a reproducible local project and private Git history.
- [x] Prepare fixed Upworthy practice, gate, and sealed pairs.
- [x] Run the code-feature baseline and fake-decider sanity check.
- [x] Complete one end-to-end learning round for Loops A and B.
- [x] Save results, costs, logs, and a clear next-run command.

## 1. Preflight

- [x] Initialize Git; ignore `.env`, raw data, caches, and logs.
- [x] Add pinned Python dependencies and example environment variables.
- [x] Confirm Gemini access.
- [x] Confirm Jev/OpenRouter access when its key is available.
- [x] Add `config.yaml` and `task.yaml`; keep experiment constants out of code.

## 2. Data and controls

- [x] Load CSVs safely with pandas and strip HTML from text.
- [x] Apply date, same-image/excerpt, impressions, and z-score filters in order.
- [x] Print counts after every filter.
- [x] Save deterministic pair IDs; never resample them.
- [x] Create practice (300), gate (300), and sealed (up to 500) sets.
- [x] Run six-feature logistic-regression baseline.
- [x] Run seeded fake decider; verify accuracy is near 50%.

## 3. Experiment harness

- [x] Add decider, editor, gate, evidence, cache, logger, and runner interfaces.
- [x] Add append-only JSONL logging and token/cost accounting.
- [x] Add retries and full-input disk caching for API calls.
- [x] Test pairing, scoring, ties, evidence, gate, and cost calculations. (26 tests pass.)

## 4. Learning loops

- [x] Generate fair version-0 instructions and rubric from the same Gemini prompt.
- [x] Loop A: predict X/Y and record one-line reasons.
- [x] Loop B: sum Jev yes-probabilities using question direction.
- [x] Build Loop B evidence table.
- [x] Edit each loop within the stated change limits.
- [x] Gate proposed edits with the one-sided sign test.
- [x] Complete four rounds for both loops.

## 5. Evaluation and handoff

- [x] Evaluate version 0 and final versions once on the sealed set.
- [x] Apply the pre-registered verdict rules without modification.
- [x] Write final versions, history, costs, machine-readable results, and concise verdict.
- [x] Document setup and one-command rerun in `README.md`.
- [x] Commit clean checkpoints and push to private `aliss77777/jev-test-poc`.

## Progress log

- 2026-09-26: Verdict rules locked before gate/sealed loop runs: Wilson accuracy intervals, paired B−A interval, exact/corrected McNemar selection, ordered verdict rows, cost ratio, and memorization flag. Eight verdict tests pass; thresholds are in `config.yaml`.
- 2026-09-26: Added strict served-model/provider checks for Gemini and Jev, disabled LLM provider fallback, made `reasoning_effort: medium` explicit, and added a Jev cache bypass for the consistency check. The paid consistency check itself has not run yet.
- 2026-09-26: Brief reviewed; dataset downloaded; CSV schema confirmed; `GEMINI_API_KEY` detected without exposing its value.
- 2026-09-26: Repo and environment created; six tests pass; fixed 300/300/500 splits saved.
- 2026-09-26: Fake control scored 50.7%/52.0%/51.2%. Code baseline scored 64.7% practice, 55.7% gate, and 58.0% sealed.
- 2026-09-26: Gemini access confirmed. Google retired `gemini-2.5-flash`. Sustained 3.8 calls and a scoped 3.7 fallback both failed under repeated provider 503 saturation; retain the 3.8 tracer-bullet version for now and resume the formal LLM run when capacity returns.
- 2026-09-26: Cache, append-only logger, cost math, rubric scorer/tie rule, evidence table, and sign-test gate implemented; 16 tests pass.
- 2026-09-26: Fair version 0 generated: prose instructions plus six yes/no rubric questions.
- 2026-09-26: OpenRouter Jev 1.13 access confirmed; pinned served snapshot is `typesafe/jev-1.13-20260917`.
- 2026-09-26: Ten-pair smoke tests passed end to end: Loop A 70%; Loop B 90% with 0% ties. These tiny samples are plumbing checks, not findings. Jev cost $0.000374 total ($0.0374 per 1,000 decisions at this sample size).
- 2026-09-26: Full Loop B version-0 practice pass complete: 63.0% on 300 pairs, 0% ties, 600 Jev calls, no failures, $0.01134 total ($0.0378 per 1,000 decisions). Practice data only—not a verdict.
- 2026-09-26: Evidence table written. Strongest split signals: `withholds_key_payoff` 82.4% yes-win rate across 68 splits; `features_list_number` 69.0% across 29; `promises_extreme_emotion` 61.7% across 47.
- 2026-09-26: Formal Loop A practice pass is waiting on Gemini provider capacity after bounded 3.8 and 3.7 retries. Failures are logged; cached work is preserved.
- 2026-09-26: Private GitHub repo created at `aliss77777/jev-test-poc`; local checkpoints pushed to `main`.
- 2026-09-26: Switched the formal LLM route to paid OpenRouter `google/gemini-3.8-flash`, retaining strict structured output, caching, retries, token/cost logs, and automatic Google-provider failover.
- 2026-09-26: Paid OpenRouter readiness checks passed: structured-output access check plus a 10-pair Loop A batch at 70.0% accuracy. The batch cost $0.00816 ($0.816 per 1,000 decisions at this sample size). Full testing intentionally paused pending Alexander's go-ahead.

---

## Handoff report — 2026-09-26 16:18:58 MDT

Repository: `https://github.com/aliss77777/jev-test-poc`
Branch: `main`
Working tree at report time: clean
Tests at report time: **35 passed**

### Completed before the review

- Created standalone Python project and private GitHub repo.
- Added fixed configuration, caching, retries, JSONL logging, and cost tracking.
- Prepared Upworthy practice/gate/sealed sets: 300/300/500.
- Fake control scored approximately 50%.
- Registered code baseline sealed score: **58.0%**. Do not rerun it.
- Implemented Gemini Loop A and Jev Loop B adapters.
- Routed paid Gemini 3.8 Flash through OpenRouter.
- OpenRouter Loop A smoke test: 10 pairs, 70%, $0.00816.
- Jev practice pass: 300 pairs, 63%, zero ties, $0.01134. This was pre-fix practice evidence, not a formal result.
- Full testing remained paused.

### Review fixes completed

#### Verdict rules locked

Commit: `0d6b7f6`

Added `verdict.py` with:

- Chance/signal check.
- Learning comparisons.
- A-versus-B comparison.
- 95% accuracy and paired-difference intervals.
- Exact McNemar tests for few disagreements.
- Corrected approximate McNemar tests for larger samples.
- Cost ratio and 5×-cheaper rule.
- 70% memorization warning.
- Verdict rows applied in the brief's fixed order.

All thresholds are in `config.yaml`. Eight verdict tests cover every verdict row. This was committed before any gate or formal sealed loop execution.

#### Jev cache bypass and model protection

Commit: `fae0cd5`

- Added `use_cache=False` support for the Jev consistency check.
- Added tests proving repeated uncached requests really make separate calls.
- Pinned the expected Jev response to model `typesafe/jev-1.13-20260917`, provider `TypeSafe`.
- Pinned OpenRouter Gemini to model ID `google/gemini-3.8-flash`, provider `Google AI Studio`.
- Disabled LLM provider fallback.
- The run stops if the served model or provider changes.
- Made `reasoning_effort: medium` explicit in config.
- Added config placeholders for the consistency-check result and starting-rubric limits.

The Gemini ID is the exact ID OpenRouter returned; OpenRouter did not expose a dated Gemini snapshot.

### Paid-call status at handoff

Since receiving the review instructions, **no paid calls were made**. The explicitly approved Jev consistency test had not run yet.

### Remaining review fixes at handoff

1. Run the approved uncached Jev consistency test and select repeated or reworded question checking.
2. Add fake mode to `run.py` through the real logging/scoring/gate pipeline.
3. Freeze pair IDs and repair practice/gate headline overlaps without changing sealed.
4. Add the single guarded sealed-evaluation entry point.
5. Write one JSONL record per decision, including allocated batch tokens/cost, reasons, probabilities, correctness, and ties.
6. Log editor changes/reasons and gate `b`, `c`, and `p`.
7. Route Loop B through `RubricDecider` instead of duplicated scoring in `run.py`.
8. Enforce editor limits from config.
9. Finish data and evidence cleanup.
10. Run all tests and commit before requesting approval for full paid testing.

### Pre-run completion — 2026-09-26 16:42:19 MDT

- Repaired cross-set headline overlap: removed/refilled 13 practice pairs and 5 gate pairs using the fixed seed. The sealed IDs remained byte-for-byte unchanged.
- Split IDs now load and validate instead of being rewritten. Filter reporting separates impressions, z-score, and unparseable dates.
- Fake control passed through the real runner: 51.0% practice, 48.3% gate, 47.8% sealed.
- Jev consistency check passed with zero binary disagreements across 10 headlines and six questions. New/reworded questions will use the two-rewording check.
- Model/provider mismatches now stop immediately without retrying.
- Loop B now uses the tested `RubricDecider` scoring path. Evidence includes zero-split questions as “rarely applies.”
- Editor limits are enforced from config. Per-pair, editor, and gate events are written to JSONL.
- Added four-round learning runner, guarded one-time sealed runner, and live telemetry at `results/run_status.json`.
- Final free preflight: **39 tests passed**.

### Full experiment — 2026-09-26 17:37:09 MDT

- Completed four rounds for Loop A and four rounds for Loop B.
- All eight proposed versions failed the statistical gate; final versions therefore equal version 0.
- One-time sealed results: Loop A 73.8%, Loop B 61.2%, registered code baseline 58.0%.
- Loop B cost $0.0378 per 1,000 decisions versus Loop A's $0.7134 (about 18.9× cheaper).
- Preregistered verdict: **hypothesis weakened**. Loop A was statistically better; neither loop learned.
- Loop A triggered the >70% memorization warning.
- Learning plus sealed paid cost: $1.9196. Three transient Jev errors retried successfully; no served-model/provider mismatch occurred.

### Archived results location — 2026-09-26

Experiment 1 is archived under `experiments/2026-09-26-upworthy-v1/`:

- `README.md` — full human-readable results and conclusions.
- `artifacts/sealed_complete.json` — final machine-readable sealed results and verdict.
- `artifacts/final_versions.json` — frozen versions and complete gate history.
- `config/` and `splits/` — exact reproducibility snapshot.
- `telemetry/` — compressed JSONL logs for every stage of the run.

### Git history at handoff

- `fae0cd5` — Pin served models and enable uncached Jev checks
- `0d6b7f6` — Lock preregistered verdict rules
- `d0b4300` — Route Gemini through paid OpenRouter
- `9ca0ba9` — Record GitHub project setup
- `b14d497` — Run full Jev practice baseline
- `4732fd3` — Add Gemini and Jev tracer bullets
- `4d6f8c9` — Add experiment harness foundations
- `a89095c` — Build data prep and control baseline

---

# Experiment 2: Chatbot Arena (long responses)

**Brief:** `Task Brief 2_Arena.md` (builds on `MVP-BRIEF-jev-learning-loop-v2_5.md`). **Started:** 2026-09-26 18:00 MDT (times below are MDT, from file and commit timestamps). **Config:** `config_arena.yaml` + `task_arena.yaml`. **Outputs:** `data/arena/`, `results/arena/`, `logs/arena/`; archived at the end under `experiments/`.

Experiment 1's exact code is preserved at git tag `exp1-upworthy-v1` (commit `c2170c5`); its archive in `experiments/2026-09-26-upworthy-v1/` is untouched.

## Decisions (Alexander, 2026-09-26)

- Dataset download approved: `lmarena-ai/arena-human-preference-55k` `train.csv` (Apache 2.0, 184 MB, SHA-256 `0692154a…5be2`), kept out of git.
- Spend cap: **$75**, enforced in code.
- Adopt all eight harness suggestions made after experiment 1:
  1. Editor sees its rejected edits and is told not to resubmit; near-copies (similarity ≥ 0.9) are refused without gating.
  2. Mistakes shown to the editor are a fresh seeded sample of 20 each round.
  3. Edits are structured single operations applied by code (A: replace/append text; B: drop/flip/reword/add one question), so "one change" is enforced, not self-reported.
  4. Spend cap enforced in code across all stages.
  5. Concurrent API calls (thread pools) with deterministic, order-independent results.
  6. Loop A batch size 5 (was 20), and the rate at which each decider picks the first response is logged.
  7. Code baseline per-pair predictions kept, for a paired B-vs-baseline McNemar.
  8. Jev tested on the longest responses in the smoke test before the full run.

## Checklist

- [x] Download dataset, record hash and licence.
- [x] `prep_arena.py`: filters in order with counts, prompt-hash split, saved IDs (load and never resample), winner position check.
- [x] Code baseline (six style features, practice-trained, no intercept) on gate.
- [x] Decider prompts parameterized from `task.yaml` (no task wording in code).
- [x] Single-edit gate (p < 0.05 per edit, keep the best passing edit, at most one per round).
- [x] "Neither loop learned" and "Only the Jev loop learned" verdict rows (`rules_version: arena_v2`), with tests.
- [x] Live telemetry: `results/arena/run_status.json` and `results/arena/wip_summary.json`.
- [x] Fake decider through the real pipeline on all sets.
- [x] Commit before any paid run (`b18f99b`).
- [x] Version 0 (same LLM, same prompt for both loops).
- [x] Paid smoke test (includes the longest responses) and cost estimate vs cap.
- [x] Four learning rounds for both loops.
- [x] One guarded sealed evaluation; verdict.
- [x] Archive, write up, and compare with experiment 1.

## Progress log

- 2026-09-26 18:05: Dataset downloaded (57,477 rows).
- 2026-09-26 18:08: Filters: 57,477 loaded → 39,716 after dropping ties → 34,297 single-turn → 34,269 after dropping empty/unparseable → 34,267 after the 1,500-word cap (removed 2) → 34,267 after hiding model names (removes columns, not rows).
- 2026-09-26 18:08: Prompt-hash split (20/40/40% of buckets) → pools of 6,933 / 13,545 / 13,789 pairs; sampled 500 / 1,500 / 1,500. Zero prompts shared between sets. Median response ≈ 155–170 words.
- 2026-09-26 18:08: **Deviation (position balance):** per-pair coin flips put the winner first in only 44.2% of practice pairs (p ≈ 0.01). Replaced with seeded balanced ordering: exactly 50.0% winner-first in every set. Done before any decider saw the pairs.
- 2026-09-26 18:08: Style code baseline (length, list items, headers, code block, refusal phrases, log length ratio; no intercept) trained on practice: **60.4% practice, 62.5% gate**. Longer responses, code blocks and non-refusals win. As the brief warned, style alone carries real signal, so Loop B must beat this baseline to claim more than style detection.
- 2026-09-26 18:13: Harness changes built (see Decisions). Verdict rules `arena_v2` added with tests; experiment 1 rules unchanged under `mvp_v1`. 56 tests pass.
- 2026-09-26 18:14: Fake decider through the real pipeline: Loop A 51.2 / 49.3 / 49.7% and Loop B 48.6 / 50.7 / 49.7% (practice / gate / sealed), tie rate ≤ 0.4%. Fake gate check correctly rejected (b 365, c 367, p 0.54).
- 2026-09-26 18:14: Committed `b18f99b` (harness + locked `arena_v2` verdict rules) before any paid Arena call. Experiment 1 code tagged `exp1-upworthy-v1`.
- 2026-09-26 18:14: Version 0 generated from the brief's prompt in one Gemini call ($0.007): 135-word instructions (instruction compliance, correctness, directness, readability, tone) and six rubric questions (`satisfies_explicit_instructions`+, `contains_factual_or_logical_errors`−, `directly_answers_without_filler`+, `uses_clean_scannable_formatting`+, `unnecessary_refusal_or_excessive_hedging`−, `leaves_task_incomplete`−). Saved to `results/arena/version0.json`.
- 2026-09-26 18:15: Paid smoke test, 20 practice pairs (incl. the 5 longest): no failures. Loop A $1.58 per 1,000 decisions (869 input + 248 output tokens per decision); Loop B $0.073 per 1,000 (1,750 Jev input tokens per decision). **B/A cost ratio 0.047 (~21× cheaper)**, similar to experiment 1's 18.9×. Jev accepted the longest gate response (1,313 words, 2,241 tokens).
- 2026-09-26 18:15: Worst-case estimate (every round proposes and gates 3 edits for both loops): **$42.15**, within the $75 cap (`results/arena/cost_estimate.json`). Proceeding under Alexander's approval.
- 2026-09-26 18:15: Learning launched: `learn.py --run-id arena-learn-20260926`. Loops A and B run in parallel threads. Live status: `results/arena/run_status.json`; finished results so far: `results/arena/wip_summary.json`; health check: `python monitor.py --run-id arena-learn-20260926`.
- 2026-09-26 18:17: **Launch 1 stopped.** Loop A hit `429 Too Many Requests` from Gemini on all 8 concurrent workers (24 failed attempts, 3 retries each, no pair lost yet). Stopped before a retry could exhaust and crash the run. Operational fix only: `llm_workers` 8 → 3 and `retries` 5 → 8 (backoff doubling from 5 s). Results do not depend on concurrency, and all finished calls are cached, so the restart reproduces launch 1's work without new spend. Launch 1's partial log is kept at `logs/arena/arena-learn-20260926.jsonl`.
- 2026-09-26 18:16: Launch 2 (`arena-learn-20260926b`) started with 3 Gemini workers.
- 2026-09-26 18:19: **Launch 2 Loop A stopped by a harness bug.** One OpenRouter call returned HTTP 200 with no model name (an error body). The strict route check treated the missing name as a model change and stopped Loop A without retrying. Loop B continued and finished round 1: it **kept** a new question, `provides_helpful_explanation_and_depth` (helps), gate 67.6% → 72.0%, b 110 vs c 44, p < 0.0001. The other two B candidates were rejected (drop `contains_factual_or_logical_errors`: p 0.81; reword it: p 0.14).
- 2026-09-26 18:24: **Fix (transport only):** a 200 response without a model name, or with an `error` field, is now retried as a transient error. A response that names a *different* model still stops the run. Also, if one loop fails, the other now stops at its next evaluation instead of running on alone. Test added (57 pass). The restart replays every finished call from cache (same prompts → same answers, including the editor's proposals), so Loop B's round 1 result is reproduced, not re-rolled. The decision to restart does not depend on any result.
- 2026-09-26 18:25: Launch 3 (`arena-learn-20260926c`) started.
- 2026-09-26 18:33: **Launch 3 Loop A stopped: Gemini content-policy blocks.** One Loop A batch was refused with `403 PROHIBITED_CONTENT` (content_policy_violation) on all 8 attempts. Arena contains real user prompts, some unsafe; Jev read the same text without complaint. The launch-2 "missing model name" response was very likely the same block. This is a genuine difference between the loops, not a transport bug.
- 2026-09-26 18:40: **Methodological decision (made by Claude while Alexander was away; flagged for his review):**
  - A pair Gemini refuses to read gets a **seeded coin flip** in Loop A and is flagged `blocked` (like the brief's tie rule, and what a deployed LLM decider would have to do). Blocks are not retried and are cached so reruns are deterministic.
  - Blocked pairs are excluded from the mistakes shown to either editor. If an editor prompt is itself blocked, the editor retries with a different seeded mistake sample (up to 3 attempts).
  - The sealed stage also reports a **sensitivity verdict** with every pair blocked for Loop A removed from all systems (A, B, baseline). This is reported, not used for the verdict.
  - Block counts are reported per evaluation (`blocked` in `wip_summary.json`). 58 tests pass.
- 2026-09-26 18:41: Launch 4 (`arena-learn-20260926d`) started. Loop B finished all 4 rounds by 18:48 (1 edit kept of 12 proposed; see below); Loop A is rate-limited (3 workers, ≈12 min per 1,500-pair gate check).
- 2026-09-26 18:48: **Loop B learning result (gate set, not a verdict):** round 1 kept `provides_helpful_explanation_and_depth` (67.6% → 72.0%, b 110 / c 44). Rounds 2–4: 7 candidates gated and rejected (each lowered gate accuracy, 69.3–71.4%), 2 failed the question check. Loop A version 0: 75.6% practice, 75.3% gate (1 pair blocked by Gemini).
- 2026-09-26 19:18: Experiment 3 (decision-trace Jev loop) designed, built and committed on branch `exp3-decision-trace` (worktree `../jev-test-poc-exp3`) before any experiment-3 paid call. Design and log: the "Experiment 3" section of this file on that branch (merged here when complete).
- 2026-09-26 19:20: **Decision (Alexander): run experiment 3's learning in parallel with experiment 2** instead of waiting for experiment 2's verdict. Experiment 3's learning reads only practice and gate; its sealed stage is still guarded to run only after experiment 2's sealed verdict exists. Its few editor calls share Gemini's rate limit with experiment 2's Loop A (a small slowdown at most).
- 2026-09-26 19:35: **Both runs stopped: OpenRouter account out of credit.** From about 19:15, Gemini calls returned `402 Payment Required`; Loop A slowed to a crawl (retries with backoff) and some calls exhausted all 8 retries. Experiment 3's two editor calls also got 402. Stopped both runs before a failure could be recorded as a result. Experiment 2 paid spend at stop: **$7.99** (36,504 paid calls). Every finished call is cached; restarting after credit is added replays them for free and reproduces the same results.
  - Experiment 2 state at stop: Loop B complete (4 rounds); Loop A in round 1 — version 0 scored (75.6% practice, 75.3% gate), candidate 1 gated (76.7% gate), candidate 2 at 940/1,500.
- 2026-09-26 19:45: **Fixes (safety only, no effect on results):** a 402 now stops the run at once with an "add credit" message instead of being retried; a failed editor call now stops the loop instead of being treated as "no edits this round" (which would have silently wasted rounds). Tests added (59 pass).
- **Waiting on Alexander:** add OpenRouter credit (Claude cannot make payments). Remaining estimate: experiment 2 ≈ $25–35 worst case (Loop A rounds 1–4 + sealed); experiment 3 ≈ $10–15.
- 2026-09-26 19:40: Alexander added credit. The OpenRouter key has a **$50 limit, $40.03 remaining** (usage $9.97 across both experiments' checks and runs). Resumed both runs: experiment 2 launch 5 (`arena-learn-20260926e`), experiment 3 launch 2 (`arena3-learn-20260926b`). The remaining worst case (~$40–50) could reach the key limit; if so, runs stop cleanly at the first 402 and resume from cache after a top-up.
- 2026-09-26 20:02: Loop A at 3 workers ran ≈80 pairs/min (≈19 min per 1,500-pair gate check; ≈3 h left). At Alexander's request, `llm_workers` 3 → 5 (operational only; results do not depend on concurrency). Stopped launch 5 mid-way through round 1 candidate 3 (1,310/1,500) and relaunched as launch 6 (`arena-learn-20260926f`); finished calls replay from cache. If 429s become persistent, drop back to 3.
- 2026-09-26 20:24: **5 workers was too many.** Round 1 completed and **Loop A kept its first edit**: c2 "do not automatically disqualify a response for minor truncation" (gate 75.3% → 77.1%, b 54 / c 28, p 0.003). All three round-1 candidates passed (c1 p 0.006, c3 p 0.026); the gate kept the one with the largest net gain. Then in round 2 one batch was rate-limited (429) on all 8 attempts (≈10 min) and failed. Stopped launch 6 at round 2 candidate 1 (≈1,050/1,500).
- 2026-09-26 20:30: **Fixes (operational, no effect on results):** workers back to 3; retries 8 → 12 with backoff capped at 120 s (≈15 min of patience per rate-limited call); a failed call now cancels queued calls at once (before, the pool ran every queued call before raising, spending for minutes on a doomed evaluation). Test added (60 pass). Relaunching as launch 7 (`arena-learn-20260926g`); all finished calls replay from cache.
- 2026-09-26 21:05: Round 2: all three Loop A candidates rejected (77.5% p 0.25; 77.7% p 0.17; 76.5% worse); round-1 version stays (77.1% gate). Round 3 started. Key credit at $25.04 of $50 with ≈ $22–24 of work left; Alexander is raising the budget.
- 2026-09-26 21:10: **Auto-chain armed** (`chain_sealed.sh arena-learn-20260926g`): when experiment 2's learning ends with frozen versions, it runs experiment 2's sealed stage (`arena-sealed-20260926`); if that writes its verdict, it runs experiment 3's sealed stage on the fresh set (`arena3-sealed-20260926`, in the worktree). Each step runs only if the previous one produced its output; any failure stops the chain.
- 2026-09-26 21:20: **Experiment 4 designed (not scheduled):** LLM + Jev hybrids — cascade, stacked vote, Jev-informed LLM — on a new 2,000-pair sealed set. Design, preregistered verdict rows, cost (≈ $11–13) and prerequisites (BYOK for speed; experiment 3's verdict selects the Jev component) in `Task Brief 4_Hybrids.md`.
- 2026-09-26 21:25: **Decisions (Alexander):** (1) future experiments use **1,000 pairs per set** (gate and sealed) instead of 1,500, for speed; the current run is unchanged. Experiment 4's brief updated (sealed-4 1,000 pairs, ≈ $7–8). (2) **OpenRouter BYOK enabled** with the Google AI Studio key. Checked on live calls: served provider still "Google AI Studio" (route check passes) and reported cost still equals tokens × reference price ($0.75 / $3.75 per million), so cost accounting is unchanged. Some 429s still occur and recover; OpenRouter's shared-capacity fallback stays on as the backup.
- 2026-09-26 21:27: **Unattended supervisor** (`supervise_overnight.sh`, run under `caffeinate -ims` to block idle sleep) replaces the simple chain: waits for launch 7; if learning ends without frozen versions, relaunches (up to 6 attempts; finished calls replay from cache); then experiment 2's sealed stage, then experiment 3's, each retried up to 6 times on transient failure. Stops outright on out-of-credit, a served model/provider change, or the spend cap. Log: `logs/supervisor.log`.
- 2026-09-26 21:35: **Experiment 4 narrowed to one hybrid (Alexander):** the stacked vote of the best LLM harness (experiment 2's final Loop A) and the best Jev harness (best of B, B-prime, B-plus on experiment 3's fresh sealed set), vs the LLM alone on a new 1,000-pair sealed set. The cascade is kept only as a free, exploratory add-on computed from the same decisions. Estimate ≈ $2–3. Brief revised: `Task Brief 4_Hybrids.md`.
- 2026-09-26 22:45: **Experiment 2 learning complete; final versions frozen** (launch 7, `arena-learn-20260926g`). Both loops: 12 candidates proposed, **1 kept** (both in round 1). Loop A final = `A-r1-c2` (gate 77.1%); rounds 2–4 all rejected (closest: r4 c1, 77.8%, p 0.10). Loop B final = `B-r1-c2` (gate 72.0%). Learning paid spend: **$32.41**. Supervisor started experiment 2's sealed stage at 22:45:47 (`arena-sealed-20260926-s1`).
- 2026-09-26 23:22: **Experiment 2 sealed evaluation complete** (`arena-sealed-20260926-s1`, 1,500 pairs, once). **Preregistered verdict: Only the Jev loop learned** (`arena_v2` row 5). Same verdict with Gemini-blocked pairs excluded (3 pairs).
  - Loop A (LLM): version 0 **72.9%** → final **73.3%**; learning test b 43 / c 36, p 0.50 → **did not learn** (its round-1 edit, +1.8 on gate, did not hold on sealed).
  - Loop B (Jev): version 0 **66.7%** → final **70.1%**; b 95 / c 44, **p 0.00002 → learned** (+3.4 points, the `provides_helpful_explanation_and_depth` question).
  - A vs B: A higher by 3.2 points (B−A 95% interval −5.6 to −0.9; p 0.008). Not within ±3, so not "same quality".
  - Cost per 1,000 decisions: A **$1.526**, B **$0.066** → B costs 4.4% of A (**≈23× cheaper**).
  - B vs style baseline (61.8%): B much better (b 341 / c 217, p < 0.0001) — the rubric learned more than style.
  - Memorization flag: **on** (Loop A version 0 at 72.9% > 70%).
  - Total experiment 2 paid spend: **$37.09** (learning $32.41).
- 2026-09-26 23:46: **Experiment 3 sealed attempt 1 failed on a new kind of Gemini refusal:** "Gemini blocked the response: OTHER" (code 502) — Gemini generated an answer, then withheld it — repeated on every retry for one Loop A batch. The block detector only knew request blocks. Supervisor stopped before attempt 2 could repeat it.
- 2026-09-26 23:55: **Fix:** a response block is retried twice, and on the third identical refusal is treated like a request block (batch split into single pairs; a refused pair gets the seeded coin flip, flagged `blocked`, cached). Same rule as before, one more signature. Test added (61 pass). Experiment 2's results are unaffected (its sealed stage had already completed without this error). Relaunching the supervisor for experiment 3's sealed stage only (run ids `arena3-sealed-20260926b-s*`).
- 2026-09-27 00:15: **Experiment 3 sealed attempt (`arena3-sealed-20260926b-s1`) crashed at the very end** (style baseline): one fresh-sealed response is literally the text "N/A", which pandas' CSV reader turns into a missing value; the deciders had been shown "nan" for that pair and the baseline crashed on it. No verdict was written. Checked every pair file: experiment 2's practice, gate and sealed sets contain **no** such case, so experiment 2's results are unaffected.
- 2026-09-27 00:25: **Fix:** all pair files are read as text (`workspace.read_pairs`, `keep_default_na=False`), so "N/A" stays "N/A". Test added (62 pass). Rerunning experiment 3's sealed stage (`arena3-sealed-20260926c-s*`): every pair except that one replays from cache; that pair gets new calls with its real text.

---

# Experiment 3: Arena, decision-trace learning for the Jev loop

**Why:** in experiment 2, Loop B kept one edit (round 1) and then stalled: 9 of 12 candidates were "add a question", and every later one lowered gate accuracy. The editor never saw *why* a pair was missed: Jev's per-question answers, which are the whole point of the hypothesis ("Jev tells the learner which criterion was wrong and by how much"). **Question:** does decision-trace feedback make the Jev loop learn more? And separately: do fitted question weights help on top of it?

**Decisions (Alexander, 2026-09-26):** run on Arena; include the weighted B-plus arm; build on branch `exp3-decision-trace` in a git worktree (`../jev-test-poc-exp3`) so experiment 2's run and sealed stage keep using `main`'s code; launch only after experiment 2's sealed verdict is written. **Updated 19:20: Alexander asked to run experiment 3's learning in parallel with experiment 2; only experiment 3's sealed stage waits for experiment 2's verdict (enforced in `sealed_trace.py`).**

## Design (fixed before any experiment-3 paid call)

- **Arms (both start from experiment 2's version 0 rubric):**
  - **B-prime (`Bp`):** decision-trace feedback + practice pre-screen; unweighted sum, as in B.
  - **B-plus (`Bw`):** the same, plus per-question weights fitted on practice for every version (logistic regression, no intercept; a negative weight means the direction looks backwards).
  - **Loop A is not rerun.** Experiment 2's Loop A (version 0 and final) is the comparison; its procedure is unchanged.
- **Decision trace for the editor:** for each of 20 sampled practice mistakes, the top 4 per-question pushes (Jev P(yes) for both responses, which response each question pushed toward, and whether that was the winner). Plus an aggregate over all practice pairs: how often each question pushed a mistake toward the loser, and how often it alone decided a pick right vs wrong. Plus a richer evidence table: win rate by probability-gap size and which questions overlap (|r| ≥ 0.6). The pick is an exact sum over questions, so the trace is exact, not an approximation.
- **Pre-screen:** the editor proposes up to 8 single edits; each valid one is scored on the 500 practice pairs with Jev (≈7¢); the best 3 with a net practice gain (b > c) go to the gate. Gate rule unchanged: one-sided sign test, p < 0.05 per edit, keep at most one per round. Same edit limits, question check, duplicate refusal and 4 rounds as experiment 2.
- **Fresh sealed set:** 1,500 pairs drawn (seed + 300) from the same prompt-hash buckets as experiment 2's sealed set, excluding all 1,500 of experiment 2's sealed pairs. No pair shared with experiment 2's sealed set; no prompt shared with practice or gate. Practice and gate files are byte-identical copies of experiment 2's. Winner shown first in exactly 50%.
- **Preregistered analysis (`verdict_trace.py`):**
  - **Primary (two-sided McNemar on the fresh sealed set, Holm-corrected across both):** P1 `Bp` final vs experiment 2's `B` final (does the trace help?); P2 `Bw` final vs `Bp` final (do weights help?). Each answer: helps / hurts / no detectable difference.
  - **Reported:** learning checks (`Bp` final vs version 0; `Bw` final vs its version 0); the Arena headline verdict (`arena_v2` rows) with `Bp` as "B" vs experiment 2's Loop A, and `Bw` as a secondary line; each arm vs the style baseline; cost per 1,000 decisions; learning cost including pre-screening.
- **Budget:** separate tracker, cap $20; experiments 2 + 3 together stay under the $75 approved.
- **Fairness note:** Loop A already learns from its own trace (its one-line reasons). The pre-screen is Jev-only because Jev makes it cheap (≈7¢ vs ≈80¢ per candidate for Loop A); that is part of the claim being tested and will be stated in the write-up.

## Checklist

- [x] Worktree + branch; experiment 2 data, cache and results linked read-only.
- [x] Fresh sealed set (`prep_arena3.py`).
- [x] Trace, aggregate trace, rich evidence, fitted weights (`trace.py`), with tests.
- [x] `learn_trace.py` (two arms in parallel), `sealed_trace.py` (guarded; refuses until experiment 2's verdict exists), `verdict_trace.py` (Holm), with tests; end-to-end dry run with fake clients. 66 tests pass.
- [x] Commit before any paid call (`cd8f701`).
- [x] Launch learning (in parallel with experiment 2, per Alexander).
- [x] Monitor; sealed (after experiment 2's verdict); verdict.
- [x] Merge to `main`; archive; compare experiments 1–3.

## Progress log

- 2026-09-26 19:14: Worktree `../jev-test-poc-exp3` on branch `exp3-decision-trace` created from `main` (`fdb7755`).
- 2026-09-26 19:15: Fresh sealed set: 13,789 pairs in the sealed buckets → 12,289 after excluding experiment 2's sealed pairs → 1,500 sampled. Overlap checks all zero.
- 2026-09-26 19:18: Build complete; dry run with fake editor and fake Jev passed (both arms, 2 rounds, trace present in the editor prompt, pre-screen and gate exercised, weights only in B-plus). 66 tests pass.
- 2026-09-26 19:20: **Learning launched in parallel with experiment 2** (`learn_trace.py --run-id arena3-learn-20260926`). Live: `results/arena3/run_status.json`, `results/arena3/wip_summary.json`.
- 2026-09-26 19:21: Version 0 on gate: `Bp` 67.6% (identical to experiment 2's B v0, replayed from cache as expected); `Bw` 69.3% (same rubric, weights fitted on practice, no edits yet).
- 2026-09-26 19:35: **Stopped: OpenRouter out of credit** (402 on both round-1 editor calls, before any candidate was gated). Experiment 3 paid spend so far ≈ /bin/zsh (version 0 evaluations replayed from cache). Will restart under a new run id after credit is added; the failed editor calls were not cached, so the restart asks again.
- 2026-09-26 19:40: Relaunched after the credit top-up as `arena3-learn-20260926b`.
- 2026-09-26 20:13: **Learning complete; final versions frozen** (`results/arena3/final_versions.json`). Paid spend for experiment 3 learning: **$4.09**. Jev rate-limit retries (both arms, 8 workers each) all recovered.
  - **B-prime:** 31 candidates proposed, **2 kept**. Gate 67.6% → 69.0% (r1: drop `directly_answers_without_filler`, b 76 / c 55, p 0.040) → **70.3%** (r3: reword `contains_factual_or_logical_errors` to severe errors only, b 54 / c 35, p 0.028). Final rubric: 5 questions.
  - **B-plus:** 32 candidates proposed, **1 kept**. Weights alone lifted version 0 to 69.3% on gate. Kept r4: reword `satisfies_explicit_instructions` (b 78 / c 55, p 0.028) → **70.8%**. Final weights (practice-fitted): instructions 2.27, formatting 1.18, incomplete 0.66, filler 0.28, refusal 0.22, factual errors 0.14 — instruction-following dominates.
  - Many candidates were stopped cheaply before the gate: pre-screen rejections and failed question checks (see `wip_summary.json`). Several near misses (p 0.07–0.08).
  - Reference (gate, not sealed): experiment 2's plain B reached 72.0% with one kept edit. The preregistered comparison is on the fresh sealed set.
- 2026-09-26 23:22–23:46: Sealed attempt 1 (`arena3-sealed-20260926-s1`) failed on a Gemini response block (see experiment 2's log, 23:46); fixed on `main` and merged here. Relaunched as `arena3-sealed-20260926b-s*`.
- 2026-09-27 00:25: Sealed rerun after the "N/A" text fix (see experiment 2 log, 00:15-00:25): `arena3-sealed-20260926c-s*`.
- 2026-09-27 00:17: **Experiment 3 sealed evaluation complete** (`arena3-sealed-20260926c-s1`, fresh 1,500-pair set, once). **Preregistered answers: trace → no detectable difference** (B-prime final 67.9% vs B final 69.0%, b 57 / c 74, p 0.16); **weights → help** (B-plus final 69.8% vs B-prime 67.9%, b 75 / c 46, p 0.011, significant after Holm). Learning: B-prime did not learn (p 0.11); **B-plus learned** (67.5% → 69.8%, p 0.002). Loop A on this set: 73.6% → 75.3% (p 0.009). Headline rows vs Loop A: hypothesis weakened for both arms. Cost ≈ 4% of Loop A per decision. Experiment 3 paid spend: $9.10.
- 2026-09-27 00:30: Archived `experiments/2026-09-26-arena-trace-v1/`; merged branch `exp3-decision-trace` into `main` (fast-forward); wrote `experiments/COMPARISON.md`. Experiment 4's Jev component resolved by its preregistered rule: **B-plus final**.

---

# Experiment 4: one LLM + Jev hybrid (stacked vote)

**Brief:** `Task Brief 4_Hybrids.md`. **Go-ahead:** Alexander, 2026-09-27. **Config:** `config_arena4.yaml` + `task_arena4.yaml`. **Outputs:** `data/arena4/`, `results/arena4/`, `logs/arena4/`.

## Design (fixed before any paid call)

- **A\*** = experiment 2's final Loop A (`A-r1-c2`); **J\*** = experiment 3's B-plus final (`Bw-r4-c1`, with its fitted weights), selected by the brief's rule (best Jev arm on experiment 3's fresh sealed set). Both read from the committed archives.
- **Hybrid:** logistic regression, no intercept, on [A\*'s pick (±1), J\*'s six weighted signed per-question differences, J\*'s total]; L2 strength by 5-fold CV accuracy over C ∈ {0.01 … 10}; fitted on practice ∪ gate (2,000 pairs; Gemini-refused pairs excluded from the fit). Refused sealed pairs use J\*'s pick. Model frozen to `results/arena4/hybrid_model.json` before sealed.
- **Sealed-4:** 1,000 fresh pairs from the sealed buckets, excluding all 3,000 pairs of experiments 2 and 3's sealed sets (10,789 left in the pool). No pair or prompt overlap with any earlier set; winner first in exactly 50%; no "N/A"-style texts.
- **Verdict (`verdict_hybrid.py`, rows in order):** hybrid significantly better than A\* (two-sided McNemar, p < 0.05) → *hybrid beats the LLM*; significantly worse → *combination hurts*; 95% interval of (hybrid − A\*) within ±3 points → *no meaningful gain*; else *inconclusive*. Also reported: hybrid vs J\*, each vs the style baseline, costs, agreement, blocked-pair accuracy, memorization flag.
- **Exploratory (not in the verdict):** cascade — J\* decides when |score| ≥ τ, A\* the rest; τ chosen on gate (best accuracy with ≤ 50% sent to the LLM), frozen with the model.
- **Budget:** separate tracker, cap $10; estimate ≈ $2–3 (practice/gate decisions replay from cache).

## Progress log

- 2026-09-27 (build): sealed-4 drawn and checked; hybrid, fit, sealed and verdict code written; 75 tests pass (6 new); end-to-end dry run with fake clients passed. Committed before any paid call.
- 2026-09-27: **Hybrid fitted and frozen** (`arena4-fit-20260927`, $0.00 — every practice/gate decision replayed from cache). CV chose C = 10 (least regularized). Coefficients: LLM pick +0.89; Jev questions (on B-plus-weighted parts) instructions +1.08, factual errors −3.54, filler −1.10, formatting +0.83, refusal +3.15, incomplete −0.44, total −0.02. Fit accuracy on practice ∪ gate: hybrid 76.7% in-sample vs LLM alone 76.8% and Jev alone ≈ 70.3% — an early sign that stacking adds little. Exploratory cascade threshold from gate: 0.608 (49% of pairs to the LLM; 75.9% on gate vs 77.1% for the LLM alone). Proceeding to the sealed stage unchanged.
- 2026-09-27: **Experiment 4 sealed evaluation complete** (`arena4-sealed-20260927-s1`, 1,000 pairs, once). **Preregistered verdict: No meaningful gain.** Hybrid 75.6% vs LLM 75.7% (8 better / 9 worse, p 1.0; 95% interval of the difference −0.9 to +0.7, inside ±3). Jev alone 71.8%; style baseline 62.2%. LLM and Jev agreed on 79.3% of pairs; the hybrid sided with Jev on 8% of disagreements. Costs per 1,000: LLM $1.51, Jev $0.065, hybrid $1.57. Exploratory cascade (threshold from gate): 49% of pairs to the LLM, 75.2%, $0.80 per 1,000. Experiment 4 total spend: **$1.57**. Archived `experiments/2026-09-27-arena-hybrid-v1/`; comparison updated.
- 2026-09-27: **Experiment 5 designed (not scheduled):** route between Jev and the LLM. Jev decides pairs where its score margin is at least τ; the rest go to the LLM. τ is set on gate so that 40% of pairs go to the LLM. Scored on a fresh 1,000-pair sealed set ("sealed-5", excluding all earlier sealed pairs). Preregistered rows: router beats the LLM → same quality (±3) at ≤ ½ cost → routing costs real accuracy → same quality but not cheap enough → inconclusive. ≈ $1.6–2. Brief: `Task Brief 5_Routing.md`.

---

# Experiment 5: route between Jev and the LLM

**Brief:** `Task Brief 5_Routing.md`. **Go-ahead:** Alexander, 2026-09-27. **Config:** `config_arena5.yaml` + `task_arena5.yaml`. **Outputs:** `data/arena5/`, `results/arena5/`, `logs/arena5/`.

## Design (fixed before any paid call)

- Components as in experiment 4: LLM = experiment 2's `A-r1-c2`; Jev = experiment 3's B-plus `Bw-r4-c1`.
- Router: Jev decides when |its weighted score| ≥ τ; otherwise the LLM decides (Jev if Gemini refuses). τ = the gate-set margin quantile sending **40%** of gate pairs to the LLM, frozen to `results/arena5/router_model.json` before sealed.
- Sealed-5: 1,000 fresh pairs (sample seed + 500, orientation seed + 5,000) excluding all 4,000 earlier sealed pairs; 9,789 left in the pool; no overlaps; winner first in exactly 50%; no "N/A"-style texts. `prep_arena4.py` now takes the seed offsets from config (defaults keep experiment 4's set byte-identical, verified).
- Verdict (`verdict_router.py`, rows in order): router significantly better → *router beats the LLM*; interval of (router − LLM) within ±3 and cost ≤ ½ → *same quality, half the cost*; significantly worse with interval below −3 → *routing costs real accuracy*; within ±3 but cost > ½ → *same quality, not cheap enough*; else *inconclusive*.
- Cost: router = Jev on every pair + the LLM on routed pairs only. Cap $5.

## Progress log

- 2026-09-27 (build): sealed-5 drawn; router, verdict and staged runner written; 79 tests pass (4 new); fake-client dry run of both stages passed. Committed before any paid call.
- 2026-09-27: **τ frozen** (`arena5-fit-20260927`, $0.00, gate decisions from cache): τ = 0.4453 sends 40.0% of gate pairs to the LLM. On gate: router 75.2%, LLM alone 77.1%, Jev alone 70.9%. Proceeding to the sealed stage unchanged.
- 2026-09-27: **Sealed stage stopped: OpenRouter 402 (out of credit)** during the LLM's sealed-5 pass. Stopped at once (fatal-error rule, no retries); no verdict written. Finished calls are cached; the rerun after a top-up resumes them for free.
- 2026-09-27: Key limit raised to $100 by Alexander (the $50 cap was on the API key itself, separate from account credit). Sealed attempt 2 resumed from cache and completed.
- 2026-09-27: **Experiment 5 sealed evaluation complete** (`arena5-sealed-20260927-s2`, 1,000 pairs, once). **Preregistered verdict: Same quality, half the cost.** Router 76.2% vs LLM alone 76.3% (36 better / 37 worse, p 1.0; 95% interval of the difference −1.8 to +1.6, inside ±3); cost $0.633 vs $1.481 per 1,000 (ratio 0.43 ≤ 0.5). Jev decided 61.8% of pairs at 81.6% (the LLM scored 81.7% on those same pairs); the LLM decided 38.2% at 67.5%. Jev alone 72.7%, baseline 59.9%. Average latency per decision: router 874 ms vs LLM 1,285 ms. Experiment 5 spend: **$1.54**. Archived `experiments/2026-09-27-arena-router-v1/`; comparison updated.

---

# Experiment 6 (designed): learning from partial feedback

- 2026-09-27: **Designed, not scheduled.** Upworthy as a contextual bandit: ≈ 11,900 tests with 3+ comparable headlines (median 4) qualify. The policy picks one headline per test and sees only its click rate; a new practice batch each round; 15% seeded exploration; the gate compares policies by the click rates of their own picks; the sealed set is scored by regret against the best headline (never shown to the learner). Arms: LLM policy, Jev policy, a Thompson-sampling baseline on code features, and a random control, starting from experiment 1's version 0. Preregistered rows mirror `arena_v2`, measured on reward and regret. ≈ $15–18. Brief: `Task Brief 6_Bandit.md`.
- 2026-09-27: **Revised and built (Alexander: "production-like, no answer key").** Primary policy is now the **Jev + LLM router** learning from partial feedback, against an LLM-only policy (L), a Jev-only policy (J), Thompson sampling on surface features (C) and a random control. Metric: click lift over a random pick (random 0, best ≈ +40). Preregistered rows (`bandit_v1`): no signal → router beats LLM → same quality (±5 lift points) at ≤ ½ cost → routing costs quality → same quality not cheap enough → inconclusive; plus "learned from partial feedback" for R, L, J. Data: practice 1,200 (exploratory; 4 × 300 new tests), gate 1,000 (confirmatory), sealed 1,000 (holdout); median 4 headlines per test. 88 tests pass (9 new, incl. a strict no-leak test that unchosen outcomes never reach an editor); end-to-end fake-client dry run passed. Smoke (10 real tests): Gemini returned valid picks; $0.0014 per LLM decision, $0.0001 per Jev decision; worst case ≈ $31, cap $40. Committed before the paid run.
- 2026-09-27 10:27: **Launched** under `supervise_exp6.sh` (`caffeinate`; log `logs/supervisor6.log`; live status `results/upworthy6/run_status.json` and `wip_summary.json`). All three arms running in parallel; no errors in the first minute. Note: arms L and R both request version-0 LLM picks on the same tests at the start, so a few hundred early calls may be paid twice before the cache fills (≈ $1–2, within the cap).
- 2026-09-27 13:01: Learning complete in one attempt (1,597 rate-limit/server retries, all recovered). Edits kept: router 1 of 12 (drop `uses_second_person`), Jev-only 2 of 12 (drop `uses_second_person`; add `references_third_person_protagonist`), LLM-only 0 of 12.
- 2026-09-27 13:16: **Sealed evaluation complete** (1,000 tests, once). **Preregistered verdict: Same quality, half the cost.** Router +10.9 vs LLM-only +13.0 lift points over a random pick (difference −2.07; 95% bootstrap interval −3.99 to −0.06, inside ±5; Wilcoxon p 0.087); cost $0.662 vs $1.452 per 1,000 (ratio 0.46). Learned from partial feedback: **Jev-only yes** (+5.6 → +7.7, p 0.020); router no (+0.7, p 0.21); LLM-only no (no edit kept). Thompson baseline +2.2; random 0; best +40.1. Memorization flag off. Spend **$25.86**. Archived `experiments/2026-09-27-upworthy-bandit-v1/`; `RESULTS.md` and the comparison updated.

---

# v2 (designed): real business tasks

- 2026-10-05: **Designed, not scheduled.** Dataset: Zapier's AutomationBench (600 graded business-workflow tasks; assertion-based `partial_credit` and pass/fail). `coreyhaines31/marketingskills` has no outcomes, so it is an optional version-0 seed only. The v1 router becomes candidate selection and escalation around an agent: a cheap agent makes K runs; the weighted Jev rubric keeps confident runs and escalates the rest to an LLM judge or a strong agent. Phases: 0 feasibility spike (go/no-go), 1 preregistered experiments V2-1 to V2-4. Brief: `Task Brief 7_V2_Business.md`.

---

# Repository restructure (v1/ and v2/)

- 2026-10-05: **Restructured (Alexander approved).** Tagged the prior state `v1-final`. Moved experiments 1–6 into `v1/` with `git mv` (history preserved): code, configs, tests, supervisor scripts, data splits and experiment archives together, so relative paths still resolve from `v1/`. This file renamed from `MVP Project Plan.md` to `v1/PLAN.md`; the MVP brief and Task Briefs 2–6 moved to `v1/briefs/`; Task Brief 7 to `v2/briefs/`. Ignored local dirs (`.venv`, `.env`, `cache/`, `logs/`, `results/`, raw data, pairs) moved into `v1/`; `.gitignore` updated. **Cleanup:** removed the merged worktree `../jev-test-poc-exp3` and branch `exp3-decision-trace` (local and origin). The worktree held experiment 3's local outputs that were not in the main checkout (`logs/arena3/`, `results/arena3/`, `data/arena3/pairs/`, `logs_arena3_learn.stdout`); they were copied, byte-verified, into `v1/logs/arena3/`, `v1/results/arena3/` and `v1/data/arena3/pairs/` first. **Fix:** `supervise_exp6.sh` and `supervise_overnight.sh` now resolve their root from their own folder (they hardcoded the old repo root and the exp3 worktree). **Checks from `v1/`:** tests 89 passed (baseline before the move: 88 passed, 1 skipped; the skipped test needs `data/arena3/pairs/`, now present); `run.py --fake --run-id restructure-check` completed at $0. v2 scaffold: `../v2/PLAN.md`.
