"""Free diagnosis of why runs miss checks (no model calls).

    .venv/bin/python scripts/diagnose_failures.py

Replays each recorded run of the 3-model comparison (phase0/compare_task_ids.txt) through a
fresh copy of its world, grades it check by check, and sorts every missed check:
  - missed action:   a required email / record / update never happened
  - wrong content:   the action happened (e.g. an email to the right person) but required values were missing
  - forbidden action: a "must not" check broke (emailed someone excluded, logged a held invoice, ...)
Replays are only counted when they reproduce the recorded score (the simulator stamps fresh IDs,
so a run that reuses an ID it created may replay differently). Writes phase0/failure_diagnosis.json.
"""
import copy
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from automationbench.rubric import partial_credit  # noqa: E402
from automationbench.rubric.registry import AssertionRegistry  # noqa: E402

from jevloop import bench  # noqa: E402

LOGS = ROOT / "logs" / "phase0"
MODELS = ["gemini", "minimax", "deepseek"]
POLICY_WORDS = re.compile(r"polic|sop|guideline|procedure|process|rule|update|hold|do not|don't", re.I)


def runs_for(name: str, ids: list[str]) -> dict:
    found = {}
    for earlier in ("smoke", "reference", "compare"):
        path = LOGS / f"{earlier}-{name}-runs.jsonl"
        if path.exists():
            for line in path.read_text().splitlines():
                r = json.loads(line)
                if r.get("event") == "candidate_run" and r["candidate"] == 0 and r["task_id"] in ids:
                    found[r["task_id"]] = r
    return found


def check_results(task: bench.Task, calls: list[dict]):
    world = bench.new_world(task)
    for call in calls:
        bench.call_tool(world, call["name"], call["args"])
    state = {"info": {"assertions": [copy.deepcopy(a) for a in task.assertions]}, "world": world,
             "initial_state": copy.deepcopy(task.initial_state)}
    credit = partial_credit(state)
    return credit, state.get("_assertion_results", []), bench.world_snapshot(world)


def sent_to(snapshot: dict, address: str) -> bool:
    for m in (snapshot.get("gmail") or {}).get("messages", []):
        if "SENT" in (m.get("label_ids") or []):
            to = m.get("to") or []
            if address in (to if isinstance(to, list) else [to]):
                return True
    return False


def classify(result: dict, snapshot: dict) -> str:
    kind = result["type"]
    if AssertionRegistry.is_negative(kind):
        return "forbidden action"
    params = result.get("params") or {}
    if kind.startswith("gmail_") and ("body_contains" in params or "subject_contains" in params) and "to" in params:
        return "wrong content" if sent_to(snapshot, params["to"]) else "missed action"
    if "cell_contains" in params and kind.endswith("row_updated"):
        return "wrong content"  # the row exists from the start; the required values were not written
    return "missed action"


def policy_messages(task: bench.Task) -> list[str]:
    msgs = (task.initial_state.get("gmail") or {}).get("messages", [])
    return [m["id"] for m in msgs if POLICY_WORDS.search(f"{m.get('subject', '')} {m.get('body_plain', '')[:300]}")]


def read_ids(calls: list[dict]) -> set[str]:
    text = " ".join(f"{c['args'].get('url', '')} {c['args'].get('params', '')}" for c in calls if c["name"] == "api_fetch")
    return set(re.findall(r"[\w-]+", text))


def main() -> None:
    ids = (ROOT / "phase0" / "compare_task_ids.txt").read_text().split()
    tasks = {t.task_id: t for t in bench.load_tasks(["finance", "hr"])}
    report = {}
    for name in MODELS:
        runs = runs_for(name, ids)
        kinds, by_type, faithful, unfaithful = Counter(), Counter(), 0, []
        per_task = {}
        behaviour = defaultdict(list)
        for t in ids:
            r = runs[t]
            task = tasks[t]
            credit, results, snapshot = check_results(task, r["calls"])
            if abs(credit - r["partial_credit"]) > 1e-9:
                unfaithful.append(t)
                continue
            faithful += 1
            missed = [x for x in results if not x["passed"] and not x.get("excluded")]
            labels = [classify(x, snapshot) for x in missed]
            kinds.update(labels)
            by_type.update(x["type"] for x in missed)
            pol = policy_messages(task)
            seen = read_ids(r["calls"])
            writes = sum(1 for c in r["calls"] if c["name"] == "api_fetch" and str(c["args"].get("method", "")).upper() != "GET")
            behaviour["steps"].append(r["steps"])
            behaviour["writes"].append(writes)
            behaviour["read_all_policy_emails"].append(all(p in seen for p in pol) if pol else None)
            per_task[t] = {"credit": r["partial_credit"], "passed": r["passed"], "steps": r["steps"],
                           "stop": r["stop_reason"], "writes": writes, "missed": Counter(labels),
                           "policy_emails": len(pol), "read_policy_emails": sum(p in seen for p in pol)}
        pol_flags = [b for b in behaviour["read_all_policy_emails"] if b is not None]
        report[name] = {
            "runs_replayed_faithfully": faithful, "runs_not_reproduced": unfaithful,
            "missed_checks": sum(kinds.values()), "missed_by_kind": dict(kinds.most_common()),
            "missed_by_check_type": dict(by_type.most_common(10)),
            "mean_steps": sum(behaviour["steps"]) / max(1, faithful),
            "mean_write_calls": sum(behaviour["writes"]) / max(1, faithful),
            "runs_reading_every_policy_email": f"{sum(pol_flags)}/{len(pol_flags)}",
            "per_task": per_task,
        }
    (ROOT / "phase0" / "failure_diagnosis.json").write_text(json.dumps(report, indent=2, default=dict) + "\n")
    for name, r in report.items():
        total = r["missed_checks"] or 1
        kinds = ", ".join(f"{k} {v} ({v / total:.0%})" for k, v in r["missed_by_kind"].items())
        print(f"{name}: replayed {r['runs_replayed_faithfully']}/20 (not reproduced: {r['runs_not_reproduced']})")
        print(f"   missed checks {r['missed_checks']}: {kinds}")
        print(f"   steps {r['mean_steps']:.1f}, write calls {r['mean_write_calls']:.1f}, read every policy email: {r['runs_reading_every_policy_email']}")
        print(f"   top missed check types: {list(r['missed_by_check_type'].items())[:5]}")
    print("written: phase0/failure_diagnosis.json")


if __name__ == "__main__":
    main()
