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

*Terms: "Jev refit", "Jev redesign (first / second attempt)", "AUC" and "same-playbook comparison" are explained in the README's Jev section and the memo's words table. Written 2026-10-10 06:55 UTC, after jevdata, rubric and tau ran (spend $46.55 of $110; the sealed exam is untouched).*

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

### The Jev refit (2026-10-10, 14:50 UTC): the bar was not met

Pre-registered in the canonical design before running: refit the weights of the final 8-question rubric on all 1,052 labelled runs (120 tasks), 5-fold cross-validation grouped by task, test on the final playbook's run on each held-out task (120 runs). Bar: AUC at least 0.65 with a 95% lower bound above 0.5, and the lowest 30% averaging at least 0.10 credit below the rest.

| Variant (120 held-out final-playbook runs) | AUC [95% interval] | Credit of lowest 30% vs rest | Correlation with credit |
|---|---|---|---|
| **Primary: final rubric, weights refit (C = 1)** | **0.525** [0.42, 0.63] | 0.696 vs 0.777 (gap 0.081) | +0.23 |
| Starting rubric, weights refit | 0.531 [0.43, 0.63] | gap 0.102 | +0.24 |
| Final rubric, refit C = 0.1 / C = 10 | 0.524 / 0.523 | gap 0.109 / 0.066 | +0.23 / +0.21 |
| As they were (partly in-sample) | 0.58 to 0.60 | gap 0.11 to 0.12 | +0.30 to +0.36 |

**Bar met: no.** More data did not rescue the rubric: the honest, cross-validated AUC is about 0.52, and even the in-sample "as they were" figures are only 0.58 to 0.60. The refit also did not make the "lowest 30%" much worse than the rest (a gap of 0.08, against 0.10 needed).

**Diagnostics (exploratory, not part of the bar):**
- **Per failure kind, how well Jev's score predicts that a run has a miss of that kind:** rules broken 0.49, skipped actions 0.58, wrong content 0.54. It cannot see any of the three.
- **Harness telemetry alone** (checkpoint holds, steps, tool calls, model calls, cost, seconds, summary length) predicts good vs bad at AUC 0.51. So this is not a case where a cheap run-level signal was ignored; there is none.
- **Fully-passed label instead of credit at or above 0.8:** AUC 0.57, so the choice of label is not the explanation.

### What this means

- **The failures are hidden in details a generic checklist cannot see.** Whether a value is right, an exclusion was honoured, or the right recipient got the message depends on the task's own data. Eight generic questions read from a run summary cannot check that. More labelled runs for fitting the same questions will not change that.
- **The honest reading of Jev as built:** it did not learn to tell good runs from bad on this task, even given 17 times more data. It remains a finding about this design, not about Jev in general: v1's task had a one-bit answer that a rubric could reflect.
- **The router needs a different kind of checker:** one that checks outputs against the task's own request, source data and policy emails (a verifier), not a generic judge of a summary. That is the Jev analogue of the harness redesign we did for MiniMax.

### Options (Alexander's call)

