"""Experiment 6 data: Upworthy tests with 3+ comparable headlines, as bandit decisions.

One test = one story shown with several headlines to randomly assigned readers. Keep the
largest group of variants sharing an image and excerpt; drop variants under the impression
floor; require >= min_arms distinct headlines (duplicates' clicks and impressions summed);
cap at max_arms (seeded sample). Each headline's click rate is its reward.
Sets come from separate source files, so no test appears twice.
"""
from __future__ import annotations

import argparse
import json
import random

import pandas as pd

from prep import clean_text
from workspace import Workspace


def build_tests(path, *, excluded_start: str, excluded_end: str, min_impressions: int,
                min_arms: int, max_arms: int, seed: int) -> tuple[list[dict], dict[str, int]]:
    df = pd.read_csv(path, low_memory=False)
    counts = {"rows_loaded": len(df), "tests_loaded": int(df["clickability_test_id"].nunique())}
    when = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df = df[~when.between(pd.Timestamp(excluded_start, tz="UTC"), pd.Timestamp(excluded_end, tz="UTC"))].copy()
    counts["tests_after_date_filter"] = int(df["clickability_test_id"].nunique())
    df["headline_clean"] = df["headline"].map(clean_text)
    df["excerpt_clean"] = df["excerpt"].map(clean_text)
    df = df[df["eyecatcher_id"].notna() & df["headline_clean"].ne("") & (df["impressions"] >= min_impressions)]
    counts["tests_with_variants_over_impression_floor"] = int(df["clickability_test_id"].nunique())
    tests = []
    for test_id, test in df.groupby("clickability_test_id", sort=True):
        best = None
        for _, group in test.groupby(["eyecatcher_id", "excerpt_clean"], dropna=False, sort=True):
            arms = group.groupby("headline_clean")[["clicks", "impressions"]].sum()
            if len(arms) >= min_arms and (best is None or len(arms) > len(best)):
                best = arms
        if best is None:
            continue
        rows = sorted(best.itertuples(), key=lambda r: r.Index)
        rng = random.Random(f"{seed}:{test_id}")
        if len(rows) > max_arms:
            rows = rng.sample(rows, max_arms)
        rng.shuffle(rows)  # seeded display order, independent of outcome
        tests.append({
            "test_id": str(test_id),
            "headlines": [r.Index for r in rows],
            "clicks": [int(r.clicks) for r in rows],
            "impressions": [int(r.impressions) for r in rows],
            "ctr": [r.clicks / r.impressions for r in rows],
        })
    counts["tests_with_3plus_arms"] = len(tests)
    return tests, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare experiment 6 bandit tests.")
    parser.add_argument("--config", default="config_upworthy6.yaml")
    parser.add_argument("--task", default="task_upworthy6.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config = ws.config
    filters = config["filters"]
    out_dir, split_dir = ws.path("pairs"), ws.path("splits")
    report = {}
    for index, set_name in enumerate(("practice", "gate", "sealed")):
        tests, counts = build_tests(
            ws.root / ws.task["data"][set_name], excluded_start=str(filters["excluded_start"]),
            excluded_end=str(filters["excluded_end"]), min_impressions=filters["min_impressions"],
            min_arms=filters["min_arms"], max_arms=filters["max_arms"], seed=config["seed"])
        id_path = split_dir / f"{set_name}_test_ids.txt"
        by_id = {t["test_id"]: t for t in tests}
        if id_path.exists():
            chosen = [by_id[i] for i in id_path.read_text().split()]
            how = "loaded_saved_ids"
        else:
            wanted = config["sets"][set_name]
            chosen = random.Random(config["seed"] + index).sample(sorted(tests, key=lambda t: t["test_id"]), wanted)
            id_path.write_text("\n".join(t["test_id"] for t in chosen) + "\n")
            how = "sampled_and_saved"
        with (out_dir / f"{set_name}.jsonl").open("w") as handle:
            for test in chosen:
                handle.write(json.dumps(test) + "\n")
        arms = [len(t["headlines"]) for t in chosen]
        counts.update(tests_saved=len(chosen), ids=how, median_arms=sorted(arms)[len(arms) // 2],
                      max_arms=max(arms))
        report[set_name] = counts
        print(set_name, json.dumps(counts))
    (out_dir / "prep_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
