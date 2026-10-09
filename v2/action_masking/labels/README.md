# Email labels for the policy-email detector (work item A2)

**What to do (≈ 20 minutes):** open `email_labels.csv` and fill the `your_label` column for every row with one of:

- **policy**: the email states a rule, procedure, exclusion or approval requirement that the task's work should follow (for example, a collections SOP, an AP guideline, a list of vendors on hold, "do not contact X").
- **not**: ordinary business email (a request, a notification, a reminder, an invoice, chit-chat), even if it mentions a process.
- **unsure**: can't tell. These are counted separately and left out of precision and recall.

The `detector_says` column is what the keyword detector decided; please label each email on its own merits.

**Why:** the action-masking checkpoint holds a write until the agent has read the task's policy emails, so it is only as good as the detector that decides which emails are policy. Your labels measure its precision (when it says "policy", is it right?) and recall (does it find the real policy emails?). If either is below 0.8, the detector stays marked "approximate".

**How the sheet was drawn** (seed `20261008:labels`): 10 tasks where the detector fires and the 4 tasks where it doesn't, among tasks MiniMax has logged runs on, plus every other quiet task in Finance and HR (the detector fires on almost every task that has email, so quiet tasks are rare; recall is measured mainly on the non-flagged emails inside flagged tasks). Every email in each task is listed.
