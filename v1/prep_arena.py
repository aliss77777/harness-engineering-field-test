from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import pandas as pd

from workspace import Workspace


SETS = ("practice", "gate", "sealed")


def parse_turns(value: object) -> list | None:
    """Arena text fields are JSON-encoded lists of turns; None when unparseable."""
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, list) else None


def word_count(text: str) -> int:
    return len(text.split())


def prompt_bucket(prompt: str, seed: int) -> float:
    """Stable position in [0, 1) for a prompt, so a prompt lands in exactly one set."""
    digest = hashlib.sha256(f"{seed}:{prompt.strip()}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / 16**12


def assign_set(bucket: float, fractions: dict[str, float]) -> str:
    edge = 0.0
    for set_name in SETS:
        edge += fractions[set_name]
        if bucket < edge:
            return set_name
    return SETS[-1]


def balanced_winner_first(pair_ids: list[str], seed: int) -> dict[str, bool]:
    """Seeded order with the winner shown first in exactly half the pairs of a set.

    Per-pair coin flips left practice at 44% winner-first (p = 0.01); balancing
    removes position skew as an explanation for any result.
    """
    shuffled = sorted(pair_ids)
    random.Random(seed).shuffle(shuffled)
    first = set(shuffled[: len(shuffled) // 2])
    return {pair_id: pair_id in first for pair_id in pair_ids}


def filter_battles(raw: pd.DataFrame, *, max_words: int) -> tuple[pd.DataFrame, dict[str, int]]:
    counts: dict[str, int] = {"1_rows_loaded": len(raw)}
    df = raw[raw["winner_tie"] == 0].copy()
    counts["2_after_drop_ties"] = len(df)

    for column in ("prompt", "response_a", "response_b"):
        df[f"{column}_turns"] = df[column].map(parse_turns)
    multi_turn = df.apply(
        lambda row: any(
            turns is not None and len(turns) != 1
            for turns in (row["prompt_turns"], row["response_a_turns"], row["response_b_turns"])
        ),
        axis=1,
    )
    df = df[~multi_turn].copy()
    counts["3_after_single_turn"] = len(df)

    def usable(turns: list | None) -> bool:
        return turns is not None and isinstance(turns[0], str) and turns[0].strip() != ""

    parsed = df.apply(
        lambda row: all(usable(row[f"{c}_turns"]) for c in ("prompt", "response_a", "response_b")),
        axis=1,
    )
    df = df[parsed].copy()
    counts["4_after_drop_empty_or_unparseable"] = len(df)

    df["prompt_text"] = df["prompt_turns"].map(lambda t: t[0].strip())
    df["response_a_text"] = df["response_a_turns"].map(lambda t: t[0].strip())
    df["response_b_text"] = df["response_b_turns"].map(lambda t: t[0].strip())
    df["words_a"] = df["response_a_text"].map(word_count)
    df["words_b"] = df["response_b_text"].map(word_count)
    df = df[(df["words_a"] <= max_words) & (df["words_b"] <= max_words)].copy()
    counts["5_after_length_cap"] = len(df)
    # Step 6 (hide model names) removes no rows: model columns are never written to pair files.
    counts["6_after_hiding_model_names"] = len(df)
    return df, counts


def to_candidates(df: pd.DataFrame) -> pd.DataFrame:
    a_won = df["winner_model_a"].astype(int) == 1
    return pd.DataFrame({
        "pair_id": df["id"].astype(str).values,
        "prompt": df["prompt_text"].values,
        "winning_response": df["response_a_text"].where(a_won, df["response_b_text"]).values,
        "losing_response": df["response_b_text"].where(a_won, df["response_a_text"]).values,
        "words_winning": df["words_a"].where(a_won, df["words_b"]).values,
        "words_losing": df["words_b"].where(a_won, df["words_a"]).values,
        "prompt_hash": df["prompt_text"].map(
            lambda p: hashlib.sha256(p.encode("utf-8")).hexdigest()[:16]
        ).values,
        "set": df["set"].values,
    })


def orient(selected: pd.DataFrame, seed: int) -> pd.DataFrame:
    winner_first = balanced_winner_first(list(selected["pair_id"]), seed)
    first = selected["pair_id"].map(winner_first)
    return pd.DataFrame({
        "pair_id": selected["pair_id"],
        "prompt": selected["prompt"],
        "response_x": selected["winning_response"].where(first, selected["losing_response"]),
        "response_y": selected["losing_response"].where(first, selected["winning_response"]),
        "winner": first.map({True: "X", False: "Y"}),
        "words_x": selected["words_winning"].where(first, selected["words_losing"]),
        "words_y": selected["words_losing"].where(first, selected["words_winning"]),
        "prompt_hash": selected["prompt_hash"],
    }).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare fixed Arena response pairs.")
    parser.add_argument("--config", default="config_arena.yaml")
    parser.add_argument("--task", default="task_arena.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    config, task = ws.config, ws.task
    seed = config["seed"]

    raw = pd.read_csv(ws.root / task["data"]["source"], low_memory=False)
    df, counts = filter_battles(raw, max_words=config["filters"]["max_response_words"])
    for step, count in counts.items():
        print(f"{step}: {count}")

    fractions = config["filters"]["split_fractions"]
    df["set"] = df["prompt_text"].map(lambda p: assign_set(prompt_bucket(p, seed), fractions))
    pairs = to_candidates(df)

    split_dir = ws.path("splits")
    pairs_dir = ws.path("pairs")
    report: dict[str, object] = {"filters": counts, "sets": {}}
    for index, set_name in enumerate(SETS):
        pool = pairs[pairs["set"] == set_name]
        id_path = split_dir / f"{set_name}_pair_ids.txt"
        if id_path.exists():
            # Never resample: reuse the saved IDs and fail loudly if any is missing.
            ids = id_path.read_text().split()
            selected = pool.set_index("pair_id").loc[ids].reset_index()
            source = "loaded_saved_ids"
        else:
            selected = pool.sample(n=config["sets"][set_name], random_state=seed + index)
            selected = selected.sort_values("pair_id").reset_index(drop=True)
            id_path.write_text("\n".join(selected["pair_id"]) + "\n")
            source = "sampled_and_saved"
        selected = orient(selected, seed + 1_000 + index)
        selected.to_csv(pairs_dir / f"{set_name}.csv", index=False)
        report["sets"][set_name] = {
            "pool_pairs": len(pool),
            "pool_prompts": int(pool["prompt_hash"].nunique()),
            "pairs_saved": len(selected),
            "ids": source,
            "winner_is_x": round(float((selected["winner"] == "X").mean()), 4),
            "median_words_x": float(selected["words_x"].median()),
            "median_words_y": float(selected["words_y"].median()),
        }
        print(f"{set_name}: {json.dumps(report['sets'][set_name])}")

    hashes = {name: set(pd.read_csv(pairs_dir / f"{name}.csv")["prompt_hash"]) for name in SETS}
    overlaps = {
        f"{a}_{b}": len(hashes[a] & hashes[b]) for i, a in enumerate(SETS) for b in SETS[i + 1:]
    }
    report["prompt_overlap_between_sets"] = overlaps
    if any(overlaps.values()):
        raise RuntimeError(f"prompt appears in two sets: {overlaps}")
    print(f"prompt overlap between sets: {overlaps}")
    (pairs_dir / "prep_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
