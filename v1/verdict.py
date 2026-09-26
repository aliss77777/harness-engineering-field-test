from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

from scipy.stats import binomtest, norm
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint


@dataclass(frozen=True)
class PairedTest:
    b: int
    c: int
    discordant: int
    p_value: float
    method: str


def _validate_same_length(*values: Sequence[bool]) -> int:
    lengths = {len(value) for value in values}
    if len(lengths) != 1:
        raise ValueError("all result vectors must contain the same sealed pairs")
    size = lengths.pop()
    if size == 0:
        raise ValueError("result vectors cannot be empty")
    return size


def accuracy(values: Sequence[bool]) -> float:
    if not values:
        raise ValueError("result vector cannot be empty")
    return sum(bool(value) for value in values) / len(values)


def accuracy_interval(
    values: Sequence[bool], *, alpha: float
) -> tuple[float, float]:
    successes = sum(bool(value) for value in values)
    low, high = proportion_confint(
        successes, len(values), alpha=alpha, method="wilson"
    )
    return float(low), float(high)


def paired_difference_interval(
    b_values: Sequence[bool],
    a_values: Sequence[bool],
    *,
    alpha: float,
) -> tuple[float, float]:
    size = _validate_same_length(b_values, a_values)
    differences = [int(b) - int(a) for b, a in zip(b_values, a_values)]
    mean = sum(differences) / size
    if size == 1:
        return mean, mean
    sample_variance = sum((value - mean) ** 2 for value in differences) / (size - 1)
    standard_error = math.sqrt(sample_variance / size)
    critical = float(norm.ppf(1 - alpha / 2))
    return max(-1.0, mean - critical * standard_error), min(
        1.0, mean + critical * standard_error
    )


def paired_test(
    old_values: Sequence[bool],
    new_values: Sequence[bool],
    *,
    exact_max_discordant: int,
) -> PairedTest:
    _validate_same_length(old_values, new_values)
    b = sum(new and not old for old, new in zip(old_values, new_values))
    c = sum(old and not new for old, new in zip(old_values, new_values))
    discordant = b + c
    if discordant == 0:
        return PairedTest(b=b, c=c, discordant=0, p_value=1.0, method="exact")
    if discordant <= exact_max_discordant:
        p_value = float(
            binomtest(b, discordant, p=0.5, alternative="two-sided").pvalue
        )
        method = "exact"
    else:
        table = [[0, c], [b, 0]]
        p_value = float(mcnemar(table, exact=False, correction=True).pvalue)
        method = "chi_square_continuity_corrected"
    return PairedTest(
        b=b, c=c, discordant=discordant, p_value=p_value, method=method
    )


def cost_ratio(cost_b_per_1000: float, cost_a_per_1000: float) -> float:
    if cost_a_per_1000 < 0 or cost_b_per_1000 < 0:
        raise ValueError("costs cannot be negative")
    if cost_a_per_1000 == 0:
        return 0.0 if cost_b_per_1000 == 0 else math.inf
    return cost_b_per_1000 / cost_a_per_1000


def compute_verdict(
    *,
    a_version0: Sequence[bool],
    a_final: Sequence[bool],
    b_version0: Sequence[bool],
    b_final: Sequence[bool],
    a_cost_per_1000: float,
    b_cost_per_1000: float,
    config: dict,
) -> dict:
    _validate_same_length(a_version0, a_final, b_version0, b_final)
    alpha = float(config["alpha"])
    margin = float(config["equivalence_margin"])
    exact_max = int(config["mcnemar_exact_max_discordant"])

    accuracies = {
        "a_version0": accuracy(a_version0),
        "a_final": accuracy(a_final),
        "b_version0": accuracy(b_version0),
        "b_final": accuracy(b_final),
    }
    intervals = {
        "a_final": accuracy_interval(a_final, alpha=alpha),
        "b_final": accuracy_interval(b_final, alpha=alpha),
        "b_minus_a": paired_difference_interval(b_final, a_final, alpha=alpha),
    }
    tests = {
        "a_learning": paired_test(
            a_version0, a_final, exact_max_discordant=exact_max
        ),
        "b_learning": paired_test(
            b_version0, b_final, exact_max_discordant=exact_max
        ),
        "b_vs_a": paired_test(a_final, b_final, exact_max_discordant=exact_max),
    }
    signal_a = intervals["a_final"][0] > 0.5
    signal_b = intervals["b_final"][0] > 0.5
    a_learned = (
        accuracies["a_final"] > accuracies["a_version0"]
        and tests["a_learning"].p_value < alpha
    )
    b_learned = (
        accuracies["b_final"] > accuracies["b_version0"]
        and tests["b_learning"].p_value < alpha
    )
    b_better = (
        accuracies["b_final"] > accuracies["a_final"]
        and tests["b_vs_a"].p_value < alpha
    )
    a_better = (
        accuracies["a_final"] > accuracies["b_final"]
        and tests["b_vs_a"].p_value < alpha
    )
    same_quality = (
        intervals["b_minus_a"][0] >= -margin
        and intervals["b_minus_a"][1] <= margin
    )
    ratio = cost_ratio(b_cost_per_1000, a_cost_per_1000)
    cheaper = ratio <= float(config["max_cost_ratio"])

    if not signal_a and not signal_b:
        verdict = "no_signal"
    elif b_learned and b_better:
        verdict = "jev_loop_learns_better"
    elif b_learned and same_quality and cheaper:
        verdict = "learns_as_well_far_cheaper"
    elif a_better:
        verdict = "hypothesis_weakened"
    else:
        verdict = "inconclusive"

    return {
        "verdict": verdict,
        "accuracy": accuracies,
        "intervals_95": {key: list(value) for key, value in intervals.items()},
        "tests": {key: asdict(value) for key, value in tests.items()},
        "checks": {
            "signal_a": signal_a,
            "signal_b": signal_b,
            "a_learned": a_learned,
            "b_learned": b_learned,
            "b_better": b_better,
            "a_better": a_better,
            "same_quality": same_quality,
            "cheaper": cheaper,
            "memorization_flag": accuracies["a_version0"]
            > float(config["memorization_accuracy"]),
        },
        "cost": {
            "a_per_1000": a_cost_per_1000,
            "b_per_1000": b_cost_per_1000,
            "b_over_a_ratio": ratio,
        },
        "thresholds": dict(config),
    }

