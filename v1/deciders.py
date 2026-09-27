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
    questions: Iterable[RubricQuestion],
    yes_probabilities: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Sum of yes-probabilities signed by direction; optional per-question weights (Loop B-plus)."""
    score = 0.0
    for question in questions:
        probability = float(yes_probabilities[question.question_id])
        if not 0 <= probability <= 1:
            raise ValueError("yes probabilities must be between 0 and 1")
        weight = 1.0 if weights is None else float(weights[question.question_id])
        score += weight * (probability if question.direction == "helps" else -probability)
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
        weights: dict[str, float] | None = None,
    ):
        self.questions = questions
        self.evaluator = evaluator
        self.rng = random.Random(seed)
        self.weights = weights

    def decide(self, headline_x: str, headline_y: str) -> Decision:
        x = self.evaluator(headline_x, self.questions)
        y = self.evaluator(headline_y, self.questions)
        return self.decide_from_probabilities(x, y)

    def decide_from_probabilities(
        self,
        x: dict[str, float],
        y: dict[str, float],
        tie_breaker: random.Random | None = None,
    ) -> Decision:
        """Pass tie_breaker (seeded per pair) when pairs are scored concurrently."""
        x_score = rubric_score(self.questions, x, self.weights)
        y_score = rubric_score(self.questions, y, self.weights)
        tied = x_score == y_score
        rng = tie_breaker or self.rng
        prediction: Choice = rng.choice(("X", "Y")) if tied else ("X" if x_score > y_score else "Y")
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


DEFAULT_WORDING = {
    "item": "headline",
    "context": "story",
    "decider_question": "Which headline received more clicks?",
    "outcome": "which headline received more clicks",
}


class LLMDecider:
    """Loop A: the LLM reads both items and picks one, with a one-line reason.

    Pairs are dicts with pair_id, context, x and y. Wording and the labels shown
    for X and Y come from task.yaml, so no task text lives in code.
    """

    def __init__(
        self,
        generator: JsonGenerator,
        *,
        wording: dict[str, str] | None = None,
        labels: dict[str, str] | None = None,
    ):
        self.generator = generator
        self.wording = {**DEFAULT_WORDING, **(wording or {})}
        self.labels = {"x": "X", "y": "Y", **(labels or {})}

    def render_pair(self, pair: dict[str, str]) -> str:
        item = self.wording["item"].capitalize()
        lines = [f"=== Pair {pair['pair_id']} ==="]
        if pair.get("context"):
            lines.append(f"{self.wording['context'].upper()}:\n{pair['context']}")
        lines.append(f"{item} {self.labels['x']}:\n{pair['x']}")
        lines.append(f"{item} {self.labels['y']}:\n{pair['y']}")
        return "\n\n".join(lines)

    def decide_batch(
        self,
        *,
        instructions: str,
        pairs: list[dict[str, str]],
        event: dict[str, Any],
    ) -> dict[str, Decision]:
        label_x, label_y = self.labels["x"], self.labels["y"]
        rendered = "\n\n".join(self.render_pair(pair) for pair in pairs)
        prompt = f"""Use these instructions to predict {self.wording['outcome']} in each pair.

INSTRUCTIONS:
{instructions}

PAIRS:
{rendered}

For every pair: {self.wording['decider_question']} Answer {label_x} or {label_y}, then give one short, single-line reason. Do not omit pairs."""
        schema = {
            "type": "object",
            "properties": {
                "decisions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pair_id": {"type": "string"},
                            "prediction": {"type": "string", "enum": [label_x, label_y]},
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
        to_choice = {label_x: "X", label_y: "Y"}
        decisions: dict[str, Decision] = {}
        for item in result.get("decisions", []):
            pair_id = str(item["pair_id"])
            if pair_id in decisions:
                raise ValueError(f"duplicate decision for pair {pair_id}")
            reason = " ".join(str(item["reason"]).splitlines()).strip()
            decisions[pair_id] = Decision(
                prediction=to_choice[str(item["prediction"])], reason=reason
            )
        expected = {pair["pair_id"] for pair in pairs}
        if set(decisions) != expected:
            missing = sorted(expected - set(decisions))
            extra = sorted(set(decisions) - expected)
            raise ValueError(f"decision IDs do not match batch; missing={missing}, extra={extra}")
        return decisions
