"""Phase 1 pilot: 2 rounds of the Agent skill loop (MiniMax edits its own working rules).

    .venv/bin/python scripts/phase1_pilot.py split   # write phase1/splits/*.txt (free; committed before any run)
    .venv/bin/python scripts/phase1_pilot.py run     # the pilot (paid; $20 hard cap)

Practice and gate tasks only; the sealed set is never touched. Every run is logged and reloaded on a
rerun, so a stop resumes without paying twice. Writes phase1/pilot/round_<n>.json, the skill versions,
and phase1/pilot/summary.json.
"""
import argparse
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import bench  # noqa: E402
from jevloop.cache import DiskCache  # noqa: E402
from jevloop.diagnostics import behaviour  # noqa: E402
from jevloop.llm_agent import LLMAgent  # noqa: E402
from jevloop.log import JsonlLogger  # noqa: E402
from jevloop.openrouter import ChatClient  # noqa: E402
from jevloop.runs import CandidateRun, run_candidate  # noqa: E402
from jevloop.skill_loop import (Edit, SkillEditor, apply_edit, best_passing, gate_decision,  # noqa: E402
                                mistakes_report, skill_text, version_id)
from jevloop.spend import SpendTracker  # noqa: E402
from jevloop.splits import phase1_split  # noqa: E402

CONFIG = yaml.safe_load((ROOT / "phase1" / "config_phase1.yaml").read_text())
PHASE0 = yaml.safe_load((ROOT / "phase0" / "config_phase0.yaml").read_text())
PILOT = CONFIG["pilot"]
OUT = ROOT / "phase1" / "pilot"
LOGS = ROOT / "logs" / "phase1"
SPLITS = ROOT / "phase1" / "splits"


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_KEY not set (v2/.env)")


def cmd_split(_args) -> None:
    tasks = bench.load_tasks(CONFIG["domains"])
    by_domain: dict[str, list[str]] = {}
    for t in tasks:
        by_domain.setdefault(t.public.domain, []).append(t.task_id)
    phase0 = set((ROOT / CONFIG["phase0_task_ids_file"]).read_text().split())
    split = phase1_split(by_domain, phase0, seed=CONFIG["seed"])
    SPLITS.mkdir(parents=True, exist_ok=True)
    for name, ids in split.items():
        path = SPLITS / f"{name}.txt"
        text = "\n".join(ids) + "\n"
        if path.exists() and path.read_text() != text:
            sys.exit(f"{path} exists with different IDs; the split is fixed once written")
        path.write_text(text)
        print(f"{name}: {len(ids)} tasks -> phase1/splits/{name}.txt")


def load_runs(path: Path) -> dict[str, CandidateRun]:
    found = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r.get("event") == "candidate_run":
                found[r["task_id"]] = CandidateRun(**{k: v for k, v in r.items() if k in CandidateRun.__dataclass_fields__})
    return found


class Pilot:
    def __init__(self):
        m = PHASE0["models"][CONFIG["agent_model"]]
        self.spend = SpendTracker(ROOT / "results" / "phase1" / "pilot_spend.json", cap_usd=PILOT["spend_cap_usd"], flush_seconds=0)
        self.client = ChatClient(
            model=m["model"], provider=m["provider"], provider_tag=m["provider_tag"], expected_model=m["expected_model"],
            api_key=api_key(), cache=DiskCache(ROOT / "cache" / "openrouter"), logger=JsonlLogger(LOGS / "pilot-calls.jsonl"),
            spend=self.spend, temperature=PHASE0["temperature"], reasoning_effort=PHASE0["reasoning_effort"],
            retries=PHASE0["retries"])
        self.tasks = {t.task_id: t for t in bench.load_tasks(CONFIG["domains"])}

    def run_set(self, rules: tuple[str, ...], task_ids: list[str], label: str) -> dict[str, CandidateRun]:
        """One run per task for this skill version; finished runs reload from the log."""
        vid = version_id(rules)
        path = LOGS / f"pilot-{vid}-{label}.jsonl"
        done = load_runs(path)
        todo = [t for t in task_ids if t not in done]
        projected = len(todo) * PILOT["cost_per_run_estimate"]
        if self.spend.total_usd + projected > self.spend.cap_usd:
            raise SystemExit(f"STOP: {len(todo)} runs (≈ ${projected:.2f}) would take the pilot past its "
                             f"${self.spend.cap_usd:.2f} cap (spent ${self.spend.total_usd:.2f}). Ask Alexander.")
        agent = LLMAgent(f"{CONFIG['agent_model']}-{vid}", self.client, max_steps=PHASE0["max_steps"], skill=skill_text(rules))
        logger = JsonlLogger(path)

        def one(task_id):
            run = run_candidate(self.tasks[task_id], agent, 0)
            logger.write({"event": "candidate_run", "run_id": f"pilot-{vid}-{label}", "version": vid, **run.record()})
            return run

        if todo:
            print(f"  {vid} on {label}: {len(done)} reloaded, running {len(todo)}", flush=True)
            with ThreadPoolExecutor(max_workers=PILOT["workers"]) as pool:
                for run in pool.map(one, todo):
                    done[run.task_id] = run
            self.spend.flush()
            print(f"  {vid} on {label}: done; pilot spend ${self.spend.total_usd:.2f}", flush=True)
        return {t: done[t] for t in task_ids}

    def measure(self, runs: dict[str, CandidateRun]) -> dict:
        rs = list(runs.values())
        beh = [behaviour(self.tasks[r.task_id], r.calls, r.missed_checks) for r in rs]
        policy = [b["read_all_policy_emails"] for b in beh if b["read_all_policy_emails"] is not None]
        return {"tasks": len(rs), "mean_credit": sum(r.partial_credit for r in rs) / len(rs),
                "pass_rate": sum(r.passed for r in rs) / len(rs),
                "read_every_policy_email": f"{sum(policy)}/{len(policy)}",
                "read_every_policy_email_rate": (sum(policy) / len(policy)) if policy else None,
                "broken_must_not_per_run": sum(b["broken_must_not"] for b in beh) / len(rs),
                "steps_per_run": sum(r.steps for r in rs) / len(rs),
                "cost_per_run_usd": sum(r.cost_usd for r in rs) / len(rs)}


