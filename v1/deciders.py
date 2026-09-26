from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Literal, Protocol


Choice = Literal["X", "Y"]


@dataclass(frozen=True)
class Decision:
    prediction: Choice
    reason: str | None = None
    question_probabilities: dict[str, dict[str, float]] | None = None
    coin_flip_tie: bool = False


@dataclass(frozen=True)
class RubricQuestion:
    question_id: str
    text: str
    direction: Literal["helps", "hurts"]


def rubric_score(
    questions: Iterable[RubricQuestion], yes_probabilities: dict[str, float]
) -> float:
    score = 0.0
    for question in questions:
        probability = float(yes_probabilities[question.question_id])
        if not 0 <= probability <= 1:
            raise ValueError("yes probabilities must be between 0 and 1")
        score += probability if question.direction == "helps" else -probability
    return score


class FakeDecider:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def decide(self, headline_x: str, headline_y: str) -> Decision:
        return Decision(prediction=self.rng.choice(("X", "Y")), reason="seeded random")


class RubricDecider:
    def __init__(
        self,
        questions: list[RubricQuestion],
        evaluator: Callable[[str, list[RubricQuestion]], dict[str, float]],
        seed: int,
    ):
        self.questions = questions
        self.evaluator = evaluator
        self.rng = random.Random(seed)

    def decide(self, headline_x: str, headline_y: str) -> Decision:
        x = self.evaluator(headline_x, self.questions)
        y = self.evaluator(headline_y, self.questions)
        return self.decide_from_probabilities(x, y)

    def decide_from_probabilities(
        self, x: dict[str, float], y: dict[str, float]
    ) -> Decision:
        x_score = rubric_score(self.questions, x)
        y_score = rubric_score(self.questions, y)
        tied = x_score == y_score
        prediction: Choice = self.rng.choice(("X", "Y")) if tied else ("X" if x_score > y_score else "Y")
        probabilities = {
            question.question_id: {
                "x_yes_probability": x[question.question_id],
                "y_yes_probability": y[question.question_id],
            }
            for question in self.questions
        }
        return Decision(
            prediction=prediction,
            question_probabilities=probabilities,
            coin_flip_tie=tied,
        )


class JsonGenerator(Protocol):
    def generate_json(
        self, *, prompt: str, schema: dict[str, Any], event: dict[str, Any]
    ) -> dict[str, Any]: ...


class LLMDecider:
    def __init__(self, generator: JsonGenerator):
        self.generator = generator

    def decide_batch(
        self,
        *,
        instructions: str,
        pairs: list[dict[str, str]],
        event: dict[str, Any],
    ) -> dict[str, Decision]:
        rendered = "\n\n".join(
            f"Pair {pair['pair_id']}\nX: {pair['headline_x']}\nY: {pair['headline_y']}"
            for pair in pairs
        )
        prompt = f"""Use these instructions to predict which headline in each pair received more clicks.

INSTRUCTIONS:
{instructions}

PAIRS:
{rendered}

For every pair, choose X or Y and give one short, single-line reason. Do not omit pairs."""
        schema = {
            "type": "object",
            "properties": {
                "decisions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pair_id": {"type": "string"},
                            "prediction": {"type": "string", "enum": ["X", "Y"]},
                            "reason": {"type": "string"},
                        },
                        "required": ["pair_id", "prediction", "reason"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["decisions"],
            "additionalProperties": False,
        }
        result = self.generator.generate_json(
            prompt=prompt,
            schema=schema,
            event={**event, "pair_id": [pair["pair_id"] for pair in pairs]},
        )
        decisions: dict[str, Decision] = {}
        for item in result.get("decisions", []):
            pair_id = str(item["pair_id"])
            if pair_id in decisions:
                raise ValueError(f"duplicate decision for pair {pair_id}")
            reason = " ".join(str(item["reason"]).splitlines()).strip()
            decisions[pair_id] = Decision(
                prediction=item["prediction"], reason=reason
            )
        expected = {pair["pair_id"] for pair in pairs}
        if set(decisions) != expected:
            missing = sorted(expected - set(decisions))
            extra = sorted(set(decisions) - expected)
            raise ValueError(f"decision IDs do not match batch; missing={missing}, extra={extra}")
        return decisions
