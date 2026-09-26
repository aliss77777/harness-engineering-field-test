import pytest

from editor import validate_edit, validate_starting_versions


CONFIG = {"learning": {
    "max_changes": 3,
    "max_instructions_words": 300,
    "max_rubric_questions": 10,
    "starting_rubric_min_questions": 5,
    "starting_rubric_max_questions": 8,
}}


def valid_versions():
    return {
        "instructions": "Prefer specific, curiosity-producing headlines.",
        "rubric_questions": [
            {"question_id": f"q{i}", "text": f"Does criterion {i} apply?", "direction": "helps"}
            for i in range(5)
        ],
    }


def test_starting_versions_are_valid():
    validate_starting_versions(valid_versions(), CONFIG)


def test_starting_versions_reject_duplicate_ids():
    data = valid_versions()
    data["rubric_questions"][1]["question_id"] = "q0"
    with pytest.raises(ValueError, match="unique"):
        validate_starting_versions(data, CONFIG)


def test_starting_versions_reject_non_question():
    data = valid_versions()
    data["rubric_questions"][0]["text"] = "Creates curiosity"
    with pytest.raises(ValueError, match="questions"):
        validate_starting_versions(data, CONFIG)


def test_edit_limits_are_enforced():
    with pytest.raises(ValueError, match="1 to 3"):
        validate_edit(
            {"instructions": "Choose.", "changes": [{"reason": "x"}] * 4},
            "A",
            CONFIG,
        )


def test_edit_reason_must_be_one_line():
    with pytest.raises(ValueError, match="single-line"):
        validate_edit(
            {"instructions": "Choose.", "changes": [{"reason": "one\ntwo"}]},
            "A",
            CONFIG,
        )
