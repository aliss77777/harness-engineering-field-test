from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml
from google import genai

from cache import DiskCache
from deciders import RubricQuestion
from jev import OpenRouterJevClient
from llm_factory import build_llm_client
from log import JsonlLogger


ROOT = Path(__file__).resolve().parent


def load_local_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def check_gemini(model: str) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents="Reply with exactly: OK",
    )
    text = (response.text or "").strip()
    if "OK" not in text.upper():
        raise RuntimeError(f"Unexpected Gemini response: {text!r}")
    usage = response.usage_metadata
    print(
        "Gemini: OK "
        f"(input_tokens={getattr(usage, 'prompt_token_count', None)}, "
        f"output_tokens={getattr(usage, 'candidates_token_count', None)})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify model access without exposing keys.")
    parser.add_argument("--gemini", action="store_true")
    parser.add_argument("--openrouter-llm", action="store_true")
    parser.add_argument("--jev", action="store_true")
    args = parser.parse_args()
    load_local_env()
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    if args.gemini:
        check_gemini(config["models"]["direct_llm"])
    elif args.openrouter_llm:
        client = build_llm_client(config, ROOT, "access-check-openrouter-llm")
        result = client.generate_json(
            prompt="Return status OK.",
            schema={
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["OK"]}},
                "required": ["status"],
                "additionalProperties": False,
            },
            event={
                "run_id": "access-check",
                "loop": "editor",
                "round": 0,
                "set": "none",
                "pair_id": None,
                "version_id": "v0",
                "call_type": "openrouter_llm_access",
            },
        )
        print(f"OpenRouter LLM: {result['status']}")
    elif args.jev:
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing")
        client = OpenRouterJevClient(
            model=config["models"]["jev"],
            api_key=api_key,
            cache=DiskCache(ROOT / "cache" / "jev"),
            logger=JsonlLogger(ROOT / "logs" / "access-check-jev.jsonl"),
            retries=config["api"]["retries"],
            backoff_seconds=config["api"]["backoff_seconds"],
            expected_model=config["models"]["jev_expected_served"],
            expected_provider=config["models"]["jev_expected_provider"],
        )
        result = client.evaluate(
            "This is excellent news.",
            [RubricQuestion("positive", "Is the text positive?", "helps")],
            {
                "run_id": "access-check",
                "loop": "B",
                "round": 0,
                "set": "none",
                "pair_id": None,
                "version_id": "v0",
            },
        )
        print(f"Jev: OK (yes_probability={result['positive']:.3f})")
    else:
        parser.error("choose an access check")


if __name__ == "__main__":
    main()
