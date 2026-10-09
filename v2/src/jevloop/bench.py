"""Adapter to AutomationBench: tasks, the simulated world, tools and grading.

This is the only module that imports AutomationBench. It drives the bench's own pieces
directly (WorldState, the "api" toolset that `auto-bench` uses by default, and the bench's
`partial_credit` grader) instead of going through `auto-bench`, so our own agent loop, cache
and spend cap stay in charge (Task Brief 7, Phase 0 item 3d).

Leak boundary: a task's grading checks live only on `Task`. Agents and the run summariser
receive a `PublicTask`, which has no grading checks and no expected state.
"""
from __future__ import annotations

import copy
import inspect
import json
from dataclasses import dataclass, field
from typing import Any

from automationbench.domains import get_available_domains, get_domain_dataset
from automationbench.rubric import partial_credit
from automationbench.rubric.registry import AssertionRegistry
from automationbench.runner import compute_allowed_services, strip_none_values
from automationbench.schema.world import WorldState
from automationbench.tools.api import API_TOOLS
from verifiers.legacy.envs.stateful_tool_env import filter_signature
from verifiers.legacy.utils.tool_utils import convert_func_to_tool_def

SCORED_DOMAINS = ["sales", "marketing", "operations", "support", "finance", "hr"]
_TOOLS = {tool.__name__: tool for tool in API_TOOLS}


@dataclass(frozen=True)
class PublicTask:
    """What an agent (and the run summary) may see: the prompt and the starting world."""

    task_id: str
    domain: str
    messages: tuple[dict[str, str], ...]

    @property
    def trigger(self) -> str:
        return "\n\n".join(m["content"] for m in self.messages if m["role"] == "user")


@dataclass(frozen=True)
class Task:
    public: PublicTask
    initial_state: dict[str, Any] = field(repr=False)
    assertions: tuple[dict[str, Any], ...] = field(repr=False)  # grading only; never shown
    zapier_tools: tuple[str, ...] = field(default=(), repr=False)

    @property
    def task_id(self) -> str:
        return self.public.task_id


@dataclass(frozen=True)
class Grade:
    partial_credit: float
    passed: bool
    scored_checks: int
    # Scored checks the run did not meet: {"type", "params", "negative"}. For the Agent skill loop's
    # editor on practice tasks only; never part of the run summary Jev reads.
    missed: tuple[dict[str, Any], ...] = ()
    # Every scored check: {"type", "kind", "passed"}. Kinds: rule_broken (a "must not" check),
    # wrong_content (a check on values written), action_missed (any other required action).
    checks: tuple[dict[str, Any], ...] = ()


def domains() -> list[str]:
    return get_available_domains()


def load_tasks(domain_names: list[str]) -> list[Task]:
    tasks = []
    for domain in domain_names:
        for row in get_domain_dataset(domain):
            info = row["info"]
            info = json.loads(info) if isinstance(info, str) else info
            public = PublicTask(
                task_id=f"{domain}:{row['example_id']}",
                domain=domain,
                messages=tuple({"role": m["role"], "content": m["content"]} for m in row["prompt"]),
            )
            tasks.append(
                Task(
                    public=public,
                    initial_state=strip_none_values(info.get("initial_state", {})),
                    assertions=tuple(strip_none_values(a) for a in info.get("assertions", [])),
                    zapier_tools=tuple(info.get("zapier_tools") or ()),
                )
            )
    return tasks


def new_world(task: Task) -> WorldState:
    """A fresh simulated world for one candidate run (runs never share state)."""
    world = WorldState(**copy.deepcopy(task.initial_state))
    world.meta.allowed_services = compute_allowed_services(
        task.initial_state, list(task.assertions), list(task.zapier_tools)
    )
    return world


def world_snapshot(world: WorldState) -> dict[str, Any]:
    return world.model_dump(mode="json")


def tool_schemas() -> list[dict[str, Any]]:
    """The "api" toolset in OpenAI function-calling format (the `world` argument is hidden)."""
    schemas = []
    for tool in API_TOOLS:
        skip = ["world"] if "world" in inspect.signature(tool).parameters else []
        tool_def = convert_func_to_tool_def(filter_signature(tool, skip))
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.parameters,
                },
            }
        )
    return schemas


def call_tool(world: WorldState, name: str, args: dict[str, Any]) -> str:
    """Run one tool call the way the bench's environment does (see runner.update_tool_args)."""
    tool = _TOOLS.get(name)
    if tool is None:
        return json.dumps({"error": {"code": 404, "message": f"unknown tool {name!r}"}})
    # The bench treats an empty object as "no value" for optional arguments.
    clean = {k: v for k, v in args.items() if not (isinstance(v, dict) and len(v) == 0)}
    if "world" in inspect.signature(tool).parameters:
        clean["world"] = world
    try:
        result = tool(**clean)
    except Exception as error:  # the bench returns tool errors to the model as text
        return json.dumps({"error": {"code": 400, "message": f"{type(error).__name__}: {error}"}})
    return result if isinstance(result, str) else json.dumps(result)


CONTENT_PARAMS = frozenset({"body_contains", "body_not_contains", "cell_contains", "subject_contains", "text_contains",
                            "text_not_contains", "value", "field_value", "contains"})


def check_kind(check: dict[str, Any]) -> str:
    """rule_broken | wrong_content | action_missed, from the check's definition (not its outcome)."""
    if AssertionRegistry.is_negative(check["type"]):
        return "rule_broken"
    params = check.get("params", check)
    return "wrong_content" if CONTENT_PARAMS & set(params) else "action_missed"


def task_check_kinds(task: Task) -> dict[str, int]:
    """How many checks of each kind a task defines: a task property, used to pick test tasks (A4)."""
    out: dict[str, int] = {}
    for a in task.assertions:
        k = check_kind(a)
        out[k] = out.get(k, 0) + 1
    return out


def grade(task: Task, world: WorldState) -> Grade:
    """AutomationBench's own grader: share of checks met, excluding ones true from the start."""
    state: dict[str, Any] = {
        "info": {"assertions": [copy.deepcopy(a) for a in task.assertions]},
        "world": world,
        "initial_state": copy.deepcopy(task.initial_state),
    }
    credit = partial_credit(state)
    results = state.get("_assertion_results", [])
    scored = sum(1 for r in results if not r.get("excluded"))
    missed = tuple(
        {"type": r["type"], "params": r.get("params", {}), "negative": AssertionRegistry.is_negative(r["type"])}
        for r in results if not r.get("excluded") and not r["passed"]
    )
    checks = tuple({"type": r["type"], "kind": check_kind({"type": r["type"], **r.get("params", {})}), "passed": bool(r["passed"])}
                   for r in results if not r.get("excluded"))
    return Grade(partial_credit=credit, passed=credit == 1.0, scored_checks=scored, missed=missed, checks=checks)
