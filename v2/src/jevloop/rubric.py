"""The Jev rubric: weighted yes/no questions about a run summary, and its learning loop's pieces.

Adapted from v1 (deciders.RubricQuestion and rubric_score; trace.fit_weights, Loop B-plus), at tag
v1-final. v1 compared two items; v2 judges one MiniMax run: is it good enough to keep? A run is
**good** if its partial credit is at least GOOD_CREDIT. The score is the sum of Jev's yes-probabilities,
signed by each question's direction and weighted by weights fitted on practice runs (B-plus).
Jev reads only the run summary (trigger, tool calls, state changes): never the grading checks.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

from jevloop.gate import gate_version  # v1's keep-or-reject test for paired right/wrong outcomes (McNemar)

GOOD_CREDIT = 0.8


@dataclass(frozen=True)
class Question:
    question_id: str
    text: str
    direction: str  # helps | hurts


# Version 0: generic, task-agnostic questions, fixed before any Phase 1 run (briefs/Phase 1 design.md).
STARTING_RUBRIC: tuple[Question, ...] = (
    Question("read_policies", "Before changing any records, did the agent read the policy, guideline or rule emails in the inbox?", "helps"),
    Question("every_item", "Did the agent handle every item the request asked for, rather than stopping partway?", "helps"),
    Question("excluded_contacted", "Did the agent send a message to, or process a record for, someone or something that a policy or the request said to exclude, skip or hold?", "hurts"),
    Question("values_verbatim", "Where the agent wrote amounts, IDs or names into emails or records, do they appear to be copied exactly from the source data?", "helps"),
    Question("tracker_updated", "If the request asked for a tracker, sheet or record to be updated, did the state changes show that update?", "helps"),
    Question("notified", "If the request asked for an email, message or summary to be sent, did the agent send it to the stated recipient?", "helps"),
    Question("unrequested_actions", "Did the agent change records or send messages that the request did not ask for?", "hurts"),
    Question("errors_ignored", "Did several of the agent's tool calls fail with errors that it did not recover from?", "hurts"),
)


def is_good(credit: float) -> bool:
    return credit >= GOOD_CREDIT


def contributions(probs: dict[str, float], questions: tuple[Question, ...]) -> list[float]:
    return [probs[q.question_id] if q.direction == "helps" else -probs[q.question_id] for q in questions]


def score(probs: dict[str, float], questions: tuple[Question, ...], weights: dict[str, float] | None) -> float:
    c = contributions(probs, questions)
    w = [1.0 if weights is None else weights[q.question_id] for q in questions]
    return float(sum(a * b for a, b in zip(c, w)))


def fit_weights(probs: list[dict[str, float]], credits: list[float], questions: tuple[Question, ...], *,
                c: float = 1.0, seed: int = 0) -> tuple[dict[str, float], float]:
    """B-plus: one weight per question, plus an intercept, by logistic regression on practice runs
    (target: good or not). Returns (weights, intercept). A negative weight means the data says the
    question's direction is backwards. With a single class in the data, weights are all 1."""
    y = np.array([is_good(x) for x in credits], dtype=int)
    if len(set(y)) < 2:
        return {q.question_id: 1.0 for q in questions}, 0.0
    x = np.array([contributions(p, questions) for p in probs])
    model = LogisticRegression(C=c, random_state=seed, max_iter=2000).fit(x, y)
    return {q.question_id: round(float(w), 4) for q, w in zip(questions, model.coef_[0])}, float(model.intercept_[0])


def classify(probs: dict[str, float], questions: tuple[Question, ...], weights: dict[str, float], intercept: float) -> bool:
    """Predicts 'good' when the weighted score plus intercept is positive."""
    return score(probs, questions, weights) + intercept > 0


def keep_rubric_edit(old_correct: list[bool], new_correct: list[bool], *, p_threshold: float = 0.10):
    """Keep a rubric edit if it classifies the same test bench runs better: v1's paired McNemar test."""
    return gate_version(old_correct, new_correct, p_threshold=p_threshold)


# ---------- the rubric editor (MiniMax), one edit per candidate ----------

@dataclass(frozen=True)
class RubricEdit:
    op: str  # add | replace | remove
    question_id: str
    text: str = ""
    direction: str = ""
    why: str = ""

    def record(self) -> dict[str, Any]:
        return asdict(self)


