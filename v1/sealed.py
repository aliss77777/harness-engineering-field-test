from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from progress import RunProgress
from verdict import compute_verdict


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the single guarded sealed evaluation.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    final_path = ROOT / "results" / "final_versions.json"
    completed_path = ROOT / "results" / "sealed_complete.json"
    if completed_path.exists():
        raise RuntimeError("sealed evaluation already completed; refusing to rerun")
    if not final_path.exists():
        raise RuntimeError("final versions are not frozen")
    frozen = json.loads(final_path.read_text())
    if frozen.get("frozen") is not True:
        raise RuntimeError("final versions are not frozen")

    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    frame = pd.read_csv(ROOT / "data" / "pairs" / "sealed.csv", dtype={"pair_id": str})
    logger = JsonlLogger(ROOT / "logs" / f"{args.run_id}.jsonl")
    status = RunProgress(ROOT / "results" / "run_status.json", args.run_id)
    llm = build_llm_client(config, ROOT, args.run_id)
    jev = build_jev_client(config, ROOT, args.run_id)
    v0 = frozen["version0"]
    versions = {
        "a_version0": ("A", "A-v0", v0["instructions"]),
        "a_final": ("A", frozen["final"]["A"]["version_id"], frozen["final"]["A"]["instructions"]),
        "b_version0": ("B", "B-v0", v0["rubric_questions"]),
        "b_final": ("B", frozen["final"]["B"]["version_id"], frozen["final"]["B"]["rubric_questions"]),
    }
    records = {}
    for name, (loop, version_id, content) in versions.items():
        def report(**values):
            status.update(stage="sealed", loop=loop, round="final", set="sealed", version_id=version_id, **values)
        records[name] = (
            evaluate_loop_a(frame, content, client=llm, logger=logger, config=config, run_id=args.run_id, round_number=5, set_name="sealed", version_id=version_id, progress=report)
            if loop == "A" else
            evaluate_loop_b(frame, content, client=jev, logger=logger, config=config, run_id=args.run_id, round_number=5, set_name="sealed", version_id=version_id, progress=report)
        )

    a_cost = summarize(records["a_final"])["cost"] / len(frame) * 1000
    b_cost = summarize(records["b_final"])["cost"] / len(frame) * 1000
    verdict = compute_verdict(
        a_version0=[item["correct"] for item in records["a_version0"]],
        a_final=[item["correct"] for item in records["a_final"]],
        b_version0=[item["correct"] for item in records["b_version0"]],
        b_final=[item["correct"] for item in records["b_final"]],
        a_cost_per_1000=a_cost, b_cost_per_1000=b_cost, config=config["verdict"],
    )
    result = {
        "run_id": args.run_id,
        "registered_code_baseline_accuracy": 0.58,
        "summaries": {name: summarize(items) for name, items in records.items()},
        "verdict": verdict,
        "notes": frozen["notes"],
    }
    completed_path.write_text(json.dumps(result, indent=2) + "\n")
    status.update(stage="complete", loop=None, round="final", set=None, completed=1, total=1, verdict=verdict["verdict"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
