# Skill loop redesign: multi-level telemetry for long, noisy workflows

**Written:** 2026-10-08 · **Status:** draft for Alexander's review; pieces built and measured for free on 2026-10-08 (see "Built and measured"); not yet run · **Replaces, if approved:** the gate and editor inputs of the Agent skill loop in [`Phase 1 design.md`](Phase%201%20design.md). The rest of that design stands.

## Why

The pilot ([report](../phase1/pilot/README.md)) kept no fix in 2 rounds, although every fix moved behaviour the right way and the best one added +6.7 points of credit. The loop itself (propose a fix, test it, keep or reject) is not the problem. **The test was built for v1's short, exact tasks and doesn't fit long, noisy workflows.**

| | v1 | v2 |
|---|---|---|
| One test item | One decision (pick A or B) | A workflow of 15–50 tool calls |
| Score per item | 1 bit, right or wrong | ~10 checks, combined into partial credit |
| Items in the gate | 1,500 | 40 |
| Randomness | None (temperature 0) | Temperature 0.7, and one early slip derails the rest |
| Does a fix touch every item? | Yes | No, only tasks where its rule applies |

This is a **credit assignment problem**, as in reinforcement learning: the score comes at the end, the mistake happened earlier. RL usually has to *learn* which steps deserve credit (TD(λ) and friends). We don't, because the bench grades each check and we record every step. So we do the credit assignment directly, with telemetry at three levels.

## The three levels of telemetry

| Level | What we record per run | Example | Used for |
|---|---|---|---|
| **1. Task** | Partial credit, pass/fail, cost, time | 0.67, fail, $0.04, 110 s | The headline numbers and the sealed verdicts |
| **2. Check** | Every grading check, passed or missed, tagged by kind | "must not: email the excluded vendor (broken)" | What a fix should move; the editor's failure profile |
| **3. Step** | Behaviours read from the tool-call trace, in order | "read the policy email before the first write: no" | Whether the fix changed the behaviour it targets |

