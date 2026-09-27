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
        {"pair_id": "one", "context": "", "x": "A", "y": "B"},
        {"pair_id": "two", "context": "", "x": "C", "y": "D"},
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
            pairs=[{"pair_id": "one", "context": "", "x": "A", "y": "B"}],
            event={},
        )


def test_llm_decider_maps_task_labels_and_shows_context():
    seen = {}

    class Generator:
        def generate_json(self, *, prompt, schema, event):
            seen["prompt"] = prompt
            seen["enum"] = schema["properties"]["decisions"]["items"]["properties"]["prediction"]["enum"]
            return {"decisions": [{"pair_id": "p", "prediction": "2", "reason": "Answers directly."}]}

    decider = LLMDecider(
        Generator(),
        wording={"item": "response", "context": "user request",
                 "decider_question": "Which response did the user prefer?",
                 "outcome": "which response the user preferred"},
        labels={"x": "1", "y": "2"},
    )
    decisions = decider.decide_batch(
        instructions="Prefer direct answers.",
        pairs=[{"pair_id": "p", "context": "What is 2+2?", "x": "Maybe 5.", "y": "4."}],
        event={},
    )
    assert decisions["p"].prediction == "Y"
    assert seen["enum"] == ["1", "2"]
    assert "USER REQUEST:\nWhat is 2+2?" in seen["prompt"]
    assert "Response 1:\nMaybe 5." in seen["prompt"]
