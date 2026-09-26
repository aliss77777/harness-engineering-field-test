from evidence import build_evidence_table


def test_evidence_counts_only_splits_and_yes_wins():
    records = [
        {
            "winner": "X",
            "questions": {
                "q1": {"x_yes_probability": 0.9, "y_yes_probability": 0.1},
                "q2": {"x_yes_probability": 0.8, "y_yes_probability": 0.7},
            },
        },
        {
            "winner": "X",
            "questions": {
                "q1": {"x_yes_probability": 0.2, "y_yes_probability": 0.8},
                "q2": {"x_yes_probability": 0.1, "y_yes_probability": 0.2},
            },
        },
    ]
    table = {row["question_id"]: row for row in build_evidence_table(records, ["q1", "q2"])}
    assert table["q1"] == {
        "question_id": "q1", "splits": 2, "yes_won": 1, "yes_win_rate": 0.5,
        "reading": None,
    }
    assert table["q2"]["splits"] == 0
    assert table["q2"]["yes_win_rate"] is None
    assert table["q2"]["reading"] == "rarely applies"
