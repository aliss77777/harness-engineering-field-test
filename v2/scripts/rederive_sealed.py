"""Re-derive the sealed-exam headline numbers from the committed per-run table alone.

    python3 scripts/rederive_sealed.py        # standard library only; no logs, no cache, no API key, no network

Reads phase1/run/take2/sealed_runs.csv and jev_cutoff_second_attempt.json, recomputes the headline numbers, and
compares each one with the value published in phase1/run/take2/sealed_results.json. Point estimates must agree to
1e-6; intervals come from a seeded paired bootstrap and are compared at a looser tolerance. Exit code 1 on any
mismatch, so CI can run it.
"""
import csv
import json
import math
import random
import re
import statistics as st
import sys
from pathlib import Path

TAKE2 = Path(__file__).resolve().parent.parent / "phase1" / "run" / "take2"
TOL_POINT, TOL_INTERVAL = 1e-6, 0.01


def load():
    arms: dict[str, dict[str, dict]] = {}
    with open(TAKE2 / "sealed_runs.csv", newline="") as f:
        for r in csv.DictReader(f):
            arms.setdefault(r["arm"], {})[r["task_id"]] = {
                "credit": float(r["partial_credit"]), "passed": int(r["passed"]), "cost": float(r["cost_usd"]),
                "jev": float(r["jev_score"]) if r["jev_score"] else None}
    return arms


def paired_bootstrap(diffs, n=20000, seed=7):
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(n))
    return st.mean(diffs), [means[int(0.025 * n)], means[int(0.975 * n) - 1]]


def jev_call_cost() -> float:
    """The flat per-task checker cost the exam's router used (config_phase1.yaml, run.cost_estimate_per_run.jev_call)."""
    cfg = (TAKE2.parent.parent / "config_phase1.yaml").read_text()
    return float(re.search(r"\bjev_call:\s*([0-9.eE+-]+)", cfg).group(1))


def wilcoxon_greater_p(diffs):
    """One-sided Wilcoxon signed-rank p (normal approximation, zeros dropped, tie-corrected), as scipy's default."""
    nz = [d for d in diffs if d != 0]
    n = len(nz)
    order = sorted(range(n), key=lambda i: abs(nz[i]))
    ranks, i = [0.0] * n, 0
    tie_term = 0.0
    while i < n:
        j = i
        while j + 1 < n and abs(nz[order[j + 1]]) == abs(nz[order[i]]):
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        tie_term += (j - i + 1) ** 3 - (j - i + 1)
        i = j + 1
    w_plus = sum(r for r, d in zip(ranks, nz) if d > 0)
    mu = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - tie_term / 48)
    z = (w_plus - mu) / sd
    return 0.5 * math.erfc(z / math.sqrt(2))


def main() -> int:
    arms = load()
    ref = json.loads((TAKE2 / "sealed_results.json").read_text())
    cutoff = json.loads((TAKE2 / "jev_cutoff_second_attempt.json").read_text())["cutoff"]
    start, final = arms["starting_playbook_checkpoint_on"], arms["final_playbook_checkpoint_on"]
    off, gem, redo = arms["final_playbook_checkpoint_off"], arms["gemini_alone"], arms["gemini_redo_for_escalated"]
    ids = sorted(final)
    assert len(ids) == 80 and set(ids) == set(start) == set(gem) == set(off), "arms do not cover the same 80 tasks"

    escalated = [t for t in ids if final[t]["jev"] < cutoff]
    router_credit = {t: redo[t]["credit"] if t in redo else final[t]["credit"] for t in ids}
    share = len(escalated) / len(ids)

    checks: list[tuple[str, float, float, float]] = []  # name, ours, published, tolerance

    def check(name, ours, published, tol=TOL_POINT):
        checks.append((name, ours, published, tol))

    mean = lambda d, k="credit": st.mean(d[t][k] for t in ids)
    d_learn, ci_learn = paired_bootstrap([final[t]["credit"] - start[t]["credit"] for t in ids])
    d_gem, ci_gem = paired_bootstrap([final[t]["credit"] - gem[t]["credit"] for t in ids])
    d_router, ci_router = paired_bootstrap([router_credit[t] - gem[t]["credit"] for t in ids])

    a = ref["V2-2a_did_minimax_learn"]
    check("MiniMax starting playbook, credit", mean(start), a["starting"])
    check("MiniMax final playbook, credit", mean(final), a["final"])
    check("learning gain (final - starting)", d_learn, a["diff"])
    check("learning gain, interval low", ci_learn[0], a["interval_95"][0], TOL_INTERVAL)
    check("learning gain, interval high", ci_learn[1], a["interval_95"][1], TOL_INTERVAL)
    check("learning gain, one-sided Wilcoxon p", wilcoxon_greater_p([final[t]["credit"] - start[t]["credit"] for t in ids]),
          a["p_one_sided"], 1e-6)
    check("Gemini alone, credit", mean(gem), ref["V2-1_starting_line"]["gemini"])

    c = ref["V2-3_main_comparison"]
    check("router, credit", st.mean(router_credit.values()), c["credit"]["router"])
    check("router - Gemini, credit", d_router, c["credit"]["diff"])
    check("router - Gemini, interval low", ci_router[0], c["credit"]["interval_95"][0], TOL_INTERVAL)
    check("router - Gemini, interval high", ci_router[1], c["credit"]["interval_95"][1], TOL_INTERVAL)
    check("share escalated to Gemini", share, ref["router_jev"]["escalated_share"])
    router_cost = st.mean(final[t]["cost"] + jev_call_cost() + (redo[t]["cost"] if t in redo else 0.0) for t in ids)
    check("router, cost per task", router_cost, c["cost_per_task"]["router"])
    check("Gemini alone, cost per task", mean(gem, "cost"), c["cost_per_task"]["gemini"])
    check("router cost / Gemini cost", router_cost / mean(gem, "cost"), c["cost_per_task"]["ratio"])

    x = ref["minimax_final_vs_gemini_alone"]
    check("MiniMax final - Gemini alone, credit", d_gem, x["diff"]) if "diff" in x else None
    check("MiniMax final, cost per task", mean(final, "cost"), x["cost_per_task"]["minimax"]) \
        if isinstance(x.get("cost_per_task"), dict) and "minimax" in x["cost_per_task"] else None

    width = max(len(n) for n, *_ in checks)
    bad = 0
    print(f"{'quantity':<{width}}  {'re-derived':>11}  {'published':>11}  ok")
    for name, ours, pub, tol in checks:
        ok = abs(ours - pub) <= tol
        bad += not ok
        print(f"{name:<{width}}  {ours:>11.4f}  {pub:>11.4f}  {'yes' if ok else 'NO  <-- differs'}")
    print(f"\n{len(checks) - bad}/{len(checks)} match "
          f"(points to {TOL_POINT:g}; bootstrap intervals to {TOL_INTERVAL:g}, seeded, so method not seed-identical)")
    print(f"fully passed: starting {sum(start[t]['passed'] for t in ids)}, final {sum(final[t]['passed'] for t in ids)}, "
          f"final checkpoint off {sum(off[t]['passed'] for t in ids)}, Gemini {sum(gem[t]['passed'] for t in ids)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
