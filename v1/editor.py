from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from llm_factory import build_llm_client


ROOT = Path(__file__).resolve().parent

START_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "instructions": {"type": "string"},
        "rubric_questions": {
            "type": "array",
            "minItems": 5,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "text": {"type": "string"},
                    "direction": {"type": "string", "enum": ["helps", "hurts"]},
                },
                "required": ["question_id", "text", "direction"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["instructions", "rubric_questions"],
    "additionalProperties": False,
}


def validate_starting_versions(data: dict[str, Any]) -> None:
    instructions = data.get("instructions", "")
    questions = data.get("rubric_questions", [])
    if not instructions or len(instructions.split()) > 300:
        raise ValueError("Loop A instructions must contain 1 to 300 words")
    if not 5 <= len(questions) <= 8:
        raise ValueError("Loop B rubric must contain 5 to 8 questions")
    ids = [question.get("question_id") for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("rubric question IDs must be unique")
    for question in questions:
        if question.get("direction") not in {"helps", "hurts"}:
            raise ValueError("rubric direction must be helps or hurts")
        if not str(question.get("text", "")).strip().endswith("?"):
            raise ValueError("rubric questions must be phrased as questions")


def starting_prompt(task_prompt: str) -> str:
    return f"""{task_prompt}

Create two equivalent starting files from that same knowledge:
1. Loop A: concise prose instructions for choosing between two headlines, at most 300 words.
2. Loop B: 5 to 8 atomic yes/no questions. Each must be answerable from one headline alone and marked `helps` when yes predicts more clicks or `hurts` when yes predicts fewer clicks.

Do not use outcome data. Use stable snake_case question IDs. Return only the requested JSON."""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or revise experiment files.")
    parser.add_argument("--start", action="store_true", help="Create fair version-0 files")
    parser.add_argument("--run-id", default="preflight")
    args = parser.parse_args()
    if not args.start:
        parser.error("choose an editor action")

    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    task = yaml.safe_load((ROOT / "task.yaml").read_text())
    client = build_llm_client(config, ROOT, args.run_id)
    data = client.generate_json(
        prompt=starting_prompt(task["starting_prompt"]),
        schema=START_SCHEMA,
        event={
            "run_id": args.run_id,
            "loop": "editor",
            "round": 0,
            "set": "none",
            "pair_id": None,
            "version_id": "v0",
            "call_type": "starting_versions",
        },
    )
    validate_starting_versions(data)
    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "version0.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Created Loop A instructions and {len(data['rubric_questions'])} Loop B questions.")


if __name__ == "__main__":
    main()
