"""Experiment 3 sets: experiment 2's practice and gate (identical files), plus a fresh
sealed set that no loop, editor or baseline has ever seen.

The fresh sealed pairs come from the same prompt-hash buckets as experiment 2's sealed
set, so no prompt in them appears in practice or gate. Experiment 2's sealed pairs are
excluded, so the two sealed sets share no pair.
"""
from __future__ import annotations

import argparse
import json
import shutil

import pandas as pd

from prep_arena import assign_set, filter_battles, orient, prompt_bucket, to_candidates
from workspace import Workspace


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare experiment 3 sets.")
    parser.add_argument("--config", default="config_arena3.yaml")
    parser.add_argument("--task", default="task_arena3.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, seed = ws.config, ws.config["seed"]
    exp2_pairs = ws.root / config["experiment2"]["pairs"]
    exp2_splits = ws.root / config["experiment2"]["splits"]
    pairs_dir, split_dir = ws.path("pairs"), ws.path("splits")

    for name in ("practice", "gate"):
        shutil.copyfile(exp2_pairs / f"{name}.csv", pairs_dir / f"{name}.csv")
        shutil.copyfile(exp2_splits / f"{name}_pair_ids.txt", split_dir / f"{name}_pair_ids.txt")

    id_path = split_dir / "sealed_pair_ids.txt"
    raw = pd.read_csv(ws.root / ws.task["data"]["source"], low_memory=False)
    df, counts = filter_battles(raw, max_words=config["filters"]["max_response_words"])
    df["set"] = df["prompt_text"].map(lambda p: assign_set(prompt_bucket(p, seed), config["filters"]["split_fractions"]))
    pool = to_candidates(df)
    pool = pool[pool["set"] == "sealed"]
    used = set((exp2_splits / "sealed_pair_ids.txt").read_text().split())
    fresh_pool = pool[~pool["pair_id"].isin(used)]
    if id_path.exists():
        ids = id_path.read_text().split()
        selected = fresh_pool.set_index("pair_id").loc[ids].reset_index()
        source = "loaded_saved_ids"
    else:
        # A different seed offset from experiment 2's draw (seed + 2).
        selected = fresh_pool.sample(n=config["sets"]["sealed"], random_state=seed + 300)
        selected = selected.sort_values("pair_id").reset_index(drop=True)
        id_path.write_text("\n".join(selected["pair_id"]) + "\n")
        source = "sampled_and_saved"
    selected = orient(selected, seed + 3_000)
    selected.to_csv(pairs_dir / "sealed.csv", index=False)

    hashes = {name: set(pd.read_csv(pairs_dir / f"{name}.csv")["prompt_hash"]) for name in ("practice", "gate", "sealed")}
    exp2_sealed = set(pd.read_csv(exp2_pairs / "sealed.csv", dtype={"pair_id": str})["pair_id"])
    report = {
        "filters": counts,
        "fresh_sealed": {
            "pool_pairs_in_sealed_buckets": len(pool),
            "excluded_experiment2_sealed": len(used),
            "fresh_pool": len(fresh_pool),
            "pairs_saved": len(selected),
            "ids": source,
            "winner_is_x": float((selected["winner"] == "X").mean()),
            "overlap_with_experiment2_sealed_pairs": len(set(selected["pair_id"]) & exp2_sealed),
            "prompt_overlap_with_practice": len(hashes["sealed"] & hashes["practice"]),
            "prompt_overlap_with_gate": len(hashes["sealed"] & hashes["gate"]),
        },
    }
    if any(report["fresh_sealed"][k] for k in (
        "overlap_with_experiment2_sealed_pairs", "prompt_overlap_with_practice", "prompt_overlap_with_gate")):
        raise RuntimeError(f"fresh sealed set overlaps: {report['fresh_sealed']}")
    (pairs_dir / "prep_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["fresh_sealed"], indent=2))


if __name__ == "__main__":
    main()
