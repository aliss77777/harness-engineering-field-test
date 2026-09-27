"""Seeded random stand-ins for the LLM and Jev clients.

They implement the same interfaces as the real clients, so the fake run exercises
the real evaluation, scoring, tie rule, logging and gate code (MVP brief section 6).
"""
from __future__ import annotations

import hashlib
import random
import threading
from typing import Any


def _rng(*parts: object) -> random.Random:
    return random.Random(hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest())


class _Usage:
    def __init__(self):
        self._local = threading.local()

    @property
    def last_call(self) -> dict[str, Any]:
        return getattr(self._local, "last_call", {})

    @last_call.setter
    def last_call(self, value: dict[str, Any]) -> None:
        self._local.last_call = value


class FakeLLMClient(_Usage):
    def __init__(self, seed: int):
        super().__init__()
        self.seed = seed

    def generate_json(self, *, prompt: str, schema: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        labels = schema["properties"]["decisions"]["items"]["properties"]["prediction"]["enum"]
        self.last_call = {"model": "seeded-random", "cached": False, "cost": 0.0}
        return {"decisions": [
            {"pair_id": pair_id, "prediction": _rng(self.seed, event.get("version_id"), pair_id).choice(labels),
             "reason": "seeded random"}
            for pair_id in event["pair_id"]
        ]}


class FakeJevClient(_Usage):
    def __init__(self, seed: int):
        super().__init__()
        self.seed = seed

    def evaluate(self, state: str, questions, event: dict[str, Any], *, use_cache: bool = True) -> dict[str, float]:
        self.last_call = {"model": "seeded-random", "cached": False, "cost": 0.0}
        return {q.question_id: round(_rng(self.seed, event.get("version_id"), state, q.question_id).random(), 2)
                for q in questions}
