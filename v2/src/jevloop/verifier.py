"""Jev as a verifier (canonical design, Takes: "Jev redesign", 2026-10-10).

Jev reads a richer state (the request, the inbox's policy emails, the source records the run read, the run's writes
in full, and the diff of the records) and answers per-task yes/no questions written once per task from the request
and the policy emails alone. A run's score is the mean probability of yes. Nothing here receives a task's grading
checks, its expected state or the world's `meta` (the same leak rule as the checkpoint).
"""
from __future__ import annotations

import json
import re
from typing import Any

from jevloop.diagnostics import is_write
from jevloop.monitor import policy_emails
from jevloop.rubric import Question

# characters per section of the state; the whole state stays near 24k characters
REQUEST_CHARS, POLICY_EMAIL_CHARS, POLICY_EMAILS_MAX = 2000, 1500, 6
SOURCE_ITEM_CHARS, SOURCE_TOTAL_CHARS = 1800, 9000
WRITE_ITEM_CHARS, WRITES_TOTAL_CHARS, DIFF_CHARS = 1500, 7000, 2500


def _cut(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 12] + " [cut]"


def _fetch_label(call: dict[str, Any]) -> str:
    a = call["args"]
    extra = {k: v for k, v in a.items() if k not in ("method", "url") and v not in (None, "", {})}
    return f"{str(a.get('method', 'GET')).upper()} {a.get('url', '')}" + (f" {json.dumps(extra, ensure_ascii=False, sort_keys=True)}" if extra else "")


def policy_text(initial_state: dict[str, Any]) -> list[dict[str, str]]:
    """The inbox's policy-like emails (the harness's keyword detector), read-only, without `meta`."""
    data = {k: v for k, v in initial_state.items() if k != "meta"}
    out = []
    for m in policy_emails(data)[:POLICY_EMAILS_MAX]:
        out.append({"subject": str(m.get("subject", "")), "body": _cut(str(m.get("body_plain") or m.get("body") or ""), POLICY_EMAIL_CHARS)})
    return out


def state_diff_section(summary: str) -> str:
    """The STATE CHANGES section of the existing run summary."""
    i = summary.find("\nSTATE CHANGES\n")
    return summary[i + len("\nSTATE CHANGES\n"):].strip() if i >= 0 else "(none)"


def build_state(request: str, initial_state: dict[str, Any], calls: list[dict[str, Any]], summary: str) -> str:
    parts = ["REQUEST", _cut(request, REQUEST_CHARS), ""]
    pol = policy_text(initial_state)
    parts += ["POLICY AND GUIDELINE EMAILS IN THE INBOX" + ("" if pol else " (none found)")]
    for m in pol:
        parts += [f"- Subject: {m['subject']}", f"  {m['body']}"]
    parts += ["", "SOURCE RECORDS THE AGENT READ"]
    used, n = 0, 0
    for c in calls:
        if c["name"] != "api_fetch" or is_write(c):
            continue
        item = f"- {_fetch_label(c)}\n  {_cut(str(c.get('result', '')), SOURCE_ITEM_CHARS)}"
        if used + len(item) > SOURCE_TOTAL_CHARS:
            n += 1
            continue
        parts.append(item)
        used += len(item)
    if n:
        parts.append(f"[{n} more reads omitted]")
    parts += ["", "WHAT THE AGENT CHANGED (every record-changing call, in order)"]
    used, w, dropped = 0, 0, 0
    for c in calls:
        if not is_write(c):
            continue
        w += 1
        item = f"{w}. {_fetch_label(c)} -> {_cut(str(c.get('result', '')), 200)}"
        item = _cut(item, WRITE_ITEM_CHARS)
        if used + len(item) > WRITES_TOTAL_CHARS:
            dropped += 1
            continue
        parts.append(item)
        used += len(item)
    if w == 0:
        parts.append("(the agent made no changes)")
    if dropped:
        parts.append(f"[{dropped} more changes omitted]")
    parts += ["", "RESULTING CHANGES TO RECORDS", _cut(state_diff_section(summary), DIFF_CHARS)]
    return "\n".join(parts)


