"""Export the sealed exam as a compact per-run table (one row per run), so the headline numbers can be re-derived
without the raw run logs (which hold full agent transcripts and are not published).

    .venv/bin/python scripts/export_sealed_runs.py          # needs the local logs/ and cache/; free, no model calls

Writes phase1/run/take2/sealed_runs.csv. Check it with scripts/rederive_sealed.py (needs only that CSV).
Columns: arm, task_id, domain, partial_credit, passed, cost_usd, steps, seconds, holds, flags, stop_reason,
jev_score (final playbook, checkpoint on only: the verifier score the router's cutoff was applied to).
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

LOGS, OUT = ROOT / "logs" / "phase1_run", ROOT / "phase1" / "run" / "take2"
FINAL = json.loads((OUT / "skill_final.json").read_text())["version"]
ARMS = {
    "starting_playbook_checkpoint_on": f"minimax-p1-v0-cp-sealed",
    "final_playbook_checkpoint_on": f"minimax-p1-{FINAL}-cp-sealed",
    "final_playbook_checkpoint_off": f"minimax-p1-{FINAL}-nocp-sealed",
    "gemini_alone": "gemini-p1-v0-nocp-sealed",
    "gemini_redo_for_escalated": "gemini-p1-v0-nocp-sealed-redo",
}


def rows_of(name: str) -> dict[str, dict]:
    return {r["task_id"]: r for r in (json.loads(line) for line in open(LOGS / f"{name}.jsonl"))}


def main() -> None:
    spec = importlib.util.spec_from_file_location("phase1_run", ROOT / "scripts" / "phase1_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Run:  # what verifier_scores reads
        def __init__(self, r):
            self.calls, self.summary = r["calls"], r["summary"]

    arms = {arm: rows_of(name) for arm, name in ARMS.items()}
    final = arms["final_playbook_checkpoint_on"]
    scores = mod.verifier_scores(mod.Phase1(paid=False), {t: Run(r) for t, r in final.items()})

    out = OUT / "sealed_runs.csv"
    cols = ["arm", "task_id", "domain", "partial_credit", "passed", "cost_usd", "steps", "seconds", "holds",
            "flags", "stop_reason", "jev_score"]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for arm, rs in arms.items():
            for t in sorted(rs):
                r = rs[t]
                js = f"{scores[t]:.6f}" if arm == "final_playbook_checkpoint_on" else ""
                w.writerow([arm, t, r.get("domain", ""), f"{r['partial_credit']:.6f}", int(bool(r["passed"])),
                            f"{r['cost_usd']:.6f}", r.get("steps", ""), f"{r.get('seconds', 0):.1f}",
                            r.get("holds", 0), r.get("flags", 0), r.get("stop_reason", ""), js])
    print(f"wrote {out.relative_to(ROOT)}: {sum(len(r) for r in arms.values())} rows, "
          f"{ {a: len(r) for a, r in arms.items()} }")


if __name__ == "__main__":
    main()
