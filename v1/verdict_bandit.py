"""Experiment 6 preregistered verdict (Task Brief 6_Bandit.md).

Metric: click lift of each policy's pick over a random pick, in points (random = 0).
All comparisons are paired, test by test, on the sealed set: two-sided Wilcoxon signed-rank
on per-test differences, and a seeded bootstrap 95% interval of the mean difference.

Primary (router R final vs LLM-only L final), first matching row wins:
  1. neither R final nor L final beats a random pick (bootstrap lower bound <= 0)  -> no_signal
  2. R significantly better than L                                                -> router_beats_llm
  3. interval of (R - L) within +/- margin and R cost <= max_cost_ratio x L cost  -> same_quality_half_cost
  4. R significantly worse and interval low < -margin                             -> routing_costs_quality
  5. interval within +/- margin but cost too high                                 -> same_quality_not_cheap_enough
  6. anything else                                                                -> inconclusive
Also preregistered (reported separately): did R, L and J each learn from partial feedback
(final vs version 0: mean difference > 0 and Wilcoxon p < alpha)?
"""
from __future__ import annotations

import numpy as np
from scipy.stats import wilcoxon


def bootstrap_interval(values, *, resamples: int, alpha: float, seed: int) -> list[float]:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = rng.choice(values, size=(resamples, len(values)), replace=True).mean(axis=1)
    return [float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))]


def paired(new, old, *, resamples: int, alpha: float, seed: int) -> dict:
    diff = np.asarray(new, dtype=float) - np.asarray(old, dtype=float)
    p = 1.0 if not np.any(diff) else float(wilcoxon(diff, zero_method="wilcox").pvalue)
    return {"mean_difference": float(diff.mean()), "p_value": p, "nonzero_pairs": int(np.count_nonzero(diff)),
            "interval_95": bootstrap_interval(diff, resamples=resamples, alpha=alpha, seed=seed)}


def compute_bandit_verdict(*, metrics: dict, config: dict, max_cost_ratio: float) -> dict:
    alpha, margin = float(config["alpha"]), float(config["equivalence_margin_lift"])
    resamples, seed = int(config["bootstrap_resamples"]), 20260926
    r, l = metrics["R_final"], metrics["L_final"]
    signal = {name: bootstrap_interval(metrics[name]["lift"], resamples=resamples, alpha=alpha, seed=seed)
              for name in ("R_final", "L_final", "J_final")}
    primary = paired(r["lift"], l["lift"], resamples=resamples, alpha=alpha, seed=seed)
    low, high = primary["interval_95"]
    ratio = r["cost_per_1000"] / l["cost_per_1000"] if l["cost_per_1000"] else float("inf")
    better = primary["mean_difference"] > 0 and primary["p_value"] < alpha
    worse = primary["mean_difference"] < 0 and primary["p_value"] < alpha
    within, cheap = low >= -margin and high <= margin, ratio <= max_cost_ratio
    if signal["R_final"][0] <= 0 and signal["L_final"][0] <= 0:
        verdict = "no_signal"
    elif better:
        verdict = "router_beats_llm"
    elif within and cheap:
        verdict = "same_quality_half_cost"
    elif worse and low < -margin:
        verdict = "routing_costs_quality"
    elif within:
        verdict = "same_quality_not_cheap_enough"
    else:
        verdict = "inconclusive"
    learning = {}
    for arm in ("R", "L", "J"):
        test = paired(metrics[f"{arm}_final"]["lift"], metrics[f"{arm}_version0"]["lift"],
                      resamples=resamples, alpha=alpha, seed=seed)
        learning[arm] = {**test, "learned": test["mean_difference"] > 0 and test["p_value"] < alpha}
    secondary = {
        name: paired(metrics[a]["lift"], metrics[b]["lift"], resamples=resamples, alpha=alpha, seed=seed)
        for name, (a, b) in {"J_vs_L": ("J_final", "L_final"), "R_vs_J": ("R_final", "J_final"),
                             "C_vs_L": ("C_final", "L_final"), "R_both_learned_vs_L": ("R_final_with_L_final", "L_final")}.items()
    }
    return {"verdict": verdict, "rules_version": "bandit_v1",
            "primary_R_vs_L": {**primary, "cost_ratio": ratio, "within_margin": within, "cheap_enough": cheap},
            "signal_intervals_vs_random": signal, "learning": learning, "secondary": secondary,
            "memorization_flag_llm": float(np.mean(metrics["L_version0"]["hit"])) > float(config["memorization_hit_rate"]),
            "thresholds": {"alpha": alpha, "equivalence_margin_lift_pts": margin, "max_cost_ratio": max_cost_ratio}}
