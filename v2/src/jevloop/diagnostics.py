"""Behaviour measures from Phase 0's failure diagnosis, reused as the skill loop's leading indicators.

- Did the run read every policy email in the task's inbox? (MiniMax read all of them in 4 of 13 runs.)
- How many "must not" checks did it break?
"Policy email" is detected by keywords in the subject and opening lines, so it is approximate.
"""
from __future__ import annotations

import re
from typing import Any

from jevloop import bench

POLICY_WORDS = re.compile(r"polic|sop|guideline|procedure|process|rule|update|hold|do not|don't", re.I)


def policy_messages(task: bench.Task) -> list[str]:
    msgs = (task.initial_state.get("gmail") or {}).get("messages", [])
    return [m["id"] for m in msgs if POLICY_WORDS.search(f"{m.get('subject', '')} {m.get('body_plain', '')[:300]}")]


def read_ids(calls: list[dict[str, Any]]) -> set[str]:
    text = " ".join(f"{c['args'].get('url', '')} {c['args'].get('params', '')}" for c in calls if c["name"] == "api_fetch")
    return set(re.findall(r"[\w-]+", text))


def behaviour(task: bench.Task, calls: list[dict[str, Any]], missed: list[dict[str, Any]]) -> dict[str, Any]:
    policy = policy_messages(task)
    seen = read_ids(calls)
    return {
        "policy_emails": len(policy),
        "read_all_policy_emails": all(p in seen for p in policy) if policy else None,
        "broken_must_not": sum(1 for m in missed if m.get("negative")),
    }
