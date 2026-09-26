from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def build_evidence_table(
    records: Iterable[dict[str, Any]], question_ids: Iterable[str] | None = None
) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, float]] = defaultdict(
        lambda: {"splits": 0, "yes_won": 0}
    )
    for question_id in question_ids or []:
        counts[question_id]
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
                "reading": "rarely applies" if splits == 0 else None,
            }
        )
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Loop B evidence table.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run = json.loads(args.input.read_text())
    question_ids = run.get("question_ids")
    table = build_evidence_table(run["decisions"], question_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(table, indent=2) + "\n")
    for row in table:
        rate = "n/a" if row["yes_win_rate"] is None else f"{row['yes_win_rate']:.1%}"
        print(f"{row['question_id']}: splits={row['splits']}, yes_win_rate={rate}")


if __name__ == "__main__":
    main()
