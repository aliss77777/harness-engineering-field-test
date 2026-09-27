from __future__ import annotations

import argparse
import json

import pandas as pd

from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from spend import SpendTracker
from telemetry import Telemetry
from verdict import compute_verdict
from workspace import Workspace


def baseline_predictions(ws: Workspace, sealed: pd.DataFrame) -> list[bool] | None:
    """Code baseline on the same sealed pairs (Arena: B vs baseline McNemar)."""
    if ws.task.get("baseline") != "arena_style":
        return None
    import baseline_arena

    practice = pd.read_csv(ws.path("pairs") / "practice.csv", dtype={"pair_id": str})
    model = baseline_arena.fit(practice, ws.config["seed"])
    return [p == w for p, w in zip(baseline_arena.predict(model, sealed), sealed["winner"])]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the single guarded sealed evaluation.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena.yaml")
    parser.add_argument("--task", default="task_arena.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, results = ws.config, ws.path("results")
    final_path, completed_path = results / "final_versions.json", results / "sealed_complete.json"
    if completed_path.exists():
        raise RuntimeError("sealed evaluation already completed; refusing to rerun")
    if not final_path.exists() or json.loads(final_path.read_text()).get("frozen") is not True:
        raise RuntimeError("final versions are not frozen")
    frozen = json.loads(final_path.read_text())

    sealed = pd.read_csv(ws.path("pairs") / "sealed.csv", dtype={"pair_id": str})
    logs = ws.path("logs")
    logger = JsonlLogger(logs / f"{args.run_id}.jsonl")
    spend = SpendTracker(results / "spend.json", config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, args.run_id, spend)
    llm = build_llm_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(config, ws.root, args.run_id, logs_dir=logs, spend=spend)
    v0, final = frozen["version0"], frozen["final"]
    versions = {
        "a_version0": ("A", "A-v0", v0["instructions"]),
        "a_final": ("A", final["A"]["version_id"], final["A"]["instructions"]),
        "b_version0": ("B", "B-v0", v0["rubric_questions"]),
        "b_final": ("B", final["B"]["version_id"], final["B"]["rubric_questions"]),
    }
    records = {}
    for name, (loop, version_id, content) in versions.items():
        def report(**values):
            telemetry.stage("sealed", stage="sealed", loop=loop, round="final", set="sealed",
                            version_id=version_id, **values)
        common = dict(client=llm if loop == "A" else jev, logger=logger, run_id=args.run_id,
                      round_number="final", set_name="sealed", version_id=version_id, progress=report)
        records[name] = (evaluate_loop_a(ws, sealed, content, **common) if loop == "A"
                         else evaluate_loop_b(ws, sealed, content, **common))

    baseline = baseline_predictions(ws, sealed)
    # Cache replays are charged at the original call's cost, so a final version equal
    # to version 0 still reports its full decision cost.
    a_cost = summarize(records["a_final"])["cost"] / len(sealed) * 1000
    b_cost = summarize(records["b_final"])["cost"] / len(sealed) * 1000
    verdict = compute_verdict(
        a_version0=[r["correct"] for r in records["a_version0"]],
        a_final=[r["correct"] for r in records["a_final"]],
        b_version0=[r["correct"] for r in records["b_version0"]],
        b_final=[r["correct"] for r in records["b_final"]],
        a_cost_per_1000=a_cost, b_cost_per_1000=b_cost, config=config["verdict"], baseline=baseline,
    )
    # Sensitivity check (not the verdict): drop pairs Gemini refused to read in any
    # Loop A evaluation, from every system alike, and recompute.
    blocked = {r["pair_id"] for name in ("a_version0", "a_final") for r in records[name] if r.get("blocked")}
    keep = [i for i, pair_id in enumerate(sealed["pair_id"]) if pair_id not in blocked]
    sensitivity = None
    if blocked:
        pick = lambda values: [values[i] for i in keep]
        sensitivity = compute_verdict(
            a_version0=pick([r["correct"] for r in records["a_version0"]]),
            a_final=pick([r["correct"] for r in records["a_final"]]),
            b_version0=pick([r["correct"] for r in records["b_version0"]]),
            b_final=pick([r["correct"] for r in records["b_final"]]),
            a_cost_per_1000=a_cost, b_cost_per_1000=b_cost, config=config["verdict"],
            baseline=pick(baseline) if baseline is not None else None,
        )
    spend.flush()
    result = {
        "run_id": args.run_id,
        "task": ws.task["name"],
        "summaries": {name: summarize(items) for name, items in records.items()},
        "verdict": verdict,
        "blocked_pairs": sorted(blocked),
        "sensitivity_excluding_blocked": sensitivity,
        "edits": frozen.get("edits"),
        "notes": {**frozen["notes"], "total_paid_spend_usd": round(spend.total_usd, 4)},
    }
    completed_path.write_text(json.dumps(result, indent=2) + "\n")
    telemetry.finish("sealed", verdict=verdict["verdict"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
