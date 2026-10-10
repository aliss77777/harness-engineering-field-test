"""Jev as a verifier: develop on practice tasks, validate once on test bench tasks (canonical design, Takes).

    .venv/bin/python scripts/jev_verifier.py baseline [--limit-tasks N]   # v0 instructions on development runs
    .venv/bin/python scripts/jev_verifier.py learn                        # edit the question writer's instructions (development only)
    .venv/bin/python scripts/jev_verifier.py validate                     # frozen instructions, test bench runs, opened once

Development runs = every logged checkpoint-on MiniMax run on a practice task; validation runs = the same on a
test bench task. The sealed set is never touched. Outputs: phase1/run/take2/verifier_*.json.
"""
import argparse
import glob
import importlib.util
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import evalstats  # noqa: E402
from jevloop.rubric import Question  # noqa: E402
from jevloop.verifier import QUESTION_WRITER_V0, build_state, make_questions, policy_text, verifier_score  # noqa: E402

OUT = ROOT / "phase1" / "run" / "take2"
SPLITS = ROOT / "phase1" / "splits"
WORKERS = 8
MIN_AUC_GAIN = 0.02      # fixed in the canonical design: keep an instruction edit if development AUC rises by this much
ROUNDS, CANDIDATES = 3, 2
MAX_INSTRUCTION_CHARS = 3000


def split(name: str) -> list[str]:
    return (SPLITS / f"{name}.txt").read_text().split()


def phase1():
    spec = importlib.util.spec_from_file_location("phase1_run", ROOT / "scripts" / "phase1_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Phase1(paid=False)


def load_runs(task_ids: set[str]) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(str(ROOT / "logs" / "phase1_run" / "minimax-p1-*-cp-*.jsonl"))):
        name = Path(path).name
        version, label = name[len("minimax-p1-"):-len(".jsonl")].split("-cp-", 1)
        for line in open(path):
            r = json.loads(line)
            if r["task_id"] in task_ids:
                rows.append({"key": f"{name}|{r['task_id']}", "task": r["task_id"], "group": version, "label": label,
                             "credit": r["partial_credit"], "calls": r["calls"], "summary": r["summary"],
                             "missed": [c["kind"] for c in r.get("checks", []) if not c["passed"]]})
    return rows


class Verifier:
    def __init__(self):
        self.p = phase1()

    def questions_for(self, instructions: str, tag: str, task_ids: list[str]) -> dict[str, list[Question]]:
        def one(t):
            task = self.p.tasks[t]
            return t, make_questions(self.p.minimax, instructions, t, task.public.trigger, policy_text(task.initial_state), tag=tag)
        with ThreadPoolExecutor(WORKERS) as pool:
            return dict(pool.map(one, task_ids))

    def score_runs(self, rows: list[dict], qmap: dict[str, list[Question]], tag: str) -> list[dict]:
        def one(r):
            task = self.p.tasks[r["task"]]
            state = build_state(task.public.trigger, task.initial_state, r["calls"], r["summary"])
            out = self.p.jev.evaluate(state, qmap[r["task"]], {"event": "verifier", "tag": tag, "task_id": r["task"]})
            return {**{k: r[k] for k in ("key", "task", "group", "label", "credit", "missed")}, "score": verifier_score(out["probabilities"]),
                    "probs": out["probabilities"], "state_chars": len(state)}
        with ThreadPoolExecutor(WORKERS) as pool:
            return list(pool.map(one, rows))

    def evaluate(self, instructions: str, tag: str, rows: list[dict]) -> tuple[dict, list[dict], dict]:
        qmap = self.questions_for(instructions, tag, sorted({r["task"] for r in rows}))
        scored = self.score_runs(rows, qmap, tag)
        return evalstats.evaluate(scored), scored, qmap


