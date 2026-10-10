"""Jev refit, stage B1 (canonical design, Takes section; written 2026-10-10 before any result).

    .venv/bin/python scripts/jev_refit.py

Refits the weights of Take 2's final rubric on all labelled MiniMax runs, validated by 5-fold cross-validation
grouped by task, and tests on the final playbook's run on each held-out task. Jev's answers come from the
disk cache (new calls, if any, are paid and counted). It does not touch the sealed set, the final playbook or
the frozen rubric/cutoff files: it writes phase1/run/take2/jev_refit.json only.
"""
import argparse
import glob
import importlib.util
import json
import random
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop.rubric import GOOD_CREDIT, Question, contributions, fit_weights, is_good  # noqa: E402
from jevloop.runs import CandidateRun  # noqa: E402

OUT = ROOT / "phase1" / "run" / "take2"
FOLDS, SEED = 5, 20261010
BAR_AUC, BAR_AUC_LOWER, BAR_GAP = 0.65, 0.5, 0.10   # fixed in the canonical design before any result
ESCALATE_SHARE = 0.30


def auc(scores, good) -> float:
    pos = [s for s, g in zip(scores, good) if g]
    neg = [s for s, g in zip(scores, good) if not g]
    if not pos or not neg:
        return float("nan")
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def bootstrap_auc_lower(scores, good, *, n=2000, seed=SEED) -> tuple[float, float]:
    rng = random.Random(seed)
    idx = list(range(len(scores)))
    vals = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        a = auc([scores[i] for i in s], [good[i] for i in s])
        if a == a:
            vals.append(a)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def lowest_share_gap(scores, credits, share=ESCALATE_SHARE) -> dict:
    """Mean credit of the rest minus mean credit of the lowest-scoring `share` of runs."""
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    k = max(1, round(share * len(scores)))
    low, rest = order[:k], order[k:]
    lo, hi = st.mean(credits[i] for i in low), st.mean(credits[i] for i in rest)
    return {"n_low": len(low), "credit_low": lo, "credit_rest": hi, "gap": hi - lo}


def metrics(scores, credits) -> dict:
    good = [is_good(c) for c in credits]
    lo, hi = bootstrap_auc_lower(scores, good)
    maj = max(sum(good), len(good) - sum(good)) / len(good)
    return {"n": len(scores), "auc": auc(scores, good), "auc_ci95": [lo, hi], "good_share": sum(good) / len(good),
            "accuracy_majority_class": maj, "corr_with_credit": float(np.corrcoef(scores, credits)[0, 1]),
            **lowest_share_gap(scores, credits)}


def bar_met(m: dict) -> bool:
    return m["auc"] >= BAR_AUC and m["auc_ci95"][0] > BAR_AUC_LOWER and m["gap"] >= BAR_GAP


def fold_of(tasks: list[str], *, folds=FOLDS, seed=SEED) -> dict[str, int]:
    order = sorted(set(tasks))
    random.Random(seed).shuffle(order)
    return {t: i % folds for i, t in enumerate(order)}


def cross_validated_scores(rows, questions, *, c=1.0, folds=FOLDS, seed=SEED):
    """rows: dicts with task, probs, credit, test (bool: a run that is scored out of fold).
    Returns (out-of-fold score for each test row, in row order; weights fitted on all rows)."""
    fold = fold_of([r["task"] for r in rows], folds=folds, seed=seed)
    oof = {}
    for f in range(folds):
        train = [r for r in rows if fold[r["task"]] != f]
        w, b = fit_weights([r["probs"] for r in train], [r["credit"] for r in train], questions, c=c, seed=0)
        for i, r in enumerate(rows):
            if fold[r["task"]] == f and r["test"]:
                oof[i] = float(sum(x * w[q.question_id] for x, q in zip(contributions(r["probs"], questions), questions)) + b)
    w_all, b_all = fit_weights([r["probs"] for r in rows], [r["credit"] for r in rows], questions, c=c, seed=0)
    return [oof[i] for i in sorted(oof)], {"weights": w_all, "intercept": b_all}


