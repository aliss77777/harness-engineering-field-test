# v2: can an open-weight agent learn on the job?

> **Core question:** can a self-learning harness make an open-weight agent learn from its own mistakes, with Jev learning when to trust it, so the system matches Gemini Flash on real back-office work, cheaper and faster?

v1 showed on public benchmarks that a learned Jev rubric learns from outcomes and that routing matches an LLM for less ([v1 results](../v1/RESULTS.md)). v2 moves from predicting judgements to **doing real work**: the Finance and HR tasks in Zapier's AutomationBench, graded on whether the company's systems end up right.

**This page is the tracker** (status, plan, results, decisions). Details live in the linked documents; the dated log is [`PLAN.md`](PLAN.md).

⭐ **Read before quoting any result: [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md)**: how learning cascades, what was reused or changed after the fact, and what each result can and cannot support.

## Live status: v2 Phase 1, Take 2 is running

**Takes.** Phase 1 runs in numbered takes so results never get mixed up (terms in the [canonical design](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md#takes)). Always cite "Take N, round M" and the keep test.

| | **Take 1** | **Take 2** (now) |
|---|---|---|
| Started | 2026-10-09 23:22 UTC | 2026-10-10 01:15 UTC |
| Playbook keep test | **P-value keep test**: targeted failure kind clearly drops (p < 0.10) and credit does not fall | **Margin keep test**: targeted failure kind improves, credit up by at least 0.02, fully passed tasks not lower; no p-value |
| Status | Stopped after round 2; **no rule kept**; $16.15 | ▶️ round 2 of 4; stops after round 2 for a comparison |
| Files | `phase1/run/take1/`, `logs/phase1_run/take1/` | `phase1/run/take2/` |

⭐ **How learning cascades, what was reused, and what we can claim: [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md).**

**Why Take 2.** At 60 tasks and one run each, one run moves about 3 points by itself, so the p-value keep test could not see the 2 to 5 point gains Take 1's candidates showed. The change was adopted *after seeing* Take 1's rounds 1 and 2 (Alexander, 2026-10-10) and is recorded that way. The sealed exam, final vs starting playbook, is the judge either way. The Jev rubric test is unchanged.

**Approved by Alexander:** `run.approved: true`, spend cap **$110**, cumulative across takes ($16.15 spent in Take 1). The sealed exam stays locked until Alexander writes the release note.

✅ done · ▶️ running now · ⬜ waiting · 🔒 held for Alexander

| # | Stage | What it does in plain words | MiniMax runs (max) | Cost (est.) | Status |
|---|---|---|---|---|---|
| 1 | **skill** | MiniMax learns. 4 rounds: do 30 practice tasks, study its mistakes, propose 2 rules, test each on the 60 test bench tasks, keep the best one that passes the keep test | 660 (Take 2: round 1 reused, so ≈ 450 new) | $34.19 total ($10.45 in rounds 3 and 4) | ✅ Take 2 done: final playbook [R1a, R2x] |
| 2 | **jevdata** | Run the final playbook on all 60 practice tasks: the examples Jev learns from | 60 | ≈ $3 | ✅ |
| 3 | **rubric** | Jev learns. MiniMax edits Jev's yes/no questions over 3 rounds (McNemar test, unchanged) | 0 (about 840 Jev calls) | < $1 | ✅ 1 of 6 edits kept |
| 4 | **tau** | Set the cutoff (τ): lowest 30% of test bench runs would go to Gemini; then freeze it | 0 (60 Jev calls) | ≈ $0 | ✅ τ = 0.019 |
| 5 | **sealed** | The final exam, once: starting playbook, final playbook (checkpoint on and off), Gemini alone, the router, 80 tasks | 240 MiniMax + 80 Gemini + ≈ 24 Gemini redos | ≈ $45 | 🔒 held until the release note |

**Active now (15:25 UTC, 10 Oct): nothing is running; the Jev verifier (option D) was built and validated once. Waiting on Alexander.** The redesigned Jev (richer input, per-task questions written from the request and policy emails, learned question-writer instructions) reached within-playbook AUC **0.612** [0.51, 0.72] on 840 test bench runs against a pre-registered bar of 0.65: **not met**, but a clear improvement on the generic rubric (0.51); lowest-30% credit gap 0.166 (needs 0.10, met). On the final playbook's own 60 runs it shows no discrimination (0.48). It flags skipped actions (0.67) and wrong content (0.66), not broken rules (0.48). Details and next options: [`LEARNINGS_AND_IMPLICATIONS.md`](LEARNINGS_AND_IMPLICATIONS.md) Part B. **Follow-up noted in the memo: the Gemini ceiling check (≈ $17; needs Alexander's go).** The sealed exam has not been run. Uncommitted: the verifier code, tests and docs.

**Overnight plan (Alexander, 2026-10-10):** `scripts/overnight_phase1.py` waits for the replay, then adopts a replay winner **only if** it passed the margin keep test with test bench credit **+0.07 or more** and passes not lower (otherwise the playbook stays [R1a, R2x]), then runs **jevdata → rubric → tau** and stops. **It never runs the sealed exam;** that waits for Alexander's written release in the morning. It checks the OpenRouter balance before each stage and waits rather than failing halfway. Log: `logs/phase1_run/overnight.log`; the decision is saved as `phase1/run/take2/replay_decision.json`.

✅ **The OpenRouter key limit was raised from $150 to $300** (Alexander, 05:42 UTC). Account credit was $4.96 of $155 and relies on auto top-up as it is used.

| Overnight step | Status |
|---|---|
| Replay of length-refused rules (4 candidates) | ✅ none kept; playbook stays [R1a, R2x] |
| Adopt a winner only if +0.07 credit and passes not lower | ✅ none qualified |
| jevdata: final playbook on all 60 practice tasks | ✅ 0.727 credit, 19 passes |
| rubric: Jev learns (3 rounds) | ✅ 1 of 6 edits kept; no held-out skill (see above) |
| tau: cutoff set and frozen | ✅ tau = 0.019 (does not separate good from bad on the test bench) |
| Sealed exam | 🔒 held for Alexander's release |

**Take 1 results (rounds 1 and 2, p-value keep test, none kept).** Every candidate was tested against the starting playbook (no rules, checkpoint on): **0.62** credit, 11 of 60 passes on the test bench.

| Round | Candidate rule (short) | Targets | Credit | Passes | Targeted checks | P-value keep test | Margin keep test |
|---|---|---|---|---|---|---|---|
| 1 | R1a: do every required write action before declaring done | skipped action | 0.675 (+5.4) | 14 | +0.035, p 0.36 | rejected | **kept** (round 1 winner) |
| 1 | R1b: copy values exactly as in the source | wrong content | 0.641 (+2.1) | 17 | +0.022, p 0.34 | rejected | kept (not the winner) |
| 2 | R2a: when held, read the policies, then finish every queued write | skipped action | 0.659 (+3.9) | 17 | +0.032, p 0.31 | rejected | would keep (vs the starting playbook) |
| 2 | R2b: enumerate every named recipient | skipped action | 0.619 (−0.2) | 14 | −0.024, p 0.67 | rejected | rejected |

Caveat: the same starting playbook and checkpoint scored 0.65 on these 60 tasks in V2-5a, so one run's noise is about 3 points; gains of 2 to 5 points are close to that. Take 1 round 2's candidates were proposed against the starting playbook; Take 2's round 2 candidates are new, proposed against R1a.

**Take 2 results, rounds 1 and 2 (margin keep test).** Spend: $23.74 in total, $7.59 of it in Take 2.

| Round | Candidate rule (short) | Targets | Test bench credit | Passes | vs its baseline | Margin keep test |
|---|---|---|---|---|---|---|
| (baseline) | Starting playbook, no rules | | 0.620 | 11 | | |
| 1 | **R1a:** do every required write action before declaring done | skipped action | 0.675 | 14 | +5.4 points, +3 passes | **kept** |
| 1 | R1b: copy values exactly as in the source | wrong content | 0.641 | 17 | +2.1 points, +6 passes | kept, not the winner |
| 2 | **R2x:** before any write, read the latest policy and override emails | skipped action | **0.778** | **21** | **+10.3 vs R1a**, +7 passes | **kept** |
| 2 | R2y: summary emails get totals only, no names or per-record amounts | rule broken | 0.652 | 15 | −2.3 vs R1a, +1 pass | rejected: targeted +0.125 (p 0.125) but credit fell |
| 3 | R3a: a per-row flag (Include / Do Not Include) is binding for all outputs | wrong content | 0.751 | 23 | −2.7 vs [R1a, R2x], +2 passes | rejected: targeted −0.038, credit fell |
| 3 | R3b: enumerate every deliverable before a batch of writes, check the count before stopping | skipped action | 0.791 | 26 | +1.3 vs [R1a, R2x], **+5 passes** | rejected: targeted +0.022 but credit +1.3 is under the +0.02 margin |
| 4 | R4a: define deliverable scope only from sources that explicitly authorize each write; when ambiguous, do not write | rule broken | 0.746 | 22 | −3.2 vs [R1a, R2x], +1 pass | rejected: targeted +0.060 (p 0.25) but credit fell |

Baselines: round 1 against the starting playbook, round 2 against R1a (0.675, 14 passes), round 3 against [R1a, R2x] (0.778, 21 passes). **Rounds 3 and 4 kept nothing:** the playbook stays at 2 rules. ⚠️ Five proposals in rounds 3 and 4 hit the 600-character limit. Three were long drafts of ideas that were then tested shortened; one idea (a verbatim checklist for wrong content) was never tested, so round 4 tried only 1 candidate. The limit is now 1,200 characters and the refused rules are being replayed as written (post hoc); see caveat 9 and section 6 in [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md). R3b is the near miss (+5 passes, +1.3 points, inside the noise). **Playbook after round 2: [R1a, R2x], 0.778 credit and 21 of 60 passes on the test bench, against 0.620 and 11 for the starting playbook (+15.8 points).** That number is optimistic: both rules were picked on the same 60 tasks, each as the better of two candidates; a rough allowance for luck is about 4 points, so about +10 is a fairer reading. Only the sealed exam settles it.

**Take 1 vs Take 2, rounds 1 and 2:**

| | Take 1 (p-value keep test) | Take 2 (margin keep test) |
|---|---|---|
| Rules kept | 0 of 4 candidates | 2 of 4 (R1a, R2x) |
| Playbook after round 2 | empty | R1a + R2x |
| Test bench credit of the playbook | 0.620 (the starting playbook) | 0.778 (optimistic: selected on the test bench) |
| Fully passed | 11 of 60 | 21 of 60 |
| Spend | $16.15 | $7.59 more (round 1 reused) |

**Two things to note.** (1) R2x is the habit the checkpoint enforces ("read the policy emails before writing"): checkpoint holds fell from 0.75 to 0.15 per run, so MiniMax now does by itself what the checkpoint was holding it to. Question 4 (what the checkpoint adds) may come out small for that reason, which would be partly learning, not a failed checkpoint. (2) R2y shows the margin keep test still rejects rules that lower credit.

*Side observation, not a claim:* R1a on the same 30 practice tasks Take 1 used in round 2 (R1a was not selected on them): credit 0.664 vs 0.582 (+8.2 points), 11 vs 8 passes, 12 tasks better, 6 worse. 30 tasks, one run each, about 3 points of noise per run.

**How we follow it.** Take 2 output: `logs/phase1_run/take2-skill.stdout`; results as JSON in `phase1/run/take2/` (`skill_history.json`); spend in `results/phase1_run/spend.json`. A stop resumes without paying twice.

## Latest findings (as of 2026-10-08 22:00 MDT)

*Step numbers refer to "Next steps" in the roadmap below.*

**In plain words (ELI5).** We're teaching a cheap robot (MiniMax) to do office paperwork as well as an expensive one (Gemini).
- **We fixed our measuring tools** *(step 1)*. They had small bugs, like cutting off the most important part of each report.
- **The robot is moody** *(step 1)*. Give it the same job twice and it does it differently, even with the "be consistent" setting on. So we have to watch it do each job more than once before deciding it got better.
- **The cheap robot is still nearly as good as the expensive one** *(v2 Phase 0 and step 1)*, at about a fifth of the price.
- **Its main bad habit: it starts sending emails before reading the rulebook** *(v2 Phase 0; step 3)*. In its old work, the jobs where it skipped the rulebook were the ones where it broke rules more often.
- **We built a "read the rulebook first" bouncer** *(step 3)* into the harness and tested it live: **with it on, the robot broke about a quarter fewer rules and scored a little higher.** Promising, not yet proven. Sometimes the robot ignored the bouncer three times in a row. Our way of spotting which emails are "the rulebook" is still rough: it flags about twice as many emails as it should and misses about a quarter of the real ones.

**The deeper summary.**

| Finding | Step | Evidence | Why it matters |
|---|---|---|---|
| **MiniMax stays comparable to Gemini** | v2 Phase 0; step 1 (temperature-0 re-checks) | Two separate tests: 0.58 vs 0.66 credit (Phase 0) and 0.62 vs 0.70 at temperature 0 (−0.07; 95% range −0.21 to +0.06), at ≈ $0.06 vs $0.30 per run, with 0 failed MiniMax runs against Gemini's 3 | The cheap-and-open-weight premise holds |
| **Temperature 0 does not make MiniMax repeatable** | step 1 (temperature-0 re-checks) | Same task twice: identical tool calls in 0 of 10, scores differ by 0.26 on average | Noise must be handled with repeats, not settings; it also explains why the pilot couldn't keep any fix |
| **Choosing test tasks by past failure creates false wins** | step 1 (A4), used in step 2 | Simulated useless fix "kept" 77% of the time this way, vs 10% when tasks are chosen by a task property | The skill loop's test now picks tasks by property and scores the targeted checks |
| **The checkpoint's target habit is real** | step 3 (replay, B) | Replay of 236 MiniMax runs: runs that skipped the policy emails broke a rule 63% of the time vs 43% overall; the checkpoint would have caught 44% of rule-breaking runs | Worth testing live (V2-5a, running now) |
| **The checkpoint targets one habit, not all rule-breaking** | step 3 (replay, B) | Gemini always reads the policies first, yet still breaks a rule in 24% of runs | Other failure kinds need other fixes |
| **The checkpoint works, in a first live test** | step 3 (V2-5a) | 60 test bench tasks, off vs on: broken "must not" rules 0.88 → 0.67 per run (−0.22; 95% range −0.45 to +0.02); credit 0.57 → 0.65 (+0.08; −0.02 to +0.17); silent-wrong 82% → 42%; +12% cost ([report](action_masking/v2_5a/REPORT.md)) | Preregistered rule says keep; both ranges just touch zero, so promising, not proof |
| **Sometimes MiniMax ignores the checkpoint** | step 3 (V2-5a) | 7 runs hit the 3-hold limit without reading the policies | Instructions alone don't fix the habit; the skill loop or a stricter checkpoint may |
| **The policy-email detector is rough** | step 1 (A2), affects step 3 | Against 72 hand-labelled emails: precision 0.50, recall 0.73 ([results](action_masking/labels/RESULTS.md)) | The checkpoint wastes some steps on irrelevant emails and misses some real rules; a better detector is a next step |

**What the "read the policies first" checkpoint is:** a feature of our harness (`src/jevloop/monitor.py`), not of MiniMax or the benchmark. Before MiniMax changes any record, the checkpoint checks whether it has opened every policy email; if not, the action is held and MiniMax is told which emails to read. After 3 holds it lets actions through and logs it. Every hold is shown to the skill loop as a near-miss, so MiniMax can learn the habit. The headline result is measured with the checkpoint off.

**Observation (Alexander, 2026-10-08; not yet a decision):** the "read the policies first" checkpoint feels a little suspect for the comparison. If Gemini isn't given it, giving it to MiniMax risks cooking the books in favour of the cheaper model. *Context:* Gemini already reads the policies first on its own (in the replay the checkpoint would never have fired on it), and the headline is measured with the checkpoint off. The concern still applies to any result that pits MiniMax with the checkpoint against Gemini without it. To revisit after V2-5a.

**Not yet shown:** that the skill loop makes MiniMax itself better (it hasn't run with its new test), and that the checkpoint's gain survives more runs.

## Roadmap (as of 2026-10-08, evening)

*Phases here are v2's own: **v2 Phase 0** = feasibility, **v2 Phase 1** = the experiments, **v2 Phase 2** = the UI and tutorial. (v1 is the finished experiments 1–6 in [`../v1/`](../v1/README.md).)*

**Done so far: $32.12**

| Step | Result | Spent |
|---|---|---|
| v2 Phase 0: feasibility | Finance + HR chosen; MiniMax M3 picked as the cheap agent; its failures diagnosed | $9.41 |
| v2 Phase 1 pilot: 2 rounds of the skill loop | No fix kept, but every fix moved behaviour the right way | $8.97 |
| Step 1: harness fixes A1–A5 | Done: summaries keep state changes; read-policy-before-first-write; check kinds; A4 (choosing test tasks by past failure keeps useless fixes 77% of the time); A5 power | $0 |
| Step 1: temperature-0 re-checks | Done. **Temperature 0 is not repeatable** for MiniMax (0 of 10 identical runs). MiniMax still comparable to Gemini at temperature 0 (-0.07 credit) | $7.84 |
| Step 2: skill loop redesign | Built and tested (not yet run) | $0 |
| Step 3: replay (B) | **Go, narrowly**: the checkpoint would have caught runs that broke rules with 63% precision (base rate 43%), 44% recall ([report](action_masking/replay/REPORT.md)) | $0 |
| Step 1: email labels for the detector (A2) | Labelled by Claude in two passes (71 of 72 agreed): detector precision 0.50, recall 0.73, stays "approximate" | $0 |
| Step 3: checkpoint and near-miss hooks (C, D) | Built and tested (67 tests) | $0 |
| Build for v2 Phase 1 | Done: Jev client ported from v1, rubric loop, cascade, the five-stage run script; dry run of all stages passes (78 tests) | $0 |
| Step 3: **V2-5a, the checkpoint live (off vs on, 60 tasks)** | **Keep the checkpoint**: broken rules −0.22 per run, credit +0.08, holds 0.82/run; ranges just touch zero ([report](action_masking/v2_5a/REPORT.md)) | $5.90 |

**What didn't work, and what we learned**

| Didn't work | Lesson |
|---|---|
| Nemotron 3 Super: rate-limited at its host, 0 of 21 runs passed | Check a model's availability and basic competence on a few tasks before planning around it |
| DeepSeek V4 Pro: wandered until the 50-step cap | Same lesson; out after 20 tasks |
| Best-of-4 selection by Jev | Too expensive at MiniMax's price → a cascade (run once, keep or escalate) |
| v1's keep-or-reject test on long, noisy workflows | Too blunt for 40 tasks × 1 noisy run → telemetry at task, check and step level; temperature 0 |
| Harness bugs: empty replies scored as "done", cache replays, rules refused for length, summaries cut before "state changes" | Fixed |
| Temperature 0 to remove noise | Not repeatable through OpenRouter (0 of 10 identical runs; scores differ by 0.26 on average) → handle noise with repeats, not temperature |

**Next steps**

| # | Step | What it settles | Cost |
|---|---|---|---|
| 1 | **General harness improvements**: fixes A1–A5, plus the temperature-0 re-checks | A trustworthy harness for v2 Phase 1 | $0 + ≈ $9 |
| 2 | **Lock the skill loop redesign**: temperature 0, telemetry at task, check and step level, targeted tests | A test that can see real improvements | ≈ $0 |
| 3 | **Action masking (V2-5), core** (Alexander, 2026-10-08: "the most important part"): replay past runs ($0, done) → simple checkpoint off vs on (V2-5a, ≤ $10, **running**) → Jev as the checkpoint (≤ $20; **optional, skipped** by Alexander 2026-10-08) | Does a check before each write cut broken rules? | $0–30 |
| 4 | **Go/no-go for v2 Phase 1** and its cap (Alexander) | **Go, 2026-10-09; cap $110** | — |
| 5 | **v2 Phase 1 experiments**: skill loop → Jev rubric loop → the sealed test, once. **▶️ running** (see Live status) | Does MiniMax learn? Does Jev learn when to trust it? Does the cascade match Gemini for less? | ≈ $94 |
| 6 | **Write-up**: results, story, insights | The claim, stated honestly | $0 |
| 7 | **v2 Phase 2**: Magic Patterns UI and tutorial (Substack) | Show it | $0 in model calls |

**How many tasks and runs action masking uses (step 3):**

| Step | Tasks | Runs | Notes |
|---|---|---|---|
| B: replay | MiniMax's past runs | 0 new runs | Re-checks the ≈ 300 logged runs, $0 |
| C: simple checkpoint, off vs on | 60 test bench tasks | 120 (60 off + 60 on) | MiniMax, starting prompt, temperature 0, one run each, paired by task. ≈ $5 (cap $10) |
| D: near-miss hooks | — | 0 | Code only |
| E: Jev checkpoint (optional; skipped) | the same 60 test bench tasks | mostly replay of logged runs, plus up to 60 new checkpoint on runs | Cap $20; only on Alexander's go |
| *Pre-registered, not run:* final playbook, checkpoint off vs on | 80 sealed tasks | 80 extra checkpoint on runs | Only if Alexander releases the sealed set |

The core test (C) is 60 tasks, run once with and once without the checkpoint: 120 runs, a mechanism test reported with paired intervals and no significance claim. Action masking is a core part of v2 (Alexander, 2026-10-08); its results are reported as their own cell next to the checkpoint off headline. The temperature-0 re-checks in step 1 are separate: 60 runs (20 repeatability, 40 MiniMax vs Gemini).

≈ $110–140 more to the end of the v2 Phase 1 experiments (depending on step 3).

**Design source of truth: [`briefs/V2 Phase 1 Canonical Experiment Design.md`](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md)** (2026-10-09; checkpoint on for the final test too). Spend cap set: **$110**, a safety stop (Alexander, 2026-10-09); estimate ≈ $94 more. **Go given 2026-10-09:** the experiments are running (see Live status). **Waiting on Alexander:** the release note for the sealed exam, later.

## The experiment in one picture

```
                  ┌──────── learns: Agent skill loop (MiniMax edits its own playbook) ────────┐
                  ▼                                                                            │
task ──► MiniMax M3 runs it once ──► run summary ──► Jev scores it (learned rubric) ──► confident? ── yes ──► keep MiniMax's result
                                                              ▲                              │
                                learns: Jev rubric loop ──────┘                              no ──► Gemini 3.8 Flash does the task
```

- **The agent learns from its own mistakes.** MiniMax M3 (open weight) reads its graded failures on practice tasks and proposes one fix to its own playbook; a held-out keep-or-reject test keeps it only if it helps. No help from Gemini.
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
| Phase 1 pilot: 2 skill-loop rounds | ✅ | No fix kept; behaviour improved; keep-or-reject test underpowered ([report](phase1/pilot/README.md)) |
| Go/no-go | ⬜ | Recommendation so far: GO ([criteria](phase0/FEASIBILITY.md#gono-go-criteria)) |

**Phase 1: experiments** (200 tasks: practice 60, test bench 60, sealed 80)

| Experiment | Question | Status |
|---|---|---|
| V2-1 Controls | Where do we start? MiniMax vs Gemini on sealed | ⬜ |
| V2-2a Agent skill loop | Does MiniMax learn from its own mistakes? | pilot done ([report](phase1/pilot/README.md)); full run ▶️ started 2026-10-09 |
| V2-2b Jev rubric loop | Does Jev learn when to trust MiniMax? | ⬜ |
| **V2-3 Router (main comparison)** | Router (checkpoint on) vs Gemini alone: close on credit, about half the cost, faster? | ⬜ |
| **V2-5 Action masking** | Does a check before each write cut broken rules without costing credit? | ▶️ starting ([brief](briefs/BRIEF-v2-action-masking-v1.md)) |

**Phase 2: Magic Patterns UI and tutorial**: not started. The minimum bar is [`v1/ui-demo-2`](../v1/ui-demo-2/README.md); the scaffold is ready ([`story/`](story/insights.yaml), [`tutorial/`](tutorial/)).

## Key results so far

### Learning progress to date (Take 2, 2026-10-10 05:40 UTC)

**In one line:** the harness learned. On the test bench MiniMax went from 0.62 to 0.78 credit and from 11 to 21 fully passed tasks of 60, learning only from its own graded mistakes (no Gemini). How much of that holds on unseen tasks is still open: it is optimistic by roughly 4 points, so a fair reading is closer to +10 than +16.

| Step (60 test bench tasks, one run each, checkpoint on) | Playbook | Credit | Passes |
|---|---|---|---|
| Start | no rules | 0.620 | 11 |
| Round 1 | + R1a (do every required write before declaring done) | 0.675 | 14 |
| Round 2 | + R2x (read the latest policy and override emails before any write) | **0.778** | **21** |
| Rounds 3 and 4 | nothing kept (best near miss R3b: 0.791, 26 passes, +1.3 points, under the +0.02 margin) | | |
| Replay of the four length-refused rules (limit now 1,200 characters): **none kept** | 0.751 / 20 passes, 0.748 / 19, 0.770 / 23, 0.792 / 22 (all against 0.778 / 21) | | |

**Evidence beyond the test bench.**
- On the same 30 practice tasks, R1a (not selected on them) vs no rules: credit 0.58 to 0.66; missed checks 74 to 57 (wrong content 40 to 32, skipped actions 14 to 11, rules broken 20 to 14).
- R2x cut checkpoint holds from 0.75 to 0.15 per run: MiniMax now reads the policies before writing on its own, the habit Phase 0 diagnosed.
- Both rules match the failure habits found before any learning ran.

**A second cross-check (jevdata, 06:35 UTC).** The final playbook ran on all 60 practice tasks (0.727 credit, 19 passes). On the 45 practice tasks the starting playbook also ran, credit rose from 0.633 to 0.756 (+12.3 points, 95% interval +1.4 to +23.3; 19 better, 8 worse, 18 equal). The rules were never chosen on these tasks, but the editor saw mistakes on them, so it is a softer hold-out than the sealed exam.

**What the replay added.** Seven near-identical playbooks ([R1a, R2x] plus one extra rule) scored 0.746 to 0.792 (mean 0.764, spread 0.020), which is about what noise gives. So two rules look like a plateau, the length limit was not what held it back, and a fairer size for the gain is about +13 points on the test bench. Details: [`LEARNINGS_AND_IMPLICATIONS.md`](LEARNINGS_AND_IMPLICATIONS.md).

**What the Jev verifier showed (15:25 UTC).** Pre-registered, validated once: within-playbook AUC 0.612 [0.51, 0.72] on 840 test bench runs (bar 0.65, not met); generic rubric on the same runs 0.51; lowest-30% credit gap 0.166 vs 0.06. It fades as the agent improves (0.70 for the starting playbook, 0.48 for the final one) and flags skipped actions and wrong content, not broken rules.

**What the Jev refit showed (14:50 UTC).** With 17 times more labelled runs (1,052, validated grouped by task), Jev's held-out AUC on the final playbook's runs is 0.525 [0.42, 0.63] against a pre-registered bar of 0.65: not met. Telemetry alone gives 0.51; per failure kind Jev's score predicts rules broken 0.49, skipped actions 0.58, wrong content 0.54. The checker does not see what is wrong inside the outputs.

**What the Jev stage showed (06:55 UTC).** The rubric was fitted on 60 practice runs and tested on the 60 test bench runs: AUC 0.73 on practice, 0.475 on the test bench (chance is 0.5; standard error about 0.07), accuracy 0.567 vs 0.533 for always guessing the majority. So Jev has not yet shown it can tell good from bad runs on held-out data; it is data-starved (60 runs; about 990 logged runs unused). Part B of [`LEARNINGS_AND_IMPLICATIONS.md`](LEARNINGS_AND_IMPLICATIONS.md).

**Not shown yet.**

| Question | Status |
|---|---|
| Does it generalize to unseen tasks? | Sealed exam only |
| Is it a cascade, or two good rules? | Unknown; WIP-1 would test it |
| Does Jev learn? | Not started |
| Does the router get close to Gemini for about half the cost? | Not started |

**Caveats that apply to every number above:** the margin keep test was adopted after seeing Take 1's results; both rules were chosen on the same 60 tasks; one run moves about 3 points on its own. Full list and the claim table: [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md).

### Earlier results (Phase 0 and the pilot)

**Phase 0: three models, one run on each of 20 Finance + HR tasks**

| | Gemini 3.8 Flash | **MiniMax M3** | DeepSeek V4 Pro |
|---|---|---|---|
| Mean partial credit | 0.66 | **0.58** | 0.21 |
| Tasks fully passed | 9 | 4 | 1 |
| Cost per run | $0.32 | **$0.062 (≈ ⅕)** | $0.048 |
| Time per run | 266 s | **129 s (≈ 2× faster)** | 443 s |
| Comparable to Gemini? (preregistered rule) | — | ✅ | ❌ |

**Why MiniMax falls short:** it acts before reading the rules. It read every policy email in 4 of 13 runs (Gemini: 12 of 12) and broke about 3× as many "must not" rules. That is what the skill loop has to fix. Details: [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md) · Phase 0 story: [`JOURNEY.md`](JOURNEY.md)

**Phase 1 pilot (2 rounds, $8.97):** MiniMax's own fixes targeted its real failures, and all three cut broken "must not" checks (0.90 → 0.50–0.70 per run). The best fix raised credit by 6.7 points and pass rate from 15% to 25%, but **no fix passed the keep-or-reject test**: one run on each of 40 tasks can't confirm gains that size. Report: [`phase1/pilot/README.md`](phase1/pilot/README.md)

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
| Action masking (V2-5) | ✅ In scope (2026-10-08). The checkpoint may read company data, never grading checks or `meta`. Checkpoint on for learning and the final test (canonical design, 2026-10-09) |
| Sealed set | Held: untouched until Alexander releases it |
| Spend cap | **$110** for v2 Phase 1, a safety stop (Alexander, 2026-10-09) |
[line omitted from the public copy]

**Keep test changed (2026-10-10, Alexander): Take 2 uses the margin keep test.** Take 1's p-value keep test rejected every candidate in rounds 1 and 2, although three of four raised credit by 2 to 5 points; at 60 tasks and one run each it could not see gains that size. Adopted after seeing those results, and recorded that way. Details: [Live status](#live-status-v2-phase-1-take-2-is-running) and the canonical design's Takes section.

How each decision was reached: [`JOURNEY.md`](JOURNEY.md); dates and detail: [`PLAN.md`](PLAN.md).

## Budget

| | Estimate | Cap |
|---|---|---|
| Phase 0 | spent **$9.41** | $25 |
| Phase 1 pilot (2 skill-loop rounds) | spent **$8.97** | $20 |
| **V2-5 action masking** (plan below) | ≤ **$40** | $40, pending approval |
| Phase 1, full design (incl. redesigned skill loop) | ≈ $94 (range ≈ $60–110) | **$110** (Alexander, 2026-10-09) |

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
| **C (V2-5a)** | Build the checkpoint; MiniMax on the 60 test bench tasks with the checkpoint off vs on. Success = fewer broken rules, credit doesn't fall, few holds | ≤ $10 | needs approval |
| **D** | Near-misses shown to the editor; holds per 100 runs by round | ≈ $0 | ⬜ |
| E (optional) | Jev as the checkpoint, with learned yes/no questions | ≤ $20 | skipped (Alexander, 2026-10-08) |
| **Total** | | **≤ $40** (≈ $19 without E) | |

The sealed set is not touched. The checkpoint is on for learning and the final test; checkpoint-off runs only show what it adds (canonical design, 2026-10-09).

## Documents

| Document | What it holds |
|---|---|
| [`LEARNINGS_AND_IMPLICATIONS.md`](LEARNINGS_AND_IMPLICATIONS.md) | What we learned and what follows from it: Part A the playbook, Part B Jev and the cutoff (living) |
| [`WIP_NOTES.md`](WIP_NOTES.md) | Work-in-progress ideas and scope notes; nothing approved or run (Alexander, 2026-10-10) |
| ⭐ [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md) | How learning cascades, what was reused or changed after the fact, what each result can and cannot support (living) |
| [`briefs/V2 Phase 1 Canonical Experiment Design.md`](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md) | **The source of truth** for the design and its words (2026-10-09) |
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
