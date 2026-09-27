"""Experiment 3: the single guarded evaluation on the fresh sealed set.

Scores, once each: experiment 2's Loop A (version 0 and final) and Loop B (version 0 and
final), experiment 3's B-prime final, B-plus version 0 and final, and the style baseline.
Runs only after experiment 2's sealed verdict exists and experiment 3's versions are frozen.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from sealed import baseline_predictions
from spend import SpendTracker
from telemetry import Telemetry
from verdict_trace import compute_trace_verdict
from workspace import Workspace, read_pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 3 sealed evaluation (fresh sealed set, once).")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena3.yaml")
    parser.add_argument("--task", default="task_arena3.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, results = ws.config, ws.path("results")
    exp2 = ws.root / config["experiment2"]["results"]
    completed_path = results / "sealed_complete.json"
    if completed_path.exists():
        raise RuntimeError("experiment 3 sealed evaluation already completed; refusing to rerun")
    if not (exp2 / "sealed_complete.json").exists():
        raise RuntimeError("experiment 2's sealed verdict must be written first")
    frozen = json.loads((results / "final_versions.json").read_text())
    if frozen.get("frozen") is not True:
        raise RuntimeError("experiment 3 versions are not frozen")
    exp2_frozen = json.loads((exp2 / "final_versions.json").read_text())

    sealed = read_pairs(ws.path("pairs") / "sealed.csv")
    logs = ws.path("logs")
    logger = JsonlLogger(logs / f"{args.run_id}.jsonl")
    spend = SpendTracker(results / "spend.json", config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, args.run_id, spend)
    llm = build_llm_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    v0 = exp2_frozen["version0"]
    systems = {
        "a_version0": ("A", "A-v0", {"instructions": v0["instructions"]}),
        "a_final": ("A", exp2_frozen["final"]["A"]["version_id"], exp2_frozen["final"]["A"]),
        "b_version0": ("B", "B-v0", {"rubric_questions": v0["rubric_questions"]}),
        "b_final": ("B", exp2_frozen["final"]["B"]["version_id"], exp2_frozen["final"]["B"]),
        "bp_final": ("Bp", frozen["final"]["Bp"]["version_id"], frozen["final"]["Bp"]),
        "bw_version0": ("Bw", "Bw-v0", frozen["arm_version0"]["Bw"]),
        "bw_final": ("Bw", frozen["final"]["Bw"]["version_id"], frozen["final"]["Bw"]),
    }
    records = {}
    for name, (loop, version_id, version) in systems.items():
        def report(**values):
            telemetry.stage("sealed", stage="sealed", loop=loop, round="final", set="sealed",
                            version_id=version_id, **values)
        common = dict(logger=logger, run_id=args.run_id, round_number="final", set_name="sealed",
                      version_id=version_id, progress=report)
        if loop == "A":
            records[name] = evaluate_loop_a(ws, sealed, version["instructions"], client=llm, **common)
        else:
            records[name] = evaluate_loop_b(ws, sealed, version["rubric_questions"], client=jev,
                                            weights=version.get("weights"), loop=loop, **common)
        telemetry.evaluation(loop=loop, round_number="final", set_name="sealed", version_id=version_id,
                             summary=summarize(records[name]))
    baseline = baseline_predictions(ws, sealed)
    vectors = {name: [r["correct"] for r in items] for name, items in records.items()}
    vectors["baseline"] = baseline
    # Cache replays are charged at the original call's cost.
    costs = {name: summarize(records[name])["cost"] / len(sealed) * 1000 for name in ("a_final", "bp_final", "bw_final")}
    verdict = compute_trace_verdict(vectors=vectors, costs_per_1000=costs, config=config["verdict"])
    blocked = sorted({r["pair_id"] for name in ("a_version0", "a_final") for r in records[name] if r.get("blocked")})
    spend.flush()
    result = {
        "run_id": args.run_id, "task": ws.task["name"],
        "summaries": {name: summarize(items) for name, items in records.items()},
        "verdict": verdict, "blocked_pairs": blocked,
        "edits": frozen.get("edits"),
        "notes": {**frozen["notes"], "experiment3_paid_spend_usd": round(spend.total_usd, 4)},
    }
    completed_path.write_text(json.dumps(result, indent=2, default=str) + "\n")
    telemetry.finish("sealed", primary=verdict["primary"])
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
