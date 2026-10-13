# v2: can an open-weight agent learn on the job?

> **Core question:** can a harness that lets an open-weight agent learn from its own mistakes, with Jev checking its work, get close to a premium model on real back-office work, for a fraction of the cost?

v1 showed on public benchmarks that a learned Jev rubric could route between itself and an LLM for half the cost ([v1 results](../v1/RESULTS.md)). v2 moves to **doing real work**: the Finance and HR tasks in Zapier's AutomationBench, graded on whether the company's systems end up right. This page is the history and the tracker; the design and the words are in the [canonical design](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md), the numbers with their sources in [`RESULTS.md`](RESULTS.md), the dated log in [`PLAN.md`](PLAN.md).

⭐ **Read before quoting any result: [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md)** (what each result can and cannot support).

## Where we ended up

**Status (Oct 10, 2026): Phase 1 is complete.** The sealed exam ran once and is written up. Nothing is running. A cross-domain live run is parked.

> An open-weight model, taught by a harness from its own mistakes, got within about 6 points of a premium model's credit on unseen tasks at 15% of the cost. A redesigned checker improved on the original but did not show value as a router on this task: the router reached Gemini's credit by sending 45% of tasks to Gemini, not by choosing well.

**Final results: sealed exam, 80 unseen tasks, one run each, opened once.**

| Question | Result |
|---|---|
| **Did MiniMax learn?** | **Yes.** Credit 0.573 to 0.755 (**+0.182**, 95% interval +0.095 to +0.272, p < 0.001); fully passed 23 (29%) to 33 (41%) |
| **MiniMax vs Gemini alone** | 0.755 vs 0.811 (−0.056, interval −0.131 to +0.020); fully passed 33 vs 47; **$0.042 vs $0.273 per task (15%)** |
| **Router vs Gemini alone** | Credit **0.804 vs 0.811** (−0.007, interval −0.061 to +0.053); cost **62%** of Gemini's (not half); 45% of tasks escalated |
| **Is Jev a good router?** | **No on the exam.** Same-playbook AUC 0.566 [0.44, 0.70] against a bar of 0.65. Against random escalation at the same share, the router gained +0.024 (interval −0.02 to +0.07) |
| **What does the checkpoint add?** | Little at exam time with the learned playbook (credit 0.755 on vs 0.775 off; **fully passed 33 on vs 30 off**). During learning, plausibly a lot: unshielded, the read-policies-first habit rose from 31% to 84% |

## History: what we did, what happened, what we learned

