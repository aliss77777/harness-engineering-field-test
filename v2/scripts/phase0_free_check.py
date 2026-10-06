"""Phase 0 free check: the whole pipeline end to end with no model calls ($0).

    .venv/bin/python scripts/phase0_free_check.py

Runs the do-nothing agent on every task (the zero line) and a scripted agent with K=4 on
simple:3001 (two candidates solve it, two do nothing), then prints the Phase 0 frame.
The paid spike swaps in the Cheap agent and Strong agent once the models are chosen.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import bench  # noqa: E402
from jevloop.agents import SIMPLE_3001_SOLUTION, DoNothingAgent, ScriptedAgent  # noqa: E402
from jevloop.feasibility import frame  # noqa: E402
from jevloop.log import JsonlLogger  # noqa: E402
from jevloop.runs import run_candidates  # noqa: E402


def main() -> None:
    out = ROOT / "results" / "phase0"
    logger = JsonlLogger(ROOT / "logs" / "phase0" / "free-check.jsonl")
    tasks = bench.load_tasks(bench.domains())
    zero = frame(run_candidates(tasks, DoNothingAgent(), k=1, logger=logger, run_id="free-do-nothing"))
    scripted_runs = run_candidates(
        [t for t in tasks if t.task_id == "simple:3001"],
        ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION, []]}),
        k=4, logger=logger, run_id="free-scripted",
    )
    scripted = frame(scripted_runs)
    report = {"do_nothing": zero.record(), "scripted_simple_3001": scripted.record(),
              "example_summary": scripted_runs[0].summary}
    out.mkdir(parents=True, exist_ok=True)
    (out / "free_check.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, f in (("do-nothing, all tasks", zero), ("scripted, simple:3001", scripted)):
        print(f"{name}: tasks={f.tasks} K={f.k} first-run pass={f.first_run_pass_rate:.0%} "
              f"random-pick pass={f.random_pick_pass_rate:.0%} oracle pass={f.oracle_pass_rate:.0%} "
              f"mixed={f.mixed_share:.0%} cost/run=${f.cost_per_run_usd:.2f}")
    print(f"\nexample run summary:\n{scripted_runs[0].summary}\n\nwritten: {out / 'free_check.json'}")


if __name__ == "__main__":
    main()
