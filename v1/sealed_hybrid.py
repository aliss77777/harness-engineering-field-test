"""Experiment 4, stage 2: the single guarded evaluation on sealed-4.

Scores A* (LLM) and J* (Jev) once each, applies the frozen hybrid model, computes the
preregistered verdict, and reports the exploratory cascade and the style baseline.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from fit_hybrid import load_components, score_both
from hybrid import cascade_curve, jev_margin, matrix, predict
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from sealed import baseline_predictions
from spend import SpendTracker
from telemetry import Telemetry
from verdict_hybrid import compute_hybrid_verdict
from workspace import Workspace, read_pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 4 sealed evaluation (sealed-4, once).")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena4.yaml")
    parser.add_argument("--task", default="task_arena4.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, results = ws.config, ws.path("results")
    completed_path = results / "sealed_complete.json"
    if completed_path.exists():
        raise RuntimeError("experiment 4 sealed evaluation already completed; refusing to rerun")
    model = json.loads((results / "hybrid_model.json").read_text())
    if model.get("frozen") is not True:
        raise RuntimeError("hybrid model is not fitted and frozen")
    llm_version, jev_version = load_components(ws)
    questions, weights = jev_version["rubric_questions"], jev_version.get("weights")

    sealed = read_pairs(ws.path("pairs") / "sealed.csv")
    logs = ws.path("logs")
    logger = JsonlLogger(logs / f"{args.run_id}.jsonl")
    spend = SpendTracker(results / "spend.json", config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, args.run_id, spend)
    llm = build_llm_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    a, j = score_both(ws, sealed, "sealed", llm_version, jev_version, llm=llm, jev=jev,
                      logger=logger, telemetry=telemetry, run_id=args.run_id)

    x, _, blocked = matrix(a, j, questions, weights)
    coef = [model["coef"][name] for name in model["feature_names"]]
    hybrid_picks = predict(coef, x, [r["pair_id"] for r in a], blocked, [r["prediction"] for r in j],
                           seed=config["seed"])
    winners = [r["winner"] for r in a]
    llm_ok = [r["correct"] for r in a]
    jev_ok = [r["correct"] for r in j]
    hybrid_ok = [p == w for p, w in zip(hybrid_picks, winners)]
    baseline = baseline_predictions(ws, sealed)

    n = len(sealed)
    cost_llm = sum(float(r.get("cost", 0)) for r in a) / n * 1000
    cost_jev = sum(float(r.get("cost", 0)) for r in j) / n * 1000
    costs = {"llm": cost_llm, "jev": cost_jev, "hybrid": cost_llm + cost_jev}
    verdict = compute_hybrid_verdict(llm=llm_ok, jev=jev_ok, hybrid=hybrid_ok, baseline=baseline,
                                     costs_per_1000=costs, config=config["verdict"])

    # Exploratory cascade, with the threshold frozen from gate.
    margins = [jev_margin(r, questions, weights) for r in j]
    tau = model["cascade_exploratory"]["threshold"]
    to_llm = [m < tau for m in margins]
    cascade = {
        "threshold_from_gate": tau,
        "llm_share": sum(to_llm) / n,
        "accuracy": sum(l if r else k for r, l, k in zip(to_llm, llm_ok, jev_ok)) / n,
        "cost_per_1000": cost_jev + cost_llm * sum(to_llm) / n,
        "curve": cascade_curve(margins, jev_ok, llm_ok),
        "note": "Exploratory; not part of the verdict.",
    }
    blocked_idx = [i for i, b in enumerate(blocked) if b]
    result = {
        "run_id": args.run_id, "task": ws.task["name"],
        "components": model["components"],
        "verdict": verdict,
        "agreement": {
            "llm_and_jev_agree": float(np.mean([r["prediction"] == k["prediction"] for r, k in zip(a, j)])),
            "hybrid_sides_with_jev_when_they_disagree": float(np.mean(
                [h == k["prediction"] for h, r, k in zip(hybrid_picks, a, j) if r["prediction"] != k["prediction"]] or [0])),
        },
        "blocked": {"pairs": len(blocked_idx),
                    "hybrid_correct": sum(hybrid_ok[i] for i in blocked_idx),
                    "llm_correct_coin_flip": sum(llm_ok[i] for i in blocked_idx)},
        "cascade_exploratory": cascade,
        "hybrid_model": {k: model[k] for k in ("c", "coef", "fit_pairs", "fit_set_accuracy")},
        "paid_spend_usd_total_experiment4": round(spend.total_usd, 4),
    }
    spend.flush()
    completed_path.write_text(json.dumps(result, indent=2) + "\n")
    telemetry.finish("sealed", verdict=verdict["verdict"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
