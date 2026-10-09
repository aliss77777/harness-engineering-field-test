# How v2 got here: the initial plan, the setbacks, and what changed

The dated log is [`PLAN.md`](PLAN.md); this page tells the story of Phase 0 (2026-10-05 to 2026-10-07) in order, with the evidence for each turn. Phase 0 spent **$9.41**.

## At a glance

| # | We planned | What happened | What changed |
|---|---|---|---|
| 1 | Test on Support + Sales tasks | A domain analysis showed back-office work lives in Finance and HR | **Finance + HR** ([DOMAINS](phase0/DOMAINS.md)) |
| 2 | A frontier model as the "strong agent" | Not approved: too expensive | **Gemini 3.8 Flash** (v1's model) is the strong agent |
| 3 | A 3-model, 20-task bake-off | 20 tasks can't separate models on quality | A 2-model **comparability check** on 50 tasks |
| 4 | The comparability check at ≈ $5 | The smoke test: one Gemini business task cost $0.48, so the check projected to ≈ $25 | Fold Gemini's comparison into Phase 1; **screen Nemotron alone** |
| 5 | Nemotron 3 Super as the cheap agent | **Rate-limited** at its only full-precision host, and **0 passes in 21 runs** | Nemotron out |
| 6 | Find another open-weight model | MiniMax M3 matched Gemini on credit at ≈ 1/5 the cost; DeepSeek V4 Pro didn't | **MiniMax M3** is the cheap agent |
| 7 | Best-of-4 selection by Jev | At MiniMax's price, 4 runs + escalation cost more than Gemini alone | A **cascade**: MiniMax once, Jev keeps or escalates |
| 8 | The agent skill loop as optional | A checker alone can't reach half cost; MiniMax's failures are systematic | The **skill loop is back**, with MiniMax editing itself |

## 1. The initial plan

[Task Brief 7](briefs/Task%20Brief%207_V2_Business.md) (2026-10-05): run v1's winning harness on Zapier's AutomationBench; a cheap agent runs each task **K times**; Jev picks the best run or escalates to a **frontier-model** strong agent; suggested domains **Support + Sales**; Phase 0 to cost ≤ $10.

## 2. Domains: Support + Sales → Finance + HR

The deciding criterion became internal back-office work, where automation cuts cost. Profiling all 600 business tasks ([DOMAINS](phase0/DOMAINS.md)) showed Finance and HR almost never touch sales or marketing systems, send 76% and 91% of their graded emails to internal staff, and grade judgement heavily (29% and 42% "must not" checks). Support was customer-facing with 32 checks per task; Sales and Marketing are go-to-market.

## 3. Models: no frontier model; Gemini as the bar

A frontier strong agent was never approved. v1 ran entirely on Gemini 3.8 Flash, so Gemini became the strong agent and the bar to match, and the focus became an **open-weight agent plus Jev against Gemini Flash**.

## 4. From bake-off to comparability check to Nemotron screen

- The first idea was a 3-model bake-off on 20 tasks. Twenty tasks with one run each can't separate models (one task is 5 points of pass rate), so it became a **comparability check**: Gemini vs Nemotron 3 Super on 50 tasks, with a rule fixed in advance (Nemotron within 10 points of Gemini's credit, under 10% failed runs).
- **The smoke test** (2 tasks per model, $0.52) proved the plumbing and found two bugs: empty provider replies were scored as "agent finished" (now retried), and reruns couldn't replay cached calls because the simulator stamps times and random IDs (now resumed by whole runs). It also priced Gemini at **$0.48** for one business task, so the 50-task check projected to ≈ $25, over the cap.
- The Gemini half of the check was folded into Phase 1, and Phase 0 would **screen Nemotron alone**: 4 runs on each of the 50 tasks, ≈ $4.

## 5. The Nemotron setback

**The API problem.** Nemotron 3 Super was pinned to DeepInfra, its only full-precision host. Through OpenRouter's shared capacity, more than half the calls came back HTTP 429, *"temporarily rate-limited upstream … add your own key."* The screen stopped twice when retries ran out, even at 2 parallel runs, after **19 of 200 runs**. The fix was a bring-your-own DeepInfra key, but by then the quality question mattered more.

