"""Agents that make no model calls, for free checks of the runner, grader and summary.

The model-backed Cheap agent and Strong agent come after the Phase 0 model choice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jevloop.bench import PublicTask
from jevloop.runs import AgentResult, ToolBox


class DoNothingAgent:
    """Takes no actions: the zero line every real agent must beat."""

    name = "do-nothing"

    def run(self, task: PublicTask, tools: ToolBox, candidate: int) -> AgentResult:
        return AgentResult(final_message="", stop_reason="done")


@dataclass
class ScriptedAgent:
    """Replays fixed tool calls for a task. `plans[task_id][candidate % len(...)]` is the list
    of (tool, args) for that candidate, so tests can make candidates differ on purpose."""

    plans: dict[str, list[list[tuple[str, dict[str, Any]]]]] = field(default_factory=dict)
    name: str = "scripted"

    def run(self, task: PublicTask, tools: ToolBox, candidate: int) -> AgentResult:
        options = self.plans.get(task.task_id) or [[]]
        for tool, args in options[candidate % len(options)]:
            tools.call(tool, args)
        return AgentResult(stop_reason="done")


# A correct hand-written solution to simple:3001 ("Jordan Lee emailed a new phone number;
# update her phone in Salesforce"), found with api_search. Used by tests and the free check.
SIMPLE_3001_SOLUTION: list[tuple[str, dict[str, Any]]] = [
    ("api_search", {"query": "gmail list messages search query"}),
    ("api_fetch", {"method": "GET", "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                   "params": '{"q": "from:jordan.lee@acmecorp.example.com"}'}),
    ("api_fetch", {"method": "GET",
                   "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/msg_3001"}),
    ("api_search", {"query": "salesforce update contact"}),
    ("api_fetch", {"method": "PATCH",
                   "url": "https://yourinstance.salesforce.com/services/data/v61.0/sobjects/Contact/003001",
                   "body": '{"Phone": "+1-555-0101"}'}),
]