**Check kinds** (from Phase 0's diagnosis): **rule broken** (a "must not" check failed), **action missed** (a required action never happened), **wrong content** (the action happened, with wrong or missing values).

**Step measures** (initial set): read every policy email *before the first write*; record-changing actions per run; steps used; whether the run stopped early or hit the step cap. The step measures are a fixed list in code, added to only between rounds and logged.

## Five changes

1. **Temperature 0 for agent runs.** The cascade runs each task once, so we no longer need runs to differ. Temperature 0 makes the same task give (nearly) the same run, which removes most of the noise. Two checks come first: a small determinism test (10 tasks × 2 runs) to see how repeatable runs really are, and a re-check of MiniMax against Gemini at temperature 0, since Phase 0 compared them at 0.7.
2. **The editor sees a failure profile, not just raw runs.** Counts by check kind and step measure across all practice failures (for example, *"rule broken 19 times; policy email skipped before first write in 9 of 13 tasks"*), plus a few examples. Each proposed fix must name the **check kind it targets**.
3. **Each fix is tested where it applies, plus a regression set.**
   - **Target set:** gate tasks where the current version missed at least one check of the targeted kind.
   - **Regression set:** a fixed sample of the other gate tasks.
4. **A three-part keep rule** (the numbers below are proposals, to be set before any run):
   - **Targeted checks improve:** on the target set, the share of targeted checks met rises; paired by task, cluster-aware one-sided test, p < 0.10.
   - **Nothing breaks:** on the regression set, mean task credit drops by no more than 3 points.
   - **No net loss:** mean task credit on the whole gate does not fall.
   Statistics treat each task as a cluster: the ~10 checks inside one task are not independent samples.
5. **Fix the length filter.** Allow rules up to 600 characters and ask the editor to shorten longer ones, instead of refusing them (4 of 5 refusals in the pilot were for length alone).

Unchanged from the Phase 1 design: MiniMax is its own editor; it learns only from its own graded practice runs; one edit per candidate; rejected edits are remembered; the sealed set is used once.

## Built and measured (2026-10-08, free)

Built in `src/jevloop/skill_loop.py` with tests: every scored check recorded with its kind; the editor's failure profile, with each fix required to name its target kind; the three-part keep rule scored at the check level, with tasks as clusters; rules up to 600 characters, longer ones sent back to be shortened. Not yet wired into a run script (that is the v2 Phase 1 run).

**A4: choosing the test tasks (decided: by task property).** In a simulation of a fix that does nothing (`scripts/gate_power.py`, 2,000 runs of 60 tasks), choosing target tasks by **past failure** "kept" the useless fix **77%** of the time against a nominal 10% (regression to the mean). Choosing them by a **task property** (the task defines a check of that kind) gave **10.1%**. A twist: in Finance and HR nearly every task defines every kind of check (190 of 200 have a "must not" check; 192 of 200 a content check), so the property selects almost the whole gate. **The targeting therefore happens at the check level:** the rule scores only the targeted kind's checks, on every gate task that has them. The regression set is usually empty, so guard (2) falls back to the whole gate.

**A5: power** (from the pilot's real gate runs, version 0 vs fix A, replayed so every check's result is known; all 40 tasks reproduced exactly). Fix A's +6.7 points showed up mainly in **wrong-content** checks. How often the rule would keep it, by resampling tasks (temperature 0.7, as in the pilot):

| Gate tasks | Redesigned rule, fix targeted at the right kind | Redesigned rule, wrong kind named | Pilot's rule |
|---|---|---|---|
| 40 | 46–47% | 0–3% | 38–39% |
| 60 | 56% | — | 48% |

**What this means:** the redesign helps, but only if the editor names the right target, and at temperature 0.7 it is still underpowered for a gain this size. Temperature 0 should raise these numbers (they include run-to-run noise it removes); the temperature-0 re-checks measure by how much. If power is still low, the next levers are more gate tasks per round or two repeats per version.

## Temperature-0 re-checks (2026-10-08, complete; $7.84)

**Temperature 0 does not make MiniMax repeatable.** The same task run twice at temperature 0 gave **identical tool calls in 0 of 10 tasks**, identical scores in 3, and an average score difference of **0.26** (hr:5005 scored 0.83, then 0.00). The likely causes are the provider's batched inference and the model's own reasoning tokens. **Change 1's assumption fails:** noise has to be handled by repeats (several runs per task per version), not by temperature. This also explains more of the pilot: one run per task carries roughly ±0.26 of luck.

**Comparison at temperature 0** (all 20 tasks; the run paused once on an OpenRouter 402 and resumed after a top-up): MiniMax 0.62 vs Gemini 0.70 credit, a difference of -0.07 (95% interval -0.21 to +0.06). **Still comparable** under the preregistered rule. Passes 4 vs 6; failed runs 0 vs 3; cost per run $0.057 vs $0.299. Data: `phase0/temperature0_rechecks.json`.

## What it costs

At the pilot's measured price ($0.03–0.055 per MiniMax run):

| Item | Runs | Cost |
|---|---|---|
| Determinism test (10 tasks × 2) | 20 | ≈ $1 |
| Re-check at temperature 0: MiniMax and Gemini on the 20 Phase 0 comparison tasks | 40 | ≈ $8 |
| Skill loop, per round: 30 practice + current version and 2 candidates on all 60 gate tasks | ≤ 210 | ≈ $6–10 |
| Skill loop, 4 rounds | | ≈ $25–40 |

Phase 1 overall stays at **≈ $100** (it was ≈ $90; the re-checks add ≈ $9).

## Why this matters beyond the experiment

The same three levels are what a business needs to trust an agent in production: **what was the outcome, which requirements were met, and how did it behave along the way.** They are also exactly what the Phase 2 observability UI should show: rounds → fixes → which checks and behaviours moved → kept or rejected.

## Questions for review

1. Temperature 0 for both agents in Phase 1 (with the two re-checks first)?
2. The keep rule's numbers: p < 0.10 on targeted checks; at most a 3-point drop on the regression set?
3. All 60 gate tasks per round (rather than 40)?
4. Any step measures to add to the initial list?