**It seemed to act "dumb".** It passed **0 of 21 runs**. A Gemini reference on the same 6 Finance tasks passed 3 ([FEASIBILITY](phase0/FEASIBILITY.md#gemini-reference-on-the-screened-tasks-2026-10-07-167)), which proved our setup was not the problem:

| Same 6 Finance tasks | Gemini 3.8 Flash | Nemotron 3 Super |
|---|---|---|
| Passes | 3 of 6 | **0 of 21 runs** (incl. one smoke-test rerun) |
| Mean partial credit | 0.62 | 0.20 (best run per task: 0.36) |
| Cost per run | $0.36 | $0.033 |

A free check-by-check replay of its runs (added 2026-10-07) shows **how** it failed. It mostly *under-acted*:

| | Gemini | MiniMax M3 | DeepSeek V4 Pro | **Nemotron 3 Super** |
|---|---|---|---|---|
| Read every policy email | 12 of 12 | 4 of 13 | 7 of 13 | **0 of 21** |
| Missed checks that were required actions never taken | 51% | 35% | 62% | **67%** |
| Record-changing actions per run | 6.5 | 6.8 | 6.7 | **4.4** |
| Tool calls returning an error | 9% | 8% | 32% | 14% |

**Why remains unknown.** It never read the policy emails, did a third fewer of the actions the tasks required, and stopped early. The settings were identical for every model and it ran at full precision (bf16), so the likeliest explanation is the model's capability on long, multi-step tool use (it is a 120B mixture-of-experts with 12B active parameters). We did not test other settings (for example, a higher reasoning effort) because it was rate-limited and far behind.

## 6. MiniMax M3 found

One run on each of 20 tasks (10 Finance, 10 HR) for three models ([FEASIBILITY](phase0/FEASIBILITY.md#three-model-comparison-2026-10-07)):

| | Gemini 3.8 Flash | **MiniMax M3** | DeepSeek V4 Pro |
|---|---|---|---|
| Mean partial credit | 0.66 | **0.58** (−0.08; 95% interval −0.29 to +0.14) | 0.21 |
| Passes | 9 of 20 | 4 of 20 | 1 of 20 |
| Failed runs (step cap, errors) | 4 | **1** | 8 |
| Cost / time per run | $0.32 / 266 s | **$0.062 / 129 s** | $0.048 / 443 s |
| Comparability rule | reference | ✅ comparable | ❌ |

MiniMax was adopted. The free diagnosis showed its failures are **systematic**: it read every policy email in only 4 of 13 runs, and when it skipped them its credit was 0.41 with 0 passes and 11 broken "must not" rules (0.55, 1 pass and 2 broken when it read them all).

## 7. Best-of-K → cascade

At $0.062 per MiniMax run, four runs plus escalating 40% of tasks to Gemini cost ≈ $0.38 per task, more than Gemini alone ($0.32). So the Router became a **cascade**, v1's experiment 5 carried over to agents: MiniMax runs once, Jev keeps the runs it is confident in, Gemini does the rest. Route, don't vote.

## 8. The skill loop comes back, and MiniMax edits itself

A cascade at half cost must keep MiniMax's result on ≈ 70% of tasks, more than its quality supports today. A checker can choose which runs to trust but can't make them better, so the **Agent skill loop** came back. Two decisions shaped it:

- **No learning from Gemini.** A "Gemini as teacher" step was proposed and removed: MiniMax learns only from its own graded mistakes.
- **MiniMax is the editor** in both loops, after weighing the pros and cons: a cleaner claim (the gains are the loop's, not a stronger model's), the closest match to v1's self-editing loop, and a deployment story where one open-weight model improves itself on the company's own infrastructure. The risk, weaker fixes, is bounded by the keep-or-reject test.

The result is the [Phase 1 design](briefs/Phase%201%20design.md), now being piloted.
