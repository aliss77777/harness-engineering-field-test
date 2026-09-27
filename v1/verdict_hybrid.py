"""Experiment 4 preregistered verdict (Task Brief 4_Hybrids.md, section 5).

Primary: hybrid vs A* (the LLM alone) on sealed-4, two-sided McNemar, alpha 0.05.
Rows, first match wins:
  1. hybrid significantly more accurate than A*  -> hybrid_beats_llm
  2. hybrid significantly less accurate than A*  -> combination_hurts
  3. 95% interval of (hybrid - A*) within +/- margin -> no_meaningful_gain
  4. anything else                                -> inconclusive
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from verdict import accuracy, accuracy_interval, paired_difference_interval, paired_test


def compute_hybrid_verdict(*, llm: Sequence[bool], jev: Sequence[bool], hybrid: Sequence[bool],
                           baseline: Sequence[bool] | None, costs_per_1000: dict[str, float],
                           config: dict) -> dict:
    alpha = float(config["alpha"])
    margin = float(config["equivalence_margin"])
    exact_max = int(config["mcnemar_exact_max_discordant"])
    primary = paired_test(llm, hybrid, exact_max_discordant=exact_max)
    difference = paired_difference_interval(hybrid, llm, alpha=alpha)
    better = accuracy(hybrid) > accuracy(llm) and primary.p_value < alpha
    worse = accuracy(hybrid) < accuracy(llm) and primary.p_value < alpha
    within = difference[0] >= -margin and difference[1] <= margin
    if better:
        verdict = "hybrid_beats_llm"
    elif worse:
        verdict = "combination_hurts"
    elif within:
        verdict = "no_meaningful_gain"
    else:
        verdict = "inconclusive"
    tests = {"hybrid_vs_llm": asdict(primary),
             "hybrid_vs_jev": asdict(paired_test(jev, hybrid, exact_max_discordant=exact_max)),
             "llm_vs_jev": asdict(paired_test(jev, llm, exact_max_discordant=exact_max))}
    if baseline is not None:
        for name, values in (("llm", llm), ("jev", jev), ("hybrid", hybrid)):
            tests[f"{name}_vs_baseline"] = asdict(paired_test(baseline, values, exact_max_discordant=exact_max))
    accuracies = {"llm": accuracy(llm), "jev": accuracy(jev), "hybrid": accuracy(hybrid)}
    if baseline is not None:
        accuracies["baseline"] = accuracy(baseline)
    return {
        "verdict": verdict,
        "accuracy": accuracies,
        "intervals_95": {"hybrid": list(accuracy_interval(hybrid, alpha=alpha)),
                         "llm": list(accuracy_interval(llm, alpha=alpha)),
                         "hybrid_minus_llm": list(difference)},
        "tests": tests,
        "checks": {"hybrid_better": better, "hybrid_worse": worse, "within_margin": within,
                   "memorization_flag_llm": accuracy(llm) > float(config["memorization_accuracy"]),
                   "memorization_flag_hybrid": accuracy(hybrid) > float(config["memorization_accuracy"])},
        "costs_per_1000": costs_per_1000,
        "rules_version": "hybrid_v1",
        "thresholds": {"alpha": alpha, "equivalence_margin": margin},
    }
