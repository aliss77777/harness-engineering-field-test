from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import pandas as pd
import yaml
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


ROOT = Path(__file__).resolve().parent


def headline_features(text: str) -> dict[str, float]:
    lowered = text.lower()
    return {
        "length": float(len(text)),
        "question_mark": float("?" in text),
        "number": float(bool(re.search(r"\d", text))),
        "you": float(bool(re.search(r"\byou\b", lowered))),
        "i_or_me": float(bool(re.search(r"\b(i|me)\b", lowered))),
        "exclamation_mark": float("!" in text),
    }


def difference_features(row: pd.Series) -> dict[str, float]:
    x = headline_features(row["headline_x"])
    y = headline_features(row["headline_y"])
    return {name: x[name] - y[name] for name in x}


def fake_accuracy(frame: pd.DataFrame, seed: int) -> float:
    rng = random.Random(seed)
    predictions = [rng.choice(("X", "Y")) for _ in range(len(frame))]
    return sum(p == y for p, y in zip(predictions, frame["winner"])) / len(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run no-API experiment controls.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--include-sealed", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / args.config).read_text())
    set_names = ["practice", "gate"] + (["sealed"] if args.include_sealed else [])
    frames = {
        name: pd.read_csv(ROOT / "data" / "pairs" / f"{name}.csv")
        for name in set_names
    }

    vectorizer = DictVectorizer(sparse=False)
    train_x = vectorizer.fit_transform([difference_features(r) for _, r in frames["practice"].iterrows()])
    train_y = (frames["practice"]["winner"] == "X").astype(int)
    model = LogisticRegression(random_state=config["seed"], max_iter=1000).fit(train_x, train_y)

    results: dict[str, object] = {"feature_names": list(vectorizer.feature_names_)}
    for offset, (name, frame) in enumerate(frames.items()):
        matrix = vectorizer.transform([difference_features(r) for _, r in frame.iterrows()])
        truth = (frame["winner"] == "X").astype(int)
        results[name] = {
            "pairs": len(frame),
            # Keep the control RNG independent from the RNG used to place winners as X/Y.
            "fake_accuracy": fake_accuracy(frame, config["seed"] + 100_000 + offset),
            "code_baseline_accuracy": accuracy_score(truth, model.predict(matrix)),
        }
    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    output_name = "controls_final.json" if args.include_sealed else "controls_preflight.json"
    (output_dir / output_name).write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