| When | What we did | What happened | Setback or course correction |
|---|---|---|---|
| **Oct 5 to 7**, Phase 0 | Set up AutomationBench; chose Finance + HR (back-office work); tried three cheap open-weight models against Gemini 3.8 Flash on 20 tasks | **MiniMax M3** came close (credit 0.58 vs 0.66, about 1/5 of the price). Its gap was one habit: acting before reading the policy emails. $9.41 | Nemotron 3 Super was rate-limited upstream and passed 0 of 21; DeepSeek V4 Pro wandered to the step cap. Both out |
| **Oct 7**, pilot | Two rounds of a self-editing playbook loop | All 3 fixes cut broken "must not" rules (0.90 to 0.50 to 0.70 per run); none passed the keep test. $8.97 | The test (40 tasks, one run each) could not see a few points. Loop redesigned: targeted rules, check-level telemetry, a longer rule limit |
| **Oct 8**, harness | Measured run-to-run noise; fixed harness bugs | Temperature 0 is **not** repeatable (0 of 10 identical; scores differ by 0.26). MiniMax stayed comparable to Gemini (−0.07). $7.84 | Choosing test tasks by past failure keeps useless fixes 77% of the time, so test tasks are chosen by task property. Noise handled with repeats, not settings |
| **Oct 8**, checkpoint | Built a "read the policies first" checkpoint (action masking); replayed 236 runs, then ran it live off vs on | Credit 0.57 to 0.65 (+0.08), broken rules 0.88 to 0.67 per run; kept (both ranges just touched zero). $5.90 | A fairness worry (the cheap model gets a shield, Gemini doesn't) led to reporting a checkpoint-off arm at the end |
| **Oct 9**, design | Adopted the canonical design: fixed words, a five-stage pipeline, checkpoint on for the final test too | Pipeline built and dry-run end to end | Terms had drifted ("gate" meant three things); renamed |
| **Oct 9**, Take 1 | Four rounds planned with the p-value keep test | 4 candidates, 3 raised credit by 2 to 5 points, **none kept**; stopped after round 2 | **Course correction:** at 60 tasks and one run each the test was too blunt. Switched to a margin keep test (adopted after seeing Take 1; recorded as post hoc) |
| **Oct 10**, Take 2 | Margin keep test: targeted failure kind improves, credit up at least 0.02, passes not lower | Two rules kept: **R1a** "do every required write" and **R2x** "read the policy emails before any write". Test bench 0.62 to **0.78** (a fair +13 points) | Rounds 3 and 4 kept nothing. Five proposals hit the 600-character limit; raised to 1,200 and replayed: still nothing. Seven further candidates scored 0.746 to 0.792, about noise (SD 0.02): a plateau |
| **Oct 10**, Jev, original | Learned the 8-question rubric on practice runs; then refit its weights on 1,052 runs | Fitted well (AUC 0.73) and **did not transfer** (0.475 on the test bench; refit 0.525) | Pre-registered a bar (AUC 0.65, lower bound above 0.5, gap 0.10) before every test and opened each held-out set once |
| **Oct 10**, Jev, redesign | Showed Jev the source records, policy emails and the agent's writes; wrote questions per task. Second attempt on 240 fresh runs of the final playbook | First attempt 0.612 (bar missed; 0.48 on the final playbook alone). Second attempt **0.666, bar met**; cutoff frozen at 0.756 | Variants added only 0.003 over the first attempt; learned instructions +0.048 (not distinguishable from zero). Jev improved by **design**, not learning |
| **Oct 10**, ceiling check | Gemini on the 54 tasks MiniMax failed ($15.30) | Gemini 0.696 vs MiniMax 0.528 there; a perfect detector would add about +7 points (about +3 against fresh draws); re-running MiniMax recovers +4.5 at $0.045 | Earlier 20-task estimate (no upside) was superseded by the larger check |
| **Oct 10**, sealed exam | Released and run once: starting playbook, final playbook (checkpoint on and off), Gemini alone, router. $42 | Results above | A 403 (key spend limit, during the replay) and a 402 mid-exam (OpenRouter's in-flight budget, not an empty balance) halted runs; diagnosed, harness now retries it, resumed without a second opening. The cutoff, set for 30%, escalated 45% |

## What we learned

1. **A harness can teach a cheap model from its own mistakes,** with no premium model in the loop. The two rules that stuck are the habits we diagnosed before any learning: finish every write, and read the policy emails first.
2. **Two rules look like a plateau.** More and longer rules were noise; prompt rules fix habits, not the accuracy of values (wrong content stayed the largest failure).
3. **At this size the keep test has to be a margin.** One run per task moves about 3 points; noise on a 60-task mean is about 0.02. Test sets get used up: fresh runs were the honest way to validate.
4. **The checkpoint worked as a training scaffold.** Holds fell from 0.75 to 0.15 per run as the playbook absorbed the habit; at exam time the shield was not needed. Whether it was necessary for learning was not tested.
5. **Jev needed to see what it checks.** A generic checklist over a summary stayed near chance; showing it the source, policies and writes roughly doubled the signal, but not enough to route: it flags wrong content and skipped actions, barely broken rules, and its estimate dropped from 0.666 (validation) to 0.566 (exam).
6. **The router's credit came from the share, not the choosing.** A perfect detector is worth about +7 points; this one bought +0.02 over random.
7. **Even the premium model fully passes only 59% here.** Published leaderboards (best 51% across all domains, strict full pass) say the same: human review stays in the loop, and a draft-plus-triage deployment is the realistic shape.

## What the results do and do not support

- **Safe to say:** a cheap open-weight model learned from its own mistakes (+18 credit points on unseen tasks, p < 0.001) and got within about 6 points of a premium model at 15% of the cost; a checker over this task's run summaries did not reach a useful bar.
- **Do not say:** "MiniMax matches Gemini" (5.6 points behind, interval includes zero); "the router works" (the share did the work); "Jev learned" (not shown); "beats published models" (different subset, version and metric).
- **Limits:** 80 tasks (about ±11 points on a pass rate), one domain subset, Gemini Flash as it comes as the yardstick, a post hoc keep test. Full list in the [memo](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md) and [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md).

## Open

| Item | Why |
|---|---|
| Cross-domain live run (Operations, Support, Sales, Marketing; about $33 per 80 tasks) | The only fresh live test of the router and of transfer; needs a scope note and a cap raise |
| Starting playbook with the checkpoint off on the sealed tasks (about $3.5) | Completes the playbook × checkpoint grid; tests the training-scaffold reading at exam time |
| A stronger verifier (full trace, per-field value checks), tested against the same bar | The router half is the part that did not show |
| Gemini with the playbook | Whether the harness helps a premium model too |
| Does R2x need R1a (about $3) | The only test of "cascade" vs "two good rules" |

## Spend and decisions

- **Spend:** Phase 1 runs $117.7 on the tracker (cap $130; sealed exam about $42, ceiling check $15.30, fresh runs $11.11); earlier work about $32 (Phase 0 $9.41, pilot $8.97, harness re-checks $7.84, checkpoint test $5.90).
- **Models:** MiniMax M3 (open weight, its own host) as the agent and editor; Gemini 3.8 Flash as baseline and fallback, never a teacher; Jev 1.13 as the checker. No frontier model.
- **Data:** 200 Finance + HR tasks: practice 60, test bench 60, sealed 80 (opened once, Oct 10).
- **Rules of the run:** one run per task; no peeking at grader checks; the sealed exam opens once; paid runs wait for `run.approved: true`; design changes go in the memo first.

## Documents

| Document | What it holds |
|---|---|
| [`briefs/V2 Phase 1 Canonical Experiment Design.md`](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md) | **The source of truth:** design, words, results, limits, sourced appendix |
| [`RESULTS.md`](RESULTS.md) | A standalone mirror of the results and their sources |
| ⭐ [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md) | How learning cascades, what was reused or changed after the fact, what each result supports |
| [`LEARNINGS_AND_IMPLICATIONS.md`](LEARNINGS_AND_IMPLICATIONS.md) | What we learned and what follows from it, in three parts |
| [`PLAN.md`](PLAN.md) | Dated log of every decision, deviation and fix |
| [`GLOSSARY.md`](GLOSSARY.md) | One name per concept |
| [`JOURNEY.md`](JOURNEY.md), [`METHODOLOGY.md`](METHODOLOGY.md) | The early plan and setbacks; what changes from v1 |
| [`phase0/FEASIBILITY.md`](phase0/FEASIBILITY.md), [`phase0/DOMAINS.md`](phase0/DOMAINS.md) | Phase 0 measurements; why Finance + HR |
| [`briefs/`](briefs/) | The original and intermediate briefs (the canonical design outranks them) |
| [`action_masking/`](action_masking/) | The checkpoint: replay and live-test reports |
| [`phase1/run/`](phase1/run/) | Machine-readable outputs: `take1/`, `take2/` (skill history, Jev stages, sealed results) |

## How to run

From inside `v2/`, with Python 3.13:

1. Download AutomationBench into `z-ignore/AutomationBench-main` (git-ignored).
2. `python3.13 -m venv .venv && .venv/bin/python -m pip install -e z-ignore/AutomationBench-main -r requirements.txt`
3. Tests (no model calls): `.venv/bin/python -m pytest -q`
4. Phase 1 stages (paid, capped, resumable): `scripts/phase1_run.py skill | replay-refused | jevdata | rubric | tau | ceiling | fresh | sealed --release-confirmed`
5. Jev work: `scripts/jev_refit.py`, `scripts/jev_verifier.py`, `scripts/jev_verifier_d2.py`, `scripts/jev_instructions_check.py`; derived numbers: `scripts/sealed_analysis.py` (free)

Model calls need `OPENROUTER_KEY` in `v2/.env`. Harness code is in `src/jevloop/`; `bench.py` is the only module that touches AutomationBench.