def load_runs(final_version: str):
    """Every labelled checkpoint-on MiniMax run in the Phase 1 logs. `test` marks the one final-playbook run per
    task used for scoring: practice-all for practice tasks, the test bench for bench tasks."""
    rows = []
    for path in sorted(glob.glob(str(ROOT / "logs" / "phase1_run" / "minimax-p1-*-cp-*.jsonl"))):
        name = Path(path).name
        stem = name[len("minimax-p1-"):-len(".jsonl")]
        version, label = stem.split("-cp-", 1)
        for line in open(path):
            r = json.loads(line)
            run = CandidateRun(**{k: v for k, v in r.items() if k in CandidateRun.__dataclass_fields__})
            test = version == final_version and label in ("practice-all", "bench")
            rows.append({"key": f"{name}|{r['task_id']}", "task": r["task_id"], "credit": run.partial_credit, "run": run,
                         "version": version, "label": label, "test": test})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="count runs and print the plan; no Jev calls")
    args = ap.parse_args()
    final = json.loads((OUT / "skill_final.json").read_text())["version"]
    rb = json.loads((OUT / "rubric_final.json").read_text())
    q_final = tuple(Question(**q) for q in rb["questions"])
    q_start = tuple(Question(**q) for q in rb["v0"]["questions"])
    rows = load_runs(final)
    n_test = sum(r["test"] for r in rows)
    print(f"{len(rows)} labelled runs, {len({r['task'] for r in rows})} tasks, {n_test} test runs (final playbook {final}); "
          f"good share {st.mean(is_good(r['credit']) for r in rows):.2f}", flush=True)
    if args.dry:
        return

    spec = importlib.util.spec_from_file_location("phase1_run", ROOT / "scripts" / "phase1_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    p = mod.Phase1(paid=False)
    spend0 = p.spend.total_usd
    runs = {r["key"]: r["run"] for r in rows}
    feats = {}
    for tag, qs in (("final", q_final), ("start", q_start)):
        probs = p.jev_probs(qs, runs, f"refit-{tag}")
        feats[tag] = [{**r, "probs": probs[r["key"]]} for r in rows]
    test_credit = [r["credit"] for r in feats["final"] if r["test"]]
    test_tasks = [r["task"] for r in feats["final"] if r["test"]]

    results, saved = {}, {}
    for name, tag, qs, c in (("primary_final_rubric_refit_C1", "final", q_final, 1.0), ("start_rubric_refit_C1", "start", q_start, 1.0),
                             ("final_rubric_refit_C0.1", "final", q_final, 0.1), ("final_rubric_refit_C10", "final", q_final, 10.0)):
        scores, full = cross_validated_scores(feats[tag], qs, c=c)
        results[name] = metrics(scores, test_credit)
        saved[name] = {"weights_all": full, "oof_scores": dict(zip(test_tasks, scores))}
    # as-is baselines (no refit; weights were fitted on the practice-all runs, so these are partly in-sample)
    for name, tag, qs, key in (("as_is_start_rubric", "start", q_start, "v0"), ("as_is_final_rubric", "final", q_final, None)):
        w = rb["v0"]["weights"] if key == "v0" else rb["weights"]
        b = rb["v0"]["intercept"] if key == "v0" else rb["intercept"]
        sc = [float(sum(x * w[q.question_id] for x, q in zip(contributions(r["probs"], qs), qs)) + b) for r in feats[tag] if r["test"]]
        results[name] = metrics(sc, test_credit)

    primary = results["primary_final_rubric_refit_C1"]
    scores = list(saved["primary_final_rubric_refit_C1"]["oof_scores"].values())
    tau = float(np.quantile(scores, ESCALATE_SHARE))
    report = {"final_playbook": final, "n_runs": len(rows), "n_tasks": len({r['task'] for r in rows}), "n_test_runs": n_test,
              "bar": {"auc": BAR_AUC, "auc_ci95_lower_above": BAR_AUC_LOWER, "credit_gap": BAR_GAP},
              "bar_met": bar_met(primary), "tau_out_of_fold": tau, "escalate_share": ESCALATE_SHARE, "results": results,
              "primary_weights_all": saved["primary_final_rubric_refit_C1"]["weights_all"],
              "primary_oof_scores": saved["primary_final_rubric_refit_C1"]["oof_scores"],
              "new_jev_spend_usd": p.spend.total_usd - spend0}
    (OUT / "jev_refit.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, m in results.items():
        print(f"{name:32} n={m['n']} AUC {m['auc']:.3f} [{m['auc_ci95'][0]:.3f}, {m['auc_ci95'][1]:.3f}]  gap {m['gap']:+.3f} "
              f"(low {m['credit_low']:.3f} vs rest {m['credit_rest']:.3f})  corr {m['corr_with_credit']:+.3f}", flush=True)
    print(f"BAR MET: {report['bar_met']}   tau (out-of-fold, lowest 30%) = {tau:.4f}   new Jev spend ${report['new_jev_spend_usd']:.3f}", flush=True)


if __name__ == "__main__":
    main()