QUESTION_WRITER_V0 = """You write verification questions for a checker that audits what an AI agent did on a business task.

You are given the request and the policy and guideline emails that were in the company's inbox. Write 6 to 10 yes/no questions.
A checker will answer each one by reading a record of the agent's actions (the messages it sent, the records it changed, the
source data it read) against the request and policies. Phrase every question so that YES means the work was done correctly.

Cover, where they apply to this task:
1. Completeness: every required item or recipient was handled, none left out.
2. Prohibitions: nothing was done that the request or a policy email forbids (exclusions, holds, "do not" rules).
3. Accuracy: values, names and identifiers written or sent match the source data exactly.
4. Policy: every applicable policy rule or approval step from the emails was followed.

Be specific to this task: name the items, rules and values involved rather than asking in general terms. Do not ask about
how the agent used its tools. Reply with JSON only: {"questions": [{"text": "..."}, ...]}"""


def question_messages(instructions: str, request: str, policies: list[dict[str, str]]) -> list[dict[str, str]]:
    pol = "\n\n".join(f"Subject: {m['subject']}\n{m['body']}" for m in policies) or "(no policy emails found)"
    return [{"role": "system", "content": instructions},
            {"role": "user", "content": f"REQUEST\n{_cut(request, REQUEST_CHARS)}\n\nPOLICY AND GUIDELINE EMAILS\n{pol}"}]


def parse_questions(content: str, *, max_questions: int = 10) -> list[str]:
    text = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start:end + 1])
    out = [str(q["text"] if isinstance(q, dict) else q).strip() for q in data["questions"]]
    out = [q for q in out if 8 <= len(q) <= 500]
    if len(out) < 3:
        raise ValueError(f"only {len(out)} usable questions")
    return out[:max_questions]


def make_questions(client, instructions: str, task_id: str, request: str, policies: list[dict[str, str]], *, tag: str) -> list[Question]:
    """One reply, or one retry, from the question writer; cached on disk by the client."""
    for attempt in range(2):
        reply = client.complete(question_messages(instructions, request, policies), [],
                                cache_key={"verifier_questions": tag, "task": task_id, "attempt": attempt},
                                event={"event": "verifier_questions", "task_id": task_id, "tag": tag, "attempt": attempt})
        try:
            texts = parse_questions(reply["message"].get("content") or "")
            return [Question(f"q{i + 1}", t, "helps") for i, t in enumerate(texts)]
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    raise ValueError(f"no usable questions for {task_id}")


def verifier_score(probs: dict[str, float]) -> float:
    return sum(probs.values()) / len(probs)


# ---------------- D2 (canonical design, Takes: "Jev verifier, second design") ----------------

COMPLIANCE_WRITER = """You write compliance questions for a checker that audits what an AI agent did on a business task.

You are given the request and the policy and guideline emails that were in the company's inbox. Write 4 to 6 yes/no
questions about what the agent must NOT do or must check first, and nothing else: items, people or accounts that are
excluded, on hold or out of scope; recipients who must not be contacted; limits, thresholds or approvals that must be
respected; "do not" and "only if" rules in the request or the policy emails. A checker answers each by reading a record
of the agent's actions (messages sent, records changed) against the request, the policies and the source data. Phrase
every question so that YES means the agent complied. Name the specific exclusions and rules involved in this task.
Reply with JSON only: {"questions": [{"text": "..."}, ...]}"""

WRITE_CHECK_QUESTIONS = (
    "Is this single action permitted by the request and by every policy email, with nothing excluded, on hold or out of scope involved?",
    "Do the names, amounts, dates and identifiers in this action match the source data exactly?",
    "Is this action addressed to the right recipient or record, as the request and policies require?",
)


def write_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in calls if is_write(c)]


def build_write_state(request: str, initial_state: dict[str, Any], calls: list[dict[str, Any]], write_index: int) -> str:
    """The request, policy emails and source records read, plus ONE record-changing call (the write_index-th) in full."""
    parts = ["REQUEST", _cut(request, REQUEST_CHARS), "", "POLICY AND GUIDELINE EMAILS IN THE INBOX"]
    for m in policy_text(initial_state):
        parts += [f"- Subject: {m['subject']}", f"  {m['body']}"]
    parts += ["", "SOURCE RECORDS THE AGENT READ"]
    used = 0
    for c in calls:
        if c["name"] != "api_fetch" or is_write(c):
            continue
        item = f"- {_fetch_label(c)}\n  {_cut(str(c.get('result', '')), SOURCE_ITEM_CHARS)}"
        if used + len(item) > SOURCE_TOTAL_CHARS:
            continue
        parts.append(item)
        used += len(item)
    w = write_calls(calls)[write_index]
    parts += ["", "THE ACTION TO CHECK", f"{_fetch_label(w)} -> {_cut(str(w.get('result', '')), 300)}"]
    return "\n".join(parts)
