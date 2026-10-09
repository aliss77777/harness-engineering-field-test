"""The Router: a cascade (briefs/Phase 1 design.md, V2-3).

MiniMax runs a task once; Jev scores the run with the learned rubric; if the score is at or above τ the
run is kept, otherwise Gemini does the task. τ is set on the test bench so that ESCALATE_SHARE of runs
escalate, and frozen before the sealed set is scored. Cost of a task: MiniMax's run + Jev's call, plus
Gemini's run when escalated.
"""
from __future__ import annotations

from typing import Any

from jevloop.feasibility import paired_bootstrap_interval

ESCALATE_SHARE = 0.30
CREDIT_MARGIN = 0.03  # ±3 points of Gemini's mean partial credit
COST_RATIO = 0.5


def set_tau(scores: list[float], escalate_share: float = ESCALATE_SHARE) -> float:
    """The score below which `escalate_share` of the test bench runs fall."""
    ordered = sorted(scores)
    k = int(round(escalate_share * len(ordered)))
    return ordered[k] if k < len(ordered) else float("inf")


def route(tasks: list[str], scores: dict[str, float], tau: float, cheap: dict[str, dict], strong: dict[str, dict],
          jev_cost: dict[str, float]) -> dict[str, dict]:
    """Per task: kept or escalated, with the credit and cost the cascade gets. `cheap`/`strong` map a task to
    {"credit", "cost_usd", "seconds"}; `strong` must cover every escalated task (fresh runs)."""
    out = {}
    for t in tasks:
        keep = scores[t] >= tau
        c = cheap[t]
        if keep:
            out[t] = {"kept": True, "credit": c["credit"], "cost_usd": c["cost_usd"] + jev_cost.get(t, 0.0), "seconds": c["seconds"]}
        else:
            s = strong[t]
            out[t] = {"kept": False, "credit": s["credit"], "cost_usd": c["cost_usd"] + jev_cost.get(t, 0.0) + s["cost_usd"],
                      "seconds": c["seconds"] + s["seconds"]}
    return out


def v2_3_verdict(routed: dict[str, dict], gemini: dict[str, dict]) -> dict[str, Any]:
    """Chef's kiss if the cascade's mean credit is within ±3 points of Gemini alone (point estimate) and its
    cost per task is at most half of Gemini's. The paired 95% interval is reported next to it. At 80 tasks
    and this much run-to-run noise the interval will be wider than ±3 points, so it cannot by itself prove
    equivalence; the report says so."""
    tasks = sorted(routed)
    diffs = [routed[t]["credit"] - gemini[t]["credit"] for t in tasks]
    lo, hi = paired_bootstrap_interval(diffs)
    mean_diff = sum(diffs) / len(diffs)
    cost_r = sum(routed[t]["cost_usd"] for t in tasks) / len(tasks)
    cost_g = sum(gemini[t]["cost_usd"] for t in tasks) / len(tasks)
    sec_r = sum(routed[t]["seconds"] for t in tasks) / len(tasks)
    sec_g = sum(gemini[t]["seconds"] for t in tasks) / len(tasks)
    credit_ok = abs(mean_diff) <= CREDIT_MARGIN
    cost_ok = cost_r <= COST_RATIO * cost_g
    return {"tasks": len(tasks), "kept_share": sum(routed[t]["kept"] for t in tasks) / len(tasks),
            "credit": {"router": sum(routed[t]["credit"] for t in tasks) / len(tasks), "gemini": sum(gemini[t]["credit"] for t in tasks) / len(tasks),
                       "diff": mean_diff, "interval_95": [lo, hi], "within_3_points": credit_ok},
            "cost_per_task": {"router": cost_r, "gemini": cost_g, "ratio": cost_r / cost_g if cost_g else None, "half_or_less": cost_ok},
            "seconds_per_task": {"router": sec_r, "gemini": sec_g},
            "chefs_kiss": credit_ok and cost_ok,
            "note": "Point-estimate rule with the paired 95% interval reported; at 80 tasks the interval cannot prove ±3-point equivalence."}
