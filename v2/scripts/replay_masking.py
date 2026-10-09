"""Work item B: would a "read the policies before the first write" check have flagged the bad runs? ($0)

    .venv/bin/python scripts/replay_masking.py

Rule and thresholds: action_masking/replay/PREREGISTRATION.md (committed before this ran).
Reads every logged run with a tool-call trace, replays it on a fresh world, grades it check by check,
applies Checkpoint 0 at the first record-changing call, and reports coverage, firing rate, precision
and recall. Also checks how many broken "must not" checks a simple matcher can tie to one call.
Writes action_masking/replay/replay_results.json and REPORT.md.
"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import bench  # noqa: E402
from jevloop.diagnostics import first_write_index, is_write, policy_messages, read_policy_before_first_write  # noqa: E402

OUT = ROOT / "action_masking" / "replay"


def family(agent: str) -> str:
    return next((m for m in ("minimax", "gemini", "deepseek", "nemotron") if agent.startswith(m)), agent)


def load_runs() -> list[dict]:
    seen, runs = set(), []
    # Agent runs logged before the replay: v2 Phase 0 and the v2 Phase 1 pilot. Excluded: the do-nothing
    # baseline (not an agent) and the temperature-0 re-checks (logs/harness), which were still running.
    files = sorted(glob.glob(str(ROOT / "logs" / "phase0" / "*-runs.jsonl")) + glob.glob(str(ROOT / "logs" / "phase1" / "pilot-*.jsonl")))
    for f in files:
        if "calls" in f:
            continue
        for line in open(f):
            r = json.loads(line)
            if r.get("event") != "candidate_run" or not r["task_id"].startswith(("finance:", "hr:")):
                continue
            key = (r["agent"], r["task_id"], json.dumps(r["calls"], sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            runs.append(r)
    return runs


def regrade(task: bench.Task, calls: list[dict]):
    world = bench.new_world(task)
    for c in calls:
        bench.call_tool(world, c["name"], c["args"])
    return bench.grade(task, world)


def mappable(check: dict, calls: list[dict]) -> bool:
    """Can a simple matcher tie this broken "must not" check to a specific write? (recipient, field or value)"""
    values = [v for v in (check.get("params") or {}).values() if isinstance(v, str) and len(v) >= 4]
    for c in calls:
        if is_write(c):
            blob = json.dumps(c["args"], ensure_ascii=False).lower()
            if any(v.lower() in blob for v in values):
                return True
    return False


def rates(rows: list[dict], outcome: str) -> dict:
    fired = [r for r in rows if r["fires"]]
    bad = [r for r in rows if r[outcome]]
    tp = sum(r[outcome] for r in fired)
    return {"runs": len(rows), "fires": len(fired), "outcome_runs": len(bad),
            "precision": tp / len(fired) if fired else None, "recall": tp / len(bad) if bad else None,
            "base_rate": len(bad) / len(rows) if rows else None}


def main() -> None:
    tasks = {t.task_id: t for t in bench.load_tasks(["finance", "hr"])}
    runs = load_runs()
    rows, map_total, map_hit = [], defaultdict(int), defaultdict(int)
    reproduced = 0
    for r in runs:
        task = tasks[r["task_id"]]
        g = regrade(task, r["calls"])
        reproduced += abs(g.partial_credit - r["partial_credit"]) < 1e-9
        broken = [m for m in g.missed if m["negative"]]
        for m in broken:
            map_total[m["type"]] += 1
            map_hit[m["type"]] += mappable(m, r["calls"])
        has_policy = bool(policy_messages(task))
        read_first = read_policy_before_first_write(task, r["calls"])
        writes = first_write_index(r["calls"]) is not None
        rows.append({"model": family(r["agent"]), "task_id": r["task_id"], "has_policy": has_policy,
                     "writes": writes, "fires": bool(has_policy and writes and read_first is False),
                     "broke_must_not": bool(broken), "credit_below_half": g.partial_credit < 0.5,
                     "credit": g.partial_credit})
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model"]].append(row)
    summary = {}
    for model, rs in sorted(by_model.items()):
        summary[model] = {"runs": len(rs), "coverage": sum(r["has_policy"] for r in rs) / len(rs),
                          "fire_rate": sum(r["fires"] for r in rs) / len(rs),
                          "broke_must_not": rates(rs, "broke_must_not"), "credit_below_half": rates(rs, "credit_below_half"),
                          "mean_credit_fired": (sum(r["credit"] for r in rs if r["fires"]) / max(1, sum(r["fires"] for r in rs))),
                          "mean_credit_not_fired": (sum(r["credit"] for r in rs if not r["fires"]) / max(1, sum(not r["fires"] for r in rs)))}
    mm = summary.get("minimax", {}).get("broke_must_not", {})
    go = bool(mm.get("precision") is not None and mm["precision"] >= 0.6 and mm.get("recall") is not None and mm["recall"] >= 0.25)
    mapping = {t: {"broken": map_total[t], "tied_to_a_call": map_hit[t], "share": map_hit[t] / map_total[t]} for t in sorted(map_total)}
    total_b, total_h = sum(map_total.values()), sum(map_hit.values())
    result = {"runs_replayed": len(runs), "runs_reproducing_their_score": reproduced, "by_model": summary,
              "go": go, "go_rule": "MiniMax: precision >= 0.6 and recall >= 0.25 for 'broke a must-not check'",
              "label_mapping": {"by_check_type": mapping, "overall_share": total_h / total_b if total_b else None, "broken_checks": total_b},
              "detector": "approximate (keyword-based; A2 labels pending)"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "replay_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "label_mapping"} | {"label_mapping_overall": result["label_mapping"]["overall_share"]}, indent=1))


if __name__ == "__main__":
    main()
