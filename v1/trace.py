"""Decision traces for the Jev loop (experiment 3).

Loop B's pick is a sum over questions, so every pick decomposes exactly into
per-question contributions: contribution_q = w_q * sign_q * (P_x(yes) - P_y(yes)),
positive = pushed toward X. sign_q is +1 for "helps", -1 for "hurts"; w_q is 1 for
plain B/B-prime and the fitted weight for B-plus. The editor sees which questions
pushed a wrong pick, and by how much.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression


def direction_sign(question: dict[str, Any]) -> float:
    return 1.0 if question["direction"] == "helps" else -1.0


def contributions(record: dict[str, Any], questions: list[dict[str, Any]],
                  weights: dict[str, float] | None = None) -> dict[str, float]:
    """Per-question push toward X for one pair (positive = toward X)."""
    out = {}
    for question in questions:
        qid = question["question_id"]
        probs = record["questions"][qid]
        weight = 1.0 if weights is None else weights[qid]
        out[qid] = weight * direction_sign(question) * (probs["x_yes_probability"] - probs["y_yes_probability"])
    return out


def mistake_trace(record: dict[str, Any], questions: list[dict[str, Any]], labels: dict[str, str],
                  weights: dict[str, float] | None = None, top: int = 4) -> list[dict[str, Any]]:
    """The questions that moved a wrong pick most, with where each one pushed."""
    shown = {"X": labels["x"], "Y": labels["y"]}
    rows = []
    for qid, value in contributions(record, questions, weights).items():
        probs = record["questions"][qid]
        toward = "X" if value > 0 else "Y" if value < 0 else None
        rows.append({
            "question_id": qid,
            f"p_yes_{labels['x']}": round(probs["x_yes_probability"], 2),
            f"p_yes_{labels['y']}": round(probs["y_yes_probability"], 2),
            "pushed_toward": shown.get(toward) if toward else "neither",
            "push": round(abs(value), 3),
            "pushed_toward_winner": toward == record["winner"] if toward else None,
        })
    return sorted(rows, key=lambda row: -row["push"])[:top]


def aggregate_trace(records: list[dict[str, Any]], questions: list[dict[str, Any]],
                    weights: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Across practice: per question, how often it pushed wrong picks and how often it decided a pick."""
    stats: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for record in records:
        parts = contributions(record, questions, weights)
        total = sum(parts.values())
        for qid, value in parts.items():
            s = stats[qid]
            toward_winner = (value > 0) == (record["winner"] == "X") if value else None
            if not record["correct"]:
                s["mistakes"] += 1
                if toward_winner is False:
                    s["pushed_mistake_to_loser"] += 1
                    s["push_to_loser_sum"] += abs(value)
                elif toward_winner is True:
                    s["pushed_mistake_to_winner"] += 1
            # Decisive: removing this question alone would flip the pick.
            if total and value and np.sign(total - value) != np.sign(total):
                s["decisive"] += 1
                s["decisive_correct" if record["correct"] else "decisive_wrong"] += 1
    rows = []
    for question in questions:
        s = stats[question["question_id"]]
        to_loser = int(s["pushed_mistake_to_loser"])
        rows.append({
            "question_id": question["question_id"],
            "direction": question["direction"],
            "mistakes_pushed_toward_loser": to_loser,
            "mistakes_pushed_toward_winner": int(s["pushed_mistake_to_winner"]),
            "mean_push_toward_loser": round(s["push_to_loser_sum"] / to_loser, 3) if to_loser else 0.0,
            "decisive_pairs": int(s["decisive"]),
            "decisive_and_right": int(s["decisive_correct"]),
            "decisive_and_wrong": int(s["decisive_wrong"]),
        })
    return rows


def rich_evidence(records: list[dict[str, Any]], questions: list[dict[str, Any]],
                  gap_bins: list[float], overlap_threshold: float) -> dict[str, Any]:
    """Win rate by size of the probability gap, and which questions overlap."""
    edges = [0.0, *gap_bins, 1.0001]
    by_question = []
    deltas: dict[str, list[float]] = {}
    for question in questions:
        qid, sign = question["question_id"], direction_sign(question)
        bins = [{"gap": f"{lo:.1f}-{min(hi, 1):.1f}", "pairs": 0, "favored_side_won": 0} for lo, hi in zip(edges, edges[1:])]
        values = []
        for record in records:
            probs = record["questions"][qid]
            delta = probs["x_yes_probability"] - probs["y_yes_probability"]
            values.append(sign * delta)
            gap = abs(delta)
            if gap == 0:
                continue
            favored = "X" if sign * delta > 0 else "Y"
            for index, (lo, hi) in enumerate(zip(edges, edges[1:])):
                if lo <= gap < hi:
                    bins[index]["pairs"] += 1
                    bins[index]["favored_side_won"] += int(favored == record["winner"])
        for row in bins:
            row["win_rate"] = round(row["favored_side_won"] / row["pairs"], 3) if row["pairs"] else None
        deltas[qid] = values
        by_question.append({"question_id": qid, "direction": question["direction"], "by_gap": bins})
    overlaps = []
    for a, b in combinations(deltas, 2):
        if np.std(deltas[a]) and np.std(deltas[b]):
            r = float(np.corrcoef(deltas[a], deltas[b])[0, 1])
            if abs(r) >= overlap_threshold:
                overlaps.append({"questions": [a, b], "correlation": round(r, 2)})
    return {"win_rate_by_gap": by_question, "overlapping_questions": overlaps}


def fit_weights(records: list[dict[str, Any]], questions: list[dict[str, Any]], *, c: float, seed: int) -> dict[str, float]:
    """Loop B-plus: one weight per question from practice (no intercept: X/Y order is arbitrary).

    A negative weight means the data says the question's direction is backwards.
    """
    ids = [q["question_id"] for q in questions]
    matrix = np.array([[v for v in contributions(r, questions).values()] for r in records])
    target = np.array([r["winner"] == "X" for r in records], dtype=int)
    model = LogisticRegression(fit_intercept=False, C=c, random_state=seed, max_iter=2000).fit(matrix, target)
    return {qid: round(float(w), 4) for qid, w in zip(ids, model.coef_[0])}


def rescore(records: list[dict[str, Any]], questions: list[dict[str, Any]], weights: dict[str, float],
            *, seed: int, label: str) -> list[dict[str, Any]]:
    """Re-pick every pair from stored Jev probabilities with weights. No API calls."""
    import random

    out = []
    for record in records:
        total = sum(contributions(record, questions, weights).values())
        tied = total == 0
        if tied:
            prediction = random.Random(f"{seed}:{label}:{record['pair_id']}").choice(("X", "Y"))
        else:
            prediction = "X" if total > 0 else "Y"
        out.append({**record, "prediction": prediction, "correct": prediction == record["winner"],
                    "coin_flip_tie": tied})
    return out
