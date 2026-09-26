from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml
from google import genai


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
    args = parser.parse_args()
    load_local_env()
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    if args.gemini:
        check_gemini(config["models"]["llm"])
    else:
        parser.error("choose an access check")


if __name__ == "__main__":
    main()