def cmd_run(_args) -> None:
    practice = (SPLITS / "practice.txt").read_text().split()
    gate_all = (SPLITS / "gate.txt").read_text().split()
    gate = sorted(random.Random(f"{CONFIG['seed']}:gate").sample(gate_all, PILOT["gate_size"]))
    pilot = Pilot()
    editor = SkillEditor(pilot.client)
    OUT.mkdir(parents=True, exist_ok=True)
    rules: tuple[str, ...] = ()
    rejected: list[Edit] = []
    history = []
    for rnd in range(1, PILOT["rounds"] + 1):
        print(f"ROUND {rnd}: current version {version_id(rules)} ({len(rules)} rules)", flush=True)
        sample = sorted(random.Random(f"{CONFIG['seed']}:practice:{rnd}").sample(practice, PILOT["practice_per_round"]))
        practice_runs = pilot.run_set(rules, sample, f"practice-r{rnd}")
        assert set(practice_runs) <= set(practice), "the editor may only see practice runs"
        mistakes = mistakes_report(list(practice_runs.values()), limit=PILOT["mistakes_shown"],
                                   rng=random.Random(f"{CONFIG['seed']}:mistakes:{rnd}"))
        edits, refused = editor.propose(rules, mistakes, rejected, n=PILOT["candidates_per_round"], round_number=rnd)
        print(f"  editor proposed {len(edits)} edits ({len(refused)} refused):", flush=True)
        for e in edits:
            print(f"    - {e.op} {e.index or ''}: {e.text}", flush=True)
        current_gate = pilot.run_set(rules, gate, "gate")
        decisions = []
        for e in edits:
            cand = apply_edit(rules, e)
            cand_gate = pilot.run_set(cand, gate, "gate")
            d = gate_decision({t: r.partial_credit for t, r in current_gate.items()},
                              {t: r.partial_credit for t, r in cand_gate.items()}, p_threshold=PILOT["gate_p_threshold"])
            decisions.append((e, d, pilot.measure(cand_gate)))
            print(f"    gate: {e.text[:70]!r} diff {d.mean_diff:+.3f} p {d.p_value:.3f} "
                  f"better {d.better} worse {d.worse} -> {'KEEP' if d.keep else 'reject'}", flush=True)
        winner = best_passing([(e, d) for e, d, _ in decisions])
        before = rules
        for e, d, _ in decisions:
            if not (winner and e is winner[0]):
                rejected.append(e)
        if winner:
            rules = apply_edit(rules, winner[0])
        record = {
            "round": rnd, "version_before": version_id(before), "rules_before": list(before),
            "practice_tasks": sample, "practice": pilot.measure(practice_runs),
            "mistakes_shown": [m["task_id"] for m in mistakes], "edits_proposed": [e.record() for e in edits],
            "edits_refused": refused, "gate_tasks": gate, "gate_current": pilot.measure(current_gate),
            "gate_candidates": [{"edit": e.record(), "decision": d.record(), "measures": m} for e, d, m in decisions],
            "kept": winner[0].record() if winner else None,
            "version_after": version_id(rules), "rules_after": list(rules), "pilot_spend_usd": pilot.spend.total_usd,
        }
        history.append(record)
        (OUT / f"round_{rnd}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        (OUT / f"skill_after_round_{rnd}.md").write_text((skill_text(rules) or "(no rules: version 0, the bench's prompt only)") + "\n")
        print(f"  ROUND {rnd} -> {'kept: ' + winner[0].text if winner else 'no edit kept'}; spend ${pilot.spend.total_usd:.2f}", flush=True)
    summary = {"rounds": len(history), "final_version": version_id(rules), "final_rules": list(rules),
               "kept_edits": [h["kept"] for h in history if h["kept"]], "pilot_spend_usd": pilot.spend.total_usd,
               "per_round": [{"round": h["round"], "practice_credit": h["practice"]["mean_credit"],
                              "gate_current_credit": h["gate_current"]["mean_credit"],
                              "candidates": [(c["edit"]["text"], c["decision"]["mean_diff"], c["decision"]["p_value"], c["decision"]["keep"])
                                             for c in h["gate_candidates"]]} for h in history]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print("written: phase1/pilot/summary.json", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("split").set_defaults(fn=cmd_split)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
