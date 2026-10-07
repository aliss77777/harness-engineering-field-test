"""Tool-calling chat client for OpenRouter, with v1's safeguards.

Adapted from v1/openrouter_llm.py (tag v1-final): pinned provider and route check, fail loudly
on 402 (no credit), retries with capped exponential backoff, a disk cache so reruns are free,
and a spend cap checked before every paid call. New for v2: tool calling, and a `cache_key`
argument so K candidate runs of one task are K independent calls, not one cached answer.

Cached replays report the original call's cost and latency (as in v1, results are charged at
the original cost), but only new calls count toward the spend cap.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from jevloop.cache import DiskCache
from jevloop.log import JsonlLogger
from jevloop.spend import SpendTracker

CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}


class RouteMismatchError(RuntimeError):
    """The provider served a different model or host than the one pinned. Fatal."""


class OutOfCreditsError(RuntimeError):
    """HTTP 402 from OpenRouter: the account has no credit. Fatal; never retried."""


class IncompleteResponseError(RuntimeError):
    """A 200 response without a usable message (usually an error body). Retried."""


class ContentBlockedError(RuntimeError):
    """The provider refused the request under its content policy. Not retried; cached."""


def is_content_block(body: dict[str, Any]) -> bool:
    error = body.get("error") or {}
    metadata = error.get("metadata") or {}
    return error.get("code") == 403 and (
        metadata.get("error_type") == "content_policy_violation"
        or "PROHIBITED_CONTENT" in str(error.get("message", ""))
    )


class ChatClient:
    def __init__(
        self,
        *,
        model: str,
        provider: str,
        provider_tag: str,
        expected_model: str,
        api_key: str,
        cache: DiskCache,
        logger: JsonlLogger,
        spend: SpendTracker | None,
        temperature: float,
        reasoning_effort: str | None,
        retries: int = 8,
        backoff_seconds: float = 5.0,
        max_backoff_seconds: float = 120.0,
        http_client: httpx.Client | None = None,
        sleep=time.sleep,
    ):
        self.model = model
        self.provider = provider  # display name OpenRouter reports back; checked on every reply
        self.provider_tag = provider_tag  # endpoint pinned in the request, e.g. "deepinfra/bf16"
        self.expected_model = expected_model
        self.api_key = api_key
        self.cache = cache
        self.logger = logger
        self.spend = spend
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.http = http_client or httpx.Client(timeout=300.0)
        self.sleep = sleep

    def request_body(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": self.temperature,
            "provider": {"order": [self.provider_tag], "allow_fallbacks": False, "require_parameters": True},
        }
        if self.reasoning_effort:
            body["reasoning"] = {"effort": self.reasoning_effort}
        return body

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        cache_key: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """One model turn. Returns {"message": assistant message dict, "usage": {...}, "cached": bool}."""
        body = self.request_body(messages, tools)
        cache_payload = {"provider": "openrouter", "key": cache_key, **body}
        cached = self.cache.get(cache_payload)
        if cached is not None:
            if cached.get("blocked"):
                self.logger.write({**event, "model": self.model, "cached": True, "blocked": True})
                raise ContentBlockedError(cached["error"])
            self._validate_route(cached["model"], cached["provider"])
            self.logger.write({**event, "model": cached["model"], "provider": cached["provider"], "cached": True, **cached["usage"]})
            return {"message": cached["message"], "usage": cached["usage"], "cached": True}

        if self.spend is not None:
            self.spend.check()
        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self.http.post(
                    CHAT_COMPLETIONS_URL,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                             "X-Title": "Jev Learning Loop v2"},
                    json=body,
                )
                if response.status_code == 402:
                    raise OutOfCreditsError("OpenRouter returned 402 Payment Required: add credit, then rerun (finished calls are cached)")
                if response.status_code in RETRYABLE_STATUS:
                    raise IncompleteResponseError(f"HTTP {response.status_code}: {response.text[:300]}")
                payload = response.json()
                if is_content_block(payload):
                    message = str(payload["error"].get("message"))
                    self.cache.put(cache_payload, {"blocked": True, "error": message})
                    self.logger.write({**event, "model": self.model, "cached": False, "attempt": attempt, "blocked": True, "error": message})
                    raise ContentBlockedError(message)
                response.raise_for_status()
                if "error" in payload or not payload.get("model") or not payload.get("choices"):
                    raise IncompleteResponseError(f"response without a message: {str(payload)[:300]}")
                self._validate_route(payload["model"], payload.get("provider"))
                message = payload["choices"][0]["message"]
                usage_body = payload.get("usage") or {}
                details = usage_body.get("completion_tokens_details") or {}
                usage = {
                    "input_tokens": int(usage_body.get("prompt_tokens", 0) or 0),
                    "output_tokens": int(usage_body.get("completion_tokens", 0) or 0),
                    "reasoning_tokens": int(details.get("reasoning_tokens", 0) or 0),
                    "cost": float(usage_body.get("cost", 0) or 0),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                }
                if self.spend is not None:
                    self.spend.record(usage["cost"])
                self.cache.put(cache_payload, {"message": message, "usage": usage, "model": payload["model"],
                                               "provider": payload.get("provider")})
                self.logger.write({**event, "model": payload["model"], "provider": payload.get("provider"),
                                   "cached": False, "attempt": attempt, **usage})
                return {"message": message, "usage": usage, "cached": False}
            except Exception as error:
                self.logger.write({**event, "model": self.model, "cached": False, "attempt": attempt,
                                   "error_type": type(error).__name__, "error": str(error)[:500]})
                fatal = isinstance(error, (RouteMismatchError, OutOfCreditsError, ContentBlockedError))
                if fatal or attempt == self.retries:
                    raise
                self.sleep(min(self.backoff_seconds * 2 ** (attempt - 1), self.max_backoff_seconds))
        raise RuntimeError("unreachable")

    def _validate_route(self, model: str | None, provider: str | None) -> None:
        if model != self.expected_model:
            raise RouteMismatchError(f"served model changed: expected {self.expected_model}, got {model}")
        if provider != self.provider:
            raise RouteMismatchError(f"served provider changed: expected {self.provider}, got {provider}")
