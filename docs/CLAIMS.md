# What the results support

A short ledger. The long version, with dates and every caveat, is [`v2/WHAT_WE_DID_AND_CAN_CLAIM.md`](../v2/WHAT_WE_DID_AND_CAN_CLAIM.md). Numbers are from the sealed exam (80 unseen tasks, one run each) and re-derive with `python3 v2/scripts/rederive_sealed.py`.

## Supported

| Claim | Evidence |
|---|---|
| A cheap open-weight model learned from its own mistakes, on unseen tasks | Credit 0.573 to 0.755: +0.182, 95% interval +0.095 to +0.272, p < 0.001. Fully passed 23 to 33 of 80. |
| It got within about 6 points of Gemini 3.8 Flash at 15% of the cost | 0.755 vs 0.811 (−0.056, interval −0.131 to +0.020); $0.042 vs $0.273 per task. "Close", not "equal": the interval includes zero. |
| The router held Gemini's credit for less | 0.804 vs 0.811 (−0.007, interval −0.061 to +0.053) at 62% of Gemini's cost per task. Not half. |
| Two rules did the work, and they are habits | "Do every required write" and "read the policy emails before any write". Rounds 3 and 4 and a replay of the length-refused rules kept nothing; seven near-identical playbooks scored 0.746 to 0.792, about noise (SD about 0.02). |
| Showing the checker the source records, the policies and the agent's writes roughly doubled its signal over a generic rubric | AUC 0.666 on 120 fresh runs against a preregistered bar of 0.65, opened once; the generic rubric scored 0.475 to 0.525 on held-out runs. On the exam the redesign scored 0.566, so about 0.6 is the fair level. |

## Not supported

| Claim | Why not |
|---|---|
| "The router works" / "the checker chose well" | Against random escalation at the same 45% share the router gained +0.024 (interval −0.02 to +0.07). The checker's AUC on the exam was 0.566 against a bar of 0.65. The credit came from the share sent to Gemini. |
| "The checker learned" | It improved by redesign. The original rubric and its refit did not transfer (AUC 0.475 and 0.525 on held-out runs). Learned instructions added +0.048 AUC, interval includes zero. |
| "The checkpoint is worth keeping with the learned playbook" | At exam time: credit 0.755 on vs 0.775 off; fully passed 33 vs 30; broken "must not" rules 0.80 vs 0.69 per run (interval includes zero). It looks like a training scaffold. |
| "MiniMax matches Gemini" | 5.6 points behind; interval includes zero. |
| "Beats published models" | Different task subset, benchmark version and metric. |
| "The margin keep test is better than the p-value test" | Nothing here compares them on unseen tasks. |
| "This generalises beyond Finance and HR" | Not tested. |

## Limits that apply to everything

- 80 tasks: about ±11 points on a pass rate. Enough for "close", not for "within 3 points".
- One domain pair, one benchmark, simulated systems, not live ones.
- The margin keep test was chosen after seeing the first attempt.
- Test bench numbers are optimistic: the same 60 tasks chose each winner. Only the sealed exam is unbiased.
- Even the strongest model here fully passes only 59% of these tasks. A draft-plus-review deployment is the realistic shape.
