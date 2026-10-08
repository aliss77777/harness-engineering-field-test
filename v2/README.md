# v2: can an open-weight agent learn on the job?

> **Core question:** can a self-learning harness make an open-weight agent learn from its own mistakes, with Jev learning when to trust it, so the system matches Gemini Flash on real back-office work, cheaper and faster?

v1 showed on public benchmarks that a learned Jev rubric learns from outcomes and that routing matches an LLM for less ([v1 results](../v1/RESULTS.md)). v2 moves from predicting judgements to **doing real work**: the Finance and HR tasks in Zapier's AutomationBench, graded on whether the company's systems end up right.

**This page is the tracker** (status, plan, results, decisions). Details live in the linked documents; the dated log is [`PLAN.md`](PLAN.md).

## Status at a glance

*Updated 2026-10-07.*

| | |
|---|---|
| **Phase** | 0 (feasibility) done · **Phase 1 pilot done** (not a GO) |
| **Latest** | Pilot: **no fix kept in 2 rounds, but every candidate moved behaviour the right way** (fewer broken rules; the best fix +6.7 credit points). The gate is underpowered at 40 tasks × 1 run ([pilot report](phase1/pilot/README.md)) |
| **Next** | Alexander reviews the **[skill loop redesign](briefs/Skill%20loop%20redesign.md)** (multi-level telemetry: task, check, step; temperature 0; targeted tests + regression set), then the go/no-go for Phase 1 |
| **Spend** | Phase 0: $9.41 (cap $25) · Pilot: $8.97 (cap $20) |

## The experiment in one picture

```
                  ┌──────── learns: Agent skill loop (MiniMax edits its own playbook) ────────┐
                  ▼                                                                            │
task ──► MiniMax M3 runs it once ──► run summary ──► Jev scores it (learned rubric) ──► confident? ── yes ──► keep MiniMax's result
                                                              ▲                              │
                                learns: Jev rubric loop ──────┘                              no ──► Gemini 3.8 Flash does the task
```

- **The agent learns from its own mistakes.** MiniMax M3 (open weight) reads its graded failures on practice tasks and proposes one fix to its own playbook; a held-out gate keeps it only if it helps. No help from Gemini.
- **The checker learns when to trust it.** Jev's rubric learns what a correct MiniMax run looks like; MiniMax writes the rubric edits too.
- **Gemini 3.8 Flash is the bar and the fallback**, never a teacher or editor.
- **The test:** on 80 sealed tasks, the cascade must match Gemini's partial credit (±3 points) at ≤ ½ its cost, and be faster.

Full design and preregistered verdicts: [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md) · Why it looks like this: [`JOURNEY.md`](JOURNEY.md) · How it relates to v1: [`METHODOLOGY.md`](METHODOLOGY.md)

## Plan and progress

✅ done · ▶️ in progress · ⬜ not started

