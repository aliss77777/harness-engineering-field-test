# Task #2 brief: Chatbot Arena (long responses)

**Written:** 2026-09-26 · **Owner:** Alexander · **Builds on:** `MVP-BRIEF-jev-learning-loop-v2.5.md` (the harness, loops, editor, logging and controls are unchanged unless stated here) · **Repo:** same `jev-loop-mvp` repo, new `task.yaml`

## 1. Why this task

Run 1 (Upworthy headlines) showed: B was 18.9× cheaper per decision; no edit passed the gate; three of B's four edit bundles leaned positive but the 300-pair gate couldn't confirm them; Loop A's 73.8% was likely memorization. Headlines are also not how people use LLMs at work.

Task #2 asks the enterprise question: **given a real user request and two long responses, which one did the user prefer?** The same loop, applied to lumpy, realistic output.

## 2. What changes from run 1 (the lessons)

| Change | Why |
|---|---|
| **Bigger sets** (Section 4) | Run 1's gate was too small to confirm edits of ~3 to 5 points |
| **Test each edit on its own.** The editor still proposes up to 3; each is gated separately; keep **at most one** per round (the best one that passes) | A bundle lets one bad edit hide a good one |
| **Gate threshold: p < 0.05 per edit** (one-sided sign test) | Several tests per round; a stricter bar offsets that. The larger gate makes it passable |
| **New verdict row: "Neither loop learned"** (Section 6) | Missing in run 1. Without it, a comparison of version 0s gets reported as a learning result |
| **Cost ratio is a question, not an assumption** | Jev reads the whole long response too; the 18.9× may shrink |

## 3. Data: `lmarena-ai/arena-human-preference-55k`

Hugging Face, Apache 2.0, ~57k rows. Columns: `id`, `model_a`, `model_b`, `prompt`, `response_a`, `response_b`, `winner_model_a`, `winner_model_b`, `winner_tie`. Prompts and responses may be JSON-encoded lists (multi-turn); parse them, don't treat them as plain strings.

**Filters, in order (print counts after each):**
1. Drop ties.
2. **Single-turn only** (one prompt, one response each). Multi-turn is parked.
3. Drop rows where either response is empty or failed to parse.
4. Length cap: both responses ≤ ~1,500 words (set in config). Keeps cost bounded; note how many rows it removes.
5. **Hide model names.** `model_a` and `model_b` never reach any decider or the editor.
6. Randomize which response is shown first (seeded). Check the winner is first in about 50% of pairs.

**Splitting: by prompt, not by row.** The same prompt can appear in several battles. Hash the prompt text and assign each hash to exactly one set, so no prompt appears in two sets. (This is the Arena equivalent of run 1's separate source files.)

**No clarity filter is possible:** each label is one user's vote. Expect noisier labels than Upworthy's z ≥ 2 pairs.

## 4. Sets

| Set | Pairs | Used |
|---|---|---|
| Practice | 500 | every round |
| Gate | 1,500 | every round, once per proposed edit |
| Sealed | 1,500 | once, at the end |

Before any paid call, estimate total calls and dollars for these sizes (long texts: Loop A cost per decision will be far above run 1's $0.71 per 1,000). Alexander sets a spend cap. If over, cut practice first, then gate to 1,000. Never cut sealed below 1,000.

## 5. The two loops on this task

**Loop A decider:** user request + response 1 + response 2 → "Which response did the user prefer? Answer 1 or 2, then one line why."

**Loop B decider:** Jev gets the **user request plus one response** and the rubric questions (e.g. "Does the response directly answer what was asked?", "Does it refuse or deflect?", "Is it padded with unnecessary length?"). Score = sum of yes-probabilities with direction signs, as in run 1. Log tie rate.

**Starting versions (5.1 of the MVP brief):** same LLM, same prompt for both: *"You're reviewing AI assistant responses. What makes a user prefer one response over another?"*

**Code baseline, new features:** length difference, number of list items/headers, has code block, refusal phrases ("I can't", "As an AI"), response-to-prompt length ratio. Arena votes are known to be swayed by length and formatting, so **this baseline may be strong. B must beat it to claim more than style detection.**

## 6. Verdict rules (updated; fixed before running)

Same four checks as MVP Section 8, on the sealed set. **Apply the first row that matches:**

| Result | Verdict |
|---|---|
| Neither loop passes the signal check | **No signal** |
| **Neither loop's final version beats its version 0** | **Neither loop learned.** Report v0 accuracies and costs descriptively. No A-vs-B claim |
| B learned, and B beats A | **Jev loop learns better** |
| B learned, same quality as A, B ≤ 1/5 cost | **Learns as well, far cheaper** |
| B learned, A didn't | **Only the Jev loop learned.** Report, then compare accuracies descriptively |
| A beats B | **Hypothesis weakened** |
| Anything else | **Inconclusive** |

Also report: B vs code baseline (paired McNemar), cost ratio, edits proposed/kept per loop, the final rubric with change history.

## 7. Honest limits to call out

- **Memorization:** Arena data (2023 to 2024) may be in LLM training sets. Keep the >70% version-0 flag.
- **Noisy labels:** one vote per pair sets a low ceiling. Accuracy in the 60s may be near the maximum possible.
- **Style vs substance:** if the code baseline matches B, the rubric learned formatting preferences, not quality.

## 8. Build (target: half a day)

1. `task_arena.yaml` + `prep_arena.py` (filters, prompt-hash split, saved IDs, counts). Code baseline on gate.
2. Parameterize decider prompts from `task.yaml` (no Upworthy wording in code).
3. Gate: single-edit mode, keep best passing edit, p from config.
4. Add the "neither learned" and "only B learned" verdict rows. **Commit before any paid run.**
5. Fake decider ~50% on all sets → cost estimate → Alexander approves cap → run.
6. Reuse `MONITOR-BRIEF-jev-loop-mvp-v1.md` during the run; update its plausibility range to ~35% to ~80%, and its set sizes.

## 9. Out of scope

SHP (backup dataset, only if Arena gives no signal), ChangeMyView, multi-turn conversations, the writer agent, Loop C (run it only after a "learned" verdict).