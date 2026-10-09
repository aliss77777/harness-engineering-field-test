"""Temperature-0 re-checks (roadmap step 1; Skill loop redesign change 1). Paid; capped at $10.

    .venv/bin/python scripts/harness_rechecks.py

1. Repeatability: MiniMax at temperature 0, two independent runs (attempts 0 and 1, so separate cache
   entries) on 10 of the 20 Phase 0 comparison tasks.
2. Comparison: MiniMax and Gemini at temperature 0 on all 20 comparison tasks, one run each, under
   the preregistered comparability rule (credit within 10 points, under 10% failed runs).
MiniMax's attempt-0 runs serve both checks. Writes results/harness/rechecks.json and
phase0/temperature0_rechecks.json. Finished runs reload from the logs on a rerun.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import bench  # noqa: E402
from jevloop.cache import DiskCache  # noqa: E402
from jevloop.feasibility import comparability, summarize_model  # noqa: E402
from jevloop.llm_agent import LLMAgent  # noqa: E402
from jevloop.log import JsonlLogger  # noqa: E402
from jevloop.openrouter import ChatClient  # noqa: E402
from jevloop.runs import CandidateRun, run_candidate  # noqa: E402
from jevloop.spend import SpendTracker  # noqa: E402

CFG = yaml.safe_load((ROOT / "phase0" / "config_phase0.yaml").read_text())
CAP_USD = 10.0
TEMPERATURE = 0.0
LOGS = ROOT / "logs" / "harness"
COST_ESTIMATE = {"minimax": 0.06, "gemini": 0.36}


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_KEY missing")


def load(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            out[(r["task_id"], r["candidate"])] = CandidateRun(**{k: v for k, v in r.items() if k in CandidateRun.__dataclass_fields__})
    return out


def main() -> None:
    ids = (ROOT / "phase0" / "compare_task_ids.txt").read_text().split()
    repeat_ids = [t for t in ids if t.startswith("finance:")][:5] + [t for t in ids if t.startswith("hr:")][:5]
    tasks = {t.task_id: t for t in bench.load_tasks(["finance", "hr"])}
    spend = SpendTracker(ROOT / "results" / "harness" / "rechecks_spend.json", cap_usd=CAP_USD, flush_seconds=0)
    jobs = [("minimax", t, 0) for t in ids] + [("minimax", t, 1) for t in repeat_ids] + [("gemini", t, 0) for t in ids]
    done = {name: load(LOGS / f"rechecks-{name}-t0.jsonl") for name in ("minimax", "gemini")}
    todo = [j for j in jobs if (j[1], j[2]) not in done[j[0]]]
    projected = sum(COST_ESTIMATE[n] for n, _, _ in todo)
    print(f"{len(jobs)} runs planned, {len(todo)} to run; projected ≈ ${projected:.2f}; spent ${spend.total_usd:.2f} of ${CAP_USD:.2f}", flush=True)
    if spend.total_usd + projected > CAP_USD:
        sys.exit("STOP: projection passes the cap. Ask Alexander.")
    agents, loggers = {}, {}
    for name in ("minimax", "gemini"):
        m = CFG["models"][name]
        client = ChatClient(model=m["model"], provider=m["provider"], provider_tag=m["provider_tag"], expected_model=m["expected_model"],
                            api_key=api_key(), cache=DiskCache(ROOT / "cache" / "openrouter"), logger=JsonlLogger(LOGS / "rechecks-calls.jsonl"),
                            spend=spend, temperature=TEMPERATURE, reasoning_effort=CFG["reasoning_effort"], retries=CFG["retries"])
        agents[name] = LLMAgent(f"{name}-t0", client, max_steps=CFG["max_steps"])
        loggers[name] = JsonlLogger(LOGS / f"rechecks-{name}-t0.jsonl")

    def one(job):
        name, task_id, attempt = job
        run = run_candidate(tasks[task_id], agents[name], attempt)
        loggers[name].write({"event": "candidate_run", "run_id": "rechecks-t0", **run.record()})
        return name, run

    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, run in pool.map(one, todo):
            done[name][(run.task_id, run.candidate)] = run
            print(f"  {name:8} {run.task_id:13} attempt {run.candidate} credit {run.partial_credit:.2f} "
                  f"steps {run.steps:2} ${run.cost_usd:.3f}; spend ${spend.total_usd:.2f}", flush=True)
    spend.flush()
    pairs = [(done["minimax"][(t, 0)], done["minimax"][(t, 1)]) for t in repeat_ids]
    same_credit = sum(abs(a.partial_credit - b.partial_credit) < 1e-9 for a, b in pairs)
    same_path = sum([c["name"] + json.dumps(c["args"], sort_keys=True) for c in a.calls] ==
                    [c["name"] + json.dumps(c["args"], sort_keys=True) for c in b.calls] for a, b in pairs)
    repeat = {"tasks": len(pairs), "identical_credit": same_credit, "identical_tool_calls": same_path,
              "mean_abs_credit_diff": sum(abs(a.partial_credit - b.partial_credit) for a, b in pairs) / len(pairs),
              "per_task": {a.task_id: [a.partial_credit, b.partial_credit] for a, b in pairs}}
    mm = [done["minimax"][(t, 0)] for t in ids]
    gm = [done["gemini"][(t, 0)] for t in ids]
    comp = comparability(gm, mm).record()
    report = {"temperature": TEMPERATURE, "repeatability": repeat, "comparison": comp,
              "summaries": {"minimax": summarize_model(mm).record(), "gemini": summarize_model(gm).record()},
              "spend_usd": spend.total_usd}
    (ROOT / "results" / "harness").mkdir(parents=True, exist_ok=True)
    (ROOT / "results" / "harness" / "rechecks.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "phase0" / "temperature0_rechecks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "comparison"} | {"comparison": {k: comp[k] for k in ("comparable", "difference", "interval_95")}}, indent=1))
    print("written: phase0/temperature0_rechecks.json", flush=True)


if __name__ == "__main__":
    main()
