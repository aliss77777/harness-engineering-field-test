"""Single-edit candidates (Arena brief section 2).

The editor proposes up to N alternative edits. Each is one structured operation
that code applies to the current version, so "one change" holds by construction.
Each candidate is gated on its own; at most one is kept per round.
"""
from __future__ import annotations

import difflib
import json
import random
from typing import Any

from editor import validate_starting_versions


A_OPERATIONS = ("replace", "append")
B_OPERATIONS = ("drop", "flip", "reword", "add")


class InvalidCandidate(ValueError):
    """The proposed operation cannot be applied to the current version."""


def candidate_schema(loop: str, config: dict[str, Any], max_items: int | None = None) -> dict[str, Any]:
    if loop == "A":
        item = {
            "operation": {"type": "string", "enum": list(A_OPERATIONS)},
            "target_text": {"type": "string"},
            "new_text": {"type": "string"},
            "reason": {"type": "string"},
        }
    elif loop == "B":
        item = {
            "operation": {"type": "string", "enum": list(B_OPERATIONS)},
            "question_id": {"type": "string"},
            "text": {"type": "string"},
            "direction": {"type": "string", "enum": ["helps", "hurts"]},
            "reason": {"type": "string"},
        }
    else:
        raise ValueError("loop must be A or B")
    return {
        "type": "object",
        "properties": {"candidates": {
            "type": "array", "minItems": 1, "maxItems": max_items or config["learning"]["max_changes"],
            "items": {"type": "object", "properties": item,
                      "required": list(item), "additionalProperties": False},
        }},
        "required": ["candidates"],
        "additionalProperties": False,
    }


def signature(loop: str, candidate: dict[str, Any]) -> str:
    if loop == "A":
        return f"{candidate['operation']}|{candidate['target_text'].strip()}|{candidate['new_text'].strip()}".lower()
    text = "" if candidate["operation"] in ("drop", "flip") else candidate["text"].strip()
    direction = candidate["direction"] if candidate["operation"] == "add" else ""
    return f"{candidate['operation']}|{candidate['question_id']}|{text}|{direction}".lower()


def is_near_duplicate(sig: str, previous: list[str], threshold: float) -> bool:
    return any(difflib.SequenceMatcher(None, sig, old).ratio() >= threshold for old in previous)


def describe(loop: str, candidate: dict[str, Any]) -> str:
    if loop == "A":
        if candidate["operation"] == "append":
            return f"append: {candidate['new_text']}"
        return f"replace '{candidate['target_text']}' with '{candidate['new_text']}'"
    operation = candidate["operation"]
    if operation == "drop":
        return f"drop {candidate['question_id']}"
    if operation == "flip":
        return f"flip direction of {candidate['question_id']}"
    if operation == "reword":
        return f"reword {candidate['question_id']}: {candidate['text']}"
    return f"add {candidate['question_id']} ({candidate['direction']}): {candidate['text']}"


