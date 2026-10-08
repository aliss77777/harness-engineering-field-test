# Phase 1 design: MiniMax M3 + Jev vs Gemini 3.8 Flash on back-office tasks

**Written:** 2026-10-07 · **Approved in outline:** Alexander, 2026-10-07 · **Status:** design; the verdict rules go into code with tests and are committed before any Phase 1 paid run · **Supersedes:** the best-of-K Router and the Phase 1 experiment table in `Task Brief 7_V2_Business.md` (sections 2–3); the rest of that brief stands.

## The claim

> **MiniMax M3, an open-weight agent, plus a learned Jev checker matches Gemini 3.8 Flash on real Finance and HR tasks at about half the cost, and faster, because two things learn: the agent's playbook and the checker.**

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

1. **The Agent skill loop teaches MiniMax its playbook.** MiniMax's version 0 is the bench's own system prompt. Each round, MiniMax runs a fresh sample of practice tasks; an editor (Gemini 3.8 Flash) sees its failed runs, which checks they missed, and, where Gemini passed the same practice task, Gemini's run side by side (the teacher). It proposes **one** edit to MiniMax's skill file (for example, *"Read every policy email and reference sheet before acting; handle every item before you stop"*). The edit is kept only if MiniMax does better on held-out gate tasks.
2. **The Jev rubric loop teaches the checker what a correct MiniMax run looks like.** Jev answers weighted yes/no questions about each run summary (*"Did it read the AP guidelines before logging?"*, *"Did it skip the accounts on hold?"*). The editor sees runs Jev judged wrongly and proposes one rubric edit; weights are refitted from partial credit (v1's B+); the edit is kept only if Jev's judgments improve on gate.

**Same v1 rules throughout:** one edit per round; rejected edits shown to the editor and near-copies refused; a fresh mistake sample each round; a held-out gate decides; the sealed set is used once; the spend cap is in code; runs resume after any stop; preregistered verdicts in code with tests.

## Data and models

| | |
|---|---|
| **Tasks** | All 200 Finance + HR tasks. **Practice 60, gate 60, sealed 80**, stratified by domain (30/30, 30/30, 40/40), fixed seed. The 50 Phase 0 tasks go into practice and gate, never sealed. |
| **Cheap agent** | MiniMax M3, pinned to MiniMax's own host (fp8) |
| **Strong agent, editor** | Gemini 3.8 Flash, Google AI Studio standard tier |
| **Checker** | Jev 1.13 (`typesafe/jev-1.13`, TypeSafe), as in v1 |
| **Agent settings** | As Phase 0: temperature 0.7, reasoning effort medium, 50-step cap, the `api` toolset |
| **Leak rule** | Jev reads only the run summary (no grading checks). The skill-loop editor may see missed checks, **on practice tasks only**. |

## Experiments and preregistered verdicts

| Exp | Question | What runs | "Learned" / verdict rule |
|---|---|---|---|
| **V2-1 Controls** | Where do we start? | Sealed: MiniMax v0 skill, Gemini, 1 run each | — sets the frame (the starting gap) |
| **V2-2a Agent skill loop** | Does MiniMax learn its playbook? | 4 rounds: 30 practice runs + 2 candidate edits × 40 gate runs per round; final skill vs v0 on sealed | **Learned** if final beats v0 on sealed partial credit, paired one-sided Wilcoxon, p < 0.05 |
| **V2-2b Jev rubric loop** | Does the checker learn what a correct run is? | Rubric learned on MiniMax runs from practice and gate (labels: run "good" = partial credit ≥ 0.8) | **Learned** if the final rubric classifies sealed runs as good / not good better than the starting rubric, paired McNemar, p < 0.05 |
| **V2-3 Router (headline)** | As good as Gemini, cheaper and faster? | Sealed: MiniMax (final skill) once → Jev (final rubric) → keep, or Gemini does it. τ is the Jev score that escalates **30%** of gate runs, frozen before sealed | **Chef's kiss** if Router mean partial credit is within **±3 points** of Gemini alone (paired 95% interval) **and** cost per task ≤ **½** Gemini's; time per task reported |
| V2-4 Partial feedback | — | not run (out of budget) | — |

Notes:
- **Escalated tasks get fresh Gemini runs** (Alexander, 2026-10-07: no reuse of the baseline's runs).
- **Power is limited:** 80 sealed tasks can show differences of several points, not one or two. Stated up front.
- A **pass-rate** comparison (all checks met) is reported next to partial credit for every verdict.

## Budget

Costs per run from Phase 0: MiniMax $0.062, Gemini $0.32 (average of 20 business tasks). Rough.

| Item | Runs | Cost |
|---|---|---|
| Agent skill loop (MiniMax) | 4 × (30 + 2 × 40) = 440 | ≈ $27 |
| Teacher: Gemini on the 60 practice tasks | 60 | ≈ $19 |
| Jev learning data: MiniMax (final skill) on practice + gate (plus the skill loop's runs) | 120 | ≈ $7 |
| Sealed: MiniMax v0 + MiniMax final skill | 160 | ≈ $10 |
| Sealed: Gemini baseline | 80 | ≈ $26 |
| Sealed: fresh Gemini runs for escalated tasks (≈ 30%) | ≈ 24 | ≈ $8 |
| Jev scoring, editor and other small calls | — | ≈ $4 |
| **Total** | | **≈ $100** (range ≈ $70–140) |

**Proposed Phase 1 cap: $120, enforced in code**; stop and ask if a projection goes over.
