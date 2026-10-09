# Brief: action masking for the v2 harness (V2-5), plus the skill-loop fixes it depends on

**For:** the coding agent · **Written:** 2026-10-08 · **Repo state this was written against:** `aliss77777/jev-test-poc`, commit `a14d11e` · **Status:** revised 2026-10-08 after review; fixes 1–6 approved by Alexander; caps and thresholds still to confirm (section 9)

**Revisions (2026-10-08, approved by Alexander):**
1. **Leak rule:** the monitor may read the company's data at the start of the task (the world's initial state, read-only) but **never the world's `meta` field** (`meta.allowed_services` is computed from the grading checks) and never grading checks or expected state. A test enforces it; the production-access assumption is stated (section 2).
2. **A4** (choose target tasks by a task property) agreed as written.
3. **A2:** label **emails, not runs**, on tasks where the detector fires and where it doesn't, with an "unsure" option, so both precision and recall are measured.
4. **V2-5a:** "≥ 90% read every policy email before the first write" is a **sanity check** (largely guaranteed by the checkpoint). The **primary outcome** is broken "must not" checks per run, checkpoint on versus off; credit and holds per run are guards; report the paired interval and claim no significance at this sample size (section 8).
5. **Silent-wrong:** "flagged" means **at least one hold or flag logged by the checkpoint** in the run; final messages don't count yet; this overstates catching (section 8).
6. **Headline stays checkpoint off:** V2-3 and the learning claim are measured without the checkpoint; the checkpoint's value is reported as a separate cell. `Phase 1 design.md` says so too.
Also: A3 may reuse the agent cache key's existing `candidate` field for repeats instead of adding a new one; the local logs and cache are confirmed present (section 9, item 5).

## In plain language: how this changes the way fixes are proposed and accepted

*This explanation is the level of clarity the repo's docs, and later the Substack post, need. See "Writing standard" in section 10.*

**Phase 1 in one line:** the agent wrote 2 candidate rules, each rule was tried on the same 40 tasks, and a rule was kept only if the *average score* clearly beat the old playbook.

**The problem.** Think of testing a study tip. A tip like "read the instructions first" only matters on some of the exams, but Phase 1 averaged its effect across all 40, with one try each and a lot of luck in every score. A real +6.7 points got lost in the noise, and the tip that cut the most rule-breaking (fix C) was rejected because the single score dipped, with no explanation of why.

**What changes:**

1. **Steadier runs.** Temperature 0 means the same task gives roughly the same run, so luck matters less.
2. **A better briefing for the proposer.** The editor sees counts by failure type ("rule broken 19 times; policy email skipped in 9 of 13 tasks") instead of a few raw examples. Each fix must name which kind it targets, and longer rules are allowed so proposals aren't thrown out for length.
3. **A three-part test instead of one score.** The fix must improve the targeted checks on the tasks where it applies. It must not drop scores by more than a few points on the other tasks. And the overall average must not fall. Fix C would now show "targeted checks improved, but it under-acted elsewhere," which tells you what to refine.
4. **A fairer way to pick the test tasks** (work item A4). Choose the "tasks where it applies" by a task property, not by who failed before. Otherwise tasks that failed once tend to look better on a retry by luck alone.

**What action masking adds.** When the checkpoint stops a bad write, the run might end up correct, which would hide the failure from the editor. So every stop is logged as a near-miss and shown to the editor (work item D). Repeated stops can later become new rules, so the checkpoint fires less and less as the agent learns.

## 0. Read first, then confirm

Read in this order and tell Alexander in 3 lines what you understood before writing code:

1. `v2/README.md` (tracker), `v2/briefs/Phase 1 design.md`, `v2/briefs/Skill loop redesign.md`, `v2/phase1/pilot/README.md`
2. `v2/src/jevloop/`: `llm_agent.py`, `runs.py` (ToolBox, run_candidate), `summary.py`, `diagnostics.py`, `skill_loop.py`, `bench.py`
3. `v1/jev.py` (the Jev client; v2 has none yet) and `v1/gate.py`

Do not edit anything under `v1/`. Files ported from v1 keep the repo's convention: first line names the source and tag (`v1-final`).

## 1. What this is and why

