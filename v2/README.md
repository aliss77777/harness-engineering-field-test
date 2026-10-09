# v2: can an open-weight agent learn on the job?

> **Core question:** can a self-learning harness make an open-weight agent learn from its own mistakes, with Jev learning when to trust it, so the system matches Gemini Flash on real back-office work, cheaper and faster?

v1 showed on public benchmarks that a learned Jev rubric learns from outcomes and that routing matches an LLM for less ([v1 results](../v1/RESULTS.md)). v2 moves from predicting judgements to **doing real work**: the Finance and HR tasks in Zapier's AutomationBench, graded on whether the company's systems end up right.

**This page is the tracker** (status, plan, results, decisions). Details live in the linked documents; the dated log is [`PLAN.md`](PLAN.md).

## Roadmap (as of 2026-10-08)

*Phases here are v2's own: **v2 Phase 0** = feasibility, **v2 Phase 1** = the experiments, **v2 Phase 2** = the UI and tutorial. (v1 is the finished experiments 1–6 in [`../v1/`](../v1/README.md).)*

**Done so far: $18.38**

| Step | Result | Spent |
|---|---|---|
| v2 Phase 0: feasibility | Finance + HR chosen; MiniMax M3 picked as the cheap agent; its failures diagnosed | $9.41 |
| v2 Phase 1 pilot: 2 rounds of the skill loop | No fix kept, but every fix moved behaviour the right way | $8.97 |

**What didn't work, and what we learned**

| Didn't work | Lesson |
|---|---|
| Nemotron 3 Super: rate-limited at its host, 0 of 21 runs passed | Check a model's availability and basic competence on a few tasks before planning around it |
| DeepSeek V4 Pro: wandered until the 50-step cap | Same lesson; out after 20 tasks |
| Best-of-4 selection by Jev | Too expensive at MiniMax's price → a cascade (run once, keep or escalate) |
| v1's keep-or-reject test on long, noisy workflows | Too blunt for 40 tasks × 1 noisy run → telemetry at task, check and step level; temperature 0 |
| Harness bugs: empty replies scored as "done", cache replays, rules refused for length, summaries cut before "state changes" | Fixed, or fixing in V2-5 work item A |

**Next steps**

