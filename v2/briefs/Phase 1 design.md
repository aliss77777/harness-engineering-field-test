# Phase 1 design: MiniMax M3 + Jev vs Gemini 3.8 Flash on back-office tasks

**Written:** 2026-10-07 · **Approved in outline:** Alexander, 2026-10-07 · **Status:** design; the verdict rules go into code with tests and are committed before any Phase 1 paid run · **Pending revision:** after the pilot, the skill loop's keep-or-reject test and editor inputs are being redesigned ([`Skill loop redesign.md`](Skill%20loop%20redesign.md), draft) · **Supersedes:** the best-of-K Router and the Phase 1 experiment table in `Task Brief 7_V2_Business.md` (sections 2–3); the rest of that brief stands.

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
| **Agent settings** | As Phase 0: temperature 0.7, reasoning effort medium, 50-step cap, the `api` toolset |
| **Leak rule** | Jev reads only the run summary (no grading checks). The skill-loop editor may see missed checks, **on practice tasks only**. |

## Experiments and preregistered verdicts

| Exp | Question | What runs | "Learned" / verdict rule |
|---|---|---|---|
| **V2-1 Controls** | Where do we start? | Sealed: MiniMax v0 skill, Gemini, 1 run each | — sets the frame (the starting gap) |
| **V2-2a Agent skill loop** | Does MiniMax learn its playbook? | 4 rounds: 30 practice runs, then the current version and 2 candidate edits on the same 40 test bench tasks per round; final skill vs v0 on sealed | **Learned** if final beats v0 on sealed partial credit, paired one-sided Wilcoxon, p < 0.05 |
| **V2-2b Jev rubric loop** | Does the checker learn what a correct run is? | Rubric learned on MiniMax runs from practice and test bench (labels: run "good" = partial credit ≥ 0.8) | **Learned** if the final rubric classifies sealed runs as good / not good better than the starting rubric, paired McNemar, p < 0.05 |
| **V2-3 Router (headline)** | As good as Gemini, cheaper and faster? **Measured checkpoint off**: action masking (V2-5) is reported as a separate cell, never blended in | Sealed: MiniMax (final skill) once → Jev (final rubric) → keep, or Gemini does it. τ is the Jev score that escalates **30%** of test bench runs, frozen before sealed | **Chef's kiss** if Router mean partial credit is within **±3 points** of Gemini alone (paired 95% interval) **and** cost per task ≤ **½** Gemini's; time per task reported |
| V2-4 Partial feedback | — | not run (out of budget) | — |

Notes:
- **Action masking (V2-5) is a core experiment** (Alexander, 2026-10-08: "the most important part"), reported as its own cell. **The headline and the learning claim stay checkpoint off** (2026-10-08). Gemini runs without a checkpoint, so any action-masking gain (V2-5, [`BRIEF-v2-action-masking-v1.md`](BRIEF-v2-action-masking-v1.md)) is reported on its own.
- **Escalated tasks get fresh Gemini runs** (Alexander, 2026-10-07: no reuse of the baseline's runs).
- **Power is limited:** 80 sealed tasks can show differences of several points, not one or two. Stated up front.
- A **pass-rate** comparison (all checks met) is reported next to partial credit for every verdict.

## Budget

Costs per run from Phase 0: MiniMax $0.062, Gemini $0.32 (average of 20 business tasks). Rough.

| Item | Runs | Cost |
|---|---|---|
| Agent skill loop (MiniMax): practice, current version on the test bench, 2 candidates on the test bench | 4 × (30 + 40 + 2 × 40) = 600 | ≈ $37 |
| Jev learning data: MiniMax (final skill) on practice + test bench (plus the skill loop's runs) | 120 | ≈ $7 |
| Sealed: MiniMax v0 + MiniMax final skill | 160 | ≈ $10 |
| Sealed: Gemini baseline | 80 | ≈ $26 |
| Sealed: fresh Gemini runs for escalated tasks (≈ 30%) | ≈ 24 | ≈ $8 |
| Jev scoring, editor and other small calls | — | ≈ $4 |
| **Total** | | **≈ $90** (range ≈ $60–125) |

**Proposed Phase 1 cap: $100, enforced in code**; stop and ask if a projection goes over.
