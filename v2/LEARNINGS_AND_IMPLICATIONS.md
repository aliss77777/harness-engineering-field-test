# Learnings and implications (Take 2)

A living write-up (Alexander asked for it, 2026-10-10). **Part A** covers the playbook learning (MiniMax's rules, rounds 1 to 4 and the replay). **Part B** covers Jev, the rubric and the cutoff, and is added once that stage has run. What each result can and cannot support is in [`WHAT_WE_DID_AND_CAN_CLAIM.md`](WHAT_WE_DID_AND_CAN_CLAIM.md); this page is about what we learned and what follows from it. Terms are the canonical design's.

## Part A: MiniMax's playbook

### What happened

| Step (60 test bench tasks, one run each, checkpoint on) | Credit | Passes |
|---|---|---|
| Starting playbook (no rules); a second draw in V2-5a scored 0.65 | 0.620 | 11 |
| + R1a: do every required write before declaring done | 0.675 | 14 |
| + R2x: read the latest policy and override emails before any write | **0.778** | **21** |
| Eight more candidate rules on top of [R1a, R2x] (rounds 3 and 4, then the replay at up to 1,073 characters) | 0.746 to 0.792 | 19 to 26 |
| Candidates kept after round 2 | **none of 8** | |

### Learnings

1. **The harness learns, and the two rules that stuck are the Phase 0 diagnosis.** MiniMax, from its own graded mistakes and with no Gemini, wrote "finish every required write" and "read the policy emails before you write". Those are the habits we found before any learning ran. The loop found the right things to fix, unaided.

2. **Two rules look like a plateau, and the replay says it is not the length limit.** All eight later candidates landed between 0.746 and 0.792 against a 0.778 baseline. Seven of them (each [R1a, R2x] plus one extra rule) average 0.764 with a spread of 0.020, which is about what pure run-to-run noise on a 60-task mean looks like. The longer versions we let through (886 to 1,073 characters) were no better than the shortened ones that had already been tested.

3. **We now have a measured noise level, and it is smaller than we assumed.** Those seven near-identical playbooks scatter with a standard deviation of about 0.02 (at most; some of that is real difference between rules). We had been assuming 0.03 to 0.035. So the +0.02 margin is about one standard deviation, and a +0.07 gain is about 3.5.

4. **A fairer size for the gain is about +13 points on the test bench, not +16 or +10.** The seven neighbours average 0.764; the starting playbook's two draws average about 0.635. The selected 0.778 was only about 1.4 points above its neighbours, so selection luck at the last step was small. The caveat that remains is the important one: the rules were chosen on these tasks, so unseen tasks are the sealed exam's job.

4b. **A second, softer cross-check on tasks the rules were not chosen on.** The final playbook ran on all 60 practice tasks (stage jevdata). Against the starting playbook's runs on the 45 of those tasks it also ran: credit 0.633 to 0.756 (**+12.3 points**, 95% interval +1.4 to +23.3; 19 tasks better, 8 worse, 18 equal). The editor learned from mistakes on these tasks but never chose between rules on them, so this is a rougher hold-out than the sealed exam. One run per task each, so the interval is wide, but it points the same way as the test bench.

5. **The keep test decided what we learned.** Under the p-value keep test (Take 1) nothing was kept in two rounds; under the margin keep test (Take 2) two rules were kept. The margin test was adopted after seeing Take 1's data, so this is a method finding with a post hoc caveat, not proof the margin test is better. What the margin test does show is that the gains were there to be seen at this sample size.

6. **There is probably a small real gain we cannot resolve.** Two candidates finished about +1.3 and +1.4 points above baseline with +5 and +1 more passes (R3b, and the verbatim checklist in the replay), both under the +0.02 margin. They are consistent with a gain of one to two points, which this design cannot separate from zero. Stacking rules that pass narrowly was noted as an idea for later; at this noise level it would mostly stack noise.

7. **Wrong content is the stubborn failure.** It stays the largest bucket (27 to 40 missed checks per 30 practice runs across all rounds) and rules aimed at it (flags binding, copy verbatim, checklists) did not move it. Prompt rules appear to fix habits (order of actions, finishing the job) but not accuracy of values. That is a hypothesis from this run, not a result.

8. **R2x partly replaces the checkpoint.** With R2x, checkpoint holds fell from 0.75 to 0.15 per run: MiniMax reads the policies first on its own. Question 4 (what the checkpoint adds, final playbook off vs on) may come out small, and that would partly be the learning working, not the checkpoint failing.

9. **The improvement costs nothing per run.** Cost per run stayed at about $0.04 to $0.05 across every playbook. The gain is free in tokens, unlike best-of-K sampling, which is why a better playbook helps the router's economics directly.

### Implications

- **For the main question:** if the sealed exam confirms even +8 to +10 points, MiniMax enters the router noticeably stronger, so fewer tasks need Gemini. The default 30% escalation may be more than needed, and cost could land under half of Gemini's. This is a hypothesis for the sealed exam, not a result.
- **For the design:** the test bench is both our selector and our noise estimate. Using neighbouring candidates to estimate noise (learning 3) is cheap and worth keeping. Borderline candidates (R3b, the verbatim checklist) are exactly where a second run per task would pay off.
- **For the WIP checks:** the neighbours already give an estimate of selection luck, so WIP-2 (a second draw of the final playbook) is mostly answered. WIP-1 (does R2x need R1a?) is still the only test of a "cascade" as opposed to "two good rules".
- **For what comes next:** prompt rules have likely given what they can. The next lever is probably not more or longer rules but the router (when to trust MiniMax) and, for wrong content, something other than a prompt rule. Both are outside Phase 1 as designed.
- **For claims:** keep saying "the harness learned on the test bench" and "the sealed exam decides generalization". Do not say "cascade" without WIP-1.

## Part B: Jev, the rubric and the cutoff

*Written 2026-10-10 06:55 UTC, after jevdata, rubric and tau ran (spend $46.55 of $110; the sealed exam is untouched).*

### What happened

| Stage | What | Result |
|---|---|---|
| jevdata | Final playbook [R1a, R2x] on all 60 practice tasks (Jev's learning data) | 0.727 credit, 19 passes; 57% of runs "good" (credit 0.8 or more) |
| rubric | 3 rounds, 2 candidate edits each; edits tested with McNemar on the test bench | 1 of 6 kept: replace "errors ignored" with "did tool errors actually prevent required actions?" (7 better, 2 worse, p 0.09) |
| tau | Cutoff set so the lowest 30% of test bench runs would go to Gemini | tau = 0.019, frozen |

### Learnings

1. **The rubric fits the practice runs and does not transfer to the test bench.** How well each rubric separates good runs from bad ones, by AUC (0.5 is chance, 1.0 is perfect):

| Data | Starting rubric | Final rubric |
|---|---|---|
| Practice runs it was fitted on (60) | 0.74 | 0.73 |
| **Test bench, final playbook (60)** | **0.42** | **0.475** |
| 992 logged runs of other playbook versions, not used for fitting | 0.56 | 0.55 |

   On the test bench the final rubric's accuracy is 0.567 against 0.533 for always guessing the majority class, and its score correlates slightly *negatively* with credit (-0.13). With 60 runs an AUC has a standard error of about 0.07, so this means "no detectable skill", not "anti-skill". But the gap between 0.73 on the data it was fitted on and 0.475 on new data is the signature of overfitting: eight questions, weights fitted on 60 runs.

2. **The cutoff does not currently separate good runs from bad.** On the test bench, the 18 runs below tau average 0.783 credit and the 42 at or above average 0.776. Routing by it would send a roughly random 30% of tasks to Gemini. On the larger pool of 992 logged runs the split is real but modest (0.628 below tau vs 0.743 above), and that pool mixes playbook versions, so part of that gap is Jev noticing which playbook produced the run, not telling good from bad within one.

3. **The one kept edit helped the accuracy number and not the ranking.** Accuracy on the test bench went 0.483 to 0.567; AUC went 0.42 to 0.475. A "keep" was selected on the same 60 runs, so it is optimistic as well.

4. **Jev is data-starved, not necessarily unlearnable.** v1's Jev learned from 1,000 to 1,500 labelled pairs. Here it had 60 labelled runs to fit and 60 to test on, while about 990 more labelled MiniMax runs (every practice and test bench run in the skill loop and replay) already exist and went unused. That is the most actionable finding.

5. **The old risk is real: Jev reads a summary, not the whole run.** The design already listed "Jev sees a summary, not the whole run" as a risk. With the playbook working, the remaining failures are mostly wrong values inside outputs, which a summary can hide.

### Implications

- **For the router (main comparison):** with no demonstrated skill, a 30% cutoff acts like random escalation. Cost would still land near the target (about $0.14 against Gemini's $0.32 per task, from 0.045 + 0.3 x 0.32), but credit would improve only to the extent Gemini beats MiniMax on the tasks it happens to get. "The router comes close to Gemini for half the cost" would then be true mostly because MiniMax with the playbook is already close, not because Jev knows when to trust it.
- **For what the sealed exam can show:** it will still answer all four questions honestly. Expect "did Jev learn" to be no or unclear. MiniMax alone against Gemini alone can be read from the same sealed runs at no extra cost, and may be the more interesting number now.
- **For the design:** the rubric loop as built (60 fitting runs, 3 rounds, 2 candidates) is too small to learn from. Using the logged runs for fitting with a proper split by task, and a within-playbook test, is the obvious repair. It is a design change for the memo.
- **For claims:** do not say "Jev learned" or "the router works". The supported claim is "the cutoff was set and frozen, and on held-out test bench runs it did not separate good from bad".

### Options for the sealed exam (Alexander's call)

| Option | What | Cost | Trade-off |
|---|---|---|---|
| A. Run it now | Sealed exam as designed, with this rubric and tau | about $45 | Honest answers to all four questions, but the router half is likely uninformative, and it is one-shot |
| **B. Improve Jev first, then run it** | Refit and validate the rubric on the ~990 logged runs (split by task, held-out check within the final playbook), re-set tau, then run sealed | about $1 to $3 plus the sealed $45 | Keeps the exam for a Jev that has shown held-out skill; a design change needing the memo first |
| C. Narrow the exam | Report MiniMax final vs starting vs Gemini, drop the router claim | about $45 | Cleaner, but gives up the router half of the question |

My recommendation is B: it is cheap, the data already exists, and the exam can only be opened once.