| # | Step | What it settles | Cost |
|---|---|---|---|
| 1 | **General harness improvements**: fixes A1–A5, plus the temperature-0 re-checks | A trustworthy harness for v2 Phase 1 | $0 + ≈ $9 |
| 2 | **Lock the skill loop redesign**: temperature 0, telemetry at task, check and step level, targeted tests | A test that can see real improvements | ≈ $0 |
| 3 | **Action masking (V2-5), optional**: replay past runs ($0) → simple gate off vs on (≤ $10) → Jev as the gate (≤ $20, only on Alexander's go) | Does a check before each write cut broken rules? | $0–30 |
| 4 | **Go/no-go for v2 Phase 1** and its cap (Alexander) | Whether to spend on the full experiments | — |
| 5 | **v2 Phase 1 experiments**: skill loop → Jev rubric loop → the sealed test, once | Does MiniMax learn? Does Jev learn when to trust it? Does the cascade match Gemini for less? | ≈ $100 |
| 6 | **Write-up**: results, story, insights | The claim, stated honestly | $0 |
| 7 | **v2 Phase 2**: Magic Patterns UI and tutorial (Substack) | Show it | $0 in model calls |

**How many tasks and runs action masking uses (step 3):**

| Step | Tasks | Runs | Notes |
|---|---|---|---|
| B: replay | MiniMax's past runs | 0 new runs | Re-checks the ≈ 300 logged runs, $0 |
| C: simple gate, off vs on | 60 gate tasks | 120 (60 off + 60 on) | MiniMax, starting prompt, temperature 0, one run each, paired by task. ≈ $5 (cap $10) |
| D: near-miss hooks | — | 0 | Code only |
| E: Jev gate (optional) | the same 60 gate tasks | mostly replay of logged runs, plus up to 60 new gate-on runs | Cap $20; only on Alexander's go |
| *Pre-registered, not run:* final playbook, gate off vs on | 80 sealed tasks | 80 extra gate-on runs | Only if Alexander releases the sealed set |

The core test (C) is 60 tasks, run once with and once without the gate: 120 runs, a mechanism test reported with paired intervals and no significance claim. Step 3 is optional and doesn't block step 5. The temperature-0 re-checks in step 1 are separate: 60 runs (20 repeatability, 40 MiniMax vs Gemini).

≈ $110–140 more to the end of the v2 Phase 1 experiments (depending on step 3).

**Waiting on Alexander:** approve the ≈ $9 temperature-0 re-checks and the optional action-masking caps (≤ $30) · confirm the replay's go/stop thresholds before results · label emails on the A2 sheet when it's ready. Step-by-step V2-5 plan: [below](#v2-5-action-masking-plan-and-costs).

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
| **V2-3 Router (headline)** | As good as Gemini, at ≤ ½ the cost, faster? (measured gate-off) | ⬜ |
| **V2-5 Action masking** | Does a check before each write cut broken rules without costing credit? | ▶️ starting ([brief](briefs/BRIEF-v2-action-masking-v1.md)) |

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
| Agent skill loop | In; redesign drafted (multi-level telemetry), [review pending](briefs/Skill%20loop%20redesign.md) |
| Action masking (V2-5) | ✅ In scope (2026-10-08). Gate may read company data, never grading checks or `meta`. Headline stays gate-off |
| Sealed set | Held: untouched until Alexander releases it |
[line omitted from the public copy]

How each decision was reached: [`JOURNEY.md`](JOURNEY.md); dates and detail: [`PLAN.md`](PLAN.md).

## Budget

| | Estimate | Cap |
|---|---|---|
| Phase 0 | spent **$9.41** | $25 |
| Phase 1 pilot (2 skill-loop rounds) | spent **$8.97** | $20 |
| **V2-5 action masking** (plan below) | ≤ **$40** | $40, pending approval |
| Phase 1, full design (incl. redesigned skill loop) | ≈ $100 (range ≈ $60–125) | to be set at go/no-go |

Caps are enforced in code: a run stops before it would pass its cap. Per-item estimates: [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md#budget).

## V2-5 action masking: plan and costs

*From [`briefs/BRIEF-v2-action-masking-v1.md`](briefs/BRIEF-v2-action-masking-v1.md), revised 2026-10-08. Each step is reported before the next starts.*

| Step | What it does | Cost | Status |
|---|---|---|---|
| **A1** | Keep the "state changes" section when long run summaries are trimmed (today it is cut first) | $0 | next |
| **A2** | Better behaviour measures: "read the policy before the first write"; check the policy-email detector against Alexander's email labels | $0 (+ ≈ 20 min of labelling) | ⬜ |
| **A3** | Let repeated runs bypass the cache, so repeats are independent | $0 | ⬜ |
| **A4** | Pick each fix's test tasks by a task property, not by past failure | $0 | ⬜ |
| **A5** | Estimate how often the redesigned test would keep a +6.7-point fix (from the pilot's logs) | $0 | ⬜ |
| **B** | **Replay past runs:** would a "read the policies first" check have flagged the runs that broke rules? Go/stop thresholds set before looking | $0 | ⬜ |
| Re-checks | Is temperature 0 repeatable? MiniMax vs Gemini again at temperature 0 | ≈ $9 | needs approval |
| **C (V2-5a)** | Build the gate; MiniMax on the 60 gate tasks with the gate off vs on. Success = fewer broken rules, credit doesn't fall, few holds | ≤ $10 | needs approval |
| **D** | Near-misses shown to the editor; holds per 100 runs by round | ≈ $0 | ⬜ |
| E (optional) | Jev as the gate, with learned yes/no questions | ≤ $20 | only on Alexander's go |
| **Total** | | **≤ $40** (≈ $19 without E) | |

The sealed set is not touched. The headline and the learning claim stay gate-off.

## Documents

| Document | What it holds |
|---|---|
| [`briefs/Phase 1 design.md`](briefs/Phase%201%20design.md) | The current design: claim, loops, data, experiments, verdict rules, budget |
| [`briefs/Skill loop redesign.md`](briefs/Skill%20loop%20redesign.md) | Draft after the pilot: multi-level telemetry and a new keep rule for long, noisy workflows |
| [`briefs/BRIEF-v2-action-masking-v1.md`](briefs/BRIEF-v2-action-masking-v1.md) | V2-5: a check before each write (action masking), plus the harness fixes it depends on |
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
