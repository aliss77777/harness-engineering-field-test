"""The Agent skill loop: MiniMax reads its own graded mistakes and edits its own working rules.

v1's rules carry over: one edit per candidate; rejected edits are shown to the editor and
near-copies refused; a fresh sample of mistakes each round; a held-out gate decides. The editor
sees missed checks on **practice** runs only; gate runs contribute only their scores.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from typing import Any

from scipy.stats import wilcoxon

from jevloop.openrouter import ChatClient
from jevloop.runs import CandidateRun

MAX_RULE_CHARS = 400
NEAR_COPY = 0.85  # difflib ratio at or above which a proposed rule counts as a copy
TRIGGER_CHARS = 700
SUMMARY_CHARS = 2500


# ---------- the skill: an ordered list of rules appended to the bench's system prompt ----------

def skill_text(rules: tuple[str, ...]) -> str:
    if not rules:
        return ""
    lines = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
    return "Working rules you have learned from your own past mistakes. Follow them on every task:\n" + lines


def version_id(rules: tuple[str, ...]) -> str:
    return "v0" if not rules else "s" + hashlib.sha256("\n".join(rules).encode()).hexdigest()[:8]


@dataclass(frozen=True)
class Edit:
    op: str  # add | replace | remove
    index: int | None  # 1-based rule number for replace / remove
    text: str
    why: str = ""

    def record(self) -> dict[str, Any]:
        return asdict(self)


def apply_edit(rules: tuple[str, ...], edit: Edit) -> tuple[str, ...]:
    if edit.op == "add":
        return rules + (edit.text.strip(),)
    i = (edit.index or 0) - 1
    if edit.op == "replace":
        return rules[:i] + (edit.text.strip(),) + rules[i + 1:]
    if edit.op == "remove":
        return rules[:i] + rules[i + 1:]
    raise ValueError(f"unknown op {edit.op!r}")


def check_edit(edit: Edit, rules: tuple[str, ...], rejected: list[Edit]) -> str | None:
    """None if the edit is acceptable, else the reason it is refused."""
    if edit.op not in ("add", "replace", "remove"):
        return f"unknown op {edit.op!r}"
    if edit.op in ("replace", "remove") and not (edit.index and 1 <= edit.index <= len(rules)):
        return f"rule number {edit.index} does not exist"
    if edit.op != "remove":
        text = edit.text.strip()
        if not text or len(text) > MAX_RULE_CHARS:
            return f"rule must be 1-{MAX_RULE_CHARS} characters"
        if "@" in text or "$" in text or re.search(r"\d{3,}", text):
            return "rule names a specific address, amount or ID; rules must be general"
        for old in [*rules, *(r.text for r in rejected)]:
            if difflib.SequenceMatcher(None, text.lower(), old.lower()).ratio() >= NEAR_COPY:
                return "near-copy of an existing or previously rejected rule"
    return None


# ---------- the gate: paired comparison on the same held-out tasks ----------

@dataclass(frozen=True)
class GateDecision:
    keep: bool
    mean_diff: float  # candidate minus current, mean partial credit
    p_value: float
    better: int
    worse: int
    tasks: int

    def record(self) -> dict[str, Any]:
        return asdict(self)


def gate_decision(current: dict[str, float], candidate: dict[str, float], *, p_threshold: float) -> GateDecision:
    """Keep if the candidate's partial credit beats the current version's on the same gate tasks:
    mean difference > 0 and one-sided Wilcoxon signed-rank p < p_threshold (ties dropped)."""
    if set(current) != set(candidate):
        raise ValueError("gate needs both versions on the same tasks")
    diffs = [candidate[t] - current[t] for t in sorted(current)]
    nonzero = [d for d in diffs if d != 0]
    p = float(wilcoxon(nonzero, alternative="greater").pvalue) if len(nonzero) >= 1 else 1.0
    mean = sum(diffs) / len(diffs)
    return GateDecision(mean > 0 and p < p_threshold, mean, p, sum(d > 0 for d in diffs),
                        sum(d < 0 for d in diffs), len(diffs))


def best_passing(decisions: list[tuple[Edit, GateDecision]]) -> tuple[Edit, GateDecision] | None:
    passing = [(e, d) for e, d in decisions if d.keep]
    return max(passing, key=lambda ed: (ed[1].mean_diff, -ed[1].p_value)) if passing else None


# ---------- what the editor sees ----------

def describe_check(check: dict[str, Any]) -> str:
    kind = "MUST NOT (broken)" if check.get("negative") else "REQUIRED (not met)"
    return f"{kind}: {check['type']} {json.dumps(check.get('params', {}), sort_keys=True, ensure_ascii=False)[:300]}"


def mistakes_report(practice_runs: list[CandidateRun], *, limit: int, rng: random.Random) -> list[dict[str, Any]]:
    """A fresh sample of failed practice runs: what the task asked, what the agent did, which checks it missed."""
    failed = [r for r in practice_runs if not r.passed]
    rng.shuffle(failed)
    report = []
    for r in failed[:limit]:
        trigger, _, rest = r.summary.partition("\n\nACTIONS")
        report.append({
            "task_id": r.task_id,
            "partial_credit": round(r.partial_credit, 2),
            "request": trigger.replace("TRIGGER\n", "", 1)[:TRIGGER_CHARS],
            "what_you_did": ("ACTIONS" + rest)[:SUMMARY_CHARS],
            "missed_checks": [describe_check(m) for m in r.missed_checks],
            "steps": r.steps,
            "stop_reason": r.stop_reason,
        })
    return report


EDITOR_SYSTEM = """You are an AI agent that automates back-office work (finance and HR) using company tools.
You are improving your own working rules by studying your own mistakes. You will see tasks you recently got wrong:
what each task asked, what you did, and which grading checks you missed ("REQUIRED (not met)" means you failed to do
something required; "MUST NOT (broken)" means you did something you should not have done).

