"""Jev verifier, second design (D2). Canonical design, Takes: "Jev verifier, second design" (pre-registered 2026-10-10).

    .venv/bin/python scripts/jev_verifier_d2.py develop    # variants V1..V4 on development runs; picks one (development only)
    .venv/bin/python scripts/jev_verifier_d2.py validate   # the chosen variant on the fresh test bench runs, opened once

Runs: the final playbook's checkpoint-on runs (label practice-all, bench, and the two fresh draws). Development =
runs on practice tasks; validation = the FRESH draws on test bench tasks only. The sealed set is never touched.
Variants: V1 the first verifier (frozen instructions); V2 mean over 3 independent question sets; V3 = V2 averaged
with a policy-compliance question set; V4 = V3 averaged with the worst single write's check.
"""
import argparse
import glob
import importlib.util
import json
import statistics as st
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import evalstats  # noqa: E402
from jevloop.rubric import Question, contributions  # noqa: E402
from jevloop.verifier import (COMPLIANCE_WRITER, WRITE_CHECK_QUESTIONS, build_state, build_write_state, make_questions,  # noqa: E402
                              policy_text, verifier_score, write_calls)

OUT = ROOT / "phase1" / "run" / "take2"
SPLITS = ROOT / "phase1" / "splits"
WORKERS, SETS, MIN_GAIN = 8, 3, 0.02
VARIANTS = ("V1", "V2", "V3", "V4")


def split(name: str) -> list[str]:
    return (SPLITS / f"{name}.txt").read_text().split()


def phase1():
    spec = importlib.util.spec_from_file_location("phase1_run", ROOT / "scripts" / "phase1_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Phase1(paid=False)


def load_final_runs(final: str) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(str(ROOT / "logs" / "phase1_run" / f"minimax-p1-{final}-cp-*.jsonl"))):
        label = Path(path).name[len(f"minimax-p1-{final}-cp-"):-len(".jsonl")]
        if label not in ("practice-all", "bench", "fresh"):
            continue
        for line in open(path):
            r = json.loads(line)
            rows.append({"key": f"{label}|{r['task_id']}|{r.get('candidate', 0)}", "task": r["task_id"], "label": label, "group": final,
                         "credit": r["partial_credit"], "calls": r["calls"], "summary": r["summary"],
                         "missed": [c["kind"] for c in r.get("checks", []) if not c["passed"]]})
    return rows


class D2:
    def __init__(self):
        self.p = phase1()
        self.instr = (OUT / "verifier_instructions_final.txt").read_text().strip()

    def question_sets(self, task_ids: list[str]) -> dict:
        def gen(client, instr, tag):
            def one(t):
                task = self.p.tasks[t]
                return t, make_questions(client, instr, t, task.public.trigger, policy_text(task.initial_state), tag=tag)
            with ThreadPoolExecutor(WORKERS) as pool:
                return dict(pool.map(one, task_ids))
        sets = {"v1": gen(self.p.minimax, self.instr, "d2v1"), "compliance": gen(self.p.minimax, COMPLIANCE_WRITER, "d2compliance")}
        for k in range(SETS):
            sets[f"s{k}"] = gen(self.p.editor_client, self.instr, f"d2s{k}")
        return sets

    def mean_p(self, state: str, questions: list[Question], tag: str, task: str) -> float:
        out = self.p.jev.evaluate(state, questions, {"event": "verifier_d2", "tag": tag, "task_id": task})
        return verifier_score(out["probabilities"])

    def score_run(self, r: dict, sets: dict) -> dict:
        task = self.p.tasks[r["task"]]
        req, init = task.public.trigger, task.initial_state
        state = build_state(req, init, r["calls"], r["summary"])
        v1 = self.mean_p(state, sets["v1"][r["task"]], "v1", r["task"])
        v2 = st.mean(self.mean_p(state, sets[f"s{k}"][r["task"]], f"s{k}", r["task"]) for k in range(SETS))
        comp = self.mean_p(state, sets["compliance"][r["task"]], "compliance", r["task"])
        v3 = 0.5 * v2 + 0.5 * comp
        wq = [Question(f"w{i + 1}", t, "helps") for i, t in enumerate(WRITE_CHECK_QUESTIONS)]
        n_writes = len(write_calls(r["calls"]))
        worst = min((self.mean_p(build_write_state(req, init, r["calls"], i), wq, "write", r["task"]) for i in range(n_writes)), default=None)
        v4 = v3 if worst is None else 0.5 * v3 + 0.5 * worst
        return {**{k: r[k] for k in ("key", "task", "label", "group", "credit", "missed")}, "V1": v1, "V2": v2, "V3": v3, "V4": v4,
                "worst_write": worst, "n_writes": n_writes}

    def score_all(self, rows: list[dict]) -> list[dict]:
        sets = self.question_sets(sorted({r["task"] for r in rows}))
        with ThreadPoolExecutor(WORKERS) as pool:
            return list(pool.map(lambda r: self.score_run(r, sets), rows))


