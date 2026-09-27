"""Experiment 3 preregistered analysis (fixed before any paid experiment-3 call).

All comparisons are paired, on the fresh sealed set.

Primary questions (two-sided McNemar, Holm-corrected across the two):
  P1 trace:   B-prime final vs experiment-2 B final  -> does decision-trace feedback help the Jev loop?
  P2 weights: B-plus final vs B-prime final           -> do fitted question weights help on top of it?
Each answer is "helps", "hurts" or "no_detectable_difference".

Reported, not primary:
  - learning checks: B-prime final vs version 0; B-plus final vs its version 0 (v0 rubric + fitted weights)
  - the Arena headline verdict (arena_v2 rows) with B-prime as "B" against experiment 2's Loop A,
    and the same with B-plus as a secondary line
  - each Jev arm vs the style code baseline; costs per 1,000 decisions
"""
from __future__ import annotations

from typing import Sequence

from verdict import accuracy, compute_verdict, paired_test


def holm(p_values: dict[str, float], alpha: float) -> dict[str, bool]:
    """Holm-Bonferroni step-down: which hypotheses are rejected at family-wise alpha."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    rejected: dict[str, bool] = {name: False for name in p_values}
    for rank, (name, p_value) in enumerate(ordered):
        if p_value <= alpha / (len(ordered) - rank):
            rejected[name] = True
        else:
            break
    return rejected


def _answer(new: Sequence[bool], old: Sequence[bool], significant: bool) -> str:
    if not significant:
        return "no_detectable_difference"
    return "helps" if accuracy(new) > accuracy(old) else "hurts"


def compute_trace_verdict(*, vectors: dict[str, Sequence[bool]], costs_per_1000: dict[str, float],
                          config: dict) -> dict:
    """vectors keys: a_version0, a_final, b_version0, b_final, bp_final, bw_version0, bw_final, baseline."""
    exact_max = int(config["mcnemar_exact_max_discordant"])
    alpha = float(config["trace_primary_alpha"])
    tests = {
        "p1_trace_bp_vs_b": paired_test(vectors["b_final"], vectors["bp_final"], exact_max_discordant=exact_max),
        "p2_weights_bw_vs_bp": paired_test(vectors["bp_final"], vectors["bw_final"], exact_max_discordant=exact_max),
    }
    significant = holm({name: test.p_value for name, test in tests.items()}, alpha)
    primary = {
        "trace": _answer(vectors["bp_final"], vectors["b_final"], significant["p1_trace_bp_vs_b"]),
        "weights": _answer(vectors["bw_final"], vectors["bp_final"], significant["p2_weights_bw_vs_bp"]),
    }
    learning = {
        "bp_final_vs_version0": paired_test(vectors["b_version0"], vectors["bp_final"], exact_max_discordant=exact_max),
        "bw_final_vs_version0": paired_test(vectors["bw_version0"], vectors["bw_final"], exact_max_discordant=exact_max),
    }
    headline = {
        arm: compute_verdict(
            a_version0=vectors["a_version0"], a_final=vectors["a_final"],
            b_version0=vectors["b_version0"] if arm == "bp" else vectors["bw_version0"],
            b_final=vectors[f"{arm}_final"],
            a_cost_per_1000=costs_per_1000["a_final"], b_cost_per_1000=costs_per_1000[f"{arm}_final"],
            config=config, baseline=vectors["baseline"],
        )
        for arm in ("bp", "bw")
    }
    return {
        "primary": primary,
        "primary_tests": {name: {**test.__dict__, "significant_after_holm": significant[name]} for name, test in tests.items()},
        "learning_checks": {name: {**test.__dict__, "learned": test.b > test.c and test.p_value < float(config["alpha"])}
                            for name, test in learning.items()},
        "accuracy": {name: accuracy(values) for name, values in vectors.items()},
        "headline_arena_v2": {"primary_bp": headline["bp"], "secondary_bw": headline["bw"]},
        "costs_per_1000": costs_per_1000,
    }
