"""Profile AutomationBench's domains from the task data alone (no model calls).

    .venv/bin/python scripts/profile_domains.py

Writes phase0/domain_profile.json; the numbers in phase0/DOMAINS.md come from it.
"""
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from automationbench.rubric.registry import AssertionRegistry  # noqa: E402
from automationbench.schema.world import WorldState  # noqa: E402

from jevloop import bench  # noqa: E402

INTERNAL_DOMAIN = "@company.example.com"
# Where a graded check lands. "Systems of record" are the business applications a function runs on.
CATEGORIES = {
    "accounting": {"quickbooks", "xero", "wave"},
    "hr_systems": {"bamboohr", "recruitee"},
    "help_desks": {"freshdesk", "gorgias", "helpcrunch", "helpscout", "hiver", "intercom", "reamaze", "zendesk", "zoho_desk"},
    "crm": {"salesforce", "hubspot"},
    "work_management": {"asana", "basecamp3", "jira", "monday", "trello", "pipefy", "airtable", "notion", "confluence"},
    "spreadsheets_files": {"google_sheets", "google_drive"},
    "email": {"gmail"},
    "chat_sms": {"slack", "twilio"},
    "calendar_meetings_esign": {"google_calendar", "calendly", "zoom", "docusign"},
    "ads_social_campaigns": {"google_ads", "facebook_conversions", "facebook_lead_ads", "facebook_pages", "instagram",
                             "linkedin", "linkedin_ads", "linkedin_conversions", "linkedin_leadgen_forms", "twitter",
                             "buffer", "mailchimp", "canva"},
    "other": {"chatgpt"},
}
GTM_SERVICES = CATEGORIES["ads_social_campaigns"] | CATEGORIES["crm"]
# Approximate keyword grouping of task names into sub-functions (first match wins).
SUBFUNCTION_RULES = {
 "finance": [
  ("Accounts payable & vendor payments", r"multicurrency_payment|fraud|vendor|bill|ap_|po_|purchase|three_way|1099|duplicate_payment|wire|early_pay|payment_approval|xero_po"),
  ("Accounts receivable, billing & collections", r"payment_terms|invoice|billing|receivable|collection|late_fee|credit_limit|customer_balance|estimate|quote|sales_receipt|statement|dispute|refund|bad_debt|undeposited|subscription|credit_allocation|customer_onboard|product_catalog"),
  ("Close, reconciliation & accounting", r"recon|journal|close|closing|accru|amortiz|depreciation|deferred|revenue_recog|intercompany|forex|fiscal|prepaid|lease|escrow|inventory_valuation|audit|reclass|cash_sweep|bank"),
  ("Expenses & reimbursements", r"expense|reimburs|receipt|travel|petty|card"),
  ("FP&A, budgeting & analysis", r"budget|forecast|variance|analysis|ratio|margin|profitab|rollup|allocation|commission|grant|capex|spend"),
  ("Tax & compliance", r"tax|compliance"),
  ("Payroll", r"payroll"),
 ],
 "hr": [
  ("Recruiting & hiring", r"candidate|interview|job_|recruit|offer|referral|background|submittal|intern_cohort|channel_roi"),
  ("Onboarding, offboarding & transfers", r"onboard|offboard|termination|new_hire|equipment|buddy|transfer|orientation|return_from_leave|exit|severance|contractor|restructure|directory|it_onboarding|slack_channel"),
  ("Compensation, payroll & benefits", r"comp_|salary|payroll|bonus|benefit|tuition|pto|break"),
  ("Compliance, policy & training", r"expense_report|compliance|training|policy|handbook|i9|visa|nda|security_access|safety|rto|mandatory|learning|skills"),
  ("Performance & employee relations", r"performance|pip|disciplinary|grievance|probation|recognition|anniversary|promotion|succession|feedback"),
  ("Workforce planning & HR analytics", r"headcount|workforce|diversity|analytics|survey|pipeline_report|standup|data_migration"),
  ("Employee services & communications", r"request|inquiry|notification|announcement|all_hands|office_hours|meeting|emergency|twilio|notion|intern_program|event"),
 ],
 "operations": [
  ("Sales/marketing-flavoured (GTM)", r"hubspot|mailchimp|facebook|google_ads|linkedin|buffer|canva|salesforce|prospect|deal_review|churn|outreach"),
  ("Facilities, safety & EHS", r"fire|safety|hazmat|chemical|gas|generator|facilit|housekeeping|parking|space|energy|utility|mailroom|dock|room|lease|move|visitor|inspection|maintenance|sensor|drill|perishable"),
  ("IT, security & incidents", r"access|incident|server|dr_drill|change_advisory|badge|(^|_)sla(_|$)"),
  ("Procurement, vendors & contracts", r"vendor|procurement|purchase|contract|insurance|equipment_lease|invoice_shipping|budget|cost"),
  ("People operations & scheduling", r"training|overtime|holiday|temporary|cross_training|contractor|calibration"),
  ("Projects, compliance & internal comms", r"annual_review|compliance|audit|asana|trello|monday|notion|confluence|drive|zoom|sheets|calendar|policy|playbook|kickoff|board|inventory|feedback|calendly"),
 ],
 "support": [
  ("Customer-facing responses & retention", r"response|reply|winback|reactivation|nurture|trial|loyalty|campaign|demo|callback|csat_followup|faq|auto_response|onboarding|renewal|refund|warranty|order_lookup"),
  ("Routing, escalation & SLA", r"routing|escalat|(^|_)sla(_|$)|handoff|queue|waterfall|weekend|categoriz|tagging|lifecycle|knowledge_routing|multi_product"),
  ("Data sync, migration & hygiene", r"sync|migration|merge|dedup|reconciliation|data_quality|gdpr|bridge|enrichment|360|isolation|consolidation"),
  ("QA, reporting & workforce management", r"audit|quality|coaching|report|digest|performance|capacity|forecast|analysis|patterns|root_cause|scoring|health|sentiment|effort|journey|satisfaction|alerts|kb_|gap|feedback|feature_request|defect|bugs|fraud|risk|vendor|compliance|maintenance|inventory|multilanguage|usage"),
 ],
}
SERVICES = sorted((f for f in WorldState.model_fields if f != "meta"), key=len, reverse=True)
CATEGORY_OF = {s: c for c, members in CATEGORIES.items() for s in members}


