"""Derived numbers behind the canonical memo's results tables (no model calls; Jev answers come from the cache).

    .venv/bin/python scripts/sealed_analysis.py

Reads the logged runs and the saved results, writes phase1/run/take2/sealed_analysis.json. Everything the memo
cites as "derived" comes from here: the router against random escalation, the review-queue curve, the
read-policies-first rates, the practice cross-check, the neighbour-playbook spread and the ceiling-check extras.
"""
import importlib.util
import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop import bench  # noqa: E402
from jevloop.diagnostics import read_policy_before_first_write  # noqa: E402

LOGS, OUT = ROOT / "logs" / "phase1_run", ROOT / "phase1" / "run" / "take2"
FINAL = json.loads((OUT / "skill_final.json").read_text())["version"]


def runs(name: str) -> dict[str, dict]:
    out = {}
    for line in open(LOGS / f"{name}.jsonl"):
        r = json.loads(line)
        out[r["task_id"]] = r
    return out


def boot_mean(xs, n=4000, seed=5):
    rng = random.Random(seed)
    b = sorted(st.mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return st.mean(xs), [b[int(0.025 * n)], b[int(0.975 * n) - 1]]


def main() -> None:
    res: dict = {}
    # ---------- sealed exam ----------
    fin, off, v0 = runs(f"minimax-p1-{FINAL}-cp-sealed"), runs(f"minimax-p1-{FINAL}-nocp-sealed"), runs("minimax-p1-v0-cp-sealed")
    gem, redo = runs("gemini-p1-v0-nocp-sealed"), runs("gemini-p1-v0-nocp-sealed-redo")
    ids = sorted(fin)
    cut = json.loads((OUT / "jev_cutoff_second_attempt.json").read_text())["cutoff"]
    spec = importlib.util.spec_from_file_location("phase1_run", ROOT / "scripts" / "phase1_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Run:  # what verifier_scores reads
        def __init__(self, r):
            self.calls, self.summary = r["calls"], r["summary"]
    p = mod.Phase1(paid=False)
    score = mod.verifier_scores(p, {t: Run(r) for t, r in fin.items()})
    mm = {t: fin[t]["partial_credit"] for t in ids}
    gm = {t: gem[t]["partial_credit"] for t in ids}
    esc = [t for t in ids if score[t] < cut]
    router = {t: (redo[t]["partial_credit"] if t in redo else mm[t]) for t in ids}
    share = len(esc) / len(ids)
    rand = {t: mm[t] + share * (gm[t] - mm[t]) for t in ids}
    m, ci = boot_mean([router[t] - rand[t] for t in ids])
    poor = [t for t in ids if mm[t] < 0.8]
    order = sorted(ids, key=lambda t: score[t])
    queue = {}
    for x in (0.2, 0.3, 0.45, 0.6):
        top = set(order[: round(x * len(ids))])
        queue[str(x)] = {"reviewed": len(top), "poor_found": sum(t in top for t in poor), "poor_total": len(poor)}
    tasks = {t.task_id: t for t in bench.load_tasks(["finance", "hr"])}

    def read_first(rs):
        v = [read_policy_before_first_write(tasks[t], r["calls"]) for t, r in rs.items()]
        v = [x for x in v if x is not None]
        return {"yes": sum(v), "n": len(v), "share": sum(v) / len(v)}
    res["sealed"] = {
        "arms": {name: {"credit": st.mean(r["partial_credit"] for r in rs.values()), "fully_passed": sum(r["passed"] for r in rs.values()),
                        "cost_per_run": st.mean(r["cost_usd"] for r in rs.values()), "holds_per_run": st.mean(r.get("holds", 0) for r in rs.values()),
                        "reads_all_policies_first": read_first(rs)}
                 for name, rs in (("starting_playbook_checkpoint_on", v0), ("final_playbook_checkpoint_on", fin),
                                  ("final_playbook_checkpoint_off", off), ("gemini_alone", gem))},
        "cutoff": cut, "escalated": len(esc), "escalated_share": share,
        "minimax_credit_escalated": st.mean(mm[t] for t in esc), "minimax_credit_kept": st.mean(mm[t] for t in ids if t not in esc),
        "gemini_redo_credit_escalated": st.mean(redo[t]["partial_credit"] for t in esc), "gemini_alone_credit_escalated": st.mean(gm[t] for t in esc),
        "router_credit": st.mean(router.values()), "router_fully_passed": sum(router[t] >= 0.999 for t in ids),
        "random_escalation_expected_credit": st.mean(rand.values()),
        "router_minus_random_escalation": {"mean": m, "interval_95": ci},
        "review_queue": queue,
    }
    # ---------- test bench learning path and neighbour spread ----------
    names = {"starting_playbook": "v0", "R1a": "sc9e21881", "R1a_R2x_final": FINAL}
    bench_runs = {k: runs(f"minimax-p1-{v}-cp-bench") for k, v in names.items()}
    res["test_bench"] = {k: {"credit": st.mean(r["partial_credit"] for r in rs.values()), "fully_passed": sum(r["passed"] for r in rs.values())}
                         for k, rs in bench_runs.items()}
    neigh = ["sb0620aa3", "sa0786ff2", "s6bf9536d", "s80b74ef2", "sf667277c", "s3e9907ba", "sc9516927"]
    vals = [st.mean(r["partial_credit"] for r in runs(f"minimax-p1-{v}-cp-bench").values()) for v in neigh]
    res["test_bench"]["seven_neighbour_playbooks"] = {"mean": st.mean(vals), "sd": st.stdev(vals), "min": min(vals), "max": max(vals)}
    # ---------- practice cross-check (final vs starting playbook on shared practice tasks) ----------
    v0p = {}
    for lab in ("practice-r1", "practice-r2"):
        for t, r in runs(f"minimax-p1-v0-cp-{lab}").items():
            v0p.setdefault(t, []).append(r["partial_credit"])
    finp = runs(f"minimax-p1-{FINAL}-cp-practice-all")
    shared = sorted(set(v0p) & set(finp))
    dm, dci = boot_mean([finp[t]["partial_credit"] - st.mean(v0p[t]) for t in shared])
    res["practice_cross_check"] = {"n_tasks": len(shared), "starting": st.mean(st.mean(v0p[t]) for t in shared),
                                   "final": st.mean(finp[t]["partial_credit"] for t in shared), "diff": dm, "interval_95": dci}
    # ---------- ceiling-check extras ----------
    ceil = json.loads((OUT / "ceiling.json").read_text())
    first = {}
    for lab in ("practice-all", "bench"):
        first.update({t: r["partial_credit"] for t, r in runs(f"minimax-p1-{FINAL}-cp-{lab}").items()})
    fresh = {}
    for line in open(LOGS / f"minimax-p1-{FINAL}-cp-fresh.jsonl"):
        r = json.loads(line)
        fresh.setdefault(r["task_id"], []).append(r["partial_credit"])
    gcre = {t: r["partial_credit"] for t, r in runs("gemini-p1-v0-nocp-ceiling").items()}
    failed = sorted(gcre)
    fresh_mean = {t: st.mean(v) for t, v in fresh.items()}
    base_fresh = st.mean(fresh_mean[t] for t in first)
    res["ceiling_extras"] = {
        "failed_tasks": len(failed), "minimax_first_run_on_failed": st.mean(first[t] for t in failed),
        "minimax_fresh_draws_on_failed": st.mean(fresh_mean[t] for t in failed), "gemini_on_failed": st.mean(gcre[t] for t in failed),
        "perfect_router_vs_fresh_baseline": st.mean(gcre[t] if t in gcre else fresh_mean[t] for t in first) - base_fresh,
        "rerun_when_first_run_failed": st.mean(fresh_mean[t] if t in gcre else first[t] for t in first) - st.mean(first.values()),
        "ceiling_json": {k: ceil[k] for k in ("minimax_alone", "perfect_router_escalating_all_failures", "perfect_router_escalating_worst_30pct")}}
    (OUT / "sealed_analysis.json").write_text(json.dumps(res, indent=2) + "\n")
    s = res["sealed"]
    print(f"router vs random escalation: {s['router_minus_random_escalation']['mean']:+.3f} {s['router_minus_random_escalation']['interval_95']}")
    print("review queue:", s["review_queue"])
    print("reads policies first:", {k: round(v["reads_all_policies_first"]["share"], 2) for k, v in s["arms"].items()})
    print("practice cross-check:", res["practice_cross_check"])
    print("neighbours:", res["test_bench"]["seven_neighbour_playbooks"])
    print("ceiling extras:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res["ceiling_extras"].items() if k != "ceiling_json"})


if __name__ == "__main__":
    main()
