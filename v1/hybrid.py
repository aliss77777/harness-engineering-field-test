"""Experiment 4: the stacked-vote hybrid of the LLM loop (A*) and the Jev loop (J*).

For each pair both systems decide. A small logistic regression (no intercept: X/Y order
is arbitrary) combines:
  - A*'s pick: +1 for X, -1 for Y
  - J*'s per-question signed differences, w_q * sign_q * (P_X(yes) - P_Y(yes))
  - J*'s total score (their sum)
Fitted on practice + gate (never sealed). If Gemini refused a pair (A* pick unknown), the
hybrid uses J*'s own pick.

The cascade (exploratory, not in the verdict): J* decides when |score| is large, A*
decides the rest; its threshold is chosen on gate.
"""
from __future__ import annotations

import random
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

from trace import contributions


def feature_names(questions: list[dict[str, Any]]) -> list[str]:
    return ["llm_pick"] + [f"jev:{q['question_id']}" for q in questions] + ["jev_total"]


def features(a_record: dict[str, Any], j_record: dict[str, Any], questions: list[dict[str, Any]],
             weights: dict[str, float] | None) -> list[float]:
    parts = contributions(j_record, questions, weights)
    llm = 0.0 if a_record.get("blocked") else (1.0 if a_record["prediction"] == "X" else -1.0)
    return [llm] + [parts[q["question_id"]] for q in questions] + [sum(parts.values())]


def matrix(a_records, j_records, questions, weights) -> tuple[np.ndarray, np.ndarray, list[bool]]:
    if [r["pair_id"] for r in a_records] != [r["pair_id"] for r in j_records]:
        raise ValueError("LLM and Jev records must cover the same pairs in the same order")
    rows = [features(a, j, questions, weights) for a, j in zip(a_records, j_records)]
    target = np.array([a["winner"] == "X" for a in a_records], dtype=int)
    blocked = [bool(a.get("blocked")) for a in a_records]
    return np.array(rows), target, blocked


def fit_stacker(x: np.ndarray, y: np.ndarray, *, c_grid: list[float], folds: int, seed: int) -> dict[str, Any]:
    """Choose C by k-fold CV accuracy (ties -> stronger regularization), then refit on all rows."""
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    scores = {}
    for c in c_grid:
        model = LogisticRegression(fit_intercept=False, C=c, max_iter=2000, random_state=seed)
        scores[c] = float(np.mean(cross_val_score(model, x, y, cv=splitter, scoring="accuracy")))
    best_c = max(c_grid, key=lambda c: (round(scores[c], 10), -c))
    model = LogisticRegression(fit_intercept=False, C=best_c, max_iter=2000, random_state=seed).fit(x, y)
    return {"c": best_c, "cv_accuracy": scores, "coef": [float(v) for v in model.coef_[0]]}


def predict(coef: list[float], x: np.ndarray, pair_ids: list[str], blocked: list[bool],
            jev_predictions: list[str], *, seed: int) -> list[str]:
    scores = x @ np.array(coef)
    out = []
    for score, pair_id, is_blocked, jev_pick in zip(scores, pair_ids, blocked, jev_predictions):
        if is_blocked:
            out.append(jev_pick)
        elif score == 0:
            out.append(random.Random(f"{seed}:hybrid:{pair_id}").choice(("X", "Y")))
        else:
            out.append("X" if score > 0 else "Y")
    return out


def jev_margin(j_record: dict[str, Any], questions, weights) -> float:
    return abs(sum(contributions(j_record, questions, weights).values()))


def choose_cascade_threshold(margins: list[float], jev_correct: list[bool], llm_correct: list[bool],
                             *, max_llm_share: float) -> dict[str, Any]:
    """Highest accuracy among thresholds sending at most max_llm_share of pairs to the LLM;
    ties go to the lower LLM share. Pairs with margin < threshold go to the LLM."""
    candidates = sorted(set(margins)) + [float("inf")]
    best = None
    n = len(margins)
    for tau in [0.0] + candidates:
        to_llm = [m < tau for m in margins]
        share = sum(to_llm) / n
        if share > max_llm_share + 1e-12:
            continue
        acc = sum(l if routed else j for routed, l, j in zip(to_llm, llm_correct, jev_correct)) / n
        key = (round(acc, 10), -share)
        if best is None or key > best[0]:
            best = (key, {"threshold": tau, "llm_share": share, "accuracy": acc})
    return best[1]


def cascade_curve(margins, jev_correct, llm_correct, points: int = 11) -> list[dict[str, float]]:
    order = sorted(margins)
    curve = []
    for i in range(points):
        share = i / (points - 1)
        tau = order[min(int(share * len(order)), len(order) - 1)] if share < 1 else float("inf")
        to_llm = [m < tau for m in margins]
        acc = sum(l if r else j for r, l, j in zip(to_llm, llm_correct, jev_correct)) / len(margins)
        curve.append({"target_llm_share": share, "llm_share": sum(to_llm) / len(margins), "accuracy": acc})
    return curve
