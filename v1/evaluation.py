from __future__ import annotations

from typing import Any

from deciders import LLMDecider, RubricDecider, RubricQuestion


def batched(items: list[dict[str, str]], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def evaluate_loop_a(frame, instructions: str, *, client, logger, config: dict[str, Any], run_id: str, round_number: int, set_name: str, version_id: str, progress=None) -> list[dict[str, Any]]:
    pairs = frame[["pair_id", "headline_x", "headline_y"]].astype({"pair_id": str}).to_dict("records")
    decider = LLMDecider(client)
    decisions = {}
    usage_by_pair = {}
    for batch_number, batch in enumerate(batched(pairs, config["api"]["batch_size"])):
        batch_decisions = decider.decide_batch(
            instructions=instructions,
            pairs=batch,
            event={"run_id": run_id, "loop": "A", "round": round_number, "set": set_name,
                   "version_id": version_id, "call_type": "decision_batch", "batch": batch_number},
        )
        decisions.update(batch_decisions)
        if progress:
            progress(completed=min((batch_number + 1) * config["api"]["batch_size"], len(pairs)), total=len(pairs))
        for pair in batch:
            usage_by_pair[str(pair["pair_id"])] = {
                key: client.last_call.get(key, 0) / len(batch)
                for key in ("input_tokens", "output_tokens", "reasoning_tokens", "cost", "latency_ms")
            }
    records = []
    for _, row in frame.iterrows():
        pair_id = str(row["pair_id"])
        decision = decisions[pair_id]
        record = {
            "run_id": run_id, "loop": "A", "round": round_number, "set": set_name,
            "pair_id": pair_id, "version_id": version_id,
            "model": config["models"]["llm_expected_served"],
            "headline_x": row["headline_x"], "headline_y": row["headline_y"],
            "winner": row["winner"], "prediction": decision.prediction,
            "correct": decision.prediction == row["winner"], "reason": decision.reason,
            "questions": None, "coin_flip_tie": False, **usage_by_pair[pair_id],
        }
        logger.write(record)
        records.append(record)
    return records


def evaluate_loop_b(frame, questions_data: list[dict[str, str]], *, client, logger, config: dict[str, Any], run_id: str, round_number: int, set_name: str, version_id: str, progress=None) -> list[dict[str, Any]]:
    questions = [RubricQuestion(**item) for item in questions_data]
    scorer = RubricDecider(questions, lambda _headline, _questions: {}, seed=config["seed"] + round_number + 200_000)
    records = []
    for _, row in frame.iterrows():
        pair_id = str(row["pair_id"])
        event = {"run_id": run_id, "loop": "B", "round": round_number, "set": set_name,
                 "pair_id": pair_id, "version_id": version_id, "call_type": "rubric_evaluation"}
        x = client.evaluate(row["headline_x"], questions, {**event, "headline_side": "X"})
        x_usage = dict(client.last_call)
        y = client.evaluate(row["headline_y"], questions, {**event, "headline_side": "Y"})
        y_usage = dict(client.last_call)
        decision = scorer.decide_from_probabilities(x, y)
        record = {
            **event, "model": y_usage.get("model", config["models"]["jev_expected_served"]),
            "headline_x": row["headline_x"], "headline_y": row["headline_y"],
            "winner": row["winner"], "prediction": decision.prediction,
            "correct": decision.prediction == row["winner"], "reason": None,
            "questions": decision.question_probabilities, "coin_flip_tie": decision.coin_flip_tie,
            "input_tokens": x_usage.get("input_tokens", 0) + y_usage.get("input_tokens", 0),
            "output_tokens": x_usage.get("output_tokens", 0) + y_usage.get("output_tokens", 0),
            "cost": x_usage.get("cost", 0) + y_usage.get("cost", 0),
            "latency_ms": x_usage.get("latency_ms", 0) + y_usage.get("latency_ms", 0),
        }
        logger.write(record)
        records.append(record)
        if progress and (len(records) % 10 == 0 or len(records) == len(frame)):
            progress(
                completed=len(records), total=len(frame),
                accuracy=sum(item["correct"] for item in records) / len(records),
                cost=sum(float(item.get("cost", 0)) for item in records),
            )
    return records


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "pairs": len(records),
        "accuracy": sum(item["correct"] for item in records) / len(records),
        "tie_rate": sum(item["coin_flip_tie"] for item in records) / len(records),
        "cost": sum(float(item.get("cost", 0)) for item in records),
    }
