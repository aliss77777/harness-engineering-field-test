# Phase 1 design: MiniMax M3 + Jev vs Gemini 3.8 Flash on back-office tasks

> **The source of truth is now [`V2 Phase 1 Canonical Experiment Design.md`](V2%20Phase%201%20Canonical%20Experiment%20Design.md)** (2026-10-09). Where this page differs, the canonical design wins.
>
> **Takes (2026-10-10):** Take 1 used the p-value keep test; Take 2 uses the margin keep test (targeted change > 0, credit up by at least 0.02, passes not lower). Wherever this page says "keep-or-reject test" for the playbook, the canonical design's Takes section says which applies.

**Written:** 2026-10-07 · **Approved in outline:** Alexander, 2026-10-07 · **Status:** built and tested (78 tests); not yet run; waiting on `run.approved: true` · **Skill loop:** the post-pilot redesign ([`Skill loop redesign.md`](Skill%20loop%20redesign.md)) is built into `scripts/phase1_run.py` · **Supersedes:** the best-of-K Router and the Phase 1 experiment table in `Task Brief 7_V2_Business.md` (sections 2–3); the rest of that brief stands.

## The core question (revised 2026-10-07)

> **Can a self-learning harness make an open-weight agent learn from its own mistakes, with Jev learning when to trust it, so the system matches Gemini Flash on real back-office work, cheaper and faster?**

- **Learning first.** MiniMax M3 learns from its own graded mistakes; nobody shows it how. That is v1's learning loop applied to an agent doing real work.
- **Jev's role, precisely.** Jev does not coach MiniMax. It learns what a correct MiniMax run looks like, so the system knows **when to trust** MiniMax and when to hand the task to Gemini.
- **The business test.** The result must match Gemini 3.8 Flash on partial credit, at about half the cost and faster (V2-3).

**No learning from Gemini, and no Gemini judgement inside the loops** (Alexander, 2026-10-07). MiniMax writes its own fixes and Jev's rubric edits. Gemini appears only as the baseline and as the cascade's fallback. If it works, the claim is: *an open-weight model ran the work, improved itself, and learned when to ask for help.*

## Why this design (from Phase 0)

- **MiniMax M3 is close to Gemini on credit but finishes fewer tasks.** On 20 tasks: credit 0.58 vs 0.66, full passes 4 vs 9, at ≈ 1/5 of Gemini's cost per run ($0.062 vs $0.32) and ≈ 2× the speed.
- **Best-of-K doesn't pay at that price.** Four MiniMax runs plus escalating 40% to Gemini cost ≈ $0.38 per task, more than Gemini alone ($0.32). So the Router is a **cascade** instead, v1's experiment 5 carried over to agents: route, don't vote.
- **A checker alone can't close the gap; the agent has to improve too.** Half cost needs ≈ 70% of tasks kept on MiniMax, more than its quality supports today. MiniMax's failures are **systematic**: it skipped the policy emails in 9 of 13 runs (Gemini: 0 of 12) and broke ≈ 3× as many "must not" rules. That is a teachable behaviour, so the **Agent skill loop** comes back.

## How it works

```
                    ┌───────────────── learns: the Agent skill loop ─────────────────┐
                    ▼                                                                 │
task ──► MiniMax M3 runs it once (with its learned skill file) ──► run summary ──► Jev scores it with the learned rubric
                                                                                      │
                                                         confident it's right ──► keep MiniMax's result
                                                         not confident        ──► Gemini 3.8 Flash does the task
                                                                                      ▲
                                                                learns: the Jev rubric loop
```

**Two things learn:**

