"""Ranking statistics for the Jev verifier: AUC within groups (playbook versions), cluster bootstrap by task,
and the credit gap of the lowest-scoring share of runs. Pure functions; no model calls."""
from __future__ import annotations

import random
import statistics as st
from collections import defaultdict
from typing import Any, Sequence

GOOD_CREDIT = 0.8


def auc(scores: Sequence[float], good: Sequence[bool]) -> float:
    pos = [s for s, g in zip(scores, good) if g]
    neg = [s for s, g in zip(scores, good) if not g]
    if not pos or not neg:
        return float("nan")
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def _pair_counts(rows: list[dict[str, Any]], key: str) -> tuple[float, int]:
    """Wins (ties half) and comparisons for good-vs-bad pairs, only within each `key` group."""
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    wins, n = 0.0, 0
    for g in groups.values():
        pos = [r["score"] for r in g if r["credit"] >= GOOD_CREDIT]
        neg = [r["score"] for r in g if r["credit"] < GOOD_CREDIT]
        wins += sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
        n += len(pos) * len(neg)
    return wins, n


def grouped_auc(rows: list[dict[str, Any]], key: str = "group") -> float:
    """AUC pooling only comparisons between runs in the same group (same playbook version, or same task)."""
    wins, n = _pair_counts(rows, key)
    return wins / n if n else float("nan")


def lowest_share_gap(rows: list[dict[str, Any]], share: float = 0.30, key: str = "group") -> dict[str, float]:
    """Within each group, the lowest-scoring `share` of runs vs the rest: mean credit of each, pooled."""
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    low, rest = [], []
    for g in groups.values():
        order = sorted(g, key=lambda r: r["score"])
        k = max(1, round(share * len(order)))
        low += [r["credit"] for r in order[:k]]
        rest += [r["credit"] for r in order[k:]]
    if not low or not rest:
        return {"credit_low": float("nan"), "credit_rest": float("nan"), "gap": float("nan"), "n_low": len(low)}
    return {"credit_low": st.mean(low), "credit_rest": st.mean(rest), "gap": st.mean(rest) - st.mean(low), "n_low": len(low)}


def cluster_bootstrap(rows: list[dict[str, Any]], stat, *, n: int = 1000, seed: int = 0) -> tuple[float, float]:
    """95% interval of stat(rows) resampling whole tasks (a task's runs stay together)."""
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    tasks = sorted(by_task)
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = [r for t in (rng.choice(tasks) for _ in tasks) for r in by_task[t]]
        v = stat(sample)
        if v == v:
            vals.append(v)
    if not vals:  # e.g. every resample had only one class
        return float("nan"), float("nan")
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]


def evaluate(rows: list[dict[str, Any]], *, boot: int = 1000, seed: int = 0) -> dict[str, Any]:
    """rows: {"task", "group", "score", "credit"}. The primary metric is the within-group (playbook) AUC."""
    primary = grouped_auc(rows, "group")
    lo, hi = cluster_bootstrap(rows, lambda s: grouped_auc(s, "group"), n=boot, seed=seed)
    gap = lowest_share_gap(rows)
    gap_lo, gap_hi = cluster_bootstrap(rows, lambda s: lowest_share_gap(s)["gap"], n=boot, seed=seed)
    return {"n_runs": len(rows), "n_tasks": len({r["task"] for r in rows}), "auc_within_playbook": primary, "auc_ci95": [lo, hi],
            "auc_within_task": grouped_auc(rows, "task"), "auc_pooled": auc([r["score"] for r in rows], [r["credit"] >= GOOD_CREDIT for r in rows]),
            **gap, "gap_ci95": [gap_lo, gap_hi]}


def bar_met(m: dict[str, Any], *, auc_bar: float = 0.65, gap_bar: float = 0.10) -> bool:
    return m["auc_within_playbook"] >= auc_bar and m["auc_ci95"][0] > 0.5 and m["gap"] >= gap_bar
