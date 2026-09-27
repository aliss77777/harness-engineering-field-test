from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from deciders import LLMDecider, RubricDecider, RubricQuestion
from workspace import Workspace


USAGE_KEYS = ("input_tokens", "output_tokens", "reasoning_tokens", "cost", "latency_ms")


def batched(items: list[dict[str, str]], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _running(records: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "accuracy": sum(item["correct"] for item in records) / len(records),
        "cost": sum(float(item.get("cost", 0)) for item in records),
    }


def evaluate_loop_a(
    ws: Workspace, frame, instructions: str, *, client, logger, run_id: str,
    round_number: int | str, set_name: str, version_id: str,
    progress: Callable[..., None] | None = None,
) -> list[dict[str, Any]]:
    """Loop A decides every pair. Batches run concurrently; results are in frame order."""
    config = ws.config
    pairs = [ws.pair_view(row) for _, row in frame.iterrows()]
    winners = dict(zip(frame["pair_id"].astype(str), frame["winner"]))
    decider = LLMDecider(client, wording=ws.wording, labels=ws.labels)
    batches = list(batched(pairs, config["api"]["batch_size"]))

    def run(batch_number: int, batch: list[dict[str, str]]):
        event = {"run_id": run_id, "loop": "A", "round": round_number, "set": set_name,
                 "version_id": version_id, "call_type": "decision_batch", "batch": batch_number}
        client.last_call = {}
        try:
            decisions = decider.decide_batch(instructions=instructions, pairs=batch, event=event)
            usage = dict(client.last_call)  # thread-local: this batch's call
            return batch, decisions, usage
        except ValueError as error:
            # The LLM skipped or duplicated a pair. Its (paid) answer is counted, then each
            # pair is re-asked on its own; a pair that still fails stops the run.
            wasted = dict(client.last_call)
            logger.write({**event, "call_type": "decision_batch_fallback", "error": str(error)})
            decisions, usage = {}, {key: wasted.get(key, 0) for key in USAGE_KEYS}
            for pair in batch:
                decisions.update(decider.decide_batch(
                    instructions=instructions, pairs=[pair],
                    event={**event, "call_type": "decision_single", "fallback_for_batch": batch_number},
                ))
                single = dict(client.last_call)
                usage = {key: usage.get(key, 0) + single.get(key, 0) for key in USAGE_KEYS}
            usage.update(model=single.get("model"), cached=single.get("cached"))
            return batch, decisions, usage

    by_pair: dict[str, dict[str, Any]] = {}
    done: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=config["api"]["llm_workers"]) as pool:
        futures = [pool.submit(run, number, batch) for number, batch in enumerate(batches)]
        for future in as_completed(futures):
            batch, decisions, usage = future.result()
            for pair in batch:
                decision = decisions[pair["pair_id"]]
                record = {
                    "run_id": run_id, "loop": "A", "round": round_number, "set": set_name,
                    "pair_id": pair["pair_id"], "version_id": version_id,
                    "model": usage.get("model", config["models"]["llm_expected_served"]),
                    "cached": usage.get("cached"),
                    "winner": winners[pair["pair_id"]], "prediction": decision.prediction,
                    "correct": decision.prediction == winners[pair["pair_id"]],
                    "reason": decision.reason, "questions": None, "coin_flip_tie": False,
                    **{key: usage.get(key, 0) / len(batch) for key in USAGE_KEYS},
                }
                by_pair[pair["pair_id"]] = record
                done.append(record)
            if progress:
                progress(completed=len(done), total=len(pairs), **_running(done))
    records = [by_pair[pair["pair_id"]] for pair in pairs]
    for record in records:
        logger.write(record)
    return records


def evaluate_loop_b(
    ws: Workspace, frame, questions_data: list[dict[str, str]], *, client, logger, run_id: str,
    round_number: int | str, set_name: str, version_id: str,
    progress: Callable[..., None] | None = None,
) -> list[dict[str, Any]]:
    """Loop B: Jev answers the rubric for each item (with its context); code picks. No LLM."""
    config = ws.config
    questions = [RubricQuestion(**item) for item in questions_data]
    scorer = RubricDecider(questions, lambda _item, _questions: {}, seed=config["seed"])
    pairs = [ws.pair_view(row) for _, row in frame.iterrows()]
    winners = dict(zip(frame["pair_id"].astype(str), frame["winner"]))

    def run(pair: dict[str, str]) -> dict[str, Any]:
        event = {"run_id": run_id, "loop": "B", "round": round_number, "set": set_name,
                 "pair_id": pair["pair_id"], "version_id": version_id, "call_type": "rubric_evaluation"}
        x = client.evaluate(ws.jev_state(pair["context"], pair["x"]), questions, {**event, "item_side": "X"})
        x_usage = dict(client.last_call)
        y = client.evaluate(ws.jev_state(pair["context"], pair["y"]), questions, {**event, "item_side": "Y"})
        y_usage = dict(client.last_call)
        tie_breaker = random.Random(f"{config['seed']}:{round_number}:{set_name}:{pair['pair_id']}")
        decision = scorer.decide_from_probabilities(x, y, tie_breaker=tie_breaker)
        winner = winners[pair["pair_id"]]
        return {
            **event, "model": y_usage.get("model", config["models"]["jev_expected_served"]),
            "cached": bool(x_usage.get("cached") and y_usage.get("cached")),
            "winner": winner, "prediction": decision.prediction,
            "correct": decision.prediction == winner, "reason": None,
            "questions": decision.question_probabilities, "coin_flip_tie": decision.coin_flip_tie,
            **{key: x_usage.get(key, 0) + y_usage.get(key, 0) for key in USAGE_KEYS},
        }

    by_pair: dict[str, dict[str, Any]] = {}
    done: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=config["api"]["jev_workers"]) as pool:
        futures = [pool.submit(run, pair) for pair in pairs]
        for future in as_completed(futures):
            record = future.result()
            by_pair[record["pair_id"]] = record
            done.append(record)
            if progress and (len(done) % 25 == 0 or len(done) == len(pairs)):
                progress(completed=len(done), total=len(pairs), **_running(done))
    records = [by_pair[pair["pair_id"]] for pair in pairs]
    for record in records:
        logger.write(record)
    return records


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "pairs": len(records),
        "accuracy": sum(item["correct"] for item in records) / len(records),
        "tie_rate": sum(item["coin_flip_tie"] for item in records) / len(records),
        "picks_x": sum(item["prediction"] == "X" for item in records) / len(records),
        "cost": sum(float(item.get("cost", 0)) for item in records),
    }
