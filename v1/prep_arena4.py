"""Experiment 4 sets: experiment 2's practice and gate (identical files, for fitting the
hybrid) and a fresh 1,000-pair sealed set ("sealed-4") that no system has ever seen.

Sealed-4 comes from the same prompt-hash buckets as the earlier sealed sets, excluding
every pair used by experiment 2's and experiment 3's sealed sets.
"""
from __future__ import annotations

import argparse
import json
import shutil

import pandas as pd

from prep_arena import assign_set, filter_battles, orient, prompt_bucket, to_candidates
from workspace import Workspace, read_pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare experiment 4 sets.")
    parser.add_argument("--config", default="config_arena4.yaml")
    parser.add_argument("--task", default="task_arena4.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, seed = ws.config, ws.config["seed"]
    components = config["components"]
    source = ws.root / components["source_pairs"]
    pairs_dir, split_dir = ws.path("pairs"), ws.path("splits")
    for name in ("practice", "gate"):
        shutil.copyfile(source / f"{name}.csv", pairs_dir / f"{name}.csv")

    used: set[str] = set()
    for path in components["used_sealed_ids"]:
        used |= set((ws.root / path).read_text().split())
    id_path = split_dir / "sealed_pair_ids.txt"
    raw = pd.read_csv(ws.root / ws.task["data"]["source"], low_memory=False)
    df, counts = filter_battles(raw, max_words=config["filters"]["max_response_words"])
    df["set"] = df["prompt_text"].map(lambda p: assign_set(prompt_bucket(p, seed), config["filters"]["split_fractions"]))
    pool = to_candidates(df)
    pool = pool[pool["set"] == "sealed"]
    fresh = pool[~pool["pair_id"].isin(used)]
    if id_path.exists():
        selected = fresh.set_index("pair_id").loc[id_path.read_text().split()].reset_index()
        how = "loaded_saved_ids"
    else:
        selected = fresh.sample(n=config["sets"]["sealed"], random_state=seed + 400)
        selected = selected.sort_values("pair_id").reset_index(drop=True)
        id_path.write_text("\n".join(selected["pair_id"]) + "\n")
        how = "sampled_and_saved"
    orient(selected, seed + 4_000).to_csv(pairs_dir / "sealed.csv", index=False)

    frames = {name: read_pairs(pairs_dir / f"{name}.csv") for name in ("practice", "gate", "sealed")}
    report = {
        "filters": counts,
        "sealed4": {
            "pool_pairs_in_sealed_buckets": len(pool), "excluded_earlier_sealed": len(used),
            "fresh_pool": len(fresh), "pairs_saved": len(frames["sealed"]), "ids": how,
            "winner_is_x": float((frames["sealed"]["winner"] == "X").mean()),
            "overlap_with_earlier_sealed_pairs": len(set(frames["sealed"]["pair_id"]) & used),
            "prompt_overlap_with_practice": len(set(frames["sealed"]["prompt_hash"]) & set(frames["practice"]["prompt_hash"])),
            "prompt_overlap_with_gate": len(set(frames["sealed"]["prompt_hash"]) & set(frames["gate"]["prompt_hash"])),
        },
    }
    checks = report["sealed4"]
    if checks["overlap_with_earlier_sealed_pairs"] or checks["prompt_overlap_with_practice"] or checks["prompt_overlap_with_gate"]:
        raise RuntimeError(f"sealed-4 overlaps: {checks}")
    (pairs_dir / "prep_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