def metrics(scored: list[dict], variant: str) -> dict:
    return evalstats.evaluate([{"task": r["task"], "group": r["group"], "score": r[variant], "credit": r["credit"]} for r in scored], boot=1000)


def line(name: str, m: dict) -> str:
    return (f"{name}: n={m['n_runs']} runs, {m['n_tasks']} tasks | AUC {m['auc_within_playbook']:.3f} [{m['auc_ci95'][0]:.3f}, {m['auc_ci95'][1]:.3f}]"
            f" | lowest 30% {m['credit_low']:.3f} vs rest {m['credit_rest']:.3f} (gap {m['gap']:+.3f})")


def choose(dev: dict[str, dict]) -> str:
    best = max(VARIANTS, key=lambda v: dev[v]["auc_within_playbook"])
    return best if dev[best]["auc_within_playbook"] >= dev["V1"]["auc_within_playbook"] + MIN_GAIN else "V1"


def cmd_develop(_args) -> None:
    final = json.loads((OUT / "skill_final.json").read_text())["version"]
    practice = set(split("practice"))
    rows = [r for r in load_final_runs(final) if r["task"] in practice]
    n_fresh = sum(r["label"] == "fresh" for r in rows)
    if n_fresh < 100:
        sys.exit(f"STOP: only {n_fresh} fresh development runs so far; run the `fresh` stage to completion first.")
    d = D2()
    s0 = d.p.spend.total_usd
    scored = d.score_all(rows)
    dev = {v: metrics(scored, v) for v in VARIANTS}
    for v in VARIANTS:
        print(line(f"development {v}", dev[v]), flush=True)
    pick = choose(dev)
    print(f"CHOSEN on development: {pick} (needs +{MIN_GAIN} AUC over V1 to replace it); Jev and question spend ${d.p.spend.total_usd - s0:.2f}", flush=True)
    (OUT / "verifier_d2_development.json").write_text(json.dumps({"metrics": dev, "chosen": pick, "n_runs": len(rows)}, indent=2) + "\n")


def cmd_validate(args) -> None:
    dev_path = OUT / "verifier_d2_development.json"
    if not dev_path.exists():
        sys.exit("STOP: run `develop` first; the variant is chosen on development only.")
    done = OUT / "verifier_d2_validation.json"
    if done.exists() and not args.again:
        sys.exit("STOP: the D2 validation was already opened; it is opened once.")
    pick = json.loads(dev_path.read_text())["chosen"]
    final = json.loads((OUT / "skill_final.json").read_text())["version"]
    gate = set(split("gate"))
    rows = [r for r in load_final_runs(final) if r["task"] in gate and r["label"] == "fresh"]
    d = D2()
    s0 = d.p.spend.total_usd
    scored = d.score_all(rows)
    res = {v: metrics(scored, v) for v in VARIANTS}
    for v in VARIANTS:
        print(line(f"validation {v}" + ("  <- chosen" if v == pick else ""), res[v]), flush=True)
    kinds = {}
    for kind in ("rule_broken", "action_missed", "wrong_content"):
        rr = [{"task": r["task"], "group": r["group"], "score": -r[pick], "credit": 1.0 if kind in r["missed"] else 0.0} for r in scored]
        kinds[kind] = {"runs_with_miss": sum(kind in r["missed"] for r in scored), "auc_low_score_flags_miss": evalstats.grouped_auc(rr)}
    met = evalstats.bar_met(res[pick])
    print(f"per kind (low score flags a miss; 0.5 = none): { {k: round(v['auc_low_score_flags_miss'], 3) for k, v in kinds.items()} }", flush=True)
    print(f"BAR MET (chosen {pick}): {met}; spend ${d.p.spend.total_usd - s0:.2f}", flush=True)
    done.write_text(json.dumps({"chosen": pick, "metrics": res, "per_kind": kinds, "bar_met": met,
                                "scores": [{k: r[k] for k in ("key", "task", "label", "credit", *VARIANTS, "worst_write", "n_writes")} for r in scored]},
                               indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("develop").set_defaults(fn=cmd_develop)
    v = sub.add_parser("validate")
    v.add_argument("--again", action="store_true")
    v.set_defaults(fn=cmd_validate)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
