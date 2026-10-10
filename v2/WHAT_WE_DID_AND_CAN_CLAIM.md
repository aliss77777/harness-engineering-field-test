# What we did, and what we can claim

A living page (Alexander, 2026-10-10). It records exactly how Phase 1 learns, what was reused or changed along the way, and what the results can and cannot support. Terms are the canonical design's ([`briefs/V2 Phase 1 Canonical Experiment Design.md`](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md)). Update it whenever the way we run or decide something changes.

## 1. How learning cascades

Improvements stack through the **playbook**, one rule per round, at most four rules.

```
Round 1:  playbook = [ ]           baseline = starting playbook (0.62 on the test bench)
          MiniMax does 30 practice tasks, proposes 2 candidate rules
          each candidate runs on all 60 test bench tasks
          the best candidate that passes the keep test joins the playbook   -> R1a (0.675)

Round 2:  playbook = [R1a]         baseline = R1a's test bench runs (reloaded, not repaid)
          MiniMax does 30 practice tasks WITH R1a, so it sees what is still wrong
          2 new candidates, each tested against the R1a baseline
          the best one that passes is added, or nothing is

Rounds 3 and 4: the same again.    Final playbook = all kept rules together.
```

- A new rule has to beat the *current* playbook, not the empty one.
- The editor sees the current playbook, the mistakes it still makes, and the list of rejected rules.
- Under the margin keep test every kept rule adds at least +0.02 test bench credit, so four kept rules would show at least +0.08 on the test bench.
- Rule texts and results come only from MiniMax's own graded runs. Gemini teaches nothing.

## 2. The two takes, and what was reused

| | Take 1 | Take 2 |
|---|---|---|
| Playbook keep test | P-value keep test (targeted failure kind clearly drops, p < 0.10; credit does not fall) | Margin keep test (targeted failure kind improves; credit up by at least 0.02; fully passed tasks not lower; no p-value) |
| Rounds run | 1 and 2, then stopped for review | 1 (reused) then 2 onward fresh |
| Result | Four candidates, none kept | Rounds 1 and 2: R1a and R2x kept; playbook has 2 rules (0.778 on the test bench, optimistic) |
| Jev rubric test | McNemar, p < 0.10 | Unchanged |

**Reuse in Take 2.** Round 1 started from the same empty playbook, the same seeded practice sample and the same editor replies as Take 1, so the harness reloaded Take 1's logged runs at $0 and only the *decision* changed. Nothing else carries from Take 1: its round 2 candidates (R2a, R2b) were written against the empty playbook and are not reused. Nothing cascades across takes.

## 3. Caveats that shape every claim

1. **The keep test was changed after seeing Take 1's results.** The margin keep test is a post hoc choice (Alexander, 2026-10-10). It is not preregistered, and the rule that "wins" under it was in view when it was chosen. Say so wherever Take 2 results appear.
2. **Take 2's round 1 is not an independent replication.** R1a was chosen from one noisy draw of 60 tasks, as the better of two candidates, so part of its +5.4 points is probably luck.
3. **The test bench is reused every round, so test bench numbers are optimistic.** Each winner is picked on the same 60 tasks, and the bias compounds. Only the sealed exam is an unbiased measure.
4. **Noise is about 3 points per run.** The identical starting playbook and checkpoint scored 0.65 on these 60 tasks in V2-5a and 0.62 in Take 1. A +0.02 margin sits inside that noise, so some useless rules will be kept.
5. **One lane per round.** Only the single best passing rule is kept; a passing runner-up (R1b in round 1) is shown to the editor as rejected and does not return. Stacking passing rules is noted as an idea for later, not adopted.
6. **Rules may interact.** Each rule is tested only against the playbook as it stood. The final combined playbook is first tested together on the sealed exam.
7. **The checkpoint is part of the harness for MiniMax and Gemini gets none.** The main comparison is router (checkpoint on) against Gemini as it comes. That is a harness-vs-model comparison, and should be described as one.
8. **Small samples.** 80 sealed tasks give about ±6 points, enough to show "close", not "within 3 points".
9. **The 600-character limit blocked one idea and shortened others** (corrected 2026-10-10 after checking). In rounds 3 and 4 five proposals were refused for length (886, 927, 946, 1,073 and 627 characters). Three were long first drafts of ideas the editor then resubmitted shorter and that were tested (R3a, R3b, R4a), so shortening may have weakened them. One idea, a verbatim extraction checklist for wrong content (1,073 and 627 characters), was never tested, which is why round 4 tested one candidate instead of two. So "rounds 3 and 4 kept nothing" is partly "one idea was never tried"; it does not show a plateau. The limit is now 1,200 characters, and the refused rules are replayed as written (see section 6).

