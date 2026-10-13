# Task #7 brief: v2 — the winning harness on real business tasks

**Written:** 2026-10-05 · **Owner:** Alexander · **Status:** design only; Phase 0 (feasibility) gates everything else · **Builds on:** experiments 1–6 in this repo (`RESULTS.md`, `experiments/COMPARISON.md`) · **Deliverables:** a new repo (`jev-loop-v2`), preregistered experiments on business tasks.

---

## 0. One-paragraph summary

v1 showed, on public benchmarks, that a **learned yes/no rubric (answered by Jev)** learns from outcomes when an LLM doesn't, and that **routing** gives LLM-level quality at less than half the cost: Jev decides the confident cases and the LLM takes the close calls. v2 asks whether that holds on **real business work**: the 600 graded workflow tasks in Zapier's **AutomationBench** (Sales, Marketing, Operations, Support, Finance, HR).

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
7. **Cheap-agent comparability check (revised 2026-10-06; replaces the 2026-10-05 bake-off):** before step 2's measurements, run Gemini 3.8 Flash and the open-weight Nemotron 3 Super (OpenRouter, one pinned provider) once each on the same 50 business tasks. Nemotron becomes the Cheap agent if its mean partial credit is within 10 points of Gemini's and under 10% of its runs fail; otherwise Gemini stays. This is a stability check, not a quality ranking. Protocol: `phase0/FEASIBILITY.md`.

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

### Phase 2 — Visualization and write-up

*Omitted from the public copy: a plan for a UI and tutorial; not part of the experiments. Section numbers are kept so references elsewhere still resolve.*
---

## 4 to 7. Repo structure, parallel storytelling, UI build prompt, tutorial outline

*Omitted from the public copy: plans for a UI and a tutorial; not part of the experiments. Section numbers are kept so references elsewhere still resolve.*

---

## 8. Honest limits to state

- AutomationBench public tasks are not the official leaderboard's private held-out tasks; scores won't match it one-to-one.
- 200 tasks over 2 domains is small. Use paired partial-credit tests, and state the minimum detectable difference.
- Simulated SaaS environments, not live systems.
- The rubric reads a run summary; summary design is a new choice that can affect results. Freeze it in Phase 0, before Phase 1.
- "Jev" vs "a yes/no rubric" wording still applies until Loop C is run.

---

## 9. Decisions

*Omitted from the public copy: pre-run decisions; the decisions actually taken are dated in `../PLAN.md`. Section numbers are kept so references elsewhere still resolve.*
