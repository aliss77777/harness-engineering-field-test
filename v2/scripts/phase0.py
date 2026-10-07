"""Phase 0 paid steps: task selection, smoke test, cheap-agent comparability check.

    .venv/bin/python scripts/phase0.py select   # fix the 50 task IDs (free; committed before any run)
    .venv/bin/python scripts/phase0.py smoke    # 2 tasks per model (cents); projects the check's cost
    .venv/bin/python scripts/phase0.py check    # 50 Finance + HR tasks per model, one run each

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
from jevloop.feasibility import comparability, select_tasks, summarize_model  # noqa: E402
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


def run_models(task_list: list[str], run_id: str) -> dict:
    tracker = spend()
    tasks = {t.task_id: t for t in bench.load_tasks(sorted({i.split(":")[0] for i in task_list}))}
    chosen = [tasks[i] for i in task_list]
    out = {}
    for name in CONFIG["models"]:
        logger = JsonlLogger(LOGS / f"{run_id}-{name}-runs.jsonl")
        runs = run_candidates(chosen, agent(name, tracker, run_id), k=1, max_workers=CONFIG["workers"],
                              logger=logger, run_id=run_id)
        out[name] = runs
        tracker.flush()
        print(f"{name}: done; Phase 0 spend so far ${tracker.total_usd:.4f}")
    return out


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


def cmd_check(args) -> None:
    smoke = json.loads((RESULTS / "smoke.json").read_text()) if (RESULTS / "smoke.json").exists() else None
    if smoke is None:
        sys.exit("run `smoke` first: the check's cost is projected from it")
    tracker = spend()
    projection = sum(
        sum(r["cost_usd"] for r in runs if not r["task_id"].startswith("simple:")) * len(task_ids())
        for runs in smoke.values()
    )
    if tracker.total_usd + projection * args.safety > tracker.cap_usd:
        sys.exit(f"STOP: projected ${projection:.2f} (x{args.safety} safety) + spent ${tracker.total_usd:.2f} "
                 f"exceeds the ${tracker.cap_usd:.2f} cap. Ask Alexander before running.")
    out = run_models(task_ids(), "check")
    result = comparability(out["gemini"], out["nemotron"])
    for name, runs in out.items():
        s = summarize_model(runs)
        print(f"{name}: credit {s.mean_credit:.3f} pass {s.pass_rate:.0%} failures {s.failures} "
              f"${s.cost_per_run_usd:.4f}/run {s.model_seconds_per_run:.1f}s/run {s.steps_per_run:.1f} steps/run")
    lo, hi = result.interval
    print(f"difference (Nemotron - Gemini): {result.difference:+.3f} [{lo:+.3f}, {hi:+.3f}] -> "
          f"{'COMPARABLE' if result.comparable else 'NOT comparable'} "
          f"(credit_ok={result.credit_ok}, failures_ok={result.failures_ok})")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "check_runs.json").write_text(json.dumps(
        {name: [r.record() for r in runs] for name, runs in out.items()}, indent=2) + "\n")
    per_task = {t: {name: {"credit": r.partial_credit, "passed": r.passed, "failed": r.failed, "steps": r.steps,
                           "cost_usd": r.cost_usd, "model_seconds": r.model_seconds}
                    for name, runs in out.items() for r in runs if r.task_id == t} for t in task_ids()}
    (ROOT / "phase0" / "comparability_results.json").write_text(json.dumps(
        {"verdict": result.record(), "settings": {k: CONFIG[k] for k in ("seed", "max_steps", "temperature", "reasoning_effort")}
         | {"models": CONFIG["models"]}, "per_task": per_task}, indent=2) + "\n")
    print("written: phase0/comparability_results.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select").set_defaults(fn=cmd_select)
    sub.add_parser("smoke").set_defaults(fn=cmd_smoke)
    check = sub.add_parser("check")
    check.add_argument("--safety", type=float, default=1.5, help="multiplier on the projected cost for the cap check")
    check.set_defaults(fn=cmd_check)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