## 4. What we can claim

| Claim | Supported now? | Needs |
|---|---|---|
| "MiniMax's candidate rules moved the test bench by 2 to 5 points in rounds 1 and 2" | Yes, as a test bench observation with caveats 2 to 4 | — |
| "The p-value keep test kept nothing at this size" | Yes (Take 1, four candidates) | — |
| "The playbook with R1a and R2x is better than the starting playbook" | **No.** Both rules were selected on the test bench (0.620 → 0.778, optimistic by about 4 points by a rough allowance). A side look at R1a on 30 practice tasks it was not selected on showed +8 points | The sealed exam |
| "MiniMax learned the checkpoint's habit" | **Partly, as an observation.** R2x (read policy emails before any write) cut checkpoint holds from 0.75 to 0.15 per run on the test bench | Sealed exam, final playbook checkpoint off vs on |
| "MiniMax learned" (question 2) | **No** | Sealed exam: final vs starting playbook, paired, checkpoint on |
| "Jev learned" (question 3) | **No** | Rubric stage, then the sealed exam |
| "The router comes close to Gemini for about half the cost" (question 1) | **No** | Sealed exam; reported as directional numbers and how close they land |
| "The checkpoint adds X" (question 4) | **No** (V2-5a's earlier result stands as a promising mechanism test only) | Sealed exam, final playbook checkpoint off vs on |
| "The margin keep test is better than the p-value keep test" | **No.** Nothing here compares them on unseen tasks | A design that holds both out |

## 5. Change log

- 2026-10-10 (04:32 UTC): caveat 9 corrected: only one idea was actually blocked, not three. Limit raised to 1,200 characters; replay of the length-refused rules added (section 6).
- 2026-10-10 (04:30 UTC): Take 2 skill stage done; final playbook [R1a, R2x], rounds 3 and 4 kept nothing. Added caveat 9 (five proposals refused for length in rounds 3 and 4, three of them on wrong content).
- 2026-10-10 (02:25 UTC): two optional checks (does R2x need R1a; how much of the test bench score is luck) written up as proposals in [`WIP_NOTES.md`](WIP_NOTES.md), not approved or run. Rounds 3 and 4 started.
- 2026-10-10 (02:12 UTC): Take 2 rounds 1 and 2 done: R1a and R2x kept; R1b passed but was the runner-up; R2y rejected. Added the claim rows for the 2-rule playbook and the checkpoint-habit observation. Caveat 3 now applies twice: two rules selected on the same test bench.
- 2026-10-10: page created, after Take 2 round 1 kept R1a.

## 6. The replay of length-refused rules (post hoc)

- **What:** four rules the loop refused for length in Take 2's rounds 3 and 4, tested as the editor wrote them (886 to 1,073 characters) against the final playbook [R1a, R2x] (0.778, 21 passes), one run per test bench task, with the margin keep test.
- **Why it is weaker evidence than a normal round:** four candidates are tried on the same 60 tasks against one baseline, so the best of four noise draws already looks about +4 points better by luck (one run's standard error is about 3.5 points). A candidate that merely clears the +0.02 margin is a "possible", not a finding.
- **Reading rule, written before the results:** a gain of +7 points or more with passes not lower counts as a clear signal on the test bench; +2 to +7 is "possible"; nothing changes in the playbook without Alexander's OK; the sealed exam is still the judge.
