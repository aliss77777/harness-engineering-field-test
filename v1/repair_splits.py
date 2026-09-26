from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import yaml

from prep import ROOT, build_pairs, headline_keys, load_locked_ids, select_locked_pairs


def eligible_pairs(config: dict, task: dict, set_name: str, index: int) -> pd.DataFrame:
    common = dict(
        seed=config["seed"] + index,
        excluded_start=str(config["filters"]["excluded_start"]),
        excluded_end=str(config["filters"]["excluded_end"]),
        min_impressions=config["filters"]["min_impressions"],
    )
    pairs, _ = build_pairs(
        ROOT / task["data"][set_name],
        min_z_score=config["filters"]["min_z_score"],
        **common,
    )
    if len(pairs) < config["sets"][set_name]:
        pairs, _ = build_pairs(
            ROOT / task["data"][set_name],
            min_z_score=config["filters"]["fallback_z_score"],
            **common,
        )
    return pairs.assign(pair_id=pairs["pair_id"].astype(str))


def repair_set(
    candidates: pd.DataFrame,
    current_ids: list[str],
    protected_headlines: set[str],
    requested: int,
    seed: int,
) -> tuple[list[str], pd.DataFrame, dict[str, int]]:
    current = select_locked_pairs(candidates, current_ids, "repair")
    conflicts = current.apply(
        lambda row: bool(
            {str(row["headline_x"]).casefold(), str(row["headline_y"]).casefold()}
            & protected_headlines
        ),
        axis=1,
    )
    kept = current.loc[~conflicts].copy()
    used_ids = set(current_ids)
    pool = candidates.loc[~candidates["pair_id"].isin(used_ids)].sample(
        frac=1, random_state=seed
    )
    additions = []
    for _, row in pool.iterrows():
        keys = {str(row["headline_x"]).casefold(), str(row["headline_y"]).casefold()}
        if keys & protected_headlines:
            continue
        additions.append(row)
        if len(kept) + len(additions) == requested:
            break
    if len(kept) + len(additions) != requested:
        raise RuntimeError("not enough non-overlapping unused pairs to refill split")
    repaired = pd.concat([kept, pd.DataFrame(additions)], ignore_index=True)
    repaired = repaired.sort_values("pair_id").reset_index(drop=True)
    return (
        repaired["pair_id"].astype(str).tolist(),
        repaired,
        {"removed_for_overlap": int(conflicts.sum()), "refilled_from_unused": len(additions)},
    )


def main() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    task = yaml.safe_load((ROOT / "task.yaml").read_text())
    split_dir = ROOT / "data" / "splits"
    backup_dir = split_dir / "pre_overlap_repair"
    backup_dir.mkdir(parents=True, exist_ok=True)

    paths = {name: split_dir / f"{name}_pair_ids.txt" for name in ("practice", "gate", "sealed")}
    for name, path in paths.items():
        backup = backup_dir / path.name
        if not backup.exists():
            shutil.copy2(path, backup)

    original_sealed = paths["sealed"].read_bytes()
    candidates = {
        name: eligible_pairs(config, task, name, index)
        for index, name in enumerate(("practice", "gate", "sealed"))
    }
    sealed = select_locked_pairs(candidates["sealed"], load_locked_ids(paths["sealed"]), "sealed")

    gate_ids, gate, gate_report = repair_set(
        candidates["gate"],
        load_locked_ids(paths["gate"]),
        headline_keys(sealed),
        config["sets"]["gate"],
        config["seed"] + 1,
    )
    practice_ids, practice, practice_report = repair_set(
        candidates["practice"],
        load_locked_ids(paths["practice"]),
        headline_keys(sealed) | headline_keys(gate),
        config["sets"]["practice"],
        config["seed"],
    )

    paths["gate"].write_text("\n".join(gate_ids) + "\n")
    paths["practice"].write_text("\n".join(practice_ids) + "\n")
    if paths["sealed"].read_bytes() != original_sealed:
        raise RuntimeError("sealed split changed")

    report = {
        "sealed": {"changed": False, "pairs": len(sealed)},
        "gate": gate_report,
        "practice": practice_report,
        "seed": config["seed"],
    }
    (split_dir / "overlap_repair_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
