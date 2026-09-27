"""Experiment 5 preregistered verdict (Task Brief 5_Routing.md, section 6).

Primary: router vs the LLM alone on sealed-5 (paired, two-sided McNemar, alpha 0.05;
95% interval of router - LLM). Rows, first match wins:
  1. router significantly more accurate                          -> router_beats_llm
  2. interval within +/- margin and cost <= max_cost_ratio x LLM -> same_quality_half_cost
  3. router significantly less accurate and interval low < -margin -> routing_costs_accuracy
  4. interval within +/- margin but cost too high                -> same_quality_not_cheap_enough
  5. anything else                                               -> inconclusive
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from verdict import accuracy, accuracy_interval, paired_difference_interval, paired_test


def compute_router_verdict(*, llm: Sequence[bool], jev: Sequence[bool], router: Sequence[bool],
                           baseline: Sequence[bool] | None, costs_per_1000: dict[str, float],
                           config: dict, max_cost_ratio: float) -> dict:
    alpha, margin = float(config["alpha"]), float(config["equivalence_margin"])
    exact_max = int(config["mcnemar_exact_max_discordant"])
    primary = paired_test(llm, router, exact_max_discordant=exact_max)
    low, high = paired_difference_interval(router, llm, alpha=alpha)
    ratio = costs_per_1000["router"] / costs_per_1000["llm"] if costs_per_1000["llm"] else float("inf")
    better = accuracy(router) > accuracy(llm) and primary.p_value < alpha
    worse = accuracy(router) < accuracy(llm) and primary.p_value < alpha
    within = low >= -margin and high <= margin
    cheap = ratio <= max_cost_ratio
    if better:
        verdict = "router_beats_llm"
    elif within and cheap:
        verdict = "same_quality_half_cost"
    elif worse and low < -margin:
        verdict = "routing_costs_accuracy"
    elif within:
        verdict = "same_quality_not_cheap_enough"
    else:
        verdict = "inconclusive"
    tests = {"router_vs_llm": asdict(primary),
             "router_vs_jev": asdict(paired_test(jev, router, exact_max_discordant=exact_max))}
    accuracies = {"llm": accuracy(llm), "jev": accuracy(jev), "router": accuracy(router)}
    if baseline is not None:
        accuracies["baseline"] = accuracy(baseline)
        for name, values in (("llm", llm), ("jev", jev), ("router", router)):
            tests[f"{name}_vs_baseline"] = asdict(paired_test(baseline, values, exact_max_discordant=exact_max))
    return {
        "verdict": verdict, "accuracy": accuracies,
        "intervals_95": {"router": list(accuracy_interval(router, alpha=alpha)),
                         "llm": list(accuracy_interval(llm, alpha=alpha)), "router_minus_llm": [low, high]},
        "tests": tests,
        "checks": {"router_better": better, "router_worse": worse, "within_margin": within,
                   "cost_ratio": ratio, "cheap_enough": cheap,
                   "memorization_flag_llm": accuracy(llm) > float(config["memorization_accuracy"])},
        "costs_per_1000": costs_per_1000, "rules_version": "router_v1",
        "thresholds": {"alpha": alpha, "equivalence_margin": margin, "max_cost_ratio": max_cost_ratio},
    }
