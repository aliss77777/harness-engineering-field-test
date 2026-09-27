"""Experiment 5: fix tau on gate (stage 1, frozen to router_model.json), then the single
guarded evaluation on sealed-5 (stage 2). Run with --stage fit, then --stage sealed.
"""
from __future__ import annotations

import argparse
import json

from fit_hybrid import load_components, score_both
from hybrid import cascade_curve, jev_margin
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from router import route, tau_for_share
from sealed import baseline_predictions
from spend import SpendTracker
from telemetry import Telemetry
from verdict_router import compute_router_verdict
from workspace import Workspace, read_pairs


def clients(ws, run_id, spend):
    logs = ws.path("logs")
    return (JsonlLogger(logs / f"{run_id}.jsonl"),
            build_llm_client(ws.config, ws.root, run_id, logs_dir=logs, spend=spend),
            build_jev_client(ws.config, ws.root, run_id, logs_dir=logs, spend=spend))


def fit(ws: Workspace, run_id: str) -> None:
    results = ws.path("results")
    model_path = results / "router_model.json"
    if model_path.exists():
        raise RuntimeError("router threshold already frozen; refusing to refit")
    spend = SpendTracker(results / "spend.json", ws.config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, run_id, spend)
    logger, llm, jev = clients(ws, run_id, spend)
    llm_version, jev_version = load_components(ws)
    questions, weights = jev_version["rubric_questions"], jev_version.get("weights")
    gate = read_pairs(ws.path("pairs") / "gate.csv")
    a, j = score_both(ws, gate, "gate", llm_version, jev_version, llm=llm, jev=jev,
                      logger=logger, telemetry=telemetry, run_id=run_id)
    margins = [jev_margin(r, questions, weights) for r in j]
    share = ws.config["router"]["llm_share"]
    tau = tau_for_share(margins, share)
    routed = route(margins, j, a, tau)
    model = {
        "frozen": True, "run_id": run_id, "llm_share_target": share, "tau": tau,
        "components": {"llm": llm_version["version_id"], "jev": jev_version["version_id"]},
        "gate": {"llm_share": sum(r["routed_to_llm"] for r in routed) / len(routed),
                 "router_accuracy": sum(r["correct"] for r in routed) / len(routed),
                 "llm_accuracy": sum(r["correct"] for r in a) / len(a),
                 "jev_accuracy": sum(r["correct"] for r in j) / len(j)},
        "paid_spend_usd": round(spend.total_usd, 4),
    }
    spend.flush()
    model_path.write_text(json.dumps(model, indent=2) + "\n")
    telemetry.note("router threshold frozen")
    print(json.dumps(model, indent=2))


def sealed(ws: Workspace, run_id: str) -> None:
    results = ws.path("results")
    completed_path = results / "sealed_complete.json"
    if completed_path.exists():
        raise RuntimeError("experiment 5 sealed evaluation already completed; refusing to rerun")
    model = json.loads((results / "router_model.json").read_text())
    if model.get("frozen") is not True:
        raise RuntimeError("router threshold is not frozen")
    spend = SpendTracker(results / "spend.json", ws.config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, run_id, spend)
    logger, llm, jev = clients(ws, run_id, spend)
    llm_version, jev_version = load_components(ws)
    questions, weights = jev_version["rubric_questions"], jev_version.get("weights")
    frame = read_pairs(ws.path("pairs") / "sealed.csv")
    a, j = score_both(ws, frame, "sealed", llm_version, jev_version, llm=llm, jev=jev,
                      logger=logger, telemetry=telemetry, run_id=run_id)
    margins = [jev_margin(r, questions, weights) for r in j]
    routed = route(margins, j, a, model["tau"])
    n = len(frame)
    costs = {"llm": sum(float(r.get("cost", 0)) for r in a) / n * 1000,
             "jev": sum(float(r.get("cost", 0)) for r in j) / n * 1000,
             "router": sum(r["cost"] for r in routed) / n * 1000}
    baseline = baseline_predictions(ws, frame)
    verdict = compute_router_verdict(
        llm=[r["correct"] for r in a], jev=[r["correct"] for r in j], router=[r["correct"] for r in routed],
        baseline=baseline, costs_per_1000=costs, config=ws.config["verdict"],
        max_cost_ratio=ws.config["router"]["max_cost_ratio"])

    def split(decider):
        rows = [r for r in routed if r["decided_by"] == decider]
        return {"pairs": len(rows), "accuracy": sum(r["correct"] for r in rows) / len(rows) if rows else None}

    latency = {name: sum(float(r.get("latency_ms", 0)) for r in rows) / n
               for name, rows in (("llm", a), ("jev", j), ("router", routed))}
    result = {
        "run_id": run_id, "task": ws.task["name"], "components": model["components"], "tau": model["tau"],
        "verdict": verdict,
        "routing": {"llm_share": sum(r["routed_to_llm"] for r in routed) / n,
                    "decided_by_jev": split("jev"), "decided_by_llm": split("llm")},
        "llm_on_jev_decided_pairs": (lambda rows: sum(rows) / len(rows) if rows else None)(
            [a_rec["correct"] for a_rec, r in zip(a, routed) if r["decided_by"] == "jev"]),
        "curve": cascade_curve(margins, [r["correct"] for r in j], [r["correct"] for r in a]),
        "avg_latency_ms_per_decision": latency,
        "blocked": {"pairs": sum(bool(r.get("blocked")) for r in a)},
        "paid_spend_usd_total_experiment5": round(spend.total_usd, 4),
    }
    spend.flush()
    completed_path.write_text(json.dumps(result, indent=2) + "\n")
    telemetry.finish("sealed", verdict=verdict["verdict"])
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 5 router: --stage fit, then --stage sealed.")
    parser.add_argument("--stage", choices=("fit", "sealed"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena5.yaml")
    parser.add_argument("--task", default="task_arena5.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    (fit if args.stage == "fit" else sealed)(ws, args.run_id)


if __name__ == "__main__":
    main()
