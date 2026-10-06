"""Phase 0 numbers and the go/no-go rule (Task Brief 7, section 3, Phase 0 item 4)."""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass

from jevloop.runs import CandidateRun

PASS_RATE_RANGE = (0.20, 0.80)  # the Cheap agent's pass rate must leave selection room to matter
MIN_MIXED_SHARE = 0.30  # share of tasks whose K candidates mix pass and fail


@dataclass(frozen=True)
class Frame:
    """V2-1 controls in one agent's runs: first run, random pick of K, oracle best of K."""

    agent: str
    tasks: int
    k: int
    first_run_pass_rate: float
    random_pick_pass_rate: float  # expected pass rate of picking one of K at random
    oracle_pass_rate: float  # share of tasks where at least one of K passed
    first_run_credit: float
    random_pick_credit: float
    oracle_credit: float
    mixed_share: float
    cost_per_run_usd: float
    seconds_per_run: float

    def record(self) -> dict:
        return asdict(self)


def frame(runs: list[CandidateRun]) -> Frame:
    by_task: dict[str, list[CandidateRun]] = defaultdict(list)
    for run in runs:
        by_task[run.task_id].append(run)
    if not by_task:
        raise ValueError("no runs")
    agents = {run.agent for run in runs}
    if len(agents) != 1:
        raise ValueError(f"one agent per frame, got {sorted(agents)}")
    groups = [sorted(g, key=lambda r: r.candidate) for g in by_task.values()]
    ks = {len(g) for g in groups}
    if len(ks) != 1:
        raise ValueError(f"every task needs the same K, got {sorted(ks)}")
    mean = statistics.fmean
    return Frame(
        agent=agents.pop(),
        tasks=len(groups),
        k=ks.pop(),
        first_run_pass_rate=mean(g[0].passed for g in groups),
        random_pick_pass_rate=mean(mean(r.passed for r in g) for g in groups),
        oracle_pass_rate=mean(any(r.passed for r in g) for g in groups),
        first_run_credit=mean(g[0].partial_credit for g in groups),
        random_pick_credit=mean(mean(r.partial_credit for r in g) for g in groups),
        oracle_credit=mean(max(r.partial_credit for r in g) for g in groups),
        mixed_share=mean(len({r.passed for r in g}) == 2 for g in groups),
        cost_per_run_usd=mean(r.cost_usd for r in runs),
        seconds_per_run=mean(r.seconds for r in runs),
    )


@dataclass(frozen=True)
class GoNoGo:
    go: bool
    pass_rate_ok: bool
    mixed_ok: bool
    cost_ok: bool
    reasons: tuple[str, ...]


def go_no_go(cheap: Frame, projected_phase1_cost_usd: float, cap_usd: float) -> GoNoGo:
    low, high = PASS_RATE_RANGE
    pass_rate_ok = low <= cheap.first_run_pass_rate <= high
    mixed_ok = cheap.mixed_share >= MIN_MIXED_SHARE
    cost_ok = projected_phase1_cost_usd <= cap_usd
    reasons = []
    if not pass_rate_ok:
        reasons.append(f"Cheap agent pass rate {cheap.first_run_pass_rate:.0%} outside {low:.0%}-{high:.0%}")
    if not mixed_ok:
        reasons.append(f"only {cheap.mixed_share:.0%} of tasks have mixed pass/fail across K (need {MIN_MIXED_SHARE:.0%})")
    if not cost_ok:
        reasons.append(f"projected Phase 1 cost ${projected_phase1_cost_usd:.2f} over cap ${cap_usd:.2f}")
    return GoNoGo(pass_rate_ok and mixed_ok and cost_ok, pass_rate_ok, mixed_ok, cost_ok, tuple(reasons))
