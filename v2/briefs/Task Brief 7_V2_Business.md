# Task #7 brief: v2 — the winning harness on real business tasks, plus a Magic Patterns observability UI

[line omitted from the public copy]

---

## 0. One-paragraph summary

v1 showed, on public benchmarks, that a **learned yes/no rubric (answered by Jev)** learns from outcomes when an LLM doesn't, and that **routing** gives LLM-level quality at less than half the cost: Jev decides the confident cases and the LLM takes the close calls. v2 asks whether that holds on **real business work**: the 600 graded workflow tasks in Zapier's **AutomationBench** (Sales, Marketing, Operations, Support, Finance, HR). Then v2 turns the whole thing into a **Magic Patterns observability UI** and a tutorial. The UI is only as good as the story in the repo, so the repo's documentation is a first-class deliverable, written to a strict, parallel structure the UI can mirror.

---

## 1. Dataset choice

| | **AutomationBench** (zapier/AutomationBench) | **marketingskills** (coreyhaines31/marketingskills) |
|---|---|---|
| What it is | 600 public business-workflow tasks (100 per domain) plus 200 "simple" tasks, run in a simulated environment of 47 SaaS tools | 60+ markdown skill files (frameworks and workflows for marketing work), MIT licence |
| Real, graded outcomes? | **Yes.** Each task is checked by assertions on the final state: `partial_credit` (0–1, the share of assertions met) and `task_completed_correctly` (pass/fail) | **No.** A skill library, not a benchmark |
| Role in v2 | **The dataset**, our new "real outcomes" | **Optional version-0 knowledge:** a starting skill file for the Marketing domain (see V2-2 variant) |

**Decision: AutomationBench**, with marketingskills as an optional seed. Before Phase 1, confirm AutomationBench's licence and terms; its README does not state a licence.

**Why AutomationBench fits the harness:**
- `partial_credit` is a dense reward, and pass/fail is the outcome; together they are the "Upworthy clicks / Arena votes" of v2.
- The simulator lets us **grade any candidate run independently**. That gives full feedback (supervised, as in experiment 5) and the option to reveal only the chosen candidate's grade (partial feedback, as in experiment 6).
- It is new and business-shaped, so memorization risk is lower than for Upworthy or Arena.

---

## 2. The key design move: from one decision to a workflow

v1 tested **one decision step** (pick the better response or headline). AutomationBench tasks are **multi-step tool-using workflows**. The winning v1 pattern carries over as a **candidate-selection and escalation** step around an agent:

```
task ──► cheap agent runs it K times (K candidate runs, in the simulator)
            │
            ▼
      Jev rubric scores each run (yes/no questions about the run's actions and final state, weighted)
            │
     confident? ──yes──► keep Jev's top-scoring run
            │no
            ▼
      escalate: an LLM decides (option A: an LLM judge picks among the K runs;
                                option B: a strong agent re-runs the task)
            │
            ▼
      graded by AutomationBench's assertions (partial credit, pass/fail)
```

What carries over from v1, one-to-one:

| v1 | v2 |
|---|---|
| Pair of responses or headlines | K candidate runs of one task |
| Jev rubric question ("Does it follow the request?") | Jev rubric question about a run ("Did it update the CRM record named in the trigger?", "Did it notify the right channel?") |
| Fitted weights (B+) | Fitted weights, from partial credit |
| Router: Jev decides confident pairs, the LLM the close calls | Router: Jev keeps confident runs; escalates the rest to an LLM judge or a strong agent |
| Winner / clicks | Assertion-based `partial_credit` and pass/fail |
| LLM loop (instructions learn) | **Agent skill loop:** the agent's skill/instruction file learns |

**What the rubric reads:** a compact, deterministic **run summary** for each candidate: the trigger, the tool calls made (names and key arguments), and a diff of the final state. Never the hidden assertions or expected state (leak check, as in experiment 6).

---

## 3. Phases

### Phase 0 — Feasibility spike (≈ ½ day, ≤ $10). Go/no-go for everything else

