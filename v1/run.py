from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import yaml

from cache import DiskCache
from deciders import FakeDecider, LLMDecider, RubricDecider, RubricQuestion
from gemini import load_env
from gate import gate_version
from jev import OpenRouterJevClient
from llm_factory import build_llm_client
from log import JsonlLogger


ROOT = Path(__file__).resolve().parent


def batched(items: list[dict[str, str]], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def evaluate_pair_decider(frame, decider, *, run_id, loop, round_number, set_name, version_id, model, logger):
    records = []
    for _, row in frame.iterrows():
        decision = decider.decide(row["headline_x"], row["headline_y"])
        record = {
            "run_id": run_id,
            "loop": loop,
            "round": round_number,
            "set": set_name,
            "pair_id": str(row["pair_id"]),
            "version_id": version_id,
            "model": model,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 0,
            "prediction": decision.prediction,
            "correct": decision.prediction == row["winner"],
            "reason": decision.reason,
            "questions": decision.question_probabilities,
            "coin_flip_tie": decision.coin_flip_tie,
        }
        logger.write(record)
        records.append(record)
    return records


def run_fake(run_id: str) -> dict:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    logger = JsonlLogger(ROOT / "logs" / f"{run_id}.jsonl")
    results = {}
    for index, set_name in enumerate(("practice", "gate", "sealed")):
        frame = pd.read_csv(ROOT / "data" / "pairs" / f"{set_name}.csv", dtype={"pair_id": str})
        records = evaluate_pair_decider(
            frame,
            FakeDecider(config["seed"] + index),
            run_id=run_id,
            loop="fake",
            round_number=0,
            set_name=set_name,
            version_id="fake-v0",
            model="seeded-random",
            logger=logger,
        )
        results[set_name] = {
            "pairs": len(records),
            "accuracy": sum(item["correct"] for item in records) / len(records),
        }
    gate_frame = pd.read_csv(ROOT / "data" / "pairs" / "gate.csv", dtype={"pair_id": str})
    old = evaluate_pair_decider(
        gate_frame, FakeDecider(config["seed"] + 10), run_id=run_id, loop="fake",
        round_number=1, set_name="gate", version_id="fake-old", model="seeded-random", logger=logger,
    )
    new = evaluate_pair_decider(
        gate_frame, FakeDecider(config["seed"] + 11), run_id=run_id, loop="fake",
        round_number=1, set_name="gate", version_id="fake-new", model="seeded-random", logger=logger,
    )
    gate = gate_version(
        [item["correct"] for item in old], [item["correct"] for item in new],
        p_threshold=config["learning"]["gate_p_threshold"],
    )
    results["gate_check"] = {"keep": gate.keep, "b": gate.b, "c": gate.c, "p": gate.p_value}
    logger.write({"run_id": run_id, "loop": "fake", "round": 1, "set": "gate", "call_type": "gate", **results["gate_check"]})
    (ROOT / "results" / f"{run_id}.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def run_loop_a_smoke(limit: int, run_id: str) -> dict:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    version0 = json.loads((ROOT / "results" / "version0.json").read_text())
    frame = pd.read_csv(ROOT / "data" / "pairs" / "practice.csv", dtype={"pair_id": str}).head(limit)
    pairs = frame[["pair_id", "headline_x", "headline_y"]].to_dict("records")
    client = build_llm_client(config, ROOT, run_id)
    decider = LLMDecider(client)
    logger = JsonlLogger(ROOT / "logs" / f"{run_id}.jsonl")
    decisions = {}
    usage_by_pair = {}
    for batch_number, batch in enumerate(batched(pairs, config["api"]["batch_size"])):
        batch_decisions = decider.decide_batch(
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
        decisions.update(batch_decisions)
        divisor = len(batch)
        for pair in batch:
            usage_by_pair[str(pair["pair_id"])] = {
                key: client.last_call.get(key, 0) / divisor
                for key in ("input_tokens", "output_tokens", "reasoning_tokens", "cost", "latency_ms")
            }
    records = []
    for _, row in frame.iterrows():
        decision = decisions[str(row["pair_id"])]
        record = {
                "run_id": run_id,
                "loop": "A",
                "round": 0,
                "set": "practice",
                "pair_id": str(row["pair_id"]),
                "version_id": "v0",
                "model": client.last_call.get("model", config["models"]["llm"]),
                "prediction": decision.prediction,
                "winner": row["winner"],
                "correct": decision.prediction == row["winner"],
                "reason": decision.reason,
                "coin_flip_tie": False,
                **usage_by_pair[str(row["pair_id"])],
            }
        logger.write(record)
        records.append(record)
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
    logger = JsonlLogger(ROOT / "logs" / f"{run_id}.jsonl")
    client = OpenRouterJevClient(
        model=config["models"]["jev"],
        api_key=api_key,
        cache=DiskCache(ROOT / "cache" / "jev"),
        logger=logger,
        retries=config["api"]["retries"],
        backoff_seconds=config["api"]["backoff_seconds"],
        expected_model=config["models"]["jev_expected_served"],
        expected_provider=config["models"]["jev_expected_provider"],
    )
    decider = RubricDecider(questions, lambda _headline, _questions: {}, seed=config["seed"] + 200_000)
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
        x_usage = dict(client.last_call)
        y = client.evaluate(
            row["headline_y"], questions, {**base_event, "headline_side": "Y"}
        )
        y_usage = dict(client.last_call)
        decision = decider.decide_from_probabilities(x, y)
        record = {
                "run_id": run_id,
                "loop": "B",
                "round": 0,
                "set": "practice",
                "pair_id": str(row["pair_id"]),
                "version_id": "v0",
                "model": y_usage.get("model", config["models"]["jev"]),
                "prediction": decision.prediction,
                "winner": row["winner"],
                "correct": decision.prediction == row["winner"],
                "coin_flip_tie": decision.coin_flip_tie,
                "questions": decision.question_probabilities,
                "input_tokens": x_usage.get("input_tokens", 0) + y_usage.get("input_tokens", 0),
                "output_tokens": x_usage.get("output_tokens", 0) + y_usage.get("output_tokens", 0),
                "cost": x_usage.get("cost", 0) + y_usage.get("cost", 0),
                "latency_ms": x_usage.get("latency_ms", 0) + y_usage.get("latency_ms", 0),
            }
        logger.write(record)
        records.append(record)
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
    parser.add_argument("--fake", action="store_true")
    args = parser.parse_args()
    if args.fake:
        result = run_fake(args.run_id)
        print("Fake: " + ", ".join(f"{name}={result[name]['accuracy']:.1%}" for name in ("practice", "gate", "sealed")))
    elif args.loop_a_smoke:
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
