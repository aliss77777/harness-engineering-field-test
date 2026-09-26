from __future__ import annotations

import argparse
import html
import json
import math
import random
import re
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parent
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = html.unescape(str(value))
    return " ".join(TAG_RE.sub(" ", text).split())


def two_proportion_z(clicks_a: int, impressions_a: int, clicks_b: int, impressions_b: int) -> float:
    pooled = (clicks_a + clicks_b) / (impressions_a + impressions_b)
    variance = pooled * (1 - pooled) * (1 / impressions_a + 1 / impressions_b)
    if variance <= 0:
        return 0.0
    return abs(clicks_a / impressions_a - clicks_b / impressions_b) / math.sqrt(variance)


def _choose_comparable_group(test: pd.DataFrame, require_excerpt: bool) -> pd.DataFrame | None:
    fields = ["eyecatcher_id"] + (["excerpt_clean"] if require_excerpt else [])
    candidates: list[pd.DataFrame] = []
    for _, group in test.groupby(fields, dropna=False, sort=True):
        if group["headline_clean"].nunique() >= 2:
            candidates.append(group)
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda g: (-g["headline_clean"].nunique(), -len(g), str(g.index.min())),
    )[0]


def build_pairs(
    source: Path,
    *,
    seed: int,
    excluded_start: str,
    excluded_end: str,
    min_impressions: int,
    min_z_score: float,
    require_excerpt: bool = True,
) -> tuple[pd.DataFrame, dict[str, int]]:
    df = pd.read_csv(source, low_memory=False)
    counts = {"rows_loaded": len(df), "tests_loaded": df["clickability_test_id"].nunique()}

    df["created_at_parsed"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    start = pd.Timestamp(excluded_start, tz="UTC")
    end = pd.Timestamp(excluded_end, tz="UTC")
    df = df[~df["created_at_parsed"].between(start, end, inclusive="both")].copy()
    counts["tests_after_date_filter"] = df["clickability_test_id"].nunique()

    df["headline_clean"] = df["headline"].map(clean_text)
    df["excerpt_clean"] = df["excerpt"].map(clean_text)
    df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce")
    df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce")
    df = df[
        df["clickability_test_id"].notna()
        & df["eyecatcher_id"].notna()
        & df["headline_clean"].ne("")
        & df["impressions"].gt(0)
        & df["clicks"].ge(0)
    ].copy()

    comparable: list[pd.DataFrame] = []
    for _, test in df.groupby("clickability_test_id", sort=True):
        group = _choose_comparable_group(test, require_excerpt=require_excerpt)
        if group is not None:
            comparable.append(group)
    counts["tests_after_same_content_filter"] = len(comparable)

    rows: list[dict[str, object]] = []
    rng = random.Random(seed)
    for group in comparable:
        variants = group.drop_duplicates("headline_clean").copy()
        variants["click_rate"] = variants["clicks"] / variants["impressions"]
        variants = variants.sort_values(
            ["click_rate", "headline_clean"], ascending=[True, True]
        )
        low, high = variants.iloc[0], variants.iloc[-1]
        if min(low["impressions"], high["impressions"]) < min_impressions:
            continue
        z_score = two_proportion_z(
            int(high["clicks"]), int(high["impressions"]),
            int(low["clicks"]), int(low["impressions"]),
        )
        if z_score < min_z_score:
            continue
        shown = [high, low]
        rng.shuffle(shown)
        winner = "X" if shown[0]["headline_clean"] == high["headline_clean"] else "Y"
        test_id = str(high["clickability_test_id"])
        rows.append(
            {
                "pair_id": test_id,
                "test_id": test_id,
                "headline_x": shown[0]["headline_clean"],
                "headline_y": shown[1]["headline_clean"],
                "winner": winner,
                "z_score": z_score,
                "x_clicks": int(shown[0]["clicks"]),
                "x_impressions": int(shown[0]["impressions"]),
                "y_clicks": int(shown[1]["clicks"]),
                "y_impressions": int(shown[1]["impressions"]),
            }
        )
    counts["pairs_after_impressions_and_z"] = len(rows)
    return pd.DataFrame(rows).sort_values("pair_id").reset_index(drop=True), counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare fixed Upworthy headline pairs.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--task", default="task.yaml")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text())
    task = yaml.safe_load((ROOT / args.task).read_text())
    output_dir = ROOT / "data" / "pairs"
    output_dir.mkdir(parents=True, exist_ok=True)
    split_dir = ROOT / "data" / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {}
    for index, set_name in enumerate(("practice", "gate", "sealed")):
        pairs, counts = build_pairs(
            ROOT / task["data"][set_name],
            seed=config["seed"] + index,
            excluded_start=str(config["filters"]["excluded_start"]),
            excluded_end=str(config["filters"]["excluded_end"]),
            min_impressions=config["filters"]["min_impressions"],
            min_z_score=config["filters"]["min_z_score"],
        )
        requested = config["sets"][set_name]
        if len(pairs) < requested:
            pairs, counts = build_pairs(
                ROOT / task["data"][set_name],
                seed=config["seed"] + index,
                excluded_start=str(config["filters"]["excluded_start"]),
                excluded_end=str(config["filters"]["excluded_end"]),
                min_impressions=config["filters"]["min_impressions"],
                min_z_score=config["filters"]["fallback_z_score"],
            )
            counts["used_fallback_z_score"] = 1
        selected = pairs.sample(
            n=min(requested, len(pairs)), random_state=config["seed"] + index
        ).sort_values("pair_id").reset_index(drop=True)
        selected.to_csv(output_dir / f"{set_name}.csv", index=False)
        (split_dir / f"{set_name}_pair_ids.txt").write_text(
            "\n".join(selected["pair_id"].astype(str)) + "\n"
        )
        counts["pairs_saved"] = len(selected)
        report[set_name] = counts
        print(f"{set_name}: {json.dumps(counts, sort_keys=True)}")

    (output_dir / "prep_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
