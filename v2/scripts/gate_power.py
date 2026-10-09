"""A4 and A5 for the skill loop redesign (no model calls).

    .venv/bin/python scripts/gate_power.py

A4: simulate a fix that does nothing (a null fix) and count how often the targeted test "keeps" it,
    when target tasks are chosen (a) by past failure (the current version missed a targeted check) or
    (b) by a task property (the task defines a check of that kind). Selecting on past failure and then
    comparing against that same run is regression to the mean; this measures the bias.
A5: from the pilot's logged gate runs (version 0 vs fix A, 40 tasks, temperature 0.7), estimate how
    often the redesigned keep rule would keep fix A, by resampling tasks. Replays each run to recover
    every check's result, since the pilot logged only missed checks.
Writes phase1/gate_power.json.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from scipy.stats import wilcoxon  # noqa: E402

from jevloop import bench  # noqa: E402
from jevloop.runs import CandidateRun  # noqa: E402
from jevloop.skill_loop import keep_rule  # noqa: E402

P = 0.10


def targeted_test(cur: list[float], cand: list[float]) -> bool:
    diffs = [b - a for a, b in zip(cur, cand)]
    nonzero = [d for d in diffs if d != 0]
    if not nonzero or sum(diffs) <= 0:
        return False
    return float(wilcoxon(nonzero, alternative="greater").pvalue) < P


def simulate_a4(sims: int = 2000, tasks: int = 60, seed: int = 20261008) -> dict:
    rng = random.Random(seed)
    keeps = {"by_past_failure": 0, "by_task_property": 0}
    for _ in range(sims):
        cur, cand, failed = [], [], []
        for _ in range(tasks):
            n = rng.randint(1, 5)  # checks of the targeted kind in this task
            p = rng.uniform(0.2, 0.95)  # this task's chance of meeting each check; same for both versions (null)
            a = sum(rng.random() < p for _ in range(n)) / n
            b = sum(rng.random() < p for _ in range(n)) / n
            cur.append(a); cand.append(b); failed.append(a < 1)
        keeps["by_task_property"] += targeted_test(cur, cand)
        idx = [i for i, f in enumerate(failed) if f]
        keeps["by_past_failure"] += targeted_test([cur[i] for i in idx], [cand[i] for i in idx])
    return {"sims": sims, "tasks": tasks, "nominal_level": P, "false_keep_rate": {k: v / sims for k, v in keeps.items()}}


def load_runs(path: Path) -> dict[str, dict]:
    return {json.loads(l)["task_id"]: json.loads(l) for l in path.read_text().splitlines()}


def regraded(task: bench.Task, record: dict) -> CandidateRun:
    """Replay the run's calls on a fresh world and grade again, to get every check's result."""
    world = bench.new_world(task)
    for c in record["calls"]:
        bench.call_tool(world, c["name"], c["args"])
    g = bench.grade(task, world)
    fields = {k: v for k, v in record.items() if k in CandidateRun.__dataclass_fields__}
    fields.update(partial_credit=g.partial_credit, passed=g.passed, checks=[dict(c) for c in g.checks])
    return CandidateRun(**fields)


def estimate_a5(boot: int = 2000, seed: int = 20261008) -> dict:
    logs = ROOT / "logs" / "phase1"
    v0_path = logs / "pilot-v0-gate.jsonl"
    rnd1 = json.loads((ROOT / "phase1" / "pilot" / "round_1.json").read_text())
    fix_a = max(rnd1["gate_candidates"], key=lambda c: c["decision"]["mean_diff"])
    from jevloop.skill_loop import apply_edit, Edit, version_id
    vid = version_id(apply_edit((), Edit(**{k: fix_a["edit"][k] for k in ("op", "index", "text", "why")})))
    a_path = logs / f"pilot-{vid}-gate.jsonl"
    if not (v0_path.exists() and a_path.exists()):
        return {"available": False, "note": "pilot gate logs not found locally"}
    tasks = {t.task_id: t for t in bench.load_tasks(["finance", "hr"])}
    v0_raw, a_raw = load_runs(v0_path), load_runs(a_path)
    ids = sorted(set(v0_raw) & set(a_raw))
    v0, fa, reproduced = {}, {}, 0
    for t in ids:
        v0[t], fa[t] = regraded(tasks[t], v0_raw[t]), regraded(tasks[t], a_raw[t])
        reproduced += (abs(v0[t].partial_credit - v0_raw[t]["partial_credit"]) < 1e-9 and
                       abs(fa[t].partial_credit - a_raw[t]["partial_credit"]) < 1e-9)
    ids = [t for t in ids if abs(v0[t].partial_credit - v0_raw[t]["partial_credit"]) < 1e-9
           and abs(fa[t].partial_credit - a_raw[t]["partial_credit"]) < 1e-9]
    rng = random.Random(seed)
    out = {"available": True, "fix": fix_a["edit"]["text"], "tasks_reproduced_on_replay": f"{len(ids)} of {len(v0_raw)}",
           "observed_credit_gain": sum(fa[t].partial_credit - v0[t].partial_credit for t in ids) / len(ids),
           "keep_rate_by_target_kind": {}, "pilot_rule_keep_rate": None}
    for kind in ("action_missed", "rule_broken", "wrong_content"):
        keeps = 0
        for _ in range(boot):
            sample = [rng.choice(ids) for _ in ids]
            cur = {f"{t}#{i}": v0[t] for i, t in enumerate(sample)}
            cand = {f"{t}#{i}": fa[t] for i, t in enumerate(sample)}
            keeps += keep_rule(cur, cand, kind=kind, regression=[]).keep
        out["keep_rate_by_target_kind"][kind] = keeps / boot
    pilot_keeps = 0
    for _ in range(boot):
        sample = [rng.choice(ids) for _ in ids]
        pilot_keeps += targeted_test([v0[t].partial_credit for t in sample], [fa[t].partial_credit for t in sample])
    out["pilot_rule_keep_rate"] = pilot_keeps / boot
    out["note"] = ("Bootstrap over tasks assuming fix A's observed effect is its true effect, at temperature 0.7 "
                   "(noisier than the planned temperature 0), on 40 tasks (the redesign uses 60): conservative.")
    return out


def main() -> None:
    report = {"a4_target_selection": simulate_a4(), "a5_power": estimate_a5()}
    (ROOT / "phase1" / "gate_power.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
