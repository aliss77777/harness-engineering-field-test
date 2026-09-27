# Task #6 brief: learning from partial feedback (contextual bandit on Upworthy)

**Written:** 2026-09-27 · **Owner:** Alexander · **Status:** design only, not scheduled · **Builds on:** the harness from experiments 2–5 (single-edit updates, anti-repeat, gate, sealed sets, spend cap, telemetry, supervisor). · **Repo:** new config/task pair (`config_upworthy6.yaml`, `task_upworthy6.yaml`).

## 1. Why this experiment

Experiments 1–5 had the shape of batched policy optimization, trained on labeled data: the policy is a text file (LLM instructions or a Jev rubric), each round is a batch, the reward is right or wrong, the editor's rewrite is the policy update, the gate is the validation check, and the sealed set is the evaluation. But every pair came with its answer, so strictly it was **supervised learning with text parameters**.

This experiment removes the labels. The policy picks one headline and sees **only that headline's outcome**, never which headline would have been best. That is a **contextual bandit**, the first step of reinforcement learning: learning from the results of your own actions, with an explore/exploit trade-off. The learning machinery is unchanged; only what the editor is allowed to see changes.

> **The question:** can a text policy, especially the cheap Jev rubric, learn to pick better headlines from partial feedback alone?

## 2. Data: Upworthy tests with 3+ headlines

- **Unit:** one Upworthy test = one story shown with several headlines to randomly assigned readers. Keep variants with the same image (`eyecatcher_id`) and excerpt, **3 or more distinct headlines**, each with **≥ 1,000 impressions**; drop the 2013-06-25 to 2014-01-10 window and the undeployed file (MVP brief 7.2). About **11,900 tests** qualify; median **4 headlines** per test.
- **Reward of a headline:** its click rate, clicks ÷ impressions, from the randomized test. Because readers were randomly assigned, each headline's click rate is an unbiased estimate, so replaying the archive is a valid offline test of any policy.
- **Sets, by source file** (as in experiment 1, so no test appears twice):

| Set | Source file | Tests | Used |
|---|---|---:|---|
| Practice stream | exploratory (≈1,700 qualify) | 4 rounds × 300 = **1,200**, a **new batch each round** | policy acts, sees only its own picks' rewards |
| Gate | confirmatory (≈8,400) | **1,000** | old vs new policy, each judged by its own picks |
| Sealed | holdout (≈1,800) | **1,000** | once, at the end |

A new practice batch each round mimics a live stream: the policy never sees the same test twice.

## 3. Policies (arms)

All start from **experiment 1's version 0** (same LLM, same prompt, generated before any Upworthy outcome was seen), so experiment 1 is the supervised twin of this experiment.

- **A — LLM policy:** sees all of a test's headlines, picks one, with a one-line reason (experiment 1's instructions, adapted from "pick X or Y" to "pick one of these").
- **B — Jev policy:** Jev answers the rubric for each headline; the headline with the highest score is picked (ties by seeded coin flip).
- **C — classic bandit baseline (no LLM, no editor):** Thompson sampling on a linear reward model over the six code surface features from experiment 1. It shows what a textbook algorithm learns from the same partial feedback, at zero API cost.
- **Random policy** (control): picks uniformly; its expected reward is the mean click rate of the test's headlines.

## 4. The learning loop (one round, per policy)

1. **Act:** the policy picks one headline for each of this round's 300 new practice tests. **Exploration:** in a seeded 15% of tests the pick is replaced by a random other headline, labelled as exploration. That is how the policy tests its own assumptions.
2. **Observe:** for each test, only the chosen headline's click rate and impressions. Nothing about the other headlines, and never which one was best.
3. **Feedback to the editor (allowed information only):**
   - its average reward this round, and on exploration vs its own picks;
   - 20 sampled tests with **the headlines shown, the one it picked, its reason (A) and the reward received**, split between low-reward picks and exploration picks that did better than the policy's usual reward;
   - **B only, bandit evidence table:** for each rubric question, average reward of chosen headlines where the answer was yes vs no, with counts. It is computed from its own picks only.
