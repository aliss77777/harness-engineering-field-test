"""V2-5a: the action-masking gate on vs off, on the 60 gate tasks (work item C). Paid; capped at $10.

    .venv/bin/python scripts/v2_5a_gate.py

MiniMax M3 with its version-0 prompt (the bench's own), temperature 0, one run per task with the gate
off and one with the gate on (ReadPoliciesFirst), paired by task. Never touches the sealed set.
Verdict rules: src/jevloop/masking.py (committed before this ran). Finished runs reload on a rerun.
Writes action_masking/v2_5a/results.json and prints the verdict.
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
from jevloop.diagnostics import read_policy_before_first_write  # noqa: E402
from jevloop.llm_agent import LLMAgent  # noqa: E402
from jevloop.log import JsonlLogger  # noqa: E402
from jevloop.masking import verdict  # noqa: E402
from jevloop.monitor import ReadPoliciesFirst, company_data  # noqa: E402
from jevloop.openrouter import ChatClient  # noqa: E402
from jevloop.runs import CandidateRun, run_candidate  # noqa: E402
from jevloop.spend import SpendTracker  # noqa: E402

CFG = yaml.safe_load((ROOT / "phase0" / "config_phase0.yaml").read_text())
CAP_USD = 10.0
COST_ESTIMATE = 0.06  # per MiniMax run, upper end of the measured $0.03-0.055
LOGS = ROOT / "logs" / "v2_5a"
OUT = ROOT / "action_masking" / "v2_5a"


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_KEY missing")


def load(path: Path) -> dict[str, CandidateRun]:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            out[r["task_id"]] = CandidateRun(**{k: v for k, v in r.items() if k in CandidateRun.__dataclass_fields__})
    return out


def main() -> None:
    ids = (ROOT / "phase1" / "splits" / "gate.txt").read_text().split()
    sealed = set((ROOT / "phase1" / "splits" / "sealed.txt").read_text().split())
    assert not sealed & set(ids), "V2-5a runs on gate tasks only"
    tasks = {t.task_id: t for t in bench.load_tasks(["finance", "hr"])}
    data = {t: company_data(tasks[t].initial_state) for t in ids}
    spend = SpendTracker(ROOT / "results" / "v2_5a" / "spend.json", cap_usd=CAP_USD, flush_seconds=0)
    arms = {"off": load(LOGS / "gate-off.jsonl"), "on": load(LOGS / "gate-on.jsonl")}
    jobs = [(arm, t) for t in ids for arm in ("off", "on") if t not in arms[arm]]
    projected = len(jobs) * COST_ESTIMATE
    print(f"{len(ids)} gate tasks x 2 arms; {len(jobs)} runs to go; projected ≈ ${projected:.2f}; "
          f"spent ${spend.total_usd:.2f} of ${CAP_USD:.2f}", flush=True)
    if spend.total_usd + projected > CAP_USD:
        sys.exit("STOP: projection passes the cap. Ask Alexander.")
    m = CFG["models"]["minimax"]
    client = ChatClient(model=m["model"], provider=m["provider"], provider_tag=m["provider_tag"], expected_model=m["expected_model"],
                        api_key=api_key(), cache=DiskCache(ROOT / "cache" / "openrouter"), logger=JsonlLogger(LOGS / "calls.jsonl"),
                        spend=spend, temperature=0.0, reasoning_effort=CFG["reasoning_effort"], retries=CFG["retries"])
    agents = {"off": LLMAgent("minimax-t0", client, max_steps=CFG["max_steps"]),
              "on": LLMAgent("minimax-t0-gate", client, max_steps=CFG["max_steps"], monitor=ReadPoliciesFirst(), company_data=data)}
    loggers = {arm: JsonlLogger(LOGS / f"gate-{arm}.jsonl") for arm in arms}

    def one(job):
        arm, t = job
        run = run_candidate(tasks[t], agents[arm], 0)
        loggers[arm].write({"event": "candidate_run", "run_id": f"v2_5a-{arm}", **run.record()})
        return arm, run

    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, (arm, run) in enumerate(pool.map(one, jobs), 1):
            arms[arm][run.task_id] = run
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} runs; spend ${spend.total_usd:.2f}", flush=True)
    spend.flush()
    off, on = {t: arms["off"][t] for t in ids}, {t: arms["on"][t] for t in ids}
    read_first = [read_policy_before_first_write(tasks[t], on[t].calls) for t in ids]
    v = verdict(off, on, [x for x in read_first if x is not None])
    v["spend_usd"] = spend.total_usd
    v["cost_per_run"] = {"off": sum(r.cost_usd for r in off.values()) / len(off), "on": sum(r.cost_usd for r in on.values()) / len(on)}
    v["steps_per_run"] = {"off": sum(r.steps for r in off.values()) / len(off), "on": sum(r.steps for r in on.values()) / len(on)}
    v["per_task"] = {t: {"off": {"credit": off[t].partial_credit, "broken": sum(1 for c in off[t].checks if c["kind"] == "rule_broken" and not c["passed"])},
                         "on": {"credit": on[t].partial_credit, "broken": sum(1 for c in on[t].checks if c["kind"] == "rule_broken" and not c["passed"]),
                                "holds": on[t].holds}} for t in ids}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(v, indent=2) + "\n")
    print(json.dumps({k: val for k, val in v.items() if k != "per_task"}, indent=1))
    print("written: action_masking/v2_5a/results.json", flush=True)


if __name__ == "__main__":
    main()
