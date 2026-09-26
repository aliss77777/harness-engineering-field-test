from __future__ import annotations

import time
from typing import Any

import httpx

from cache import DiskCache
from deciders import RubricQuestion
from log import JsonlLogger


DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class OpenRouterJevClient:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        cache: DiskCache,
        logger: JsonlLogger,
        retries: int,
        backoff_seconds: float,
        http_client: httpx.Client | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.cache = cache
        self.logger = logger
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.http = http_client or httpx.Client(timeout=60.0)

    def evaluate(
        self,
        headline: str,
        questions: list[RubricQuestion],
        event: dict[str, Any],
    ) -> dict[str, float]:
        payload = {
            "model": self.model,
            "state": headline,
            "questions": {
                question.question_id: {
                    "type": "noul",
                    "instructions": question.text,
                }
                for question in questions
            },
        }
        cached = self.cache.get(payload)
        if cached is not None:
            self.logger.write(
                {
                    **event,
                    "model": cached.get("model", self.model),
                    "cached": True,
                    **cached["usage"],
                }
            )
            return cached["probabilities"]

        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self.http.post(
                    DECISIONS_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-Title": "Jev Learning Loop MVP",
                    },
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                probabilities = {
                    question.question_id: float(body["answers"][question.question_id]["noul"])
                    for question in questions
                }
                usage_body = body.get("usage", {})
                usage = {
                    "input_tokens": int(usage_body.get("input_tokens", 0) or 0),
                    "output_tokens": int(usage_body.get("output_tokens", 0) or 0),
                    "cost": float(usage_body.get("cost", 0) or 0),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                }
                cached_value = {
                    "probabilities": probabilities,
                    "usage": usage,
                    "model": body.get("model", self.model),
                    "provider": body.get("provider"),
                }
                self.cache.put(payload, cached_value)
                self.logger.write(
                    {
                        **event,
                        "model": cached_value["model"],
                        "provider": cached_value["provider"],
                        "cached": False,
                        "attempt": attempt,
                        **usage,
                    }
                )
                return probabilities
            except Exception as error:
                self.logger.write(
                    {
                        **event,
                        "model": self.model,
                        "cached": False,
                        "attempt": attempt,
                        "latency_ms": round((time.perf_counter() - started) * 1000),
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
                if attempt == self.retries:
                    raise
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise RuntimeError("unreachable")