**Phase 0: feasibility** ([`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md))

| Step | Status | Result |
|---|---|---|
| Set up AutomationBench; build the harness | ✅ | MIT licence; 800 tasks load and grade; our agent loop drives the bench |
| Choose domains | ✅ | **Finance + HR**: core back-office work ([DOMAINS](phase0/DOMAINS.md)) |
| Choose the cheap agent | ✅ | **MiniMax M3**. Nemotron 3 Super (rate-limited, 0/21 passes) and DeepSeek V4 Pro out ([JOURNEY](JOURNEY.md)) |
| Diagnose the cheap agent's failures | ✅ | Systematic and teachable: skips policy emails, breaks "must not" rules |
| Design Phase 1 | ✅ | Cascade + two learning loops ([design](briefs/Phase%201%20design.md)) |
| Phase 1 pilot: 2 skill-loop rounds | ✅ | No fix kept; behaviour improved; gate underpowered ([report](phase1/pilot/README.md)) |
| Go/no-go | ⬜ | Recommendation so far: GO ([criteria](phase0/FEASIBILITY.md#gono-go-criteria)) |

**Phase 1: experiments** (200 tasks: practice 60, gate 60, sealed 80)

| Experiment | Question | Status |
|---|---|---|
| V2-1 Controls | Where do we start? MiniMax vs Gemini on sealed | ⬜ |
| V2-2a Agent skill loop | Does MiniMax learn from its own mistakes? | pilot done ([report](phase1/pilot/README.md)) |
| V2-2b Jev rubric loop | Does Jev learn when to trust MiniMax? | ⬜ |
| **V2-3 Router (headline)** | As good as Gemini, at ≤ ½ the cost, faster? | ⬜ |

**Phase 2: Magic Patterns UI and tutorial**: not started. The minimum bar is [`v1/ui-demo-2`](../v1/ui-demo-2/README.md); the scaffold is ready ([`story/`](story/insights.yaml), [`tutorial/`](tutorial/)).

## Key results so far

**Phase 0: three models, one run on each of 20 Finance + HR tasks**

| | Gemini 3.8 Flash | **MiniMax M3** | DeepSeek V4 Pro |
|---|---|---|---|
| Mean partial credit | 0.66 | **0.58** | 0.21 |
| Tasks fully passed | 9 | 4 | 1 |
| Cost per run | $0.32 | **$0.062 (≈ ⅕)** | $0.048 |
| Time per run | 266 s | **129 s (≈ 2× faster)** | 443 s |
| Comparable to Gemini? (preregistered rule) | — | ✅ | ❌ |

**Why MiniMax falls short:** it acts before reading the rules. It read every policy email in 4 of 13 runs (Gemini: 12 of 12) and broke about 3× as many "must not" rules. That is what the skill loop has to fix. Details: [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md) · Phase 0 story: [`JOURNEY.md`](JOURNEY.md)

**Phase 1 pilot (2 rounds, $8.97):** MiniMax's own fixes targeted its real failures, and all three cut broken "must not" checks (0.90 → 0.50–0.70 per run). The best fix raised credit by 6.7 points and pass rate from 15% to 25%, but **no fix passed the gate**: one run on each of 40 tasks can't confirm gains that size. Report: [`phase1/pilot/README.md`](phase1/pilot/README.md)

## Decisions

| Decision | Choice |
|---|---|
| Domains | Finance + HR |
| Cheap agent | MiniMax M3 (open weight), pinned to MiniMax's own host |
| Strong agent | Gemini 3.8 Flash: baseline and fallback only; no frontier model |
| Checker | Jev 1.13 (v1's model) |
| Router | A cascade (not best-of-K) |
| Editor in both loops | MiniMax M3: no Gemini judgement inside the loops |
| Agent skill loop | In, lean version (piloted; gate power to be decided) |
[line omitted from the public copy]

How each decision was reached: [`JOURNEY.md`](JOURNEY.md); dates and detail: [`PLAN.md`](PLAN.md).

## Budget

| | Estimate | Cap |
|---|---|---|
| Phase 0 | spent **$9.41** | $25 |
| Phase 1 pilot (2 skill-loop rounds) | spent **$8.97** | $20 |
| Phase 1, full design | ≈ $90 (range ≈ $60–125) | to be set at go/no-go |

Caps are enforced in code: a run stops before it would pass its cap. Per-item estimates: [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md#budget).

## Documents

| Document | What it holds |
|---|---|
| [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md) | The current design: claim, loops, data, experiments, verdict rules, budget |
| [`briefs/Skill loop redesign.md`](briefs/Skill%20loop%20redesign.md) | Draft after the pilot: multi-level telemetry and a new keep rule for long, noisy workflows |
| [`JOURNEY.md`](JOURNEY.md) | The initial plan and the setbacks (including Nemotron), and how the design changed |
| [`METHODOLOGY.md`](METHODOLOGY.md) | What changes from v1 and why; who does what |
| [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md) | Phase 0 measurements and the go/no-go |
| [`phase0/DOMAINS.md`](phase0/DOMAINS.md) | Anatomy of a task; why Finance + HR |
| [`PLAN.md`](PLAN.md) | Dated log of every decision, deviation and fix |
| [`GLOSSARY.md`](GLOSSARY.md) | One name per concept |
| [`briefs/Task Brief 7_V2_Business.md`](briefs/Task%20Brief%207_V2_Business.md) | The original v2 brief (partly superseded by the Phase 1 design) |
| [`STORY.md`](STORY.md), [`story/insights.yaml`](story/insights.yaml), [`RESULTS.md`](RESULTS.md) | The story and results pages, filled after Phase 1 |
| [`experiments/`](experiments/), [`ui-data/`](ui-data/), [`tutorial/`](tutorial/) | Experiment packages, UI data (generated), tutorial chapters |

## How to run

From inside `v2/`, with Python 3.13:

1. Download AutomationBench into `z-ignore/AutomationBench-main` (git-ignored).
2. `python3.13 -m venv .venv && .venv/bin/python -m pip install -e z-ignore/AutomationBench-main -r requirements.txt`
3. Tests (no model calls): `.venv/bin/python -m pytest -q`
4. Phase 0: `scripts/phase0.py` (`smoke`, `compare`, …) · free diagnosis: `scripts/diagnose_failures.py`
5. Phase 1 pilot: `scripts/phase1_pilot.py split` (free), then `run` (paid; capped)

Model calls need `OPENROUTER_KEY` in `v2/.env`. Harness code is in `src/jevloop/`; `bench.py` is the only module that touches AutomationBench.
