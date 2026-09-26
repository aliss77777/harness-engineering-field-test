import pytest

from deciders import LLMDecider, RubricDecider, RubricQuestion, rubric_score


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


def test_llm_decider_parses_complete_batch():
    class Generator:
        def generate_json(self, *, prompt, schema, event):
            assert event["pair_id"] == ["one", "two"]
            return {
                "decisions": [
                    {"pair_id": "one", "prediction": "X", "reason": "More curiosity."},
                    {"pair_id": "two", "prediction": "Y", "reason": "Stronger emotion."},
                ]
            }

    pairs = [
        {"pair_id": "one", "headline_x": "A", "headline_y": "B"},
        {"pair_id": "two", "headline_x": "C", "headline_y": "D"},
    ]
    decisions = LLMDecider(Generator()).decide_batch(
        instructions="Choose well.", pairs=pairs, event={"run_id": "test"}
    )
    assert decisions["one"].prediction == "X"
    assert decisions["two"].reason == "Stronger emotion."


def test_llm_decider_rejects_missing_pair():
    class Generator:
        def generate_json(self, **_kwargs):
            return {"decisions": []}

    with pytest.raises(ValueError, match="missing"):
        LLMDecider(Generator()).decide_batch(
            instructions="Choose.",
            pairs=[{"pair_id": "one", "headline_x": "A", "headline_y": "B"}],
            event={},
        )