4. **Update:** the editor proposes up to 3 single, structured edits (same operations, limits, anti-repeat and question check as experiments 2–3).
5. **Gate:** each candidate and the current policy pick greedily (no exploration) on the 1,000 gate tests. Compare **the click rates of their own picks** test by test: one-sided sign test on tests where the picks differ, p < 0.05; keep at most the best passing edit. This uses only each policy's chosen headline, exactly what a live A/B test between two policies would show.
6. **Four rounds per policy.**

Policy C updates its reward model after each round from the same observations, with no editor and no gate.

## 5. What the editor never sees

Other headlines' click rates · which headline was best · regret · any gate or sealed outcome beyond keep/discard. Enforced in code and tested.

## 6. Sealed evaluation and preregistered verdict

On the 1,000 sealed tests, each policy picks greedily once (version 0 and final for A and B; C final; random).

**Metrics:** mean click rate of picks · **normalized regret**, (best click rate − chosen) ÷ best, averaged over tests · best-headline hit rate. Regret and hit rate use the archive's full data; the policies never saw them.

**Tests:** paired, test by test, on the chosen headlines' click rates (Wilcoxon signed-rank on the differences, α = 0.05), with a 95% bootstrap interval for mean differences.

**Apply the first row that matches:**

| Result | Verdict |
|---|---|
| Neither A nor B final beats the random policy | **No signal from partial feedback** |
| Neither A's nor B's final beats its version 0 | **Neither learned from partial feedback** |
| B learned, and B's final beats A's final | **Jev learns better from partial feedback** |
| B learned, within ±5% relative regret of A, at ≤ ⅕ of A's cost | **Jev learns as well from partial feedback, far cheaper** |
| B learned, A didn't | **Only the Jev policy learned from partial feedback** |
| A's final beats B's final | **LLM policy better under partial feedback** |
| Anything else | **Inconclusive** |

**Also reported:**
- Policy C vs A and B: can a textbook bandit on six surface features keep up?
- The supervised twin: the same policies' experiment 1 numbers.
- The **router** of experiment 5 applied to A and B's final policies on sealed, using the same routing rule re-fitted on gate: does routing still work under partial feedback?
- Cost per 1,000 decisions, exploration cost (reward given up during exploration), and the memorization flag.

## 7. Cost and time (estimate)

| Item | Estimate |
|---|---:|
| Policy A (≈ 16,000 pick-one-of-K decisions: practice, gate candidates, sealed) | ≈ $12–15 |
| Policy B (Jev on ≈ 4 headlines per decision) | ≈ $1–2 |
| Editors | ≈ $1 |
| Policy C, random, oracle | $0 |
| **Total** | **≈ $15–18**, cap $25 |

About 2–3 hours with BYOK; the supervisor runs it unattended.

## 8. Honest limits

- **Replay, not live traffic:** rewards come from past randomized tests. That is the standard offline method, not a deployment.
- **Weak signal:** Upworthy headline differences are small (≈ 0.1–0.5 click-rate points), and each test gives one noisy reward. Learning may need more than 1,200 practice tests; if the result is "no signal", that is informative.
- **Story baselines differ:** a 1% click rate is good for one story and poor for another, and the policy cannot see the other headlines to tell. Averaging over many tests helps; it does not remove the noise.
- **Memorization:** the archive is public and experiment 1's LLM scored above the memorization threshold; any LLM advantage may partly be recall.
- **Bandit ≠ full RL:** each decision is independent; actions do not change what happens next. Multi-step RL needs an interactive environment and is a later step.

## 9. Build (≈ half a day)

1. `prep_upworthy6.py`: multi-headline tests, filters with counts, sets by source file, saved IDs, per-headline click rates.
2. `bandit.py`: pick-one-of-K deciders (A: list prompt; B: per-headline Jev scores, argmax), seeded exploration, reward lookup, regret and hit rate, bandit evidence table, Thompson-sampling baseline (C).
3. `learn_bandit.py`: the round loop in section 4 (reuses the editor, candidate operations, question check, anti-repeat, telemetry), with a test that the editor's inputs contain no unchosen-headline outcomes.
4. `verdict_bandit.py` and `sealed_bandit.py`: rows above, guarded single sealed run; tests for every row.
5. Fake-client dry run, smoke test, cost estimate against the cap; commit before any paid call; run under the supervisor.

## 10. Out of scope

Live traffic; multi-step RL; re-learning the router; Arena as a bandit (it is pairwise, and a reconstruction from pairwise votes would be sparse and indirect).
