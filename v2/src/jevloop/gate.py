# Ported from v1/gate.py at tag v1-final (a8aae97); unchanged apart from this line.
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from scipy.stats import binomtest


@dataclass(frozen=True)
class GateResult:
    keep: bool
    b: int
    c: int
    p_value: float


def gate_version(
    old_correct: Sequence[bool],
    new_correct: Sequence[bool],
    *,
    p_threshold: float,
) -> GateResult:
    if len(old_correct) != len(new_correct):
        raise ValueError("old and new results must contain the same pairs")
    b = sum(new and not old for old, new in zip(old_correct, new_correct))
    c = sum(old and not new for old, new in zip(old_correct, new_correct))
    discordant = b + c
    p_value = (
        float(binomtest(b, discordant, p=0.5, alternative="greater").pvalue)
        if discordant
        else 1.0
    )
    return GateResult(keep=b > c and p_value < p_threshold, b=b, c=c, p_value=p_value)



def best_passing(results: list[tuple[str, GateResult]]) -> str | None:
    """Single-edit mode: the passing candidate with the largest net gain (b - c), then lowest p."""
    passing = [(key, result) for key, result in results if result.keep]
    if not passing:
        return None
    return min(passing, key=lambda item: (-(item[1].b - item[1].c), item[1].p_value, item[0]))[0]