def show(name: str, m: dict) -> None:
    print(f"{name}: n={m['n_runs']} runs, {m['n_tasks']} tasks | within-playbook AUC {m['auc_within_playbook']:.3f} "
          f"[{m['auc_ci95'][0]:.3f}, {m['auc_ci95'][1]:.3f}] | within-task {m['auc_within_task']:.3f} | pooled {m['auc_pooled']:.3f} | "
          f"lowest 30%: {m['credit_low']:.3f} vs rest {m['credit_rest']:.3f} (gap {m['gap']:+.3f})", flush=True)


def cmd_baseline(args) -> None:
    v = Verifier()
    tasks = split("practice")
    if args.limit_tasks:
        tasks = sorted(random.Random(1).sample(tasks, args.limit_tasks))
    rows = load_runs(set(tasks))
    spend0 = v.p.spend.total_usd
    m, scored, qmap = v.evaluate(QUESTION_WRITER_V0, "v0", rows)
    show("development, v0 instructions", m)
    print(f"mean state size {sum(r['state_chars'] for r in scored) / len(scored):.0f} chars; questions per task "
          f"{sum(len(q) for q in qmap.values()) / len(qmap):.1f}; Jev + question spend ${v.p.spend.total_usd - spend0:.3f}", flush=True)
    if not args.limit_tasks:
        (OUT / "verifier_baseline.json").write_text(json.dumps({"metrics": m, "instructions": QUESTION_WRITER_V0}, indent=2) + "\n")


EDITOR_SYSTEM = """You improve the instructions given to a model that writes verification questions for a checker. The checker reads
a record of what an AI agent did on a business task (messages sent, records changed, source data read) and answers each
question yes or no; a run's score is the average of its yes answers, and the scores are used to rank runs from most to
least likely to be correct. You will see the current instructions and examples of runs the ranking got wrong: runs that
scored high but were actually poor (false assurance) and runs that scored low but were actually good (false alarm), with the
questions that were written for that task and which parts of the work were wrong. Rewrite the instructions so the questions
catch the kinds of mistakes that were missed without condemning good runs. Keep them general (no task-specific values, no
names or amounts). Reply with JSON only: {"instructions": "..."} where instructions is at most %d characters."""


def editor_messages(instructions: str, examples: list[dict]) -> list[dict]:
    body = []
    for e in examples:
        body.append(f"- {e['kind']}: score {e['score']:.2f}, actual credit {e['credit']:.2f}; wrong: {', '.join(sorted(set(e['missed']))) or 'nothing recorded'}\n"
                    f"  request: {e['request'][:500]}\n  questions: " + " | ".join(q.text[:160] for q in e["questions"][:8]))
    return [{"role": "system", "content": EDITOR_SYSTEM % MAX_INSTRUCTION_CHARS},
            {"role": "user", "content": f"CURRENT INSTRUCTIONS\n{instructions}\n\nRUNS THE RANKING GOT WRONG\n" + "\n".join(body)}]


