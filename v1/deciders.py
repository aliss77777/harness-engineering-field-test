from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterable, Literal


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