1. Install AutomationBench; run a cheap agent on 20 tasks from the "simple" domain and 20 from one business domain.
2. Measure **cost and time per run**, and the cheap and strong models' pass rates.
3. Confirm we can: (a) run K independent candidates per task; (b) grade each one; (c) export a run summary that contains no assertion text; (d) plug in our own agent loop or wrap theirs (their README does not document custom agents, so check the code).
4. **Go if:**
   - the cheap agent passes 20–80% of tasks (so selection has room to matter);
   - candidates differ (at least 30% of tasks have mixed pass/fail across K);
   - the projected Phase 1 cost fits the cap.
5. **Choose the domains:** start with **two** domains where the outcome is a clear decision (suggested: **Support**, which covers ticket routing and SLAs, and **Sales**, which covers CRM and leads). Use the full set of 6 only if cost allows.
6. **If K-run generation is too expensive,** fall back to the 200 "simple" tasks (one or two steps), which behave like v1's decisions.

Deliverable: `phase0/FEASIBILITY.md` with the numbers and the go/no-go call, committed.

### Phase 1 — Repeat the experiment on new data (preregistered, same rigour as v1)

Splits are **by task, stratified by domain**:

| Set | Size (2 domains) | Use |
|---|---|---|
| Practice | 60 tasks (×K runs) | learning signal for both loops |
| Gate | 60 tasks | keep or reject edits; set τ |
| Sealed | 80 tasks | once, at the end |

Report sets in **tasks and runs**. 200 tasks is small, so primary tests use **paired, continuous `partial_credit`** (Wilcoxon), with pass rate reported alongside. State the power limit up front: with these sizes, only differences of several points are detectable.

