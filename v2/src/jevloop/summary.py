"""Compact, deterministic run summary: what the Jev rubric reads (Task Brief 7, section 2).

Three parts: the trigger, the tool calls (names and key arguments), and the diff of the
world from start to finish. Built only from what the agent itself saw and did; this module
never receives a task's grading checks or expected state (tests/test_summary.py checks this).
"""
from __future__ import annotations

import json
from typing import Any

# Bookkeeping fields the simulator stamps on every write; they say nothing about the work.
NOISE_FIELDS = frozenset({"last_modified_date", "updated_at", "modified_at", "system_modstamp"})
SKIP_SERVICES = frozenset({"meta"})
MAX_VALUE_CHARS = 160
MAX_CHARS = 8000


def _short(value: Any, limit: int = MAX_VALUE_CHARS) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _status(result: str) -> str:
    try:
        body = json.loads(result)
    except (TypeError, ValueError):
        return "ok"
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return f"error {body['error'].get('code', '')}".strip()
    return "ok"


def _describe_call(call) -> str:
    args = dict(call.args)
    if call.name == "api_fetch":
        parts = [str(args.pop("method", "")).upper(), str(args.pop("url", ""))]
        parts += [f"{k}={_short(v)}" for k, v in sorted(args.items()) if v not in (None, "", {})]
    else:
        parts = [f"{k}={_short(v)}" for k, v in sorted(args.items())]
    return f"{call.name} {' '.join(p for p in parts if p)} -> {_status(call.result)}"


def _is_record_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict) and "id" in item for item in value
    )


def _record_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in NOISE_FIELDS and v not in (None, [], {}, "")}


def _diff_records(path: str, before: list, after: list) -> list[str]:
    old = {str(r["id"]): r for r in before}
    new = {str(r["id"]): r for r in after}
    lines = []
    for rid in sorted(new.keys() - old.keys()):
        lines.append(f"+ {path}[{rid}] {_short(_record_fields(new[rid]), 2 * MAX_VALUE_CHARS)}")
    for rid in sorted(old.keys() - new.keys()):
        lines.append(f"- {path}[{rid}]")
    for rid in sorted(old.keys() & new.keys()):
        keys = sorted((old[rid].keys() | new[rid].keys()) - NOISE_FIELDS)
        changes = [
            f"{k}: {_short(old[rid].get(k))} -> {_short(new[rid].get(k))}"
            for k in keys
            if old[rid].get(k) != new[rid].get(k)
        ]
        if changes:
            lines.append(f"~ {path}[{rid}] " + "; ".join(changes))
    return lines


def state_diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for service in sorted((before.keys() | after.keys()) - SKIP_SERVICES):
        b, a = before.get(service), after.get(service)
        if b == a:
            continue
        if not (isinstance(b, dict) and isinstance(a, dict)):
            lines.append(f"~ {service}: {_short(b)} -> {_short(a)}")
            continue
        for key in sorted(b.keys() | a.keys()):
            bv, av = b.get(key), a.get(key)
            if bv == av or key in NOISE_FIELDS:
                continue
            path = f"{service}.{key}"
            if _is_record_list(bv or []) or _is_record_list(av or []):
                lines += _diff_records(path, bv or [], av or [])
            else:
                lines.append(f"~ {path}: {_short(bv)} -> {_short(av)}")
    return lines


def summarize(task, calls, before: dict[str, Any], after: dict[str, Any]) -> str:
    """`task` is a bench.PublicTask; `calls` the ToolBox's recorded calls."""
    actions = [f"{i}. {_describe_call(c)}" for i, c in enumerate(calls, 1)] or ["(none)"]
    changes = state_diff(before, after) or ["(no changes)"]
    text = "\n".join(
        ["TRIGGER", task.trigger.strip(), "", f"ACTIONS ({len(calls)} tool calls)", *actions,
         "", "STATE CHANGES", *changes]
    )
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 12] + "\n[truncated]"