def apply_rubric_edit(questions: tuple[Question, ...], edit: RubricEdit) -> tuple[Question, ...]:
    if edit.op == "add":
        return questions + (Question(edit.question_id, edit.text, edit.direction),)
    if edit.op == "replace":
        return tuple(Question(q.question_id, edit.text, edit.direction) if q.question_id == edit.question_id else q for q in questions)
    if edit.op == "remove":
        return tuple(q for q in questions if q.question_id != edit.question_id)
    raise ValueError(edit.op)


def check_rubric_edit(edit: RubricEdit, questions: tuple[Question, ...], rejected: list[RubricEdit]) -> str | None:
    ids = {q.question_id for q in questions}
    if edit.op not in ("add", "replace", "remove"):
        return f"unknown op {edit.op!r}"
    if edit.op == "add" and (edit.question_id in ids or not re.fullmatch(r"[a-z0-9_]{2,40}", edit.question_id)):
        return "new question needs a new id: 2-40 lowercase letters, digits or underscores"
    if edit.op in ("replace", "remove") and edit.question_id not in ids:
        return f"no question with id {edit.question_id!r}"
    if edit.op == "remove" and len(questions) <= 3:
        return "keep at least 3 questions"
    if edit.op != "remove":
        if edit.direction not in ("helps", "hurts"):
            return "direction must be helps or hurts"
        if not (10 <= len(edit.text) <= 400) or "?" not in edit.text:
            return "question must be a yes/no question of 10-400 characters"
        if "@" in edit.text or re.search(r"\d{3,}", edit.text):
            return "question names a specific address or ID; questions must be general"
    if any(r.op == edit.op and r.question_id == edit.question_id and r.text == edit.text for r in rejected):
        return "already tried and rejected"
    return None


RUBRIC_EDITOR_SYSTEM = """You are improving a checklist of yes/no questions that a judge answers about an AI agent's run of a
back-office task (finance and HR). The judge reads only a summary of the run: the request, the tool calls and the state
changes. A run counts as GOOD if it met at least 80% of the task's requirements. The checklist's job is to tell good runs
from bad ones. You will see runs the checklist judged wrongly, with the judge's yes-probability for each question.

Propose exactly {n} DIFFERENT candidate edits. Each candidate is ONE edit:
- {{"op": "add", "question_id": "<new_snake_case_id>", "text": "<yes/no question>", "direction": "helps|hurts", "why": "..."}}
- {{"op": "replace", "question_id": "<existing id>", "text": "<new wording>", "direction": "helps|hurts", "why": "..."}}
- {{"op": "remove", "question_id": "<existing id>", "why": "..."}}
"helps" means a yes points to a good run; "hurts" means a yes points to a bad run. Questions must be general (no names,
addresses, amounts or IDs). Do not repeat edits already tried. Reply with JSON only: {{"edits": [ ... ]}}"""


def rubric_editor_prompt(questions: tuple[Question, ...], mistakes: list[dict[str, Any]], rejected: list[RubricEdit], n: int) -> list[dict[str, str]]:
    current = "\n".join(f"- {q.question_id} ({q.direction}): {q.text}" for q in questions)
    tried = "\n".join(f"- {e.op} {e.question_id}: {e.text}" for e in rejected) or "(none)"
    user = (f"CURRENT CHECKLIST:\n{current}\n\nEDITS ALREADY TRIED AND REJECTED:\n{tried}\n\n"
            f"RUNS THE CHECKLIST JUDGED WRONGLY ({len(mistakes)}):\n{json.dumps(mistakes, indent=1, ensure_ascii=False)}")
    return [{"role": "system", "content": RUBRIC_EDITOR_SYSTEM.format(n=n)}, {"role": "user", "content": user}]


def parse_rubric_edits(content: str) -> list[RubricEdit]:
    m = re.search(r"\{.*\}", content, re.S)
    data = json.loads(m.group(0) if m else content)
    return [RubricEdit(op=str(e.get("op", "")).lower(), question_id=str(e.get("question_id", "")),
                       text=str(e.get("text") or ""), direction=str(e.get("direction") or ""), why=str(e.get("why") or ""))
            for e in data.get("edits", [])]