| Exp | Question | Arms | Preregistered chef's kiss |
|---|---|---|---|
| **V2-1 Controls** | How much room is there? | cheap agent (first run) · cheap best-of-K by random pick · **oracle best-of-K** · strong agent | — (sets the frame: random → oracle gap, and cheap → strong gap) |
| **V2-2 Learning** | Does each loop learn on business tasks? | **Jev rubric loop** (weighted B+ style: picks the best of K; editor plus single-edit gate) · **agent skill loop** (the agent's skill file learns; LLM editor; gate on pass rate and credit) | Final beats its own start on sealed (p < 0.05); reports whether v1's "the rubric learns, the LLM doesn't" replicates |
| **V2-3 Router (headline)** | Does routing keep strong-agent quality for less? | **Router:** Jev keeps confident runs, escalates the rest (τ frozen on gate; 40% escalation budget) vs **strong agent alone** | Router within **±3 points** of the strong agent on partial credit **and** ≤ **½ its cost** (interval centred near zero, as in experiment 5) |
| **V2-4 Partial feedback** *(optional)* | Does it still learn without an answer key? | as V2-2, but loops see only the **chosen** run's grade | Jev rubric learns (p < 0.05); router stays in the margin |

**Variant (cheap, optional):** seed the agent skill loop's version 0 in the **Marketing** domain with a relevant `marketingskills` skill file instead of an LLM-written one. Does expert-written starting knowledge learn faster?

**Carry over every v1 harness lesson** (`RESULTS.md` → "What the harness taught us"):
- single-edit updates;
- rejected edits shown to the editor, near-copies refused;
- fresh mistake sample each round;
- held-out gate, then sealed once;
- fitted weights;
- route, don't vote;
- provider-refusal rule;
- spend cap in code;
- concurrency, with results independent of it;
- BYOK;
- the supervisor that resumes from cache;
- fail loudly on 402 errors and model-route changes;
- read data as text.

Preregister each experiment's verdict rules in code, with tests, before its paid run.

**Budget:** set the cap after Phase 0 measures cost per run. Placeholder: **$60 total**, enforced in code. Get Alexander's approval before Phase 1's paid runs.

### Phase 2 — The Magic Patterns observability UI and the tutorial

The build itself is easy (connect the GitHub repo and give Magic Patterns one prompt). **Quality comes from the repo's story.** Phase 2 has three steps.

**2a. Harden the story in the repo** (before touching Magic Patterns):
- `STORY.md` plus a machine-readable `story/insights.yaml` (section 5): 3–5 insights, each with a fixed ID, a **one-sentence headline used verbatim everywhere**, its key number, and the experiments that support it.
- Every experiment README follows the template in section 4, and its first section repeats the exact headline sentence(s) of the insight(s) it supports.
- `scripts/export_ui_data.py` writes `ui-data/*.json` (insights, experiments, metrics, learning histories, costs) **from the results files**. The UI reads these files and never hand-copies numbers. *(The v1 demo hardcoded numbers into TypeScript; that is how stories drift.)*
- A glossary with one name per concept, used everywhere: "Agent skill loop", "Jev rubric loop", "Router", "Strong agent", "Cheap agent", "Sealed set", "Learned?".

**2b. Build with Magic Patterns:** connect the repo; use the prompt in section 6. Iterate in at most 3 rounds, each one judged against the UI checklist in section 6.

**2c. The tutorial** (`tutorial/` chapters; see section 7): document each step with screenshots, the exact prompts, what Magic Patterns produced, and what we changed and why.

---

## 4. Repo structure and documentation standards (`jev-loop-v2`)

Mirror this repo's rigour, but make the story easier to follow:

```
jev-loop-v2/
  README.md              ← story-first: the 3–5 insights (verbatim from insights.yaml), then how to run
  STORY.md               ← the narrative: question → approach → insights → caveats → next
  story/insights.yaml    ← single source of truth for headline sentences and key numbers
  RESULTS.md             ← one page: scorecard + learning table (same names as the UI)
  GLOSSARY.md            ← one name per concept
  PLAN.md                ← dated log of every decision, deviation and fix (like MVP Project Plan.md)
  briefs/                ← one brief per experiment, preregistration included
  phase0/FEASIBILITY.md
  experiments/<date>-<id>/
      README.md          ← fixed template (below), with front matter
      artifacts/ config/ splits/ telemetry/
  ui-data/*.json         ← generated by scripts/export_ui_data.py; never hand-edited
  scripts/ src/ tests/   ← harness code (ported from jev-test-poc), tests, supervisor
[line omitted from the public copy]
```

**Experiment README template (every experiment, same order, same headings):**

```markdown
---
id: v2-3
title: Router on business tasks
question: Does routing keep strong-agent quality for less?
verdict: same_quality_half_cost        # machine-readable
verdict_label: Same quality, half the cost
insights: [I2]                          # which STORY insights this supports
key_metrics: {router_credit: …, strong_credit: …, cost_ratio: …}
---
## Headline            ← the insight sentence(s), verbatim from insights.yaml
## The question        ← one paragraph, plain English
## What we did         ← setup in 5 bullets max; diagram link
## Result              ← one table; the verdict row that matched
## What was learned    ← kept edits, with before/after (rubric or skill diff)
## How sure are we     ← intervals, p-values, power, caveats
## Run integrity       ← preregistration commit, restarts, refusals, spend
## Files
```

---

## 5. Parallel storytelling (the directive for the docs and the UI)

The v1 demo is accurate but hard to follow. Its overview headline, panels and experiment pages each tell their own version of the story. v2 fixes this with **one story, told at two depths:**

1. **Insights first.** The overview states 3–5 **numbered insights**, each a one-sentence headline with one number (for example, *"I2 · Routing kept strong-agent quality at 45% of the cost."*). These sentences live in `story/insights.yaml` and nowhere else.
2. **Same words, deeper.** Each experiment page opens with the **exact same sentence(s)** for the insights it supports, tagged with the same IDs and colours, then goes deeper: question → what we did → result table → what was learned → how sure we are.
3. **Two-way links.** Each insight card on the overview links to its supporting experiments; each experiment page links back to its insight(s).
4. **Parallel structure.** Every experiment page uses the identical section order and component layout, so readers learn the page once.
5. **Consistent encoding.** One colour per system (Agent skill loop, Jev rubric loop, Router, Strong agent), the same everywhere. Names come from `GLOSSARY.md`, with no synonyms.
6. **Numbers come from data, not prose.** Every number in the UI comes from `ui-data/*.json`.
7. **Honesty is visible.** Caveats sit next to the claims they qualify, not in a footer. "Win with an asterisk" gets its own badge style.

Draft `story/insights.yaml` shape (fill after Phase 1):

```yaml
- id: I1
  headline: "The rubric learns on business tasks; the agent's skill file …"   # fill from results
  key_number: {label: "rubric gain on sealed tasks", value: "…"}
  experiments: [v2-2]
- id: I2
  headline: "Routing kept strong-agent quality at …% of the cost."
  key_number: {label: "partial credit, router vs strong agent", value: "…"}
  experiments: [v2-3]
```

---

## 6. Magic Patterns build prompt and UI checklist

**Prompt (Phase 2b, after the repo is connected):**

> Build an observability and insights UI for the self-learning agent harness experiments in this repository.
> Read `story/insights.yaml` and `GLOSSARY.md` first; they define the story and the names.
> Use only the data in `ui-data/*.json` for numbers.
> Overview page: show each insight from `insights.yaml` as a numbered card (ID, the headline sentence verbatim, its key number, links to its experiments); then the scorecard and the learning table from `ui-data`.
> Experiment pages: one per entry in `ui-data/experiments.json`; open with the exact headline sentence(s) of the insights the experiment supports (same IDs and colours as the overview), then the sections in this order: The question · What we did · Result · What was learned (rubric or skill diff) · How sure are we · Run integrity. Every experiment page has identical layout.
> Use one consistent colour per system from `GLOSSARY.md`. Put caveats next to the claims they qualify. Add a "learning loop" view per experiment showing rounds → candidate edits → gate decisions (kept/rejected) from the learning history.

**UI checklist (a pass needs every box):**
- [ ] Every overview insight sentence appears verbatim on its experiment page(s).
- [ ] No number in the UI that isn't in `ui-data`.
- [ ] Identical section order on every experiment page.
- [ ] One colour per system, consistent across pages and charts.
- [ ] Each insight card ↔ experiment page link works both ways.
- [ ] Caveats are visible beside the claims they qualify.
- [ ] A new reader can answer in under a minute: what was tested, what won, how sure we are, what it cost.

---

[line omitted from the public copy]

1. **The idea:** self-improving harnesses, and why observability matters (link the v1 results).
2. **The data:** AutomationBench, what a task and its grade look like.
3. **Running the harness:** Phase 0, then Phase 1, with the supervisor and live telemetry.
4. **Writing the repo for an AI UI builder:** insights.yaml, the template, generated ui-data. *This is the key lesson: structure the story before you prompt.*
5. **Building with Magic Patterns:** connect the repo, the prompt, the first output.
6. **Iterating on the story:** the checklist, what we changed and why (before/after screenshots).
7. **What the UI shows:** walking the insights from the overview down into one experiment.
8. **Takeaways and next steps.**

Each chapter gets a "you can copy this" box: the exact prompt, file or command.

---

## 8. Honest limits to state

- AutomationBench public tasks are not the official leaderboard's private held-out tasks; scores won't match it one-to-one.
- 200 tasks over 2 domains is small. Use paired partial-credit tests, and state the minimum detectable difference.
- Simulated SaaS environments, not live systems.
- The rubric reads a run summary; summary design is a new choice that can affect results. Freeze it in Phase 0, before Phase 1.
- "Jev" vs "a yes/no rubric" wording still applies until Loop C is run.

---

## 9. Decisions for Alexander (before Phase 1)

1. **Repo:** new `jev-loop-v2` (recommended, clean story) or a folder in this repo.
2. **Domains:** Support + Sales (recommended) or others, informed by Phase 0.
3. **Models:** the cheap agent (e.g. Gemini 3.8 Flash), the strong agent (a frontier model), and the escalation option (LLM judge among K runs, or strong-agent re-run). Phase 0 compares the cost of both.
4. **Budget cap**, after Phase 0's measured cost per run (placeholder $60).
[line omitted from the public copy]
