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

MAX_RULE_CHARS = 1200  # was 400 (pilot) then 600 (Take 1, Take 2 rounds 1-4); raised 2026-10-10: the editor wrote 627-1,073 character rules
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
    target: str = ""  # redesign: the check kind this fix targets (rule_broken | action_missed | wrong_content)

    def record(self) -> dict[str, Any]:
        return asdict(self)


def length_refused_edits(history: list[dict[str, Any]], *, from_round: int = 1) -> list[Edit]:
    """Proposals the loop refused for length alone, as Edits, from a saved skill history. At most one per
    (round, target kind): the longest, which is the editor's own first draft rather than a condensed retry."""
    best: dict[tuple[int, str], Edit] = {}
    for rnd in history:
        if rnd["round"] < from_round:
            continue
        for ref in rnd.get("refused", []):
            e = ref.get("edit")
            if not isinstance(e, dict) or not str(ref.get("reason", "")).startswith("rule must be 1-"):
                continue
            edit = Edit(e["op"], e.get("index"), e["text"], e.get("why", ""), e.get("target", ""))
            key = (rnd["round"], edit.target)
            if key not in best or len(edit.text) > len(best[key].text):
                best[key] = edit
    return [best[k] for k in sorted(best)]


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
            return f"rule must be 1-{MAX_RULE_CHARS} characters: shorten it and resubmit"
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
    """A fresh sample of failed practice runs: what the task asked, what the agent did, which checks it missed.
    Near-misses count as failures (V2-5, work item D): a run the gate had to stop, even if it then passed."""
    failed = [r for r in practice_runs if not r.passed or getattr(r, "holds", 0) > 0]
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
            "near_miss": r.passed and getattr(r, "holds", 0) > 0,
            "held_by_gate": [e["message"] for e in getattr(r, "monitor_events", []) if e["verdict"] == "hold"],
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
                        text=str(e.get("text") or ""), why=str(e.get("why") or ""), target=str(e.get("target") or "")))
    return out


EDITOR_SYSTEM_V2 = EDITOR_SYSTEM.replace(
    "Reply with JSON only",
    "You also get a FAILURE PROFILE: counts of your missed checks by kind across all recent practice tasks, and how you "
    "behaved (for example, whether you read the policy emails before your first write). Fix the biggest patterns first. "
    "Each edit must include \"target\": the check kind it should reduce, one of rule_broken (you did something you "
    "must not), action_missed (you failed to do something required), wrong_content (you did it with wrong or missing values). "
    "Reply with JSON only").replace('"why": "<the mistake pattern it fixes>"}', '"why": "<the mistake pattern it fixes>", "target": "<check kind>"}')


def editor_prompt_v2(rules: tuple[str, ...], profile: dict[str, Any], mistakes: list[dict[str, Any]], rejected: list[Edit], n: int) -> list[dict[str, str]]:
    msgs = editor_prompt(rules, mistakes, rejected, n)
    msgs[0] = {"role": "system", "content": EDITOR_SYSTEM_V2.format(n=n)}
    msgs[1] = {"role": "user", "content": f"FAILURE PROFILE (all recent practice tasks):\n{json.dumps(profile, indent=1)}\n\n" + msgs[1]["content"]}
    return msgs


class SkillEditor:
    """MiniMax as its own editor (no tools). Invalid or refused edits are dropped; if fewer than `n`
    survive, it is asked once more with the reasons."""

    def __init__(self, client: ChatClient):
        self.client = client

    def propose(self, rules: tuple[str, ...], mistakes: list[dict[str, Any]], rejected: list[Edit], *,
                n: int, round_number: int, profile: dict[str, Any] | None = None) -> tuple[list[Edit], list[dict[str, Any]]]:
        """With `profile` (the redesign), the editor sees the failure profile first and each fix must name
        the check kind it targets; without it, the pilot's prompt is used unchanged."""
        messages = editor_prompt_v2(rules, profile, mistakes, rejected, n) if profile is not None else editor_prompt(rules, mistakes, rejected, n)
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
                if reason is None and profile is not None and edit.target not in CHECK_KINDS:
                    reason = f"name the check kind the fix targets: one of {', '.join(CHECK_KINDS)}"
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


# ================= Redesign (briefs/Skill loop redesign.md; built 2026-10-08) =================
# Telemetry at three levels (task, check, step); fixes name the check kind they target; a three-part
# keep rule scored at the check level, with tasks as clusters. Not yet used by a run script.

CHECK_KINDS = ("rule_broken", "action_missed", "wrong_content")
MAX_RULE_CHARS_V2 = MAX_RULE_CHARS


