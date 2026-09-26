from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from llm_factory import build_llm_client


ROOT = Path(__file__).resolve().parent

def start_schema(config: dict[str, Any]) -> dict[str, Any]:
    learning = config["learning"]
    return {
    "type": "object",
    "properties": {
        "instructions": {"type": "string"},
        "rubric_questions": {
            "type": "array",
            "minItems": learning["starting_rubric_min_questions"],
            "maxItems": learning["starting_rubric_max_questions"],
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


def validate_starting_versions(data: dict[str, Any], config: dict[str, Any]) -> None:
    instructions = data.get("instructions", "")
    questions = data.get("rubric_questions", [])
    learning = config["learning"]
    max_words = learning["max_instructions_words"]
    minimum = learning["starting_rubric_min_questions"]
    maximum = learning["starting_rubric_max_questions"]
    if not instructions or len(instructions.split()) > max_words:
        raise ValueError(f"Loop A instructions must contain 1 to {max_words} words")
    if not minimum <= len(questions) <= maximum:
        raise ValueError(f"Loop B rubric must contain {minimum} to {maximum} questions")
    ids = [question.get("question_id") for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("rubric question IDs must be unique")
    for question in questions:
        if question.get("direction") not in {"helps", "hurts"}:
            raise ValueError("rubric direction must be helps or hurts")
        if not str(question.get("text", "")).strip().endswith("?"):
            raise ValueError("rubric questions must be phrased as questions")


def validate_edit(data: dict[str, Any], loop: str, config: dict[str, Any]) -> None:
    learning = config["learning"]
    changes = data.get("changes", [])
    if not 1 <= len(changes) <= learning["max_changes"]:
        raise ValueError(f"edit must contain 1 to {learning['max_changes']} changes")
    for change in changes:
        reason = str(change.get("reason", "")).strip()
        if not reason or "\n" in reason or "\r" in reason:
            raise ValueError("each change needs one single-line reason")
    if loop == "A":
        instructions = str(data.get("instructions", "")).strip()
        if not instructions or len(instructions.split()) > learning["max_instructions_words"]:
            raise ValueError("Loop A edit exceeds its instruction word limit")
    elif loop == "B":
        questions = data.get("rubric_questions", [])
        if not 1 <= len(questions) <= learning["max_rubric_questions"]:
            raise ValueError("Loop B edit exceeds its rubric question limit")
        ids = [question.get("question_id") for question in questions]
        if len(ids) != len(set(ids)):
            raise ValueError("rubric question IDs must be unique")
        for question in questions:
            if question.get("direction") not in {"helps", "hurts"}:
                raise ValueError("rubric direction must be helps or hurts")
            if not str(question.get("text", "")).strip().endswith("?"):
                raise ValueError("rubric questions must be phrased as questions")
    else:
        raise ValueError("loop must be A or B")


def starting_prompt(task_prompt: str, config: dict[str, Any]) -> str:
    learning = config["learning"]
    return f"""{task_prompt}

Create two equivalent starting files from that same knowledge:
1. Loop A: concise prose instructions for choosing between two headlines, at most {learning['max_instructions_words']} words.
2. Loop B: {learning['starting_rubric_min_questions']} to {learning['starting_rubric_max_questions']} atomic yes/no questions. Each must be answerable from one headline alone and marked `helps` when yes predicts more clicks or `hurts` when yes predicts fewer clicks.

Do not use outcome data. Use stable snake_case question IDs. Return only the requested JSON."""


def _changes_schema(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "array", "minItems": 1, "maxItems": config["learning"]["max_changes"],
        "items": {"type": "object", "properties": {
            "change": {"type": "string"}, "reason": {"type": "string"},
        }, "required": ["change", "reason"], "additionalProperties": False},
    }


def edit_schema(loop: str, config: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {"changes": _changes_schema(config)}
    required = ["changes"]
    if loop == "A":
        properties["instructions"] = {"type": "string"}
        required.append("instructions")
    elif loop == "B":
        properties["rubric_questions"] = {
            "type": "array", "minItems": 1, "maxItems": config["learning"]["max_rubric_questions"],
            "items": {"type": "object", "properties": {
                "question_id": {"type": "string"}, "text": {"type": "string"},
                "direction": {"type": "string", "enum": ["helps", "hurts"]},
            }, "required": ["question_id", "text", "direction"], "additionalProperties": False},
        }
        required.append("rubric_questions")
    else:
        raise ValueError("loop must be A or B")
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def propose_edit(*, loop: str, current: dict[str, Any], feedback: dict[str, Any], history: list[dict[str, Any]], client, config: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    limits = config["learning"]
    if loop == "A":
        instruction = f"Rewrite only where evidence supports it. Return no more than {limits['max_changes']} changes and at most {limits['max_instructions_words']} words."
    else:
        instruction = f"You may drop, flip, reword, or add questions. Return no more than {limits['max_changes']} changes and at most {limits['max_rubric_questions']} questions. Cite the evidence table in each reason."
    prompt = f"""Improve learning Loop {loop} using only the supplied practice evidence.
{instruction}
Each change needs one short single-line reason.

CURRENT:
{json.dumps(current, ensure_ascii=False)}

PRACTICE FEEDBACK:
{json.dumps(feedback, ensure_ascii=False)}

CHANGE HISTORY:
{json.dumps(history, ensure_ascii=False)}
"""
    proposal = client.generate_json(prompt=prompt, schema=edit_schema(loop, config), event=event)
    validate_edit(proposal, loop, config)
    return proposal


def make_rewordings(*, question: dict[str, str], client, event: dict[str, Any]) -> list[str]:
    schema = {"type": "object", "properties": {"rewordings": {
        "type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "string"},
    }}, "required": ["rewordings"], "additionalProperties": False}
    result = client.generate_json(
        prompt=("Write two semantically equivalent, atomic yes/no rewordings of this question. "
                "Each must be answerable from one headline alone and end with a question mark.\n\n" + question["text"]),
        schema=schema, event=event,
    )
    rewordings = [" ".join(str(text).splitlines()).strip() for text in result["rewordings"]]
    if any(not text.endswith("?") for text in rewordings):
        raise ValueError("question rewordings must end with question marks")
    return rewordings


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
        prompt=starting_prompt(task["starting_prompt"], config),
        schema=start_schema(config),
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
    validate_starting_versions(data, config)
    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "version0.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Created Loop A instructions and {len(data['rubric_questions'])} Loop B questions.")


if __name__ == "__main__":
    main()