Propose exactly {n} DIFFERENT candidate edits to your working rules. Each candidate is ONE edit:
- {{"op": "add", "index": null, "text": "<new rule>", "why": "<the mistake pattern it fixes>"}}
- {{"op": "replace", "index": <rule number>, "text": "<new wording>", "why": "..."}}
- {{"op": "remove", "index": <rule number>, "text": "", "why": "..."}}

Rules must be GENERAL habits that help across many different finance and HR tasks. Never mention specific people,
email addresses, companies, amounts, dates or IDs. Do not repeat or rephrase rules that already exist or were rejected.
Reply with JSON only: {{"edits": [ ... ]}}"""


def editor_prompt(rules: tuple[str, ...], mistakes: list[dict[str, Any]], rejected: list[Edit], n: int) -> list[dict[str, str]]:
    current = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1)) or "(none yet)"
    tried = "\n".join(f"- {e.op} {e.index or ''}: {e.text}" for e in rejected) or "(none)"
    user = (f"YOUR CURRENT WORKING RULES:\n{current}\n\nEDITS ALREADY TRIED AND REJECTED (they did not help):\n{tried}\n\n"
            f"YOUR RECENT MISTAKES ({len(mistakes)} tasks):\n{json.dumps(mistakes, indent=1, ensure_ascii=False)}")
    return [{"role": "system", "content": EDITOR_SYSTEM.format(n=n)}, {"role": "user", "content": user}]


def parse_edits(content: str) -> list[Edit]:
    text = content.strip()
    fenced = re.search(r"\{.*\}", text, re.S)
    data = json.loads(fenced.group(0) if fenced else text)
    out = []
    for e in data.get("edits", []):
        index = e.get("index")
        out.append(Edit(op=str(e.get("op", "")).lower(), index=int(index) if index not in (None, "") else None,
                        text=str(e.get("text") or ""), why=str(e.get("why") or "")))
    return out


class SkillEditor:
    """MiniMax as its own editor (no tools). Invalid or refused edits are dropped; if fewer than `n`
    survive, it is asked once more with the reasons."""

    def __init__(self, client: ChatClient):
        self.client = client

    def propose(self, rules: tuple[str, ...], mistakes: list[dict[str, Any]], rejected: list[Edit], *,
                n: int, round_number: int) -> tuple[list[Edit], list[dict[str, Any]]]:
        messages = editor_prompt(rules, mistakes, rejected, n)
        refused: list[dict[str, Any]] = []
        accepted: list[Edit] = []
        for attempt in range(2):
            reply = self.client.complete(messages, [], cache_key={"editor": "skill", "round": round_number, "attempt": attempt},
                                         event={"event": "skill_editor", "round": round_number, "attempt": attempt})
            content = reply["message"].get("content") or ""
            try:
                proposals = parse_edits(content)
            except (ValueError, json.JSONDecodeError) as error:
                proposals, refused = [], refused + [{"edit": content[:300], "reason": f"unparseable: {error}"}]
            for edit in proposals:
                reason = check_edit(edit, rules, rejected + accepted)
                if reason:
                    refused.append({"edit": edit.record(), "reason": reason})
                elif len(accepted) < n:
                    accepted.append(edit)
            if len(accepted) >= n:
                break
            messages = messages + [{"role": "assistant", "content": content},
                                   {"role": "user", "content": "Some edits were refused: "
                                    + json.dumps(refused[-5:], ensure_ascii=False)
                                    + f". Reply with JSON containing {n - len(accepted)} more valid, general, new edits."}]
        return accepted, refused
