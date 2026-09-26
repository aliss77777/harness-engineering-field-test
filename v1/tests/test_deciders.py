import pytest

from deciders import RubricDecider, RubricQuestion, rubric_score


QUESTIONS = [
    RubricQuestion("curiosity", "Does it create curiosity?", "helps"),
    RubricQuestion("spoils", "Does it reveal the outcome?", "hurts"),
]


def test_rubric_score_applies_direction():
    assert rubric_score(QUESTIONS, {"curiosity": 0.8, "spoils": 0.2}) == pytest.approx(0.6)


def test_rubric_decider_sums_probabilities():
    def evaluate(headline, _questions):
        return (
            {"curiosity": 0.9, "spoils": 0.1}
            if headline == "curious"
            else {"curiosity": 0.2, "spoils": 0.8}
        )

    decision = RubricDecider(QUESTIONS, evaluate, seed=1).decide("curious", "plain")
    assert decision.prediction == "X"
    assert not decision.coin_flip_tie


def test_rubric_decider_marks_seeded_exact_tie():
    def evaluate(_headline, _questions):
        return {"curiosity": 0.5, "spoils": 0.5}

    first = RubricDecider(QUESTIONS, evaluate, seed=7).decide("same", "same")
    second = RubricDecider(QUESTIONS, evaluate, seed=7).decide("same", "same")
    assert first.prediction == second.prediction
    assert first.coin_flip_tie
