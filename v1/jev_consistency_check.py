from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import yaml

from cache import DiskCache
from deciders import RubricQuestion
from gemini import load_env
from jev import OpenRouterJevClient
from log import JsonlLogger


ROOT = Path(__file__).resolve().parent


def main() -> None:
    load_env(ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_KEY is missing")
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    version0 = json.loads((ROOT / "results" / "version0.json").read_text())
    questions = [RubricQuestion(**item) for item in version0["rubric_questions"]]
    pairs = pd.read_csv(ROOT / "data" / "pairs" / "practice.csv").head(5)
    headlines = [headline for _, row in pairs.iterrows() for headline in (row["headline_x"], row["headline_y"])]
    run_id = "jev-consistency"
    client = OpenRouterJevClient(
        model=config["models"]["jev"], api_key=api_key,
        cache=DiskCache(ROOT / "cache" / "jev"),
        logger=JsonlLogger(ROOT / "logs" / f"{run_id}.jsonl"),
        retries=config["api"]["retries"], backoff_seconds=config["api"]["backoff_seconds"],
        expected_model=config["models"]["jev_expected_served"],
        expected_provider=config["models"]["jev_expected_provider"],
    )
    comparisons = []
    for index, headline in enumerate(headlines):
        answers = []
        for repeat in (1, 2):
            answers.append(client.evaluate(
                headline, questions,
                {"run_id": run_id, "loop": "B", "round": 0, "set": "practice",
                 "pair_id": f"headline-{index}", "version_id": "v0",
                 "call_type": "consistency_check", "repeat": repeat},
                use_cache=False,
            ))
        differing = [q.question_id for q in questions if (answers[0][q.question_id] >= 0.5) != (answers[1][q.question_id] >= 0.5)]
        comparisons.append({"headline_index": index, "differing_questions": differing})
    disagreement_count = sum(len(item["differing_questions"]) for item in comparisons)
    mode = "repeated_calls" if disagreement_count else "reworded_questions"
    result = {
        "headlines": len(headlines), "questions": len(questions),
        "binary_disagreements": disagreement_count,
        "question_check_mode": mode,
        "comparisons": comparisons,
    }
    (ROOT / "results" / "jev_consistency_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
