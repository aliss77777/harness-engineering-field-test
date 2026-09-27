import pytest

from candidates import (
    InvalidCandidate, apply_candidate, is_near_duplicate, sample_mistakes, signature,
)
from gate import GateResult, best_passing


CONFIG = {"learning": {"max_instructions_words": 20, "max_rubric_questions": 3}}
RUBRIC = {"rubric_questions": [
    {"question_id": "direct", "text": "Does it answer directly?", "direction": "helps"},
    {"question_id": "refuses", "text": "Does it refuse?", "direction": "hurts"},
]}


def b(operation, question_id, text="", direction="helps"):
    return {"operation": operation, "question_id": question_id, "text": text,
            "direction": direction, "reason": "evidence table"}


def test_loop_a_replace_requires_unique_target():
    current = {"instructions": "Prefer short answers. Prefer short answers."}
    with pytest.raises(InvalidCandidate, match="exactly once"):
        apply_candidate("A", current, {"operation": "replace", "target_text": "Prefer short answers.",
                                       "new_text": "x", "reason": "r"}, CONFIG)


def test_loop_a_replace_and_word_limit():
    current = {"instructions": "Prefer short answers."}
    out = apply_candidate("A", current, {"operation": "replace", "target_text": "short",
                                         "new_text": "complete", "reason": "r"}, CONFIG)
    assert out == {"instructions": "Prefer complete answers."}
    with pytest.raises(InvalidCandidate, match="word limit"):
        apply_candidate("A", current, {"operation": "append", "target_text": "",
                                       "new_text": "word " * 30, "reason": "r"}, CONFIG)


def test_loop_b_operations_change_exactly_one_thing():
    assert [q["question_id"] for q in apply_candidate("B", RUBRIC, b("drop", "refuses"), CONFIG)["rubric_questions"]] == ["direct"]
    flipped = apply_candidate("B", RUBRIC, b("flip", "refuses"), CONFIG)["rubric_questions"]
    assert flipped[1]["direction"] == "helps" and flipped[0] == RUBRIC["rubric_questions"][0]
    added = apply_candidate("B", RUBRIC, b("add", "padded", "Is it padded?", "hurts"), CONFIG)["rubric_questions"]
    assert added[-1] == {"question_id": "padded", "text": "Is it padded?", "direction": "hurts"}
    assert RUBRIC["rubric_questions"][1]["direction"] == "hurts"  # original untouched


def test_loop_b_rejects_invalid_operations():
    with pytest.raises(InvalidCandidate):
        apply_candidate("B", RUBRIC, b("drop", "missing"), CONFIG)
    with pytest.raises(InvalidCandidate):
        apply_candidate("B", RUBRIC, b("add", "direct", "Dup?"), CONFIG)
    full = {"rubric_questions": RUBRIC["rubric_questions"] + [{"question_id": "c", "text": "C?", "direction": "helps"}]}
    with pytest.raises(InvalidCandidate, match="limit"):
        apply_candidate("B", full, b("add", "d", "D?"), CONFIG)


def test_near_duplicates_of_rejected_edits_are_detected():
    rejected = [signature("B", b("drop", "refuses"))]
    assert is_near_duplicate(signature("B", b("drop", "refuses")), rejected, 0.9)
    assert not is_near_duplicate(signature("B", b("flip", "direct")), rejected, 0.9)


def test_mistake_sample_changes_by_round_and_is_seeded():
    records = [{"pair_id": str(i), "correct": i % 3 == 0} for i in range(300)]
    first = sample_mistakes(records, count=20, seed=1, round_number=1, loop="A")
    assert first == sample_mistakes(records, count=20, seed=1, round_number=1, loop="A")
    assert first != sample_mistakes(records, count=20, seed=1, round_number=2, loop="A")
    assert all(not item["correct"] for item in first) and len(first) == 20


def test_best_passing_prefers_largest_net_gain():
    results = [
        ("c1", GateResult(True, 40, 20, 0.01)),
        ("c2", GateResult(True, 60, 30, 0.001)),
        ("c3", GateResult(False, 90, 80, 0.2)),
    ]
    assert best_passing(results) == "c2"
    assert best_passing([("c3", GateResult(False, 1, 0, 0.5))]) is None
