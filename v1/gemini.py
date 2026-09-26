from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from cache import DiskCache
from log import JsonlLogger


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


class GeminiJsonClient:
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
    ):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.cache = cache
        self.logger = logger
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.temperature = temperature

    def generate_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "provider": "google_ai_studio",
            "model": self.model,
            "prompt": prompt,
            "schema": schema,
            "temperature": self.temperature,
        }
        cached = self.cache.get(payload)
        if cached is not None:
            self.logger.write({**event, "model": self.model, "cached": True, **cached["usage"]})
            return cached["data"]

        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        response_mime_type="application/json",
                        response_json_schema=schema,
                    ),
                )
                latency_ms = round((time.perf_counter() - started) * 1000)
                data = json.loads(response.text or "{}")
                metadata = response.usage_metadata
                usage = {
                    "input_tokens": int(getattr(metadata, "prompt_token_count", 0) or 0),
                    "output_tokens": int(getattr(metadata, "candidates_token_count", 0) or 0),
                    "latency_ms": latency_ms,
                }
                self.cache.put(payload, {"data": data, "usage": usage})
                self.logger.write(
                    {**event, "model": self.model, "cached": False, "attempt": attempt, **usage}
                )
                return data
            except Exception as error:
                latency_ms = round((time.perf_counter() - started) * 1000)
                self.logger.write(
                    {
                        **event,
                        "model": self.model,
                        "cached": False,
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
                if attempt == self.retries:
                    raise
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise RuntimeError("unreachable")

