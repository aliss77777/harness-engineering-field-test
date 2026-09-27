"""Read-only health check of a live run (monitor brief checks 1-10). Makes no API calls.

    python monitor.py --config config_arena.yaml --task task_arena.yaml --run-id arena-learn-20260926
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

from workspace import Workspace


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config_arena.yaml")
    parser.add_argument("--task", default="task_arena.yaml")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--low", type=float, default=0.35)
    parser.add_argument("--high", type=float, default=0.80)
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    lines = [json.loads(line) for line in (ws.path("logs") / f"{args.run_id}.jsonl").open()]
    issues: list[str] = []

    sealed = [i for i, r in enumerate(lines, 1) if r.get("set") == "sealed"]
    if sealed and not args.run_id.startswith("sealed"):
        issues.append(f"STOP: {len(sealed)} sealed entries in a learning log (first line {sealed[0]})")

    calls = [r for r in lines if "cached" in r and r.get("call_type") in (
        "decision_batch", "decision_single", "rubric_evaluation", "candidate_proposal",
        "question_rewording", "question_check")]
    failed = [r for r in lines if "error_type" in r]
    rate = len(failed) / max(len(calls) + len(failed), 1)
    if rate > 0.02:
        issues.append(f"STOP: call failure rate {rate:.1%}")

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in lines:
        if "correct" in r and "prediction" in r:
            groups[(r["loop"], r["round"], r["set"], r["version_id"])].append(r)
    expected = ws.config["sets"]
    print(f"calls ok {len(calls)} · failed {len(failed)} {dict(Counter(r.get('error_type') for r in failed))}")
    for key, records in groups.items():
        n = len(records)
        acc = sum(r["correct"] for r in records) / n
        ties = sum(bool(r["coin_flip_tie"]) for r in records) / n
        picks_x = sum(r["prediction"] == "X" for r in records) / n
        win_x = sum(r["winner"] == "X" for r in records) / n
        missing = sum(1 for r in records if (r["loop"] == "A" and not r.get("reason") and not r.get("blocked"))
                      or (r["loop"] == "B" and not r.get("questions")))
        blocked = sum(bool(r.get("blocked")) for r in records)
        print(f"{key}: n={n} blocked={blocked} acc={acc:.1%} picks_first={picks_x:.1%} winner_first={win_x:.1%} tie={ties:.1%}")
        if n != expected.get(key[2], n):
            issues.append(f"STOP: {key} has {n} pairs, expected {expected[key[2]]}")
        if missing:
            issues.append(f"STOP: {key} has {missing} records without reasons/probabilities")
        if key[0] == "B" and ties > 0.10:
            issues.append(f"STOP: {key} tie rate {ties:.1%}")
        if not args.low <= acc <= args.high:
            issues.append(f"CHECK: {key} accuracy {acc:.1%} outside {args.low:.0%}-{args.high:.0%}")
        if picks_x > 0.8 or picks_x < 0.2:
            issues.append(f"CHECK: {key} picks the first item {picks_x:.1%} of the time")

    for r in lines:
        if r.get("call_type") == "gate":
            print(f"GATE {r['loop']} r{r['round']} {r['candidate_id']}: {r['status']} "
                  f"b={r['b']} c={r['c']} p={r['p']} gate_acc={r['gate_accuracy']} vs {r['current_gate_accuracy']} · {r['change'][:90]}")
        elif r.get("call_type") == "candidate":
            print(f"CAND {r['loop']} r{r['round']} {r['candidate_id']}: {r['status']} · {str(r.get('change'))[:90]}")
    summary = ws.path("results") / "wip_summary.json"
    if summary.exists():
        wip = json.loads(summary.read_text())
        print(f"spend ${wip.get('spend_usd', 0):.2f} of ${wip.get('spend_cap_usd', 0):.0f}")
    print("ISSUES:" if issues else "HEALTHY: no issues")
    for issue in issues:
        print("  " + issue)


if __name__ == "__main__":
    main()
