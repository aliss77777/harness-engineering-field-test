"""Phase 0 numbers and the go/no-go rule (Task Brief 7, section 3, Phase 0 item 4)."""
from __future__ import annotations

import random
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


# ---- Cheap-agent comparability check (phase0/FEASIBILITY.md, fixed 2026-10-06 before any run) ----

COMPARABILITY_MARGIN = 0.10  # Nemotron's mean partial credit may be at most 10 points below Gemini's
MAX_FAILURE_RATE = 0.10  # under 10% of Nemotron's runs may fail (step cap, unparseable call, error)


def select_tasks(task_ids_by_domain: dict[str, list[str]], per_domain: int, seed: int) -> list[str]:
    """Fixed-seed sample of `per_domain` task IDs from each domain, in a stable order."""
    chosen = []
    for domain in sorted(task_ids_by_domain):
        ids = sorted(task_ids_by_domain[domain], key=lambda t: int(t.split(":")[1]))
        chosen += sorted(random.Random(f"{seed}:{domain}").sample(ids, per_domain), key=lambda t: int(t.split(":")[1]))
    return chosen


@dataclass(frozen=True)
class ModelSummary:
    agent: str
    runs: int
    mean_credit: float
    pass_rate: float
    failures: int
    failure_rate: float
    cost_per_run_usd: float
    model_seconds_per_run: float
    steps_per_run: float

    def record(self) -> dict:
        return asdict(self)


def summarize_model(runs: list[CandidateRun]) -> ModelSummary:
    mean = statistics.fmean
    return ModelSummary(
        agent=runs[0].agent,
        runs=len(runs),
        mean_credit=mean(r.partial_credit for r in runs),
        pass_rate=mean(r.passed for r in runs),
        failures=sum(r.failed for r in runs),
        failure_rate=mean(r.failed for r in runs),
        cost_per_run_usd=mean(r.cost_usd for r in runs),
        model_seconds_per_run=mean(r.model_seconds for r in runs),
        steps_per_run=mean(r.steps for r in runs),
    )


def paired_bootstrap_interval(diffs: list[float], *, resamples: int = 10_000, seed: int = 20261006) -> tuple[float, float]:
    """95% percentile bootstrap interval for the mean of paired differences."""
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(statistics.fmean(diffs[rng.randrange(n)] for _ in range(n)) for _ in range(resamples))
    return means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]


@dataclass(frozen=True)
class Comparability:
    comparable: bool
    credit_ok: bool
    failures_ok: bool
    difference: float  # candidate minus reference, mean partial credit (0-1 scale)
    interval: tuple[float, float]
    reference: ModelSummary
    candidate: ModelSummary

    def record(self) -> dict:
        return {"comparable": self.comparable, "credit_ok": self.credit_ok, "failures_ok": self.failures_ok,
                "difference": self.difference, "interval_95": list(self.interval),
                "reference": self.reference.record(), "candidate": self.candidate.record()}


def comparability(reference: list[CandidateRun], candidate: list[CandidateRun]) -> Comparability:
    """Paired by task: both lists must cover the same tasks, one run each."""
    ref = {r.task_id: r for r in reference}
    cand = {r.task_id: r for r in candidate}
    if set(ref) != set(cand) or len(ref) != len(reference) or len(cand) != len(candidate):
        raise ValueError("reference and candidate must have exactly one run on each of the same tasks")
    diffs = [cand[t].partial_credit - ref[t].partial_credit for t in sorted(ref)]
    difference = statistics.fmean(diffs)
    cand_summary = summarize_model(candidate)
    credit_ok = difference >= -COMPARABILITY_MARGIN
    failures_ok = cand_summary.failure_rate < MAX_FAILURE_RATE
    return Comparability(credit_ok and failures_ok, credit_ok, failures_ok, difference,
                         paired_bootstrap_interval(diffs), summarize_model(reference), cand_summary)
