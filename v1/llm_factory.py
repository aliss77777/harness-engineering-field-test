from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cache import DiskCache
from gemini import GeminiJsonClient, load_env
from log import JsonlLogger
from openrouter_llm import OpenRouterJsonClient
from jev import OpenRouterJevClient


def build_llm_client(config: dict[str, Any], root: Path, run_id: str, *, logs_dir: Path | None = None, spend=None):
    load_env(root / ".env")
    provider = config["models"]["llm_provider"]
    common = {
        "model": config["models"]["llm"],
        "logger": JsonlLogger((logs_dir or root / "logs") / f"{run_id}.jsonl"),
        "retries": config["api"]["retries"],
        "backoff_seconds": config["api"]["backoff_seconds"],
        "temperature": config["api"]["temperature"],
        "max_backoff_seconds": config["api"].get("max_backoff_seconds", 120.0),
    }
    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_KEY is missing")
        return OpenRouterJsonClient(
            api_key=api_key,
            cache=DiskCache(root / "cache" / "openrouter_llm"),
            reasoning_effort=config["api"]["reasoning_effort"],
            expected_model=config["models"]["llm_expected_served"],
            expected_provider=config["models"]["llm_expected_provider"],
            allow_fallbacks=config["models"]["llm_allow_fallbacks"],
            spend=spend,
            **common,
        )
    if provider == "google_ai_studio":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        return GeminiJsonClient(
            api_key=api_key,
            cache=DiskCache(root / "cache" / "gemini"),
            **{k: v for k, v in common.items() if k != "max_backoff_seconds"},
        )
    raise ValueError(f"unsupported LLM provider: {provider}")


def build_jev_client(config: dict[str, Any], root: Path, run_id: str, *, logs_dir: Path | None = None, spend=None):
    load_env(root / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_KEY is missing")
    return OpenRouterJevClient(
        model=config["models"]["jev"], api_key=api_key,
        cache=DiskCache(root / "cache" / "jev"),
        logger=JsonlLogger((logs_dir or root / "logs") / f"{run_id}.jsonl"),
        retries=config["api"]["retries"], backoff_seconds=config["api"]["backoff_seconds"],
        expected_model=config["models"]["jev_expected_served"],
        expected_provider=config["models"]["jev_expected_provider"],
        spend=spend, max_backoff_seconds=config["api"].get("max_backoff_seconds", 120.0),
    )
