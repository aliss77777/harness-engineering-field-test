"""K independent candidate runs per task, each graded (Task Brief 7, section 2).

An agent gets a `PublicTask` and a `ToolBox` over its own fresh world. It never sees the
grading checks. Each candidate is told its index, and an agent that caches model calls must
put the index in the cache key; otherwise K runs replay one answer K times.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from jevloop import bench
import httpx

from jevloop.log import JsonlLogger
from jevloop.openrouter import IncompleteResponseError, OutOfCreditsError, RouteMismatchError
from jevloop.spend import SpendCapExceeded
from jevloop.summary import summarize


# Problems with the provider, the account or the budget: they stop the whole run.
INFRASTRUCTURE_ERRORS = (SpendCapExceeded, OutOfCreditsError, RouteMismatchError, IncompleteResponseError, httpx.HTTPError)


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]
    result: str


class ToolBox:
    """The agent's only handle on the world: runs tools and records every call."""

    def __init__(self, world):
        self._world = world
        self.calls: list[ToolCall] = []

    @staticmethod
    def schemas() -> list[dict[str, Any]]:
        return bench.tool_schemas()

    def call(self, name: str, args: dict[str, Any]) -> str:
        result = bench.call_tool(self._world, name, dict(args))
        self.calls.append(ToolCall(name=name, args=dict(args), result=result))
        return result


@dataclass
class AgentResult:
    final_message: str = ""
    cost_usd: float = 0.0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "done"  # done | max_steps | error
    steps: int = 0
    parse_errors: int = 0  # tool calls whose arguments could not be parsed
    model_seconds: float = 0.0  # summed model latency (original latency on cache replays)


class Agent(Protocol):
    name: str

    def run(self, task: bench.PublicTask, tools: ToolBox, candidate: int) -> AgentResult: ...


@dataclass
class CandidateRun:
    task_id: str
    domain: str
    agent: str
    candidate: int
    partial_credit: float
    passed: bool
    scored_checks: int
    tool_calls: int
    cost_usd: float
    seconds: float
    stop_reason: str
    summary: str = field(repr=False)
    steps: int = 0
    parse_errors: int = 0
    model_seconds: float = 0.0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    calls: list[dict[str, Any]] = field(default_factory=list, repr=False)
    missed_checks: list[dict[str, Any]] = field(default_factory=list, repr=False)  # editor-only, practice tasks

    @property
    def failed(self) -> bool:
        """A run failure (comparability rule): step cap hit, an unparseable tool call, or an error."""
        return self.stop_reason in ("max_steps", "error") or self.parse_errors > 0

    def record(self) -> dict[str, Any]:
        return asdict(self)


def run_candidate(task: bench.Task, agent: Agent, candidate: int) -> CandidateRun:
    world = bench.new_world(task)
    before = bench.world_snapshot(world)
    tools = ToolBox(world)
    started = time.monotonic()
    try:
        result = agent.run(task.public, tools, candidate)
    except INFRASTRUCTURE_ERRORS:
        raise  # fail loudly; a rerun resumes from cache. Never graded as the agent's failure.
    except Exception as error:  # a crashed run is graded as it stands, and marked
        result = AgentResult(final_message=f"{type(error).__name__}: {error}", stop_reason="error")
    seconds = time.monotonic() - started
    grade = bench.grade(task, world)
    return CandidateRun(
        task_id=task.task_id,
        domain=task.public.domain,
        agent=agent.name,
        candidate=candidate,
        partial_credit=grade.partial_credit,
        passed=grade.passed,
        scored_checks=grade.scored_checks,
        tool_calls=len(tools.calls),
        cost_usd=result.cost_usd,
        seconds=seconds,
        stop_reason=result.stop_reason,
        summary=summarize(task.public, tools.calls, before, bench.world_snapshot(world)),
        calls=[asdict(c) for c in tools.calls],
        steps=result.steps,
        parse_errors=result.parse_errors,
        model_seconds=result.model_seconds,
        model_calls=result.model_calls,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        missed_checks=[dict(m) for m in grade.missed],
    )


def run_candidates(
    tasks: list[bench.Task],
    agent: Agent,
    k: int,
    *,
    max_workers: int = 1,
    logger: JsonlLogger | None = None,
    run_id: str = "",
) -> list[CandidateRun]:
    """Run K candidates for every task. Output order is fixed (task, then candidate) whatever
    the concurrency, so results never depend on it."""
    jobs = [(task, c) for task in tasks for c in range(k)]

    def one(job):
        run = run_candidate(job[0], agent, job[1])
        if logger is not None:
            logger.write({"event": "candidate_run", "run_id": run_id, **run.record()})
        return run

    if max_workers <= 1:
        return [one(job) for job in jobs]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(one, jobs))
