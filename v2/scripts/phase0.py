"""Phase 0 paid steps: task selection, smoke test, Nemotron screen.

    .venv/bin/python scripts/phase0.py select   # fix the 50 task IDs (free; committed before any run)
    .venv/bin/python scripts/phase0.py smoke    # 2 tasks per model (cents); measures cost per run
    .venv/bin/python scripts/phase0.py screen   # Nemotron alone, 4 runs x 50 Finance + HR tasks (go/no-go)

The Nemotron vs Gemini comparability test moved to Phase 1 (2026-10-07); see phase0/FEASIBILITY.md.

Settings: phase0/config_phase0.yaml. Spend is capped in code for all of Phase 0; finished model
calls are cached, so a rerun after any stop resumes for free.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import bench  # noqa: E402
from jevloop.cache import DiskCache  # noqa: E402
from jevloop.feasibility import select_tasks  # noqa: E402
from jevloop.llm_agent import LLMAgent  # noqa: E402
from jevloop.log import JsonlLogger  # noqa: E402
from jevloop.openrouter import ChatClient  # noqa: E402
from jevloop.runs import run_candidates  # noqa: E402
from jevloop.spend import SpendTracker  # noqa: E402

CONFIG = yaml.safe_load((ROOT / "phase0" / "config_phase0.yaml").read_text())
RESULTS = ROOT / "results" / "phase0"
LOGS = ROOT / "logs" / "phase0"


def api_key() -> str:
    key = os.environ.get("OPENROUTER_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENROUTER_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("OPENROUTER_KEY not set (v2/.env)")
    return key


def spend() -> SpendTracker:
    return SpendTracker(RESULTS / "spend.json", cap_usd=CONFIG["spend_cap_usd"], flush_seconds=0)


def agent(name: str, tracker: SpendTracker, run_id: str) -> LLMAgent:
    m = CONFIG["models"][name]
    client = ChatClient(
        model=m["model"], provider=m["provider"], provider_tag=m["provider_tag"],
        expected_model=m["expected_model"], api_key=api_key(),
        cache=DiskCache(ROOT / "cache" / "openrouter"), logger=JsonlLogger(LOGS / f"{run_id}-calls.jsonl"),
        spend=tracker, temperature=CONFIG["temperature"], reasoning_effort=CONFIG["reasoning_effort"],
        retries=CONFIG["retries"],
    )
    return LLMAgent(name, client, max_steps=CONFIG["max_steps"])


def task_ids() -> list[str]:
    path = ROOT / CONFIG["comparability"]["task_ids_file"]
    if not path.exists():
        sys.exit(f"{path} missing: run `select` first")
    return path.read_text().split()


def cmd_select(_args) -> None:
    tasks = bench.load_tasks(CONFIG["comparability"]["domains"])
    by_domain: dict[str, list[str]] = {}
    for t in tasks:
        by_domain.setdefault(t.public.domain, []).append(t.task_id)
    ids = select_tasks(by_domain, CONFIG["comparability"]["per_domain"], CONFIG["seed"])
    path = ROOT / CONFIG["comparability"]["task_ids_file"]
    text = "\n".join(ids) + "\n"
    if path.exists() and path.read_text() != text:
        sys.exit(f"{path} exists with different IDs; the set is fixed once chosen")
    path.write_text(text)
    print(f"{len(ids)} task IDs -> {path.relative_to(ROOT)}")


def run_models(task_list: list[str], run_id: str, reuse_from: tuple[str, ...] = ()) -> dict:
    tracker = spend()
    tasks = {t.task_id: t for t in bench.load_tasks(sorted({i.split(":")[0] for i in task_list}))}
    chosen = [tasks[i] for i in task_list]
    out = {}
    for name in CONFIG["models"]:
        log_path = LOGS / f"{run_id}-{name}-runs.jsonl"
        # Resume by whole runs: the simulator stamps clock times and random IDs into tool results,
        # so a rerun can't replay model calls from the cache past the first write. Finished runs are
        # reloaded from the log and only missing tasks run (an interrupted run is paid for again).
        finished = {}
        for earlier in reuse_from:  # same settings, same tasks: e.g. the smoke test's business task
            finished |= {t: r for t, r in load_finished(LOGS / f"{earlier}-{name}-runs.jsonl").items() if t in task_list}
        finished |= load_finished(log_path)
        todo = [t for t in chosen if t.task_id not in finished]
        if finished:
            print(f"{name}: {len(finished)} finished runs reloaded from {log_path.name}; {len(todo)} to run")
        new = run_candidates(todo, agent(name, tracker, run_id), k=1, max_workers=CONFIG["workers"],
                             logger=JsonlLogger(log_path), run_id=run_id)
        by_id = {**finished, **{r.task_id: r for r in new}}
        runs = [by_id[t] for t in task_list]
        out[name] = runs
        tracker.flush()
        print(f"{name}: done; Phase 0 spend so far ${tracker.total_usd:.4f}")
    return out


def load_finished(log_path: Path) -> dict:
    """Candidate-0 runs already recorded in a runs log, keyed by task ID (last record wins)."""
    from jevloop.runs import CandidateRun

    finished = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            record = json.loads(line)
            if record.get("event") == "candidate_run" and record.get("candidate") == 0:
                fields = {k: v for k, v in record.items() if k in CandidateRun.__dataclass_fields__}
                finished[record["task_id"]] = CandidateRun(**fields)
    return finished


def describe(runs) -> None:
    for r in runs:
        print(f"  {r.agent:9} {r.task_id:14} credit={r.partial_credit:.2f} pass={r.passed!s:5} steps={r.steps:2} "
              f"calls={r.tool_calls:2} stop={r.stop_reason:9} parse_err={r.parse_errors} in_tok={r.input_tokens:7} "
              f"out_tok={r.output_tokens:6} cost=${r.cost_usd:.4f} model_s={r.model_seconds:.1f}")


def cmd_smoke(_args) -> None:
    ids = [CONFIG["smoke"]["simple_task"], next(i for i in task_ids() if i.startswith("finance:"))]
    out = run_models(ids, "smoke")
    projection = 0.0
    for name, runs in out.items():
        describe(runs)
        business = [r for r in runs if not r.task_id.startswith("simple:")]
        per_run = sum(r.cost_usd for r in business) / len(business)
        projection += per_run * len(task_ids())
        print(f"  {name}: business-task cost per run ${per_run:.4f} -> 50 tasks ≈ ${per_run * len(task_ids()):.2f}")
    tracker = spend()
    print(f"\nProjected comparability check ≈ ${projection:.2f} (from one business task per model; rough). "
          f"Spent so far ${tracker.total_usd:.4f} of the ${tracker.cap_usd:.2f} cap.")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "smoke.json").write_text(json.dumps(
        {name: [r.record() for r in runs] for name, runs in out.items()}, indent=2) + "\n")


GEMINI_SMOKE_COST_PER_RUN = 0.4842  # smoke test, finance:4001 (one task): the only Gemini business-task measurement
PHASE1_NEMOTRON_RUNS = 800  # 4 runs x 200 Finance + HR tasks (practice, gate, sealed)
PHASE1_GEMINI_RUNS = 80  # Strong agent on the sealed set
PHASE1_OVERHEAD_USD = 3.0  # Jev scoring, editor and escalation-judge calls (v1 prices)
PHASE1_CAP_USD = 60.0  # placeholder Phase 1 cap (brief); set after Phase 0
SKILL_LOOP_RUNS = 2100  # optional Agent skill loop: 5 rounds x (60 practice + 3 edits x 60 gate x 2)


def cmd_screen(args) -> None:
    """Nemotron alone, K runs on each of the 50 Finance + HR tasks: the go/no-go numbers."""
    from concurrent.futures import ThreadPoolExecutor

    from jevloop.feasibility import frame, go_no_go
    from jevloop.runs import run_candidate

    k, name, run_id = args.k, "nemotron", "screen"
    ids = task_ids()
    tracker = spend()
    smoke_cost = [r for r in json.loads((RESULTS / "smoke.json").read_text())[name] if not r["task_id"].startswith("simple:")]
    per_run = sum(r["cost_usd"] for r in smoke_cost) / len(smoke_cost)
    log_path = LOGS / f"{run_id}-{name}-runs.jsonl"
    finished = {(t, 0): r for t, r in load_finished(LOGS / f"smoke-{name}-runs.jsonl").items() if t in ids}
    finished |= load_finished_all(log_path)
    tasks = {t.task_id: t for t in bench.load_tasks(CONFIG["comparability"]["domains"])}
    jobs = [(tasks[t], c) for t in ids for c in range(k) if (t, c) not in finished]
    projection = per_run * len(jobs)
    print(f"{len(finished)} runs reloaded, {len(jobs)} to run; projected ${projection:.2f} "
          f"(spent ${tracker.total_usd:.2f} of ${tracker.cap_usd:.2f})")
    if tracker.total_usd + projection * args.safety > tracker.cap_usd:
        sys.exit(f"STOP: spend + {args.safety} x projection would pass the ${tracker.cap_usd:.2f} cap. Ask Alexander.")
    logger = JsonlLogger(log_path)
    if args.retries:
        CONFIG["retries"] = args.retries
    nemotron = agent(name, tracker, run_id)
    workers = args.workers or CONFIG["workers"]

    def one(job):
        run = run_candidate(job[0], nemotron, job[1])
        logger.write({"event": "candidate_run", "run_id": run_id, **run.record()})
        return run

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, run in enumerate(pool.map(one, jobs), 1):
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} runs; spend ${tracker.total_usd:.2f}", flush=True)
    tracker.flush()
    finished |= load_finished_all(log_path)
    runs = [finished[(t, c)] for t in ids for c in range(k)]
    f = frame(runs)
    cost = f.cost_per_run_usd
    phase1 = cost * PHASE1_NEMOTRON_RUNS + GEMINI_SMOKE_COST_PER_RUN * PHASE1_GEMINI_RUNS + PHASE1_OVERHEAD_USD
    decision = go_no_go(f, projected_phase1_cost_usd=phase1, cap_usd=PHASE1_CAP_USD)
    first = [finished[(t, 0)] for t in ids]
    failure_rate = sum(r.failed for r in runs) / len(runs)
    by_domain = {d: {"first_run_pass_rate": sum(r.passed for r in first if r.domain == d) / sum(r.domain == d for r in first),
                     "first_run_credit": sum(r.partial_credit for r in first if r.domain == d) / sum(r.domain == d for r in first)}
                 for d in CONFIG["comparability"]["domains"]}
    report = {
        "frame": f.record(), "by_domain": by_domain,
        "run_failure_rate": failure_rate, "run_failures": sum(r.failed for r in runs),
        "stop_reasons": {s_: sum(r.stop_reason == s_ for r in runs) for s_ in ("done", "max_steps", "error")},
        "parse_error_runs": sum(r.parse_errors > 0 for r in runs),
        "steps_per_run": sum(r.steps for r in runs) / len(runs),
        "projected_phase1_cost_usd": phase1,
        "projected_phase1_cost_with_skill_loop_usd": phase1 + cost * SKILL_LOOP_RUNS,
        "projection_inputs": {"nemotron_cost_per_run": cost, "gemini_cost_per_run_smoke": GEMINI_SMOKE_COST_PER_RUN,
                              "nemotron_runs": PHASE1_NEMOTRON_RUNS, "gemini_runs": PHASE1_GEMINI_RUNS,
                              "overhead_usd": PHASE1_OVERHEAD_USD, "phase1_cap_usd": PHASE1_CAP_USD},
        "go_no_go": {"go": decision.go, "pass_rate_ok": decision.pass_rate_ok, "mixed_ok": decision.mixed_ok,
                     "cost_ok": decision.cost_ok, "reasons": list(decision.reasons)},
        "phase0_spend_usd": tracker.total_usd,
        "per_task": {t: [{"credit": finished[(t, c)].partial_credit, "passed": finished[(t, c)].passed,
                          "failed": finished[(t, c)].failed, "steps": finished[(t, c)].steps,
                          "cost_usd": finished[(t, c)].cost_usd} for c in range(k)] for t in ids},
    }
    (ROOT / "phase0" / "screen_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k_: v for k_, v in report.items() if k_ != "per_task"}, indent=2))
    print("written: phase0/screen_results.json")


def load_finished_all(log_path: Path) -> dict:
    """All runs in a runs log, keyed by (task ID, candidate); last record wins."""
    from jevloop.runs import CandidateRun

    finished = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            record = json.loads(line)
            if record.get("event") == "candidate_run":
                fields = {k: v for k, v in record.items() if k in CandidateRun.__dataclass_fields__}
                finished[(record["task_id"], record["candidate"])] = CandidateRun(**fields)
    return finished


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select").set_defaults(fn=cmd_select)
    sub.add_parser("smoke").set_defaults(fn=cmd_smoke)
    screen = sub.add_parser("screen")
    screen.add_argument("--k", type=int, default=4)
    screen.add_argument("--workers", type=int, default=None, help="override config workers (results do not depend on it)")
    screen.add_argument("--retries", type=int, default=None, help="override config retries")
    screen.add_argument("--safety", type=float, default=1.5, help="multiplier on the projected cost for the cap check")
    screen.set_defaults(fn=cmd_screen)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