**The problem.** In multi-step workflows a mistake early in a run is only felt at the end, when it can no longer be repaired (an email can't be unsent). Phase 0 found MiniMax M3 skipping policy emails and breaking "must not" rules about 3x as often as Gemini. The Phase 1 pilot showed its own fixes moved behaviour the right way but the end-of-run score was too thin a signal to keep them.

**The idea: action masking.** Before the agent's record-changing action executes, a checker looks at the proposed action, what the agent has read, and what has changed so far. If the action breaks a policy the agent has read, the action is held (not executed), the agent is told why, and it re-proposes. Same runs, same agent; the bad write never happens.

- **Term:** use **action masking** in docs and code comments. Strictly it is a shield (a veto after the action is proposed, not removal from the action set); say so once in `GLOSSARY.md`.
- **Pipeline analogs** for prose: a pre-commit hook, a dbt-style test before downstream steps, Write-Audit-Publish.
- **Sources of the idea:** the World of Workflows paper (Skyfall AI, arXiv 2601.22130) names "dynamics blindness": agents failing to foresee hidden or delayed consequences of actions. **Do not claim v2 solves it.** Phase 0 evidence shows MiniMax skipping policy that was visible in the inbox, which is a different failure.

**It is part of the learning loop** (section 6): every hold is logged and labelled by the run's graded outcome; the editor sees holds as failures even if the run later passes; repeated holds can be promoted to playbook rules.

## 2. Hard rules

- **`monitor=None` must leave behaviour byte-identical** to today. A test proves it with a fake model client; existing tests (53 at last count) still pass; existing cache keys unchanged.
- **No leak.** The monitor sees only: the public task; the calls so far with their results; the world diff since the start; and the **company's data at the start of the task** (the world's initial state, read-only, so it can tell which policy documents exist, including ones the agent never opened). It must **exclude the world's `meta` field**: `meta.allowed_services` is computed from the grading checks, so it would leak which services are graded. It never sees grading checks or expected state. Add tests like `tests/test_summary.py`'s that fail if grading checks, expected state or `meta` reach the monitor's context type.
- **Production-access assumption (state it in the docs):** a real deployment's pre-write check could read the company's own systems (the mailbox, the shared sheets) with read-only access. It could not read an answer key, because none exists in production. The monitor's access mirrors that.
- **The sealed set is not touched** by anything in this brief until Alexander says so in writing (section 9, item 6).
- **Caps in code.** Every paid script takes a spend cap and stops before passing it (reuse `spend.py`). Free steps make no model calls.
- **Preregister.** Verdict rules (section 8) go into code with tests, committed before any paid run. Never change them after seeing numbers.
- **Scope floor and ceiling.** Do not shrink the design quietly (no dropping the leak test, the identity test, or the near-miss logging). Do not add anything not listed: no UI, no new agent tool, no new infrastructure.
- **How to work** (from Alexander's "Hero Coding to Systematic Agentic Workflows"): small bounded jobs; any fix over about 30 minutes gets a written note (what broke, why, the fix, a rule to prevent it); "done" means verified, not written.

## 3. Work item A: fixes the redesign depends on (free, do first)

Found in review of `a14d11e`. Each has a test.

| # | Fix | Done when |
|---|---|---|
| A1 | **`summary.py` truncation drops STATE CHANGES.** `summarize()` cuts from the end at 8,000 characters, and state changes come last, so long runs lose the audit-log part Jev needs. Give each section its own budget and keep state changes. | A test with a synthetic 50-call run keeps every state-change line within budget and marks what it dropped. |
| A2 | **Step measures are thin and loose.** `diagnostics.py` has two measures; the policy-email detector keys on generic words ("update", "process", "rule", "hold"). Add `read_policy_before_first_write` (needs call order). Measure the detector's precision and recall against Alexander's labels. **The labelling unit is the email, not the run**: whether a run read an email is mechanical; which emails count as policy is the judgement. Prepare a sheet of every email in about 20 tasks (sender, subject, first lines), drawn from tasks where the detector fires **and** tasks where it doesn't, so recall is measured as well as precision. Options: **policy / not policy / unsure**; report unsure separately. Do not guess the labels. | Fixture tests pass; precision and recall are reported (unsure excluded and counted); the detector stays marked "approximate" if either is below 0.8. |
| A3 | **Determinism test must bypass the cache.** The cache key hashes the full request, so reruns replay (the pilot's 15 of 16 identical scores were replays). Give repeats distinct cache keys: reuse the agent cache key's existing `candidate` field (or add a `repeat` field). | A test shows two repeats get different cache entries; the default path is unchanged. |
| A4 | **Target-set selection bias** (redesign change 3). Choosing "test bench tasks where the current version missed the targeted check kind" selects on the outcome and biases the test toward improvement; the regression set is biased the opposite way. Select target tasks by a **task property** (for example, the task has a policy email, or its definition contains a check of that kind), or re-run the current version for a fresh baseline on the target set. *(Agreed 2026-10-08: select by task property.)* | The redesign doc is updated with the choice and the reason; a simulation under a null fix shows the false-keep rate near the nominal level. |
| A5 | **Power estimate** from the pilot's per-task test bench scores, if the local logs have them (section 4). Estimate how often the redesigned keep rule would keep a +6.7-point targeted fix. | A short note with the number and the method. If the logs are missing, say so and stop this item. |

## 4. Work item B: free replay (the first real experiment, $0)

**Question:** using only what was visible before each write, could a simple check have flagged the runs that broke rules?

**Inputs:** the committed results (`phase0/*.json`, `phase1/pilot/*.json`) do **not** contain per-call traces. The traces are in `v2/logs/*.jsonl` (`candidate_run` events include `calls`, `summary`, `missed_checks`) and `v2/cache/`, which are git-ignored and live on Alexander's machine. **If you cannot find them, stop and ask; do not rerun paid work to regenerate them.**

**Build** `v2/scripts/replay_masking.py` (no model calls):

1. For each logged run, list record-changing calls in order (`api_fetch` with POST, PATCH, PUT, or DELETE; confirm the exact argument names against `llm_agent.py` and `summary.py`).
2. Apply Checkpoint 0 (rule only): at the first write, were all policy-like documents in the task's inbox already read? (The inbox comes from the initial state, as the leak rule allows; never from `meta`.) Use the A2 detector.
3. Report, per rule: coverage (share of runs with policy emails), how often it fires, and precision and recall against two outcomes: "at least one broken must-not check" and "credit below 0.5".
4. **Label-mapping feasibility.** For every missed negative check across the logged runs, count how many can be tied to a specific call by a simple matcher (email recipient, record field and value). Report the share by check type. Do not build the full mapper.

**Output:** `v2/action_masking/replay/REPORT.md` with the tables above and a one-paragraph recommendation.

**Go or stop** (proposed; Alexander confirms before you look at results): proceed to section 5 if the rule's precision is at least 0.6 and it fires on at least a quarter of the runs that broke a must-not check. Otherwise stop and report; that is a result.

## 5. Work item C: monitor interface and the checkpoint (about $10 cap)

**Code**, small and with clean seams:

- `v2/src/jevloop/monitor.py`: a `Monitor` protocol with `before_write(ctx) -> Verdict` and `before_finish(ctx) -> Verdict`. `Verdict` is `allow | hold | flag` plus a message and evidence. `MonitorContext` holds only the fields listed in section 2 (initial state read-only, `meta` excluded).
- One optional `monitor` parameter on `LLMAgent`. Before executing a tool call classified as a write, call the monitor. On `hold`: do not execute, append a tool message with the held reason, count it. Cap **3 holds per run**; after that, allow and log.
- Log a `monitor_verdict` event per check (step, verdict, evidence, whether the next call changed). Add intervention counts and flags to `AgentResult` and `CandidateRun.record()` with defaults, so old records still load.
- The first monitor is **rule-based**: Checkpoint 0 from section 4. No Jev, no ledger, no new agent tool (the agent's three tools stay as the bench defines them, so Gemini remains comparable).

**Tests:** identity with `monitor=None`; hold path; hold cap; no-leak; logging; a fake model that tries a held write and then complies.

**Experiment V2-5a** (on the **test bench** tasks, not sealed): MiniMax with its version-0 prompt, temperature 0, checkpoint off versus on, one run each, paired by task. Report mean credit, pass rate, broken must-not per run, policy-read rate, steps, cost, holds per run. This tests the mechanism, not the learning.

**Before this runs, the determinism test and the temperature-0 re-checks in `Skill loop redesign.md` (about $9) need Alexander's approval**; they set whether temperature 0 is usable.

## 6. Work item D: the learning-loop hooks (small, after C)

- **Near-miss logging.** A run where the monitor held an action and the run then passed is a near-miss. `mistakes_report` must include near-misses, marked as such, so the checkpoint does not hide failures from the editor. Without this the loop loses the signal the checkpoint is masking.
- **Report catches per 100 runs by round.** A falling rate with a steady pass rate is the legible learning curve.
- **Catch to rule is manual in V2-5:** list repeated holds in the report and propose candidate rules; do not automate promotion.
- **Final-playbook checkpoint comparison:** one extra cell, the final playbook with the checkpoint off versus on, 80 sealed runs (about $3 to $5). This is **pre-registered here and not run** until Alexander releases the sealed set.

## 7. Work item E (optional, only after C passes and Alexander approves): Jev monitor

- Port `v1/jev.py` into `v2/src/jevloop/jev.py` (source line at the top). Start with **6 to 10 generic yes/no questions**, task-agnostic, for example: is the target excluded by a policy the agent read; is this action allowed by that policy for this item's status; do the values match the source the agent read; was any policy-like document left unread.
- The ledger is **derived by the harness** from calls and the world diff, not written by the agent.
- Rubric edits come from the same MiniMax editor, accepted by **offline replay** on logged traces with a cluster-aware test (cluster by task). Replay is off-policy: confirm any claim end to end on the sealed set once.
- Needs the label mapping from section 4. If it is poor, fall back to run-level labels and say so.
- Cap about $20. Do not start without a go from Alexander.

## 8. Verdict rules (proposed; Alexander confirms; code and tests before paid runs)

**V2-5a, hard checkpoint on test bench tasks.** Checkpoint on versus checkpoint off, one run each, paired by task.
- **Sanity check (not a success criterion):** the share of runs that read every policy email before the first write rises to at least 90%. The checkpoint largely guarantees this, so it only shows the mechanism works.
- **Primary outcome:** broken "must not" checks per run **fall** with the checkpoint on versus off.
- **Guards:** (a) mean credit on the whole test bench does not fall; (b) holds per run average at most 2.
- **Worth keeping** if the primary outcome falls and both guards hold.
- **Report** the mean paired difference with a 95% paired interval for the primary outcome and the guards. **Claim no statistical significance** at this sample size; this is a mechanism test.
- If the primary outcome falls but credit falls too, report "the checkpoint changes behaviour but costs credit" and diagnose from the logs; do not tune thresholds.

**Silent-wrong rate** (new, business-facing): runs with credit below 1 and not flagged, divided by all runs. **Caught-wrong:** credit below 1 and flagged. Report both next to partial credit and pass rate for every comparison.
- **"Flagged" means at least one hold or flag logged by the checkpoint in that run.** For now, only the checkpoint's own logged verdicts count; the agent's final message does not (it has no defined rule yet).
- **Caveat to state wherever these are reported:** this overstates catching. A flagged run can still be wrong for a reason the checkpoint didn't catch, so "caught-wrong" means "wrong, and the checkpoint raised something", not "wrong, and the checkpoint found the error".

**Learning claim and headline stay checkpoint off.** The learning claim stays what `Phase 1 design.md` says: final playbook versus v0 on sealed, checkpoint off. **The V2-3 headline (Router vs Gemini) is also checkpoint off**, because Gemini runs without a checkpoint. The checkpoint on cell shows the checkpoint's own value, reported separately; never blend it into the headline or the learning claim.

**Honesty rules:** state the limits (80 sealed tasks resolve differences of several points, not one or two; the simulator gives free observability that production would pay for in audit logs or polling; step measures are diagnostics, not the objective).

## 9. Decisions Alexander needs to make (ask; do not assume)

1. Approve the section 0 reading summary and these caps: free steps $0; V2-5a up to $10; determinism and temperature-0 re-checks about $9 (as in the redesign); optional Jev monitor up to $20; this brief's total not above **$40** without a new approval.
2. Confirm the go or stop thresholds in sections 4 and 8.
3. The redesign's four open questions (temperature 0, keep-rule numbers, 60 test bench tasks, extra step measures).
4. Provide the A2 email labels (policy / not policy / unsure) on the sheet the coding agent prepares (about 20 tasks).
5. ~~Confirm where the local `v2/logs` and `v2/cache` are.~~ Confirmed 2026-10-08: present (306 recorded runs with full traces; the pilot's per-task test bench scores).
6. Release or hold the sealed set for the final-playbook checkpoint cell.

## 10. Reporting contract and tracking

After each work item, write: what changed; what was verified and how; what surprised us; open questions. Update `v2/README.md` (tracker) and `v2/PLAN.md` (dated log) when a step finishes, and add **action masking** (and **silent-wrong rate**) to `v2/GLOSSARY.md`. Do not edit `v2/RESULTS.md` or `v2/STORY.md` until a verdict exists. Commit messages in the repo's existing style.

**Writing standard (applies to every doc you write in this work, and is the bar for the Substack post later).** Alexander approved the "In plain language" section at the top of this brief as the register to aim for. Concretely:

- Say the problem before the mechanism, and introduce a term (action masking, near-miss, silent-wrong rate) only after the plain description of what it does.
- One everyday analogy per idea (the study-tip test is the model). No RL or statistics jargon in the main text; put it in a footnote or the glossary if it must appear.
- Short sentences. Numbers only where they carry the point, always with what they were measured on.
- State what failed and what is unproven in the same breath as what worked (the Phase 1 pilot's "no fix was kept" belongs in the story, not an appendix). Never claim v2 solves dynamics blindness.
- This applies to `REPORT.md`, README tracker entries, the `GLOSSARY.md` entries, and any text meant to be lifted into the Substack post. Flag in each report the two or three sentences you think could be lifted as is.

**If a block overruns by 30 minutes, cut in this order:** Work item E; the A5 power note; the Jev port. **Never cut:** the identity test, the no-leak test, the spend cap, near-miss logging, and sealed-set protection.