def cmd_learn(args) -> None:
    v = Verifier()
    rows = load_runs(set(split("practice")))
    instructions = QUESTION_WRITER_V0
    m, scored, qmap = v.evaluate(instructions, "v0", rows)
    show("development, v0 instructions", m)
    history = [{"round": 0, "instructions": instructions, "metrics": m}]
    rng = random.Random(20261010)
    for rnd in range(1, ROUNDS + 1):
        by_group: dict = {}
        for r in scored:
            by_group.setdefault(r["group"], []).append(r)
        wrong = []
        for g in by_group.values():  # within each playbook: the highest-scoring poor runs and the lowest-scoring good runs
            poor = sorted((r for r in g if r["credit"] < 0.8), key=lambda r: -r["score"])[:6]
            good = sorted((r for r in g if r["credit"] >= 0.8), key=lambda r: r["score"])[:6]
            wrong += [{**r, "kind": "false assurance"} for r in poor] + [{**r, "kind": "false alarm"} for r in good]
        rng.shuffle(wrong)
        examples = [{**r, "request": v.p.tasks[r["task"]].public.trigger, "questions": qmap[r["task"]]} for r in wrong[:10]]
        cands = []
        for k in range(CANDIDATES):
            reply = v.p.editor_client.complete(editor_messages(instructions, examples), [], cache_key={"verifier_editor": rnd, "k": k},
                                               event={"event": "verifier_editor", "round": rnd, "k": k})
            try:
                text = json.loads(reply["message"]["content"][reply["message"]["content"].find("{"):reply["message"]["content"].rfind("}") + 1])["instructions"].strip()
            except Exception as error:  # noqa: BLE001
                print(f"  round {rnd} candidate {k}: unparseable ({error})", flush=True)
                continue
            if 200 <= len(text) <= MAX_INSTRUCTION_CHARS and text != instructions:
                cands.append(text)
        results = []
        for k, text in enumerate(cands):
            mc, sc, qm = v.evaluate(text, f"r{rnd}c{k}", rows)
            gain = mc["auc_within_playbook"] - m["auc_within_playbook"]
            print(f"  round {rnd} candidate {k}: development AUC {mc['auc_within_playbook']:.3f} ({gain:+.3f}) -> {'KEEP' if gain >= MIN_AUC_GAIN else 'reject'}", flush=True)
            results.append((gain, text, mc, sc, qm))
        kept = [x for x in results if x[0] >= MIN_AUC_GAIN]
        winner = max(kept, key=lambda x: x[0]) if kept else None
        if winner:
            _, instructions, m, scored, qmap = winner
        history.append({"round": rnd, "candidates": [{"gain": g, "auc": mc["auc_within_playbook"], "text": t} for g, t, mc, _, _ in results],
                        "kept": bool(winner), "instructions": instructions, "metrics": m})
        (OUT / "verifier_learning.json").write_text(json.dumps(history, indent=2) + "\n")
    (OUT / "verifier_instructions_final.txt").write_text(instructions + "\n")
    show("development, final instructions", m)
    print(f"final instructions saved; spend ${v.p.spend.total_usd:.2f}", flush=True)


def cmd_validate(args) -> None:
    path = OUT / "verifier_instructions_final.txt"
    if not path.exists():
        sys.exit("STOP: no frozen instructions (run `learn` first). Validation is opened once.")
    done = OUT / "verifier_validation.json"
    if done.exists() and not args.again:
        sys.exit(f"STOP: validation already opened ({done.name}); it is opened once.")
    instructions = path.read_text().strip()
    v = Verifier()
    rows = load_runs(set(split("gate")))
    m, scored, qmap = v.evaluate(instructions, "validation", rows)
    show("validation (test bench), frozen instructions", m)
    final = json.loads((OUT / "skill_final.json").read_text())["version"]
    fin_rows = [r for r in scored if r["group"] == final and r["label"] == "bench"]
    mf = {"n_final_playbook_runs": len(fin_rows), "auc": evalstats.auc([r["score"] for r in fin_rows], [r["credit"] >= 0.8 for r in fin_rows]),
          **evalstats.lowest_share_gap(fin_rows)}
    print(f"final playbook only: n={mf['n_final_playbook_runs']} AUC {mf['auc']:.3f}; lowest 30% {mf['credit_low']:.3f} vs rest {mf['credit_rest']:.3f}", flush=True)
    print(f"BAR MET: {evalstats.bar_met(m)}", flush=True)
    done.write_text(json.dumps({"metrics": m, "final_playbook_only": mf, "bar_met": evalstats.bar_met(m), "instructions": instructions,
                                "scores": [{k: r[k] for k in ('key', 'task', 'group', 'label', 'credit', 'score')} for r in scored]}, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("baseline")
    b.add_argument("--limit-tasks", type=int, default=0)
    b.set_defaults(fn=cmd_baseline)
    sub.add_parser("learn").set_defaults(fn=cmd_learn)
    va = sub.add_parser("validate")
    va.add_argument("--again", action="store_true")
    va.set_defaults(fn=cmd_validate)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