def apply_candidate(loop: str, current: dict[str, Any], candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return the new version, or raise InvalidCandidate."""
    reason = " ".join(str(candidate.get("reason", "")).splitlines()).strip()
    if not reason:
        raise InvalidCandidate("each candidate needs a one-line reason")
    limits = config["learning"]
    if loop == "A":
        instructions = current["instructions"]
        new_text = candidate["new_text"].strip()
        if candidate["operation"] == "append":
            if not new_text:
                raise InvalidCandidate("append needs new text")
            updated = f"{instructions.rstrip()} {new_text}"
        else:
            target = candidate["target_text"]
            if not target or instructions.count(target) != 1:
                raise InvalidCandidate("replace target must appear exactly once in the current instructions")
            updated = instructions.replace(target, new_text)
        updated = " ".join(updated.split())
        if updated == " ".join(instructions.split()):
            raise InvalidCandidate("edit does not change the instructions")
        if not updated or len(updated.split()) > limits["max_instructions_words"]:
            raise InvalidCandidate("edit exceeds the instruction word limit")
        return {"instructions": updated}

    questions = [dict(item) for item in current["rubric_questions"]]
    ids = [item["question_id"] for item in questions]
    operation, question_id = candidate["operation"], candidate["question_id"].strip()
    text = " ".join(candidate["text"].split())
    if operation == "add":
        if question_id in ids or not question_id:
            raise InvalidCandidate("add needs a new, unique question_id")
        if len(questions) + 1 > limits["max_rubric_questions"]:
            raise InvalidCandidate("add exceeds the rubric question limit")
        if not text.endswith("?"):
            raise InvalidCandidate("new question must end with a question mark")
        questions.append({"question_id": question_id, "text": text, "direction": candidate["direction"]})
    else:
        if question_id not in ids:
            raise InvalidCandidate(f"unknown question_id {question_id}")
        index = ids.index(question_id)
        if operation == "drop":
            if len(questions) <= 1:
                raise InvalidCandidate("cannot drop the last question")
            questions.pop(index)
        elif operation == "flip":
            old = questions[index]["direction"]
            questions[index]["direction"] = "hurts" if old == "helps" else "helps"
        else:  # reword
            if not text.endswith("?") or text == questions[index]["text"]:
                raise InvalidCandidate("reword needs a different question ending in a question mark")
            questions[index]["text"] = text
    return {"rubric_questions": questions}


def changed_question(loop: str, candidate: dict[str, Any], version: dict[str, Any]) -> dict[str, Any] | None:
    """The question whose wording is new (needs the 5.4 consistency check), if any."""
    if loop != "B" or candidate["operation"] not in ("add", "reword"):
        return None
    return next(item for item in version["rubric_questions"] if item["question_id"] == candidate["question_id"].strip())


def trim(text: str, words: int) -> str:
    parts = str(text).split()
    return text if len(parts) <= words else " ".join(parts[:words]) + " […trimmed]"


def sample_mistakes(records: list[dict[str, Any]], *, count: int, seed: int, round_number: int, loop: str) -> list[dict[str, Any]]:
    """A fresh seeded sample each round, so the editor sees new evidence."""
    mistakes = [item for item in records if not item["correct"]]
    rng = random.Random(f"{seed}:{loop}:{round_number}:mistakes")
    return sorted(rng.sample(mistakes, min(count, len(mistakes))), key=lambda item: item["pair_id"])


def candidate_prompt(
    *, loop: str, current: dict[str, Any], feedback: dict[str, Any], history: list[dict[str, Any]],
    rejected: list[str], config: dict[str, Any], wording: dict[str, str],
    max_items: int | None = None, guidance: str = "",
) -> str:
    limits = config["learning"]
    if loop == "A":
        operations = (
            "Each candidate is ONE operation on the instructions: `replace` (target_text must be an exact, "
            "unique substring of the current instructions; new_text replaces it; empty new_text deletes it) "
            f"or `append` (new_text is added at the end; leave target_text empty). Stay within {limits['max_instructions_words']} words. "
            "Base each candidate on patterns in the mistakes and the decider's own reasons."
        )
    else:
        operations = (
            "Each candidate is ONE operation on the rubric: `drop` a question, `flip` its direction, `reword` it "
            "(text = new wording), or `add` a new question (new snake_case question_id, text, direction). "
            f"At most {limits['max_rubric_questions']} questions. Each question must be answerable from "
            f"{wording.get('item_scope', 'one item alone')}. Cite the evidence table in each reason. "
            "For drop/flip, text may be empty; direction is only used by add."
        )
    return f"""You improve a decision file for learning Loop {loop}. The task: {wording.get('decider_question', '')}

Propose up to {max_items or limits['max_changes']} ALTERNATIVE single edits. Each is tested on its own on held-out pairs; at most one will be kept.
{operations}{guidance}
Make the candidates genuinely different from each other. Each needs a one-line reason.

DO NOT resubmit any edit listed under REJECTED EDITS, or a near-copy of one. They were tested and did not help.

CURRENT FILE:
{json.dumps(current, ensure_ascii=False)}

PRACTICE FEEDBACK (accuracy, a sample of mistakes{', evidence table' if loop == 'B' else ''}):
{json.dumps(feedback, ensure_ascii=False)}

CHANGE HISTORY (every candidate so far and whether the gate kept it):
{json.dumps(history, ensure_ascii=False)}

REJECTED EDITS:
{json.dumps(rejected, ensure_ascii=False)}
"""


def validate_version(loop: str, version: dict[str, Any], config: dict[str, Any]) -> None:
    """Reuse the starting-version checks on the fields a loop owns."""
    if loop == "B":
        probe = {"instructions": "placeholder", "rubric_questions": version["rubric_questions"]}
        learning = {**config["learning"], "starting_rubric_min_questions": 1,
                    "starting_rubric_max_questions": config["learning"]["max_rubric_questions"]}
        validate_starting_versions(probe, {**config, "learning": learning})