def service_of(check_type: str) -> str:
    return next((s for s in SERVICES if check_type == s or check_type.startswith(s + "_")), "unknown")


def recipients(check: dict) -> list[str]:
    to = check.get("to")
    return [to] if isinstance(to, str) else list(to or [])


def profile_task(task: bench.Task) -> dict:
    checks = task.assertions
    services = [service_of(c["type"]) for c in checks]
    positive_to = [r for c in checks if not AssertionRegistry.is_negative(c["type"]) for r in recipients(c)]
    seeded = {s for s, v in task.initial_state.items() if v and s != "meta"}
    return {
        "task_id": task.task_id,
        "checks": len(checks),
        "negative_checks": sum(AssertionRegistry.is_negative(c["type"]) for c in checks),
        "check_services": sorted(set(services)),
        "check_categories": Counter(CATEGORY_OF.get(s, "other") for s in services),
        "seeded_services": sorted(seeded),
        "systems_touched": len(seeded | set(services)),
        "prompt_words": len(task.public.trigger.split()),
        "emails_to_internal": sum(r.endswith(INTERNAL_DOMAIN) for r in positive_to),
        "emails_to_external": sum(not r.endswith(INTERNAL_DOMAIN) for r in positive_to),
        "gtm_systems": bool((seeded | set(services)) & GTM_SERVICES),
    }


def profile_domain(tasks: list[bench.Task]) -> dict:
    rows = [profile_task(t) for t in tasks]
    checks = sum(r["checks"] for r in rows)
    cats = sum((r["check_categories"] for r in rows), Counter())
    to_int = sum(r["emails_to_internal"] for r in rows)
    to_ext = sum(r["emails_to_external"] for r in rows)
    return {
        "tasks": len(rows),
        "median_checks": statistics.median(r["checks"] for r in rows),
        "mean_checks": round(statistics.fmean(r["checks"] for r in rows), 1),
        "negative_check_share": round(sum(r["negative_checks"] for r in rows) / checks, 3),
        "tasks_with_negative_checks": sum(r["negative_checks"] > 0 for r in rows),
        "median_systems_touched": statistics.median(r["systems_touched"] for r in rows),
        "median_prompt_words": statistics.median(r["prompt_words"] for r in rows),
        "check_share_by_category": {c: round(n / checks, 3) for c, n in cats.most_common()},
        "graded_email_recipients_internal_share": round(to_int / (to_int + to_ext), 3) if to_int + to_ext else None,
        "tasks_touching_gtm_systems": sum(r["gtm_systems"] for r in rows),
        "gtm_task_ids": [r["task_id"] for r in rows if r["gtm_systems"]],
    }


def task_names() -> dict[str, str]:
    """task_id -> the bench's descriptive task name (e.g. finance.overdue_invoice_followup)."""
    from automationbench.domains import get_domain_dataset

    names = {}
    for domain in bench.domains():
        for row in get_domain_dataset(domain):
            info = row["info"]
            info = json.loads(info) if isinstance(info, str) else info
            names[f"{domain}:{row['example_id']}"] = info.get("task_name", "").split(".", 1)[-1]
    return names


def subfunctions(domain: str, names: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for name in names:
        label = next((g for g, pattern in SUBFUNCTION_RULES[domain] if re.search(pattern, name)), "unmatched")
        groups.setdefault(label, []).append(name)
    return {g: sorted(v) for g, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))}


def main() -> None:
    tasks = bench.load_tasks(bench.domains())
    names = task_names()
    out = {}
    for domain in bench.SCORED_DOMAINS + ["simple"]:
        out[domain] = profile_domain([t for t in tasks if t.public.domain == domain])
        if domain in SUBFUNCTION_RULES:
            out[domain]["subfunctions"] = subfunctions(domain, [names[t.task_id] for t in tasks if t.public.domain == domain])
    path = ROOT / "phase0" / "domain_profile.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    cols = ["tasks", "median_checks", "negative_check_share", "median_systems_touched",
            "median_prompt_words", "graded_email_recipients_internal_share", "tasks_touching_gtm_systems"]
    print("domain".ljust(11) + "".join(c[:14].rjust(15) for c in cols))
    for d, p in out.items():
        print(d.ljust(11) + "".join(str(p[c]).rjust(15) for c in cols))
    for d, p in out.items():
        print(f"{d}: " + ", ".join(f"{c} {v:.0%}" for c, v in p["check_share_by_category"].items()))
    for d, p in out.items():
        for g, members in p.get("subfunctions", {}).items():
            print(f"{d} | {g}: {len(members)}")
    print(f"\nwritten: {path}")


if __name__ == "__main__":
    main()
