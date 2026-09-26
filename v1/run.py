from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import pandas as pd
import yaml

from cache import DiskCache
from deciders import LLMDecider, RubricQuestion, rubric_score
from gemini import load_env
from jev import OpenRouterJevClient
from llm_factory import build_llm_client
from log import JsonlLogger


ROOT = Path(__file__).resolve().parent


def batched(items: list[dict[str, str]], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def run_loop_a_smoke(limit: int, run_id: str) -> dict:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    version0 = json.loads((ROOT / "results" / "version0.json").read_text())
    frame = pd.read_csv(ROOT / "data" / "pairs" / "practice.csv", dtype={"pair_id": str}).head(limit)
    pairs = frame[["pair_id", "headline_x", "headline_y"]].to_dict("records")
    client = build_llm_client(config, ROOT, run_id)
    decider = LLMDecider(client)
    decisions = {}
    for batch_number, batch in enumerate(batched(pairs, config["api"]["batch_size"])):
        decisions.update(
            decider.decide_batch(
                instructions=version0["instructions"],
                pairs=batch,
                event={
                    "run_id": run_id,
                    "loop": "A",
                    "round": 0,
                    "set": "practice",
                    "version_id": "v0",
                    "call_type": "decision_batch",
                    "batch": batch_number,
                },
            )
        )
    records = []
    for _, row in frame.iterrows():
        decision = decisions[str(row["pair_id"])]
        records.append(
            {
                "pair_id": str(row["pair_id"]),
                "prediction": decision.prediction,
                "winner": row["winner"],
                "correct": decision.prediction == row["winner"],
                "reason": decision.reason,
            }
        )
    result = {
        "run_id": run_id,
        "loop": "A",
        "set": "practice",
        "version_id": "v0",
        "pairs": len(records),
        "accuracy": sum(record["correct"] for record in records) / len(records),
        "decisions": records,
    }
    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    (output_dir / f"{run_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_loop_b_smoke(limit: int, run_id: str) -> dict:
    load_env(ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_KEY is missing")
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    version0 = json.loads((ROOT / "results" / "version0.json").read_text())
    questions = [RubricQuestion(**item) for item in version0["rubric_questions"]]
    frame = pd.read_csv(ROOT / "data" / "pairs" / "practice.csv", dtype={"pair_id": str}).head(limit)
    client = OpenRouterJevClient(
        model=config["models"]["jev"],
        api_key=api_key,
        cache=DiskCache(ROOT / "cache" / "jev"),
        logger=JsonlLogger(ROOT / "logs" / f"{run_id}.jsonl"),
        retries=config["api"]["retries"],
        backoff_seconds=config["api"]["backoff_seconds"],
    )
    rng = random.Random(config["seed"] + 200_000)
    records = []
    for _, row in frame.iterrows():
        base_event = {
            "run_id": run_id,
            "loop": "B",
            "round": 0,
            "set": "practice",
            "pair_id": str(row["pair_id"]),
            "version_id": "v0",
            "call_type": "rubric_evaluation",
        }
        x = client.evaluate(
            row["headline_x"], questions, {**base_event, "headline_side": "X"}
        )
        y = client.evaluate(
            row["headline_y"], questions, {**base_event, "headline_side": "Y"}
        )
        x_score = rubric_score(questions, x)
        y_score = rubric_score(questions, y)
        tied = x_score == y_score
        prediction = rng.choice(("X", "Y")) if tied else ("X" if x_score > y_score else "Y")
        records.append(
            {
                "pair_id": str(row["pair_id"]),
                "prediction": prediction,
                "winner": row["winner"],
                "correct": prediction == row["winner"],
                "coin_flip_tie": tied,
                "x_score": x_score,
                "y_score": y_score,
                "questions": {
                    question.question_id: {
                        "x_yes_probability": x[question.question_id],
                        "y_yes_probability": y[question.question_id],
                    }
                    for question in questions
                },
            }
        )
    result = {
        "run_id": run_id,
        "loop": "B",
        "set": "practice",
        "version_id": "v0",
        "pairs": len(records),
        "accuracy": sum(record["correct"] for record in records) / len(records),
        "tie_rate": sum(record["coin_flip_tie"] for record in records) / len(records),
        "decisions": records,
    }
    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    (output_dir / f"{run_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the learning-loop experiment.")
    parser.add_argument("--loop-a-smoke", type=int, metavar="PAIRS")
    parser.add_argument("--loop-b-smoke", type=int, metavar="PAIRS")
    parser.add_argument("--run-id", default="smoke")
    args = parser.parse_args()
    if args.loop_a_smoke:
        result = run_loop_a_smoke(args.loop_a_smoke, args.run_id)
        print(f"Loop A smoke: {result['pairs']} pairs, accuracy={result['accuracy']:.1%}")
    elif args.loop_b_smoke:
        result = run_loop_b_smoke(args.loop_b_smoke, args.run_id)
        print(
            f"Loop B smoke: {result['pairs']} pairs, accuracy={result['accuracy']:.1%}, "
            f"tie_rate={result['tie_rate']:.1%}"
        )
    else:
        parser.error("choose a run mode")


if __name__ == "__main__":
    main()
