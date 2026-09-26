import pytest

from editor import validate_starting_versions


def valid_versions():
    return {
        "instructions": "Prefer specific, curiosity-producing headlines.",
        "rubric_questions": [
            {"question_id": f"q{i}", "text": f"Does criterion {i} apply?", "direction": "helps"}
            for i in range(5)
        ],
    }


def test_starting_versions_are_valid():
    validate_starting_versions(valid_versions())


def test_starting_versions_reject_duplicate_ids():
    data = valid_versions()
    data["rubric_questions"][1]["question_id"] = "q0"
    with pytest.raises(ValueError, match="unique"):
        validate_starting_versions(data)


def test_starting_versions_reject_non_question():
    data = valid_versions()
    data["rubric_questions"][0]["text"] = "Creates curiosity"
    with pytest.raises(ValueError, match="questions"):
        validate_starting_versions(data)
