"""Experiment 4, stage 1: fit the stacked vote (and the exploratory cascade threshold)
on practice + gate. Never reads sealed data. Writes results/arena4/hybrid_model.json,
which the sealed stage loads unchanged.
"""
from __future__ import annotations

import argparse
import json

from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from hybrid import choose_cascade_threshold, feature_names, fit_stacker, jev_margin, matrix, predict
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from spend import SpendTracker
from telemetry import Telemetry
from workspace import Workspace, read_pairs


def load_components(ws: Workspace) -> tuple[dict, dict]:
    c = ws.config["components"]
    llm = json.loads((ws.root / c["llm_versions"]).read_text())["final"][c["llm_version"]]
    jev = json.loads((ws.root / c["jev_versions"]).read_text())["final"][c["jev_version"]]
    return llm, jev


def score_both(ws, frame, set_name, llm_version, jev_version, *, llm, jev, logger, telemetry, run_id):
    def report(loop, version_id):
        return lambda **values: telemetry.stage(loop, stage="evaluate", set=set_name, version_id=version_id, **values)

    a = evaluate_loop_a(ws, frame, llm_version["instructions"], client=llm, logger=logger, run_id=run_id,
                        round_number="hybrid", set_name=set_name, version_id=llm_version["version_id"],
                        progress=report("llm", llm_version["version_id"]))
    j = evaluate_loop_b(ws, frame, jev_version["rubric_questions"], client=jev, logger=logger, run_id=run_id,
                        round_number="hybrid", set_name=set_name, version_id=jev_version["version_id"],
                        progress=report("jev", jev_version["version_id"]), weights=jev_version.get("weights"),
                        loop="J")
    for loop, records, version_id in (("llm", a, llm_version["version_id"]), ("jev", j, jev_version["version_id"])):
        telemetry.evaluation(loop=loop, round_number="hybrid", set_name=set_name, version_id=version_id,
                             summary=summarize(records))
    return a, j


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit the experiment-4 hybrid on practice + gate.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena4.yaml")
    parser.add_argument("--task", default="task_arena4.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, results = ws.config, ws.path("results")
    model_path = results / "hybrid_model.json"
    if model_path.exists():
        raise RuntimeError("hybrid model already fitted and frozen; refusing to refit")
    llm_version, jev_version = load_components(ws)
    questions, weights = jev_version["rubric_questions"], jev_version.get("weights")
    logs = ws.path("logs")
    logger = JsonlLogger(logs / f"{args.run_id}.jsonl")
    spend = SpendTracker(results / "spend.json", config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, args.run_id, spend)
    llm = build_llm_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)

    scored = {}
    for set_name in ("practice", "gate"):
        frame = read_pairs(ws.path("pairs") / f"{set_name}.csv")
        scored[set_name] = score_both(ws, frame, set_name, llm_version, jev_version, llm=llm, jev=jev,
                                      logger=logger, telemetry=telemetry, run_id=args.run_id)
    a_all = scored["practice"][0] + scored["gate"][0]
    j_all = scored["practice"][1] + scored["gate"][1]
    x, y, blocked = matrix(a_all, j_all, questions, weights)
    keep = [i for i, b in enumerate(blocked) if not b]  # refused pairs have no LLM pick to learn from
    hyb = config["hybrid"]
    fit = fit_stacker(x[keep], y[keep], c_grid=hyb["c_grid"], folds=hyb["cv_folds"], seed=config["seed"])
    in_sample = predict(fit["coef"], x, [r["pair_id"] for r in a_all], blocked,
                        [r["prediction"] for r in j_all], seed=config["seed"])

    gate_a, gate_j = scored["gate"]
    cascade = choose_cascade_threshold([jev_margin(r, questions, weights) for r in gate_j],
                                       [r["correct"] for r in gate_j], [r["correct"] for r in gate_a],
                                       max_llm_share=hyb["cascade_max_llm_share"])
    model = {
        "frozen": True, "run_id": args.run_id,
        "components": {"llm": llm_version["version_id"], "jev": jev_version["version_id"]},
        "feature_names": feature_names(questions), "c": fit["c"], "cv_accuracy": fit["cv_accuracy"],
        "coef": dict(zip(feature_names(questions), fit["coef"])),
        "fit_pairs": len(keep), "excluded_blocked_pairs": len(blocked) - len(keep),
        "in_sample_accuracy": sum(p == r["winner"] for p, r in zip(in_sample, a_all)) / len(a_all),
        "fit_set_accuracy": {name: {"llm": summarize(scored[name][0])["accuracy"],
                                    "jev": summarize(scored[name][1])["accuracy"]} for name in scored},
        "cascade_exploratory": cascade,
        "paid_spend_usd": round(spend.total_usd, 4),
    }
    spend.flush()
    model_path.write_text(json.dumps(model, indent=2) + "\n")
    telemetry.note("hybrid fitted and frozen")
    print(json.dumps({k: model[k] for k in ("c", "coef", "fit_pairs", "in_sample_accuracy", "fit_set_accuracy",
                                            "cascade_exploratory", "paid_spend_usd")}, indent=2))


if __name__ == "__main__":
    main()
