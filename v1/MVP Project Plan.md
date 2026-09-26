# MVP Project Plan

Updated as work progresses. The experiment rules in `MVP-BRIEF-jev-learning-loop-v2_5.md` stay fixed.

## Two-hour target

- [x] Create a reproducible local project and private Git history.
- [x] Prepare fixed Upworthy practice, gate, and sealed pairs.
- [x] Run the code-feature baseline and fake-decider sanity check.
- [ ] Complete one end-to-end learning round for Loops A and B.
- [ ] Save results, costs, logs, and a clear next-run command.

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
- [ ] Document setup and one-command rerun in `README.md`.
- [ ] Commit clean checkpoints and push to private `aliss77777/jev-test-poc`.

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
