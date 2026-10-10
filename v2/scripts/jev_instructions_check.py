"""Did learning the question writer's instructions help on fresh data? (outside the pipeline; Alexander approved, 2026-10-10)

Scores the fresh test bench runs of the final playbook with the STARTING question-writer instructions and compares
with the learned instructions (variant 1 of the second attempt, already scored in verifier_d2_validation.json).
Same runs, same scoring (mean P(yes) over one question set); only the instructions differ. Cost: a few cents.
"""
import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import jev_verifier_d2 as d2  # noqa: E402
from jevloop import evalstats  # noqa: E402
from jevloop.verifier import QUESTION_WRITER_V0, build_state, make_questions, policy_text, verifier_score  # noqa: E402

OUT = ROOT / "phase1" / "run" / "take2"


def main() -> None:
    final = json.loads((OUT / "skill_final.json").read_text())["version"]
    gate = set(d2.split("gate"))
    rows = [r for r in d2.load_final_runs(final) if r["task"] in gate and r["label"] == "fresh"]
    learned = {s["key"]: s["V1"] for s in json.loads((OUT / "verifier_d2_validation.json").read_text())["scores"]}
    d = d2.D2()
    s0 = d.p.spend.total_usd
    tasks = sorted({r["task"] for r in rows})
    qs = {t: make_questions(d.p.minimax, QUESTION_WRITER_V0, t, d.p.tasks[t].public.trigger, policy_text(d.p.tasks[t].initial_state), tag="check-v0")
          for t in tasks}
    out = []
    for r in rows:
        task = d.p.tasks[r["task"]]
        state = build_state(task.public.trigger, task.initial_state, r["calls"], r["summary"])
        probs = d.p.jev.evaluate(state, qs[r["task"]], {"event": "instructions_check", "task_id": r["task"]})["probabilities"]
        out.append({"task": r["task"], "group": r["group"], "credit": r["credit"], "starting": verifier_score(probs), "learned": learned[r["key"]]})
    res = {}
    for name in ("starting", "learned"):
        rr = [{"task": o["task"], "group": o["group"], "score": o[name], "credit": o["credit"]} for o in out]
        res[name] = evalstats.evaluate(rr, boot=1000)
        m = res[name]
        print(f"{name:9} instructions: AUC {m['auc_within_playbook']:.3f} [{m['auc_ci95'][0]:.3f}, {m['auc_ci95'][1]:.3f}] | lowest 30% {m['credit_low']:.3f} vs rest {m['credit_rest']:.3f} (gap {m['gap']:+.3f})")
    # paired bootstrap by task of (learned AUC - starting AUC)
    by = {}
    for o in out:
        by.setdefault(o["task"], []).append(o)
    rng, diffs = random.Random(7), []
    for _ in range(1000):
        s = [o for t in (rng.choice(tasks) for _ in tasks) for o in by[t]]
        a = lambda k: evalstats.auc([x[k] for x in s], [x["credit"] >= 0.8 for x in s])  # noqa: E731
        v = a("learned") - a("starting")
        if v == v:
            diffs.append(v)
    diffs.sort()
    diff = res["learned"]["auc_within_playbook"] - res["starting"]["auc_within_playbook"]
    print(f"learned minus starting AUC: {diff:+.3f} (95% interval {diffs[25]:+.3f} to {diffs[974]:+.3f}); spend ${d.p.spend.total_usd - s0:.3f}")
    (OUT / "verifier_instructions_check.json").write_text(json.dumps({"metrics": res, "auc_difference": diff, "auc_difference_ci95": [diffs[25], diffs[974]],
                                                                       "rows": out}, indent=2) + "\n")


if __name__ == "__main__":
    main()