| Option | What | Cost | Notes |
|---|---|---|---|
| A. Run the sealed exam now | As designed, with the frozen rubric and cutoff | about $45 | Router half will be close to random escalation; the MiniMax vs Gemini and learning questions are answered honestly |
| Edit the questions on the pooled data (the refit's second option) | MiniMax proposes new questions, scored by cross-validation | about $1 to $3 | Low odds: the problem is not the weights, and generic questions share the blind spot |
| **C. Run the sealed exam narrowed** | Report MiniMax final vs starting vs Gemini, router reported as "Jev as built shows no skill; cutoff acts like random escalation" | about $45 | Cleanest honest result for this phase |
| **Redesign Jev's input, then decide (the redesign)** | Give Jev what it needs to verify: the request, source data, policy emails and the run's writes; questions that check values against source; pre-registered AUC bar on held-out tasks; may need new MiniMax runs for labels | about $5 to $15 to try, plus design time | The real fix; a bigger design change needing the memo first. Sealed exam waits |

My recommendation: C now or D first, depending on how you weigh the one-shot exam. C closes Phase 1 cleanly and keeps D as the headline of what comes next. D is the better use of the exam if you want the router half to be meaningful, at the cost of a delay.

### A check on how much a better Jev could be worth (2026-10-10, 15:10 UTC; free, from logged runs) [superseded by the larger ceiling check below]

On the 20 practice and test bench tasks that have Gemini runs from Phase 0 and the temperature-0 re-checks (about 2 Gemini runs per task, averaged) and the final playbook's MiniMax run:

| | Credit |
|---|---|
| MiniMax, final playbook | 0.713 |
| Gemini alone | 0.669 |
| Tasks where MiniMax scored under 0.8 (11): MiniMax / Gemini | 0.563 / 0.591 |
| Tasks where MiniMax scored 0.8 or more (9): MiniMax / Gemini | 0.896 / 0.763 |
| Router that escalates MiniMax's worst 30% to Gemini, with a perfect failure detector | 0.699 |
| Random 30% escalation (expected) | 0.700 |

So on this small sample, **MiniMax is already at or above Gemini, and where MiniMax fails Gemini does only about 3 points better**: the hard tasks are hard for both. Even a perfect failure detector would not lift the router above MiniMax alone (0.699 vs 0.713; n = 20, one MiniMax run each, so treat as indicative). If that holds on the sealed exam, a better Jev has little quality to buy by routing to Gemini, and a router costs more than MiniMax alone. Jev's value would then be as a **guardrail** (flag runs for human review) rather than a router. The sealed exam's head-to-head, MiniMax final vs Gemini alone on 80 tasks, will show which world we are in.

### Jev redesign, first attempt (2026-10-10, 15:25 UTC): a real improvement, still short of the bar

Built as pre-registered: Jev reads the request, the policy emails, the source records the run read, the writes in full and the diff; per-task yes/no questions are written by MiniMax from the request and policy emails; a run's score is the mean probability of yes; the question writer's instructions are learned on development tasks; validation (test bench runs) is opened once. Total spend under $0.50 for Jev and question writing.

| On the 840 test bench runs of 14 playbook versions (validation, opened once) | Within-playbook AUC [95%] | Within-task AUC | Lowest 30% vs rest (gap) |
|---|---|---|---|
| Generic rubric, final (as fitted) | 0.511 [0.42, 0.61] | 0.53 | 0.058 |
| Generic rubric, starting (as fitted) | 0.518 [0.42, 0.62] | 0.57 | 0.066 |
| **Verifier, learned instructions (frozen)** | **0.612 [0.51, 0.72]** | **0.714** | **0.166** [0.08, 0.28] |
| Bar (fixed in advance) | 0.65, lower bound above 0.5 | | 0.10 |

**Bar met: no** (AUC 0.612 against 0.65; the gap clears 0.10 and the lower bound clears 0.5). Development went 0.650 (starting instructions) to 0.677 (one kept edit; two further rounds kept nothing), so most of the gain came from the design, not from learning the instructions.

### Learnings from the first attempt

1. **Giving Jev what it needs to verify roughly doubled its useful signal.** The generic rubric sat at chance (0.51); the verifier, with no fitted weights, is at 0.61, and the runs it scores lowest are 17 points of credit worse than the rest (against 6). The diagnosis was right: the checker could not see the source.
2. **It works best where the agent is weakest, and fades as the agent improves.** Within-playbook AUC by version runs from 0.70 (starting playbook) down through 0.65 (R1a) to 0.48 for the final playbook (n = 60, interval 0.33 to 0.64). The failures left in the best playbook are the subtle ones. That is exactly where a router would be used, so the deployment case is not yet met.
3. **It detects some failure kinds and not others.** Across all runs, a low score flags skipped actions (AUC 0.67) and wrong content (0.66) but not broken rules (0.48). On the final playbook alone the figures are 0.58, 0.60 and 0.50. Broken rules need reasoning about what a policy forbids, which the questions do not elicit.
4. **Within-task comparisons are strong (0.71), but partly because runs of the same task come from different playbooks.** A checker that can tell a run from a better playbook is useful for evaluation; it is not what a router needs.
5. **The learned instructions added little.** The kept edit (do not invent procedures; ask about specific findings; ask prohibitions positively) is sensible, and it gained 0.027 on development; on validation the gap to the generic rubric is mostly the verifier design itself.

### What this means

- **Per the pre-registration, the router claim is not supported:** Jev as a verifier has not met the bar on validation, and on the final playbook it shows no discrimination (n = 60, wide interval). The sealed exam would report MiniMax against Gemini without a router claim.
- **The direction is right and worth continuing,** which is your point that Jev needs a redesign as large as the harness got. The next gains likely come from: several independent question sets averaged (the questions are one sample from one model); a policy-compliance question set aimed at rules broken; checking each write separately and taking the worst; and more labelled runs of the final playbook, which are the ones that matter.
- **The test bench validation is now used up.** More design work needs fresh labelled runs, for example two or three more draws of the final playbook on the practice and test bench tasks (about 240 runs, about $11), then a second pre-registered validation. The Gemini ceiling check (about $17) still decides how much a better Jev is worth.

### The Gemini ceiling check (2026-10-10, 15:50 UTC; $15.30): a better Jev is worth real credit

Gemini (as it comes: no playbook, no checkpoint) on the 54 of 120 practice and test bench tasks where the final playbook's MiniMax run scored under 0.8. This **supersedes the earlier 20-task indication**, which suggested almost no upside; with 54 failed tasks the picture is clear.

| 120 practice and test bench tasks, one run each | Credit |
|---|---|
| MiniMax, final playbook, all tasks | 0.753 |
| On the 54 tasks MiniMax failed: MiniMax | 0.528 |
| On the same 54: Gemini (20 fully passed) | **0.696** |
| **Perfect failure detector, escalating all 54 failures (45%)** | **0.828** (+7.5 points) |
| Perfect failure detector, escalating the worst 30% | **0.820** (+6.7 points) |

**What it means.**
1. **Where MiniMax fails, Gemini is clearly better (+17 points on those tasks),** so a router has real room: up to about +7 points over MiniMax alone, at roughly 30% more cost than MiniMax alone (Gemini about $0.28 a run on the escalated 30%).
2. **The value is entirely in how well Jev finds the failures.** The gain from escalating a set of runs is about (Gemini's credit on them minus MiniMax's credit on them) x their share. Escalating a random 30%, or a set whose MiniMax credit is 0.735 (what the first verifier's lowest 30% achieved on the final playbook), buys about nothing, because Gemini is not better than MiniMax on tasks MiniMax already does well (0.735 against about 0.70). To gain 4 points the escalated 30% must average about 0.55 MiniMax credit. A perfect detector's worst 30% averages near 0.35.
3. **Part of the 0.528 is bad luck.** Failed runs include unlucky draws, so a fresh MiniMax run on the same tasks would score above 0.528. The fresh runs in progress will measure this (and whether simply re-running MiniMax, at $0.045, is a cheaper fallback than Gemini at $0.28).
4. **The business reading is the one you suggested:** with a perfect detector the lift is about +7 points of credit; even capturing a third of it is +2 to +3 points. That is the prize Jev's redesign is chasing, and it justifies D2.

### Jev redesign, second attempt (2026-10-10, 16:45 UTC): bar met, with a caveat

As pre-registered: two fresh independent runs of the final playbook on every practice and test bench task (240 runs, $11.11); variants 1 to 4 scored on the practice-task runs (development, 180 runs); the best variant chosen there; then scored once on the fresh test bench runs (120 runs, 60 tasks).

| Fresh test bench runs of the final playbook (opened once) | AUC [95%] | Lowest 30% vs rest | Gap |
|---|---|---|---|
| Variant 1 (the first attempt as frozen) | 0.663 [0.54, 0.79] | 0.602 vs 0.774 | 0.173 |
| Variant 2 (average of 3 question sets) | 0.655 [0.53, 0.78] | 0.600 vs 0.775 | 0.175 |
| **Variant 3 (variant 2 + compliance questions), chosen on development** | **0.666 [0.55, 0.78]** | **0.587 vs 0.781** | **0.194** [0.07, 0.33] |
| Variant 4 (variant 3 + worst single write) | 0.588 [0.48, 0.70] | 0.637 vs 0.759 | 0.122 |
| Bar (fixed in advance) | 0.65, lower bound above 0.5 | | 0.10 |

**Bar met: yes** (0.666 and a lower bound of 0.548; gap 0.194). Development scores for the same variants were 0.608, 0.596, 0.648 and 0.602.

**Learnings.**
1. **The redesign works on the playbook we will deploy,** at about 0.67 AUC on fresh runs, and the runs it scores lowest are 19 points of credit worse than the rest.
2. **Most of the gain came from the first attempt's design, not from the variants.** Variant 3 beats variant 1 by 0.003 on validation and by 0.04 on development. The first attempt scored 0.48 on the final playbook's original 60 runs, 0.61 on 180 development runs and 0.66 on the fresh 120. These differ by more than the sample sizes would explain, so I would put the true level around 0.60 to 0.65. The pre-registered bar is met, and the honest claim is "about 0.6 to 0.65".
3. **A per-write worst-case check hurt** (variant 4, 0.588). One bad-looking write is not a good signal of a failed run on its own.
4. **It flags wrong content best (0.72), skipped actions next (0.61) and rules broken barely (0.53).** Broken rules remain the blind spot.
5. **The test bench tasks were seen by the first attempt's validation** (their fresh runs were not), and the variants were motivated by that result. Both were recorded in advance.

**What it implies for the router.** The cutoff is frozen at 0.756 (the 30th percentile of variant 3's scores on these 120 runs). The 36 runs below it averaged 0.587 MiniMax credit against 0.722 overall. From the ceiling check, Gemini averaged 0.696 on tasks MiniMax failed. A rough estimate, not a measurement: escalating that lowest 30% to Gemini would gain about 0.3 x (0.70 - 0.587), roughly **+3 points of credit**, at about $0.13 per task against $0.28 for Gemini alone. The sealed exam is what measures it.

### Did Jev learn in v2? (2026-10-10, 17:00 UTC)

The Jev became useful through **redesign** (what it sees, per-task questions), not through learning from outcomes. The learned part is one kept edit to the question writer's instructions. A direct check on the same 120 fresh runs: starting instructions AUC 0.615 [0.49, 0.75], learned 0.663 [0.54, 0.79], a difference of +0.048 (95% interval −0.027 to +0.129; lowest-30% gap 0.185 against 0.173). That is a small step in the right direction that cannot be told from zero. Honest wording: "Jev's usefulness on v2 came from design; learning from outcomes added at most a small, uncertain amount." Cost $0.105.

