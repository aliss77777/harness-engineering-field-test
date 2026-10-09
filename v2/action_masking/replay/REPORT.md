# Replay: would a "read the policies first" check have caught the bad runs? (work item B, $0)

**Date:** 2026-10-08 · **Rule and thresholds:** [`PREREGISTRATION.md`](PREREGISTRATION.md), committed before this ran · **Data:** `replay_results.json` · **Script:** `scripts/replay_masking.py`

## The question, plainly

Think of a new hire who starts sending emails before reading the team's rulebook. Phase 0 found MiniMax doing exactly that. Before building a gate that stops it, we asked: **if we had held every first write until the policy emails were read, would we have caught the runs that went wrong?** We answered it for free, from runs we had already logged.

## What we did

We took every logged agent run on Finance and HR tasks (298 runs; 297 replayed to exactly their original score), replayed each on a fresh copy of its world, and graded it check by check. At each run's first record-changing action we asked whether it had read every policy-like email in the inbox. If not, the gate **would have fired**.

## Result: go, narrowly

| MiniMax M3, 236 runs | Value | Preregistered bar |
|---|---|---|
| **Precision:** when the gate would have fired, the run broke a "must not" rule | **63%** | ≥ 60% ✅ |
| **Recall:** share of rule-breaking runs it would have caught | **44%** | ≥ 25% ✅ |
| How often rule-breaking happens anyway (base rate) | 43% | — |
| How often the gate would fire | 31% of runs | — |
| Mean credit, runs where it would fire vs not | 0.52 vs 0.57 | — |

**Verdict: go to work item C** (build the gate and test it live).

## What it tells us

- **The signal is real but modest.** Runs that skip the policy emails break rules 63% of the time, against 43% overall. The gate catches a bit under half of the rule-breaking.
- **It targets MiniMax's habit, not rule-breaking in general.** Gemini always read the policies first, so the gate would never fire on it, yet Gemini still broke a rule in 24% of runs. Those mistakes come from somewhere else (misreading a policy it did read, for example).
- **Nemotron shows the other extreme:** the gate would fire on 95% of its runs, because it never read the policies.
- **For the later Jev gate (work item E):** a simple matcher could tie 49% of the 194 broken "must not" checks to the specific write that broke them. Email-content checks map poorly; record and message checks map well. A Jev gate would have to learn from run-level labels for much of its data.

## Limits

- The policy-email detector is **keyword-based and approximate**: it fires on 130 of 137 Finance and HR tasks that have email. Alexander's email labels (A2) will measure it; these numbers may move once they are in.
- A replay is not a live test. In a live run, a held write changes what the agent does next, which can help or hurt. Work item C measures that.
- 236 MiniMax runs, many on overlapping tasks (the pilot reran the same tasks under different playbooks).

**Lines that could be lifted as is:**
- *"Runs that skipped the policy emails broke a rule 63% of the time, against 43% overall."*
- *"The gate targets one bad habit, acting before reading the rules; it is not a cure for rule-breaking in general."*
