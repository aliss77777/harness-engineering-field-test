# Ported from v1/jev.py at tag v1-final (a8aae97). Adapted: v2's cache/log/spend modules; questions are
# passed as Question objects from jevloop.rubric; the request and answer format are unchanged.
"""Jev client: Jev answers yes/no questions about a text (in v2, a run summary) with a probability of "yes".

Kept from v1: the pinned model and provider are checked on every reply (RouteMismatchError is fatal);
HTTP 402 means no credit and is fatal; other failures retry with capped exponential backoff; answers are
cached on disk so reruns are free; the spend cap is checked before every paid call.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from jevloop.cache import DiskCache
from jevloop.log import JsonlLogger
from jevloop.openrouter import IncompleteResponseError, OutOfCreditsError, RouteMismatchError
from jevloop.spend import SpendTracker

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class JevClient:
    def __init__(self, *, model: str, expected_model: str, expected_provider: str, api_key: str, cache: DiskCache,
                 logger: JsonlLogger, spend: SpendTracker | None, retries: int = 8, backoff_seconds: float = 5.0,
                 max_backoff_seconds: float = 120.0, http_client: httpx.Client | None = None, sleep=time.sleep):
        self.model = model
        self.expected_model = expected_model
        self.expected_provider = expected_provider
        self.api_key = api_key
        self.cache = cache
        self.logger = logger
        self.spend = spend
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.http = http_client or httpx.Client(timeout=60.0)
        self.sleep = sleep

    def evaluate(self, state: str, questions: list, event: dict[str, Any]) -> dict[str, Any]:
        """Returns {"probabilities": {question_id: P(yes)}, "usage": {...}, "cached": bool}."""
        payload = {"model": self.model, "state": state,
                   "questions": {q.question_id: {"type": "noul", "instructions": q.text} for q in questions}}
        cached = self.cache.get(payload)
        if cached is not None:
            self._validate_route(cached.get("model"), cached.get("provider"))
            self.logger.write({**event, "model": cached.get("model"), "cached": True, **cached["usage"]})
            return {"probabilities": cached["probabilities"], "usage": cached["usage"], "cached": True}
        if self.spend is not None:
            self.spend.check()
        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self.http.post(DECISIONS_URL, json=payload, headers={
                    "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "X-Title": "Jev Learning Loop v2"})
                if response.status_code == 402:
                    raise OutOfCreditsError("OpenRouter returned 402 Payment Required: add credit, then rerun (finished calls are cached)")
                if response.status_code in (408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529):
                    raise IncompleteResponseError(f"HTTP {response.status_code}: {response.text[:300]}")
                response.raise_for_status()
                body = response.json()
                if not body.get("model") or "error" in body:
                    raise IncompleteResponseError(f"response without model: {str(body)[:300]}")
                self._validate_route(body.get("model"), body.get("provider"))
                probabilities = {q.question_id: float(body["answers"][q.question_id]["noul"]) for q in questions}
                u = body.get("usage", {})
                usage = {"input_tokens": int(u.get("input_tokens", 0) or 0), "output_tokens": int(u.get("output_tokens", 0) or 0),
                         "cost": float(u.get("cost", 0) or 0), "latency_ms": round((time.perf_counter() - started) * 1000)}
                if self.spend is not None:
                    self.spend.record(usage["cost"])
                self.cache.put(payload, {"probabilities": probabilities, "usage": usage, "model": body.get("model"),
                                         "provider": body.get("provider")})
                self.logger.write({**event, "model": body.get("model"), "provider": body.get("provider"), "cached": False,
                                   "attempt": attempt, **usage})
                return {"probabilities": probabilities, "usage": usage, "cached": False}
            except Exception as error:
                self.logger.write({**event, "model": self.model, "cached": False, "attempt": attempt,
                                   "error_type": type(error).__name__, "error": str(error)[:500]})
                if isinstance(error, (RouteMismatchError, OutOfCreditsError)) or attempt == self.retries:
                    raise
                self.sleep(min(self.backoff_seconds * 2 ** (attempt - 1), self.max_backoff_seconds))
        raise RuntimeError("unreachable")

    def _validate_route(self, model: str | None, provider: str | None) -> None:
        if model != self.expected_model:
            raise RouteMismatchError(f"served model changed: expected {self.expected_model}, got {model}")
        if provider != self.expected_provider:
            raise RouteMismatchError(f"served provider changed: expected {self.expected_provider}, got {provider}")