def failure_profile(runs: list[CandidateRun], behaviours: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts across practice runs: missed checks by kind (with how many runs missed each kind)
    and step measures. This is what the editor sees first, before a few examples."""
    missed = {k: 0 for k in CHECK_KINDS}
    runs_with = {k: 0 for k in CHECK_KINDS}
    for r in runs:
        kinds = [c["kind"] for c in r.checks if not c["passed"]]
        for k in CHECK_KINDS:
            missed[k] += kinds.count(k)
            runs_with[k] += k in kinds
    policy = [b["read_policy_before_first_write"] for b in behaviours if b.get("read_policy_before_first_write") is not None]
    return {
        "runs": len(runs),
        "failed_runs": sum(not r.passed for r in runs),
        "missed_checks_by_kind": missed,
        "runs_missing_each_kind": runs_with,
        "policy_emails_read_before_first_write": f"{sum(policy)} of {len(policy)} runs with policy emails",
        "runs_hitting_step_cap": sum(r.stop_reason == "max_steps" for r in runs),
        "gate_holds_per_100_runs": round(100 * sum(getattr(r, "holds", 0) for r in runs) / max(1, len(runs)), 1),
        "near_misses": sum(r.passed and getattr(r, "holds", 0) > 0 for r in runs),
        "mean_steps": round(sum(r.steps for r in runs) / max(1, len(runs)), 1),
    }


def targeted_pass_rates(runs: dict[str, CandidateRun], kind: str) -> dict[str, float]:
    """Per task: the share of its scored checks of `kind` that passed (tasks with none are left out)."""
    out = {}
    for t, r in runs.items():
        cs = [c for c in r.checks if c["kind"] == kind]
        if cs:
            out[t] = sum(c["passed"] for c in cs) / len(cs)
    return out


@dataclass(frozen=True)
class KeepDecision:
    keep: bool
    targeted_ok: bool
    guard_ok: bool
    net_ok: bool
    targeted_diff: float  # mean per-task change in the targeted checks' pass rate
    targeted_p: float
    targeted_tasks: int
    guard_diff: float  # mean task-credit change on the regression set (or the whole gate if it is empty)
    guard_tasks: int
    net_diff: float  # mean task-credit change on the whole gate
    passes_ok: bool = True  # margin keep test only: the candidate fully passes at least as many tasks as the current version
    passes_diff: int = 0  # candidate's fully passed tasks minus the current version's

    def record(self) -> dict[str, Any]:
        return asdict(self)


def keep_rule(current: dict[str, CandidateRun], candidate: dict[str, CandidateRun], *, kind: str,
              regression: list[str], p_threshold: float = 0.10, max_regression_drop: float = 0.03,
              test: str = "p_value", min_credit_gain: float = 0.02) -> KeepDecision:
    """Keep a fix only if it passes the keep-or-reject test named by `test`.

    "p_value" (Take 1): (1) the targeted checks improve: per-task pass rate of checks of `kind`, paired by task
    (each task is one cluster), mean up and one-sided Wilcoxon p < p_threshold; (2) the regression set's mean
    credit drops by at most `max_regression_drop` (the whole gate is used when the regression set is empty);
    and (3) mean credit over the whole gate does not fall.

    "margin" (Take 2, 2026-10-10): (1) the targeted checks' mean pass rate rises (no p-value); (2) mean credit over
    the whole gate rises by at least `min_credit_gain`; (3) the candidate fully passes at least as many tasks as
    the current version; and the same regression guard as above."""
    if test not in ("p_value", "margin"):
        raise ValueError(f"unknown keep test {test!r}")
    if set(current) != set(candidate):
        raise ValueError("both versions must run on the same gate tasks")
    cur_t, cand_t = targeted_pass_rates(current, kind), targeted_pass_rates(candidate, kind)
    shared = sorted(set(cur_t) & set(cand_t))
    diffs = [cand_t[t] - cur_t[t] for t in shared]
    nonzero = [d for d in diffs if d != 0]
    p = float(wilcoxon(nonzero, alternative="greater").pvalue) if nonzero else 1.0
    t_diff = sum(diffs) / len(diffs) if diffs else 0.0
    guard_ids = [t for t in regression if t in current] or sorted(current)
    g_diff = sum(candidate[t].partial_credit - current[t].partial_credit for t in guard_ids) / len(guard_ids)
    n_diff = sum(candidate[t].partial_credit - current[t].partial_credit for t in current) / len(current)
    passes_diff = sum(r.passed for r in candidate.values()) - sum(r.passed for r in current.values())
    guard_ok = g_diff >= -max_regression_drop
    if test == "margin":
        targeted_ok = t_diff > 0
        net_ok = n_diff >= min_credit_gain - 1e-9
        passes_ok = passes_diff >= 0
    else:
        targeted_ok = t_diff > 0 and p < p_threshold
        net_ok = n_diff >= 0
        passes_ok = True
    return KeepDecision(targeted_ok and guard_ok and net_ok and passes_ok, targeted_ok, guard_ok, net_ok, t_diff, p, len(shared),
                        g_diff, len(guard_ids), n_diff, passes_ok, passes_diff)