1. **The Agent skill loop: MiniMax learns from its own mistakes.** MiniMax's version 0 is the bench's own system prompt. Each round, MiniMax runs a fresh sample of practice tasks, then **MiniMax itself, acting as editor,** reads its failed runs and which checks they missed, and proposes **one** edit to its own skill file (for example, *"Read every policy email and reference sheet before acting; handle every item before you stop"*). The edit is kept only if MiniMax does better on held-out test bench tasks. This mirrors v1's LLM loop, where the model edited its own instructions.
2. **The Jev rubric loop: the checker learns when to trust MiniMax.** Jev answers weighted yes/no questions about each run summary (*"Did it read the AP guidelines before logging?"*, *"Did it skip the accounts on hold?"*). The rubric editor (**MiniMax**) sees runs Jev judged wrongly and proposes one rubric edit; weights are refitted from partial credit (v1's B+); the edit is kept only if Jev's judgments improve on the test bench.

**Why MiniMax edits both** (pros and cons weighed with Alexander, 2026-10-07): a clean claim (gains come from the loop, not from a stronger model's judgement); closest to v1's self-editing LLM loop; and a deployment story where one open-weight model does the work and improves itself, so business data can stay on the company's own infrastructure. The risk is weaker fixes: the same blind spot that skips policy emails may miss why it failed. That risk is bounded: the keep-or-reject test rejects bad edits, so the worst case is an honest "did not learn". The editor sees the exact missed checks, which makes the diagnosis largely mechanical.

**Same v1 rules throughout:** one edit per round; rejected edits shown to the editor and near-copies refused; a fresh mistake sample each round; a held-out keep-or-reject test decides; the sealed set is used once; the spend cap is in code; runs resume after any stop; preregistered verdicts in code with tests.

## Data and models

| | |
|---|---|
| **Tasks** | All 200 Finance + HR tasks. **Practice 60, test bench 60, sealed 80**, stratified by domain (30/30, 30/30, 40/40), fixed seed. The 50 Phase 0 tasks go into practice and test bench, never sealed. |
| **Cheap agent** | MiniMax M3, pinned to MiniMax's own host (fp8) |
| **Editor (both loops)** | MiniMax M3, same pinned host |
| **Strong agent** | Gemini 3.8 Flash, Google AI Studio standard tier: the baseline and the cascade's fallback only |
| **Checker** | Jev 1.13 (`typesafe/jev-1.13`, TypeSafe), as in v1 |
| **Agent settings** | As Phase 0 except temperature: agents (MiniMax, Gemini) at 0; the editor (MiniMax) at 0.7. Reasoning effort medium, 50-step cap, the `api` toolset |
| **Leak rule** | Jev reads only the run summary (no grading checks). The skill-loop editor may see missed checks, **on practice tasks only**. |

## Experiments and preregistered verdicts

| Exp | Question | What runs | "Learned" / verdict rule |
|---|---|---|---|
| **V2-1 Controls** | Where do we start? | Sealed: MiniMax starting playbook (checkpoint on) and Gemini alone, 1 run each | — sets the starting line |
| **V2-2a Agent skill loop** | Does MiniMax learn its playbook? | 4 rounds: 30 practice runs, then the current version and 2 candidate rules on all 60 test bench tasks per round; final skill vs v0 on sealed | **Learned** if final beats v0 on sealed partial credit, paired one-sided Wilcoxon, p < 0.05 |
| **V2-2b Jev rubric loop** | Does the checker learn what a correct run is? | Rubric learned on MiniMax runs from practice and test bench (labels: run "good" = partial credit ≥ 0.8) | **Learned** if the final rubric classifies sealed runs as good / not good better than the starting rubric, paired McNemar, p < 0.05 |
| **V2-3 Router (main comparison)** | As good as Gemini, cheaper and faster? **Main comparison, checkpoint on** (canonical design, 2026-10-09) | Sealed: MiniMax (final skill) once → Jev (final rubric) → keep, or Gemini does it. τ is the Jev score that escalates **30%** of test bench runs, frozen before sealed | **Reference lines (directional, not a pass/fail verdict):** router credit within **3 points** of Gemini alone and cost per task at most **½** Gemini's. We report the numbers, the paired 95% interval and how close they land; time per task reported |
| V2-4 Partial feedback | — | not run (out of budget) | — |

Notes:
- **Action masking (V2-5) is a core experiment** (Alexander, 2026-10-08). **The checkpoint is on for learning and for the final test, including the main comparison** (canonical design, 2026-10-09; reverses the 2026-10-08 checkpoint-off rule). Final-playbook checkpoint-off runs exist only to show what the checkpoint adds.
- **Escalated tasks get fresh Gemini runs** (Alexander, 2026-10-07: no reuse of the baseline's runs).
- **Power is limited:** 80 sealed tasks can show differences of several points, not one or two. Stated up front.
- A **pass-rate** comparison (all checks met) is reported next to partial credit for every verdict.

## Built for the run (2026-10-08; not yet run)

`scripts/phase1_run.py` runs v2 Phase 1 in five stages, each logged and resumable: **skill** (the Agent skill loop) → **jevdata** (MiniMax's final playbook on practice and the test bench) → **rubric** (the Jev rubric loop) → **tau** (the Router's threshold) → **sealed** (the final exam, once). Supporting code: the Jev client ported from v1 (`src/jevloop/jev.py`), the rubric and its loop (`rubric.py`), the cascade (`cascade.py`). An end-to-end dry run of all five stages against fake models passes (`tests/test_phase1_run_dry.py`).

**Decisions built in (Alexander, 2026-10-08):**
- **The checkpoint is on while MiniMax learns** (it is part of the harness); every hold reaches the editor as a near-miss.
- **The sealed exam (canonical design, 2026-10-09):** starting playbook and final playbook, both with the checkpoint on; the main comparison is the checkpoint-on router against Gemini alone; final playbook with the checkpoint off only for question 4 (what the checkpoint adds).
- **Jev's starting rubric** is 8 generic yes/no questions fixed in code (`STARTING_RUBRIC`); MiniMax edits them. A run counts as good at partial credit ≥ 0.8.
- **One run per task** everywhere (`runs_per_task: 1`; canonical design, 2026-10-09).

**Safety:** nothing paid runs until `run.approved: true` in `phase1/config_phase1.yaml`; the sealed stage also needs Alexander's `phase1/SEALED_RELEASE.md`; the spend cap is enforced in code.

**An honest note on the V2-3 rule:** "within ±3 points of Gemini" is checked on the point estimate, with the paired 95% interval reported next to it. Given MiniMax's run-to-run noise, 80 sealed tasks give an interval of roughly ±6 points, so the experiment can show the cascade is *close* to Gemini but cannot *prove* equivalence within 3 points.

## Budget

Costs per run from Phase 0: MiniMax $0.062, Gemini $0.32 (average of 20 business tasks). Rough. Run counts below are from `scripts/phase1_run.py` (re-counted 2026-10-09): the current version's test bench runs are reloaded from the previous round, not paid twice.

| Item | Runs | Cost |
|---|---|---|
| Agent skill loop (MiniMax, checkpoint on): practice 30 per round, 2 candidates on all 60 test bench tasks per round, plus the starting playbook on the test bench once | 4 × (30 + 2 × 60) + 60 = 660 | ≈ $40 |
| Jev learning data: final playbook on all 60 practice tasks (test bench runs are reloaded) | 60 | ≈ $4 |
| Sealed: MiniMax starting playbook (checkpoint on), final playbook (checkpoint on), final playbook (checkpoint off) | 240 | ≈ $14 |
| Sealed: Gemini alone | 80 | ≈ $26 |
| Sealed: Gemini redoes the tasks Jev doubts (≈ 30%) | ≈ 24 | ≈ $8 |
| Jev scoring, editor and other small calls | — | ≈ $2 |
| **Total** | | **≈ $94** (range ≈ $60–110) |

**Spend cap: $110** (Alexander, 2026-10-09), **enforced in code**; the run stops before a stage would pass it and asks.
