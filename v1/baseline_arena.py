from __future__ import annotations

import argparse
import json
import math
import re

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from workspace import Workspace


REFUSAL_RE = re.compile(
    r"\b(i can['’]?t|i cannot|i['’]m (?:sorry|unable|not able)|as an ai|i am (?:sorry|unable|not able)|i won['’]?t)\b",
    re.IGNORECASE,
)
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
HEADER_RE = re.compile(r"^\s*#{1,6}\s+\S", re.MULTILINE)

FEATURES = ("words_100", "list_items", "headers", "code_block", "refusal", "log_length_ratio")


def response_features(prompt: str, response: str) -> dict[str, float]:
    words = len(response.split())
    prompt_words = max(len(prompt.split()), 1)
    return {
        "words_100": words / 100,
        "list_items": float(len(LIST_ITEM_RE.findall(response))),
        "headers": float(len(HEADER_RE.findall(response))),
        "code_block": float("```" in response),
        "refusal": float(bool(REFUSAL_RE.search(response))),
        "log_length_ratio": math.log((words + 1) / prompt_words),
    }


def difference_matrix(frame: pd.DataFrame) -> np.ndarray:
    rows = []
    for _, row in frame.iterrows():
        x = response_features(row["prompt"], row["response_x"])
        y = response_features(row["prompt"], row["response_y"])
        rows.append([x[name] - y[name] for name in FEATURES])
    return np.array(rows)


def fit(practice: pd.DataFrame, seed: int) -> LogisticRegression:
    # X/Y order is arbitrary, so the model is symmetric: no intercept.
    model = LogisticRegression(fit_intercept=False, random_state=seed, max_iter=1000)
    return model.fit(difference_matrix(practice), (practice["winner"] == "X").astype(int))


def predict(model: LogisticRegression, frame: pd.DataFrame) -> list[str]:
    return ["X" if value == 1 else "Y" for value in model.predict(difference_matrix(frame))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Arena style-feature baseline (no LLM).")
    parser.add_argument("--config", default="config_arena.yaml")
    parser.add_argument("--task", default="task_arena.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    frames = {
        name: pd.read_csv(ws.path("pairs") / f"{name}.csv", dtype={"pair_id": str})
        for name in ("practice", "gate")
    }
    model = fit(frames["practice"], ws.config["seed"])
    result: dict[str, object] = {
        "features": list(FEATURES),
        "coefficients": dict(zip(FEATURES, map(float, model.coef_[0]))),
        "note": "Trained on practice only. Sealed is scored once, in sealed_arena.py.",
    }
    for name, frame in frames.items():
        predictions = predict(model, frame)
        result[name] = {
            "pairs": len(frame),
            "accuracy": float(np.mean([p == w for p, w in zip(predictions, frame["winner"])])),
            "picks_x": float(np.mean([p == "X" for p in predictions])),
        }
    (ws.path("results") / "baseline_preflight.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
