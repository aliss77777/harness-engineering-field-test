from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def build_evidence_table(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, float]] = defaultdict(
        lambda: {"splits": 0, "yes_won": 0}
    )
    for record in records:
        winner = record["winner"]
        for question_id, answers in record["questions"].items():
            x_yes = float(answers["x_yes_probability"]) >= 0.5
            y_yes = float(answers["y_yes_probability"]) >= 0.5
            if x_yes == y_yes:
                continue
            counts[question_id]["splits"] += 1
            yes_headline = "X" if x_yes else "Y"
            counts[question_id]["yes_won"] += int(yes_headline == winner)

    table = []
    for question_id in sorted(counts):
        splits = int(counts[question_id]["splits"])
        yes_won = int(counts[question_id]["yes_won"])
        table.append(
            {
                "question_id": question_id,
                "splits": splits,
                "yes_won": yes_won,
                "yes_win_rate": yes_won / splits if splits else None,
            }
        )
    return table

