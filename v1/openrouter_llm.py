from __future__ import annotations

import json
import threading
import time
from typing import Any

import httpx

from cache import DiskCache
from log import JsonlLogger


CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class RouteMismatchError(RuntimeError):
    """The provider served a different model or route than preregistered."""


class OutOfCreditsError(RuntimeError):
    """HTTP 402 from OpenRouter: the account has no credit. Fatal; never retried."""


class IncompleteResponseError(RuntimeError):
    """A 200 response without a model name (usually an error body); retried."""


class ContentBlockedError(RuntimeError):
    """The provider refused the input under its content policy. Not retried; cached."""


def is_content_block(body: dict[str, Any]) -> bool:
    error = body.get("error") or {}
    metadata = error.get("metadata") or {}
    return error.get("code") == 403 and (
        metadata.get("error_type") == "content_policy_violation"
        or "PROHIBITED_CONTENT" in str(error.get("message", ""))
    )


class OpenRouterJsonClient:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        cache: DiskCache,
        logger: JsonlLogger,
        retries: int,
        backoff_seconds: float,
        temperature: float,
        reasoning_effort: str,
        expected_model: str,
        expected_provider: str,
        allow_fallbacks: bool,
        http_client: httpx.Client | None = None,
        spend=None,
    ):
        self.model = model
        self.api_key = api_key
        self.cache = cache
        self.logger = logger
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.expected_model = expected_model
        self.expected_provider = expected_provider
        self.allow_fallbacks = allow_fallbacks
        self._local = threading.local()
        self.spend = spend
        self.http = http_client or httpx.Client(timeout=120.0)

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, Any]:
        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "reasoning_effort": self.reasoning_effort,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": schema,
                },
            },
            "provider": {
                "require_parameters": True,
                "allow_fallbacks": self.allow_fallbacks,
            },
        }
        cache_payload = {"provider": "openrouter", **request_body}
        cached = self.cache.get(cache_payload)
        if cached is not None and cached.get("blocked"):
            self.logger.write({**event, "model": self.model, "cached": True, "blocked": True, "cost": 0.0})
            raise ContentBlockedError(cached["error"])
        if cached is not None:
            self._validate_route(cached.get("model"), cached.get("provider"))
            self.last_call = {**cached["usage"], "model": cached["model"], "provider": cached["provider"], "cached": True}
            self.logger.write(
                {
                    **event,
                    "model": cached.get("model", self.model),
                    "provider": cached.get("provider"),
                    "cached": True,
                    **cached["usage"],
                }
            )
            return cached["data"]

        if self.spend is not None:
            self.spend.check()
        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self.http.post(
                    CHAT_COMPLETIONS_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-Title": "Jev Learning Loop MVP",
                    },
                    json=request_body,
                )
                if response.status_code == 402:
                    raise OutOfCreditsError("OpenRouter returned 402 Payment Required: add credit, then rerun (finished calls are cached)")
                response.raise_for_status()
                body = response.json()
                if is_content_block(body):
                    message = str(body["error"].get("message"))
                    # Cached so a rerun makes the same call the same way.
                    self.cache.put(cache_payload, {"blocked": True, "error": message})
                    self.logger.write({**event, "model": self.model, "cached": False, "attempt": attempt,
                                       "blocked": True, "cost": 0.0, "error": message})
                    raise ContentBlockedError(message)
                if not body.get("model") or "error" in body:
                    raise IncompleteResponseError(f"response without model: {str(body)[:300]}")
                self._validate_route(body.get("model"), body.get("provider"))
                content = body["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("OpenRouter returned non-text structured content")
                data = json.loads(content)
                usage_body = body.get("usage", {})
                details = usage_body.get("completion_tokens_details") or {}
                usage = {
                    "input_tokens": int(usage_body.get("prompt_tokens", 0) or 0),
                    "output_tokens": int(usage_body.get("completion_tokens", 0) or 0),
                    "reasoning_tokens": int(details.get("reasoning_tokens", 0) or 0),
                    "cost": float(usage_body.get("cost", 0) or 0),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                }
                cached_value = {
                    "data": data,
                    "usage": usage,
                    "model": body.get("model", self.model),
                    "provider": body.get("provider"),
                }
                if self.spend is not None:
                    self.spend.record(usage["cost"])
                self.cache.put(cache_payload, cached_value)
                self.last_call = {**usage, "model": cached_value["model"], "provider": cached_value["provider"], "cached": False}
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
                return data
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
                if isinstance(error, (RouteMismatchError, ContentBlockedError, OutOfCreditsError)) or attempt == self.retries:
                    raise
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise RuntimeError("unreachable")

    @property
    def last_call(self) -> dict[str, Any]:
        """Usage of the most recent call made by the current thread."""
        return getattr(self._local, "last_call", {})

    @last_call.setter
    def last_call(self, value: dict[str, Any]) -> None:
        self._local.last_call = value

    def _validate_route(self, model: str | None, provider: str | None) -> None:
        if model != self.expected_model:
            raise RouteMismatchError(
                f"served model changed: expected {self.expected_model}, got {model}"
            )
        if provider != self.expected_provider:
            raise RouteMismatchError(
                f"served provider changed: expected {self.expected_provider}, got {provider}"
            )
