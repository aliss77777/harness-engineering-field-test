"""Preflight modes for a task: fake decider, paid smoke test, and cost estimate.

    python run.py --fake                 # seeded random clients through the real pipeline
    python run.py --smoke 20             # version 0, both loops, on N practice pairs (paid)
    python run.py --estimate             # project full-run spend from the smoke test

Experiment 1's version of this file is at git tag exp1-upworthy-v1.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from fakes import FakeJevClient, FakeLLMClient
from gate import gate_version
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from spend import SpendTracker
from workspace import Workspace, read_pairs


SETS = ("practice", "gate", "sealed")


def load(ws: Workspace, set_name: str) -> pd.DataFrame:
    return read_pairs(ws.path("pairs") / f"{set_name}.csv")


def run_fake(ws: Workspace, run_id: str) -> dict:
    logger = JsonlLogger(ws.path("logs") / f"{run_id}.jsonl")
    llm, jev = FakeLLMClient(ws.config["seed"]), FakeJevClient(ws.config["seed"])
    rubric = [{"question_id": f"q{i}", "text": f"Question {i}?", "direction": "helps" if i % 2 else "hurts"}
              for i in range(6)]
    results: dict = {}
    for set_name in SETS:
        frame = load(ws, set_name)
        common = dict(logger=logger, run_id=run_id, round_number=0, set_name=set_name)
        a = evaluate_loop_a(ws, frame, "Pick at random.", client=llm, version_id="fake-A", **common)
        b = evaluate_loop_b(ws, frame, rubric, client=jev, version_id="fake-B", **common)
        results[set_name] = {"loop_a": summarize(a), "loop_b": summarize(b)}
    gate_frame = load(ws, "gate")
    common = dict(logger=logger, run_id=run_id, round_number=1, set_name="gate")
    old = evaluate_loop_a(ws, gate_frame, "Pick at random.", client=llm, version_id="fake-old", **common)
    new = evaluate_loop_a(ws, gate_frame, "Pick at random.", client=llm, version_id="fake-new", **common)
    gate = gate_version([r["correct"] for r in old], [r["correct"] for r in new],
                        p_threshold=ws.config["learning"]["gate_p_threshold"])
    results["gate_check"] = {"keep": gate.keep, "b": gate.b, "c": gate.c, "p": gate.p_value}
    (ws.path("results") / f"{run_id}.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def smoke_frame(ws: Workspace, count: int) -> pd.DataFrame:
    """Random practice pairs plus the longest ones, to test Jev's input limit."""
    practice = load(ws, "practice")
    longest = practice.assign(size=practice[["words_x", "words_y"]].max(axis=1)).nlargest(max(2, count // 4), "size")
    rest = practice.drop(longest.index).sample(n=count - len(longest), random_state=ws.config["seed"])
    return pd.concat([rest, longest.drop(columns="size")]).reset_index(drop=True)


def run_smoke(ws: Workspace, count: int, run_id: str) -> dict:
    results_dir, logs = ws.path("results"), ws.path("logs")
    version0 = json.loads((results_dir / "version0.json").read_text())
    spend = SpendTracker(results_dir / "spend.json", ws.config["budget"]["spend_cap_usd"])
    logger = JsonlLogger(logs / f"{run_id}.jsonl")
    llm = build_llm_client(ws.config, ws.root, run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(ws.config, ws.root, run_id, logs_dir=logs, spend=spend)
    frame = smoke_frame(ws, count)
    common = dict(logger=logger, run_id=run_id, round_number=0, set_name="practice")
    a = evaluate_loop_a(ws, frame, version0["instructions"], client=llm, version_id="A-v0-smoke", **common)
    b = evaluate_loop_b(ws, frame, version0["rubric_questions"], client=jev, version_id="B-v0-smoke", **common)
    spend.flush()
    result = {
        "run_id": run_id, "pairs": len(frame),
        "max_words_in_sample": int(frame[["words_x", "words_y"]].max().max()),
        "loop_a": {**summarize(a), "cost_per_1000": summarize(a)["cost"] / len(a) * 1000,
                   "input_tokens_per_decision": sum(r["input_tokens"] for r in a) / len(a),
                   "output_tokens_per_decision": sum(r["output_tokens"] for r in a) / len(a)},
        "loop_b": {**summarize(b), "cost_per_1000": summarize(b)["cost"] / len(b) * 1000,
                   "input_tokens_per_decision": sum(r["input_tokens"] for r in b) / len(b)},
        "note": "Plumbing and cost check on practice pairs only; not a finding.",
    }
    (results_dir / "smoke.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def estimate(ws: Workspace) -> dict:
    """Worst case: every round the editor proposes the maximum and every candidate is gated."""
    config = ws.config
    smoke = json.loads((ws.path("results") / "smoke.json").read_text())
    sets, rounds = config["sets"], config["learning"]["rounds"]
    candidates = config["learning"]["max_changes"]
    decisions = {
        "practice": sets["practice"] * (1 + rounds),       # v0 plus one new version per kept edit
        "gate": sets["gate"] * (1 + candidates * rounds),  # current once, then each candidate
        "sealed": sets["sealed"] * 2,                     # version 0 and final
    }
    per_loop = sum(decisions.values())
    a = per_loop * smoke["loop_a"]["cost_per_1000"] / 1000
    b = per_loop * smoke["loop_b"]["cost_per_1000"] / 1000
    editor = rounds * 2 * 0.10  # generous: long prompts with 20 mistakes each
    total = a + b + editor
    result = {
        "decisions_per_loop_worst_case": decisions,
        "loop_a_usd": round(a, 2), "loop_b_usd": round(b, 2), "editor_usd": round(editor, 2),
        "worst_case_total_usd": round(total, 2),
        "spend_cap_usd": config["budget"]["spend_cap_usd"],
        "within_cap": total <= config["budget"]["spend_cap_usd"],
        "cost_ratio_b_over_a": smoke["loop_b"]["cost_per_1000"] / smoke["loop_a"]["cost_per_1000"],
    }
    (ws.path("results") / "cost_estimate.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight modes for a task.")
    parser.add_argument("--config", default="config_arena.yaml")
    parser.add_argument("--task", default="task_arena.yaml")
    parser.add_argument("--run-id", default="preflight")
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--smoke", type=int, metavar="PAIRS")
    parser.add_argument("--estimate", action="store_true")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    if args.fake:
        result = run_fake(ws, args.run_id)
    elif args.smoke:
        result = run_smoke(ws, args.smoke, args.run_id)
    elif args.estimate:
        result = estimate(ws)
    else:
        parser.error("choose --fake, --smoke N or --estimate")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
