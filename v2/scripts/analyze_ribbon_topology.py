"""Exploratory topology audit for the AutomationBench policy ribbons.

Requires the pinned AutomationBench environment, scipy, and scikit-learn.

  PYTHONPATH=v2/src v2/.venv/bin/python v2/scripts/analyze_ribbon_topology.py \
      --logs /path/to/v2/logs/phase1_run

This reads task definitions and local run logs. It writes aggregate metrics and
an SVG only; no prompts, tool arguments, results, or assertions are exported.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import random
from pathlib import Path
import statistics

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from jevloop.bench import load_tasks, task_check_kinds
from jevloop.diagnostics import policy_messages
from explore_policy_visuals import (
    INK, MUTED, OUTPUT, READ, SEARCH, WRITE, counts, failed, kind,
    line, read_runs, rect, svg, text,
)


GATE_FILES = ("minimax-p1-v0-cp-bench.jsonl", "minimax-p1-s78766c8a-cp-bench.jsonl")
SEALED_FILES = ("minimax-p1-v0-cp-sealed.jsonl", "minimax-p1-s78766c8a-cp-sealed.jsonl")
FRESH_FILE = "minimax-p1-s78766c8a-cp-fresh.jsonl"


def feature_row(task) -> list[float]:
    kinds = task_check_kinds(task)
    return [
        kinds.get("wrong_content", 0) + kinds.get("action_missed", 0),
        kinds.get("rule_broken", 0),
        len(task.initial_state) - int("meta" in task.initial_state),
        len(policy_messages(task)),
        len(task.public.trigger.split()),
        int(task.public.domain == "hr"),
    ]


def action_motifs(run: dict) -> dict[str, int]:
    calls = run["calls"]
    sequence = [kind(call) for call in calls]
    first_write = next((index for index, action in enumerate(sequence) if action == "write"), len(sequence))
    return {
        "first_write_index": first_write,
        "write_to_write": sum(a == b == "write" for a, b in zip(sequence, sequence[1:])),
        "write_to_information": sum(a == "write" and b in {"search", "read"}
                                    for a, b in zip(sequence, sequence[1:])),
        "error_reads": sum(action == "read" and failed(call)
                           for action, call in zip(sequence, calls)),
    }


def paired(logs: Path, files: tuple[str, str], tasks: dict) -> list[dict]:
    first, last = (read_runs(logs / filename) for filename in files)
    if set(first) != set(last):
        raise ValueError("The paired runs must cover identical task IDs")
    result = []
    for task_id in sorted(first):
        a, b = first[task_id], last[task_id]
        before, after = counts(a), counts(b)
        before_motifs, after_motifs = action_motifs(a), action_motifs(b)
        result.append({
            "task_id": task_id,
            "before": a,
            "after": b,
            "length_change": len(b["calls"]) - len(a["calls"]),
            "credit_change": b["partial_credit"] - a["partial_credit"],
            "action_change": {kind: after[kind] - before[kind]
                              for kind in ("search", "read", "write", "other", "error")},
            "motif_change": {motif: after_motifs[motif] - before_motifs[motif]
                             for motif in before_motifs},
            "topology": feature_row(tasks[task_id]),
            "prompt": tasks[task_id].public.trigger,
        })
    return result


def shape_groups(rows: list[dict]) -> dict[str, dict]:
    groups = {"grow": [], "shrink": []}
    for row in rows:
        if row["credit_change"] <= 0 or row["length_change"] == 0:
            continue
        groups["grow" if row["length_change"] > 0 else "shrink"].append(row)
    result = {}
    for label, members in groups.items():
        result[label] = {
            "tasks": len(members),
            "mean_length_change": statistics.mean(row["length_change"] for row in members),
            "mean_credit_change": statistics.mean(row["credit_change"] for row in members),
            "mean_action_change": {kind: statistics.mean(row["action_change"][kind] for row in members)
                                   for kind in ("search", "read", "write", "other", "error")},
            "mean_motif_change": {motif: statistics.mean(row["motif_change"][motif] for row in members)
                                  for motif in ("first_write_index", "write_to_write",
                                                "write_to_information", "error_reads")},
        }
    return result


def auc_interval(labels: np.ndarray, scores: np.ndarray, *, seed: int = 20261016) -> list[float]:
    rng = random.Random(seed)
    estimates = []
    n = len(labels)
    for _ in range(2000):
        sample = [rng.randrange(n) for _ in range(n)]
        ys = labels[sample]
        if len(set(ys)) < 2:
            continue
        estimates.append(roc_auc_score(ys, scores[sample]))
    estimates.sort()
    return [estimates[int(0.025 * len(estimates))], estimates[int(0.975 * len(estimates)) - 1]]


def predict_growth(gate: list[dict], sealed: list[dict]) -> dict:
    train = [row for row in gate if row["length_change"]]
    test = [row for row in sealed if row["length_change"]]
    y = np.array([int(row["length_change"] > 0) for row in train])
    y_test = np.array([int(row["length_change"] > 0) for row in test])

    def evaluate(name: str, model, train_x, test_x) -> tuple[str, dict]:
        model.fit(train_x, y)
        probability = model.predict_proba(test_x)[:, 1]
        return name, {
            "auc_on_sealed": roc_auc_score(y_test, probability),
            "auc_interval_95_exploratory": auc_interval(y_test, probability),
            "balanced_accuracy_on_sealed": balanced_accuracy_score(y_test, probability >= 0.5),
        }

    topology_train = np.array([row["topology"] for row in train], dtype=float)
    topology_test = np.array([row["topology"] for row in test], dtype=float)
    before_train = np.array([[len(row["before"]["calls"])] for row in train], dtype=float)
    before_test = np.array([[len(row["before"]["calls"])] for row in test], dtype=float)
    models = [
        evaluate("task_topology", make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
                 topology_train, topology_test),
        evaluate("starting_ribbon_length", make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
                 before_train, before_test),
        evaluate("topology_plus_start_length", make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
                 np.column_stack([before_train, topology_train]), np.column_stack([before_test, topology_test])),
    ]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.8,
                                 stop_words="english", max_features=2000)
    train_text = vectorizer.fit_transform([row["prompt"] for row in train])
    test_text = vectorizer.transform([row["prompt"] for row in test])
    models.append(evaluate("prompt_tfidf", LogisticRegression(max_iter=1000, class_weight="balanced"),
                           train_text, test_text))
    return dict(models)


def repeatability(logs: Path, gate: list[dict]) -> dict:
    fresh: dict[str, dict[int, dict]] = defaultdict(dict)
    for raw in (logs / FRESH_FILE).open(encoding="utf-8"):
        run = json.loads(raw)
        fresh[run["task_id"]][run["candidate"]] = run
    if any(task_id not in fresh or set(fresh[task_id]) != {1, 2} for task_id in (r["task_id"] for r in gate)):
        raise ValueError("Expected two fresh same-policy runs for each gate task")
    policy_delta = []
    repeat_delta = []
    stable_direction = 0
    for row in gate:
        task_id = row["task_id"]
        baseline = len(row["before"]["calls"])
        variants = [row["after"], fresh[task_id][1], fresh[task_id][2]]
        lengths = [len(run["calls"]) for run in variants]
        policy_delta.append(lengths[0] - baseline)
        repeat_delta.append(lengths[2] - lengths[1])
        directions = {(length > baseline) - (length < baseline) for length in lengths}
        stable_direction += len(directions) == 1
    return {
        "tasks": len(gate),
        "median_abs_change_start_to_final": statistics.median(map(abs, policy_delta)),
        "median_abs_change_same_final_policy_repeats": statistics.median(map(abs, repeat_delta)),
        "growth_direction_stable_across_three_final_runs": stable_direction,
    }


def mechanisms_figure(gate: dict, sealed: dict) -> str:
    width, height = 1280, 585
    body = [text(36, 38, "Two ways an improved ribbon changes", size=23, weight=500),
            text(36, 65, "Mean change in tool calls among tasks whose final credit rose; positive bars add calls, negative bars remove them.",
                 size=13, color=MUTED)]
    for label, color, x in [("Search", SEARCH, 38), ("Read", READ, 136),
                            ("Write", WRITE, 226), ("Other", MUTED, 318)]:
        body += [rect(x, 83, 15, 15, fill=color), text(x + 22, 96, label, size=12)]
    center, scale = 635, 11
    for index, (name, group) in enumerate([
        ("Gate · growing", gate["grow"]), ("Gate · shortening", gate["shrink"]),
        ("Sealed · growing", sealed["grow"]), ("Sealed · shortening", sealed["shrink"]),
    ]):
        y = 139 + index * 108
        body += [text(38, y + 7, name, size=17, weight=500),
                 text(38, y + 28, f'{group["tasks"]} tasks · Δ credit {group["mean_credit_change"]:+.2f}',
                      size=12, color=MUTED),
                 line(center - 380, y + 53, center + 380, y + 53),
                 line(center, y + 35, center, y + 71, color=INK)]
        positive_x = center
        negative_x = center
        for kind, color in [("search", SEARCH), ("read", READ), ("write", WRITE), ("other", MUTED)]:
            change = group["mean_action_change"][kind]
            magnitude = abs(change) * scale
            if change >= 0:
                body += [rect(positive_x, y + 40, magnitude, 26, fill=color)]
                positive_x += magnitude
            else:
                negative_x -= magnitude
                body += [rect(negative_x, y + 40, magnitude, 26, fill=color)]
        body += [text(1050, y + 52, f'Δ calls {group["mean_length_change"]:+.1f}', size=14),
                 text(1050, y + 72, f'Δ tool errors {group["mean_action_change"]["error"]:+.1f}',
                      size=12, color=MUTED)]
    body += [text(36, 563, "Descriptive groups selected by credit improvement and ribbon direction; bars do not establish why credit changed.",
                  size=13, color=MUTED)]
    return svg(width, height, "Action mix changes for longer and shorter successful ribbons", body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True, type=Path, help="phase1_run log directory")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    tasks = {task.task_id: task for task in load_tasks(["finance", "hr"])}
    gate = paired(args.logs, GATE_FILES, tasks)
    sealed = paired(args.logs, SEALED_FILES, tasks)
    if len(gate) != 60 or len(sealed) != 80:
        raise SystemExit("Expected 60 gate and 80 sealed matched tasks")
    report = {
        "gate": shape_groups(gate),
        "sealed": shape_groups(sealed),
        "growth_prediction_gate_to_sealed": predict_growth(gate, sealed),
        "same_policy_repeatability_on_gate": repeatability(args.logs, gate),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "topology-audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output / "ribbon-mechanisms.svg").write_text(
        mechanisms_figure(report["gate"], report["sealed"]), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
