import json
import random

import numpy as np
import pytest

from bandit import ThompsonPolicy, explore, hit, jev_pick, lift, observe, regret, router_tau
from learn_bandit import feedback, gate_outcome
from verdict_bandit import compute_bandit_verdict

RUBRIC = [{"question_id": "q1", "text": "Q1?", "direction": "helps"}]


def make_test(tid, ctrs):
    return {"test_id": tid, "headlines": [f"headline {tid}-{i}" for i in range(len(ctrs))],
            "ctr": ctrs, "impressions": [1000 + i for i in range(len(ctrs))]}


def test_metrics_relative_to_random_and_best():
    t = make_test("a", [0.01, 0.02, 0.03])
    assert lift(t, 2) == pytest.approx(50.0) and lift(t, 1) == pytest.approx(0.0)
    assert regret(t, 0) == pytest.approx(2 / 3) and hit(t, 2) and not hit(t, 1)


def test_observe_returns_only_the_chosen_outcome():
    assert observe(make_test("a", [0.01, 0.02, 0.03]), 1) == {"ctr": 0.02, "impressions": 1001}


def test_exploration_is_seeded_changes_pick_and_hits_rate():
    tests = [make_test(str(i), [0.01, 0.02, 0.03, 0.04]) for i in range(2000)]
    runs = [[explore(t, 0, rate=0.15, seed=1, round_number=1) for t in tests] for _ in range(2)]
    assert runs[0] == runs[1]
    explored = [p for p, e in runs[0] if e]
    assert all(p != 0 for p in explored) and 0.12 < len(explored) / len(tests) < 0.18


def test_router_tau_is_label_free_share():
    margins = list(np.linspace(0, 1, 100))
    assert sum(m < router_tau(margins, 0.4) for m in margins) == 40


def test_jev_pick_margin_and_seeded_tie():
    t = make_test("a", [0.1, 0.2, 0.3])
    assert jev_pick(t, {"scores": [0.2, 0.9, 0.5]}, 1) == (1, pytest.approx(0.4))
    assert jev_pick(t, {"scores": [0.9, 0.9, 0.1]}, 1) == jev_pick(t, {"scores": [0.9, 0.9, 0.1]}, 1)


def test_feedback_never_leaks_unchosen_outcomes():
    rng = random.Random(0)
    tests = [make_test(str(i), [round(rng.uniform(0.001, 0.05), 6) for _ in range(4)]) for i in range(60)]
    decisions = [{"test_id": t["test_id"], "pick": i % 4, "greedy_pick": i % 4, "explored": i % 5 == 0,
                  "decided_by": "jev", "reason": "because", "blocked": False, "cost": 0.0, "latency_ms": 0.0,
                  "chosen_probs": {"q1": 0.7}} for i, t in enumerate(tests)]
    for arm in ("L", "J", "R"):
        out = feedback(arm, {"rubric_questions": RUBRIC}, tests, [dict(d) for d in decisions], count=20, seed=1,
                       round_number=1)
        text = json.dumps(out)
        chosen = {round(100 * t["ctr"][d["pick"]], 3) for t, d in zip(tests, decisions)}
        for t, d in zip(tests, decisions):
            for i, ctr in enumerate(t["ctr"]):
                value = round(100 * ctr, 3)
                if i != d["pick"] and value not in chosen:
                    assert str(value) not in text
        assert "best" not in text and "regret" not in text


def test_gate_compares_only_each_policys_own_pick():
    tests = [make_test(str(i), [0.01, 0.03]) for i in range(40)]
    old = [{"test_id": t["test_id"], "pick": 0} for t in tests]
    new = [{"test_id": t["test_id"], "pick": 1} for t in tests]
    outcome = gate_outcome(tests, old, new, 0.05)
    assert outcome.keep and outcome.b == 40 and outcome.c == 0
    assert not gate_outcome(tests, old, old, 0.05).keep


def test_thompson_learns_a_simple_feature_from_chosen_outcomes_only():
    policy = ThompsonPolicy(1.0, 0.25, seed=1)
    obs = [(f"Big question {i}?", 0.04) for i in range(100)] + [(f"Plain statement {i}", 0.01) for i in range(100)]
    policy.update(obs)
    t = {"test_id": "x", "headlines": ["Plain words here", "Is this the one?"], "ctr": [0.01, 0.04]}
    assert policy.pick(t, sample=False, round_number=0) == 1


def metrics(lifts, cost):
    return {"lift": lifts, "hit": [False] * len(lifts), "cost_per_1000": cost}


CONFIG = {"alpha": 0.05, "equivalence_margin_lift": 5.0, "bootstrap_resamples": 2000, "memorization_hit_rate": 0.7}


def verdict(r, l, r_cost=0.6, l_cost=1.5):
    base = {"R_final": metrics(r, r_cost), "L_final": metrics(l, l_cost), "J_final": metrics(r, 0.07),
            "R_version0": metrics(l, r_cost), "L_version0": metrics(l, l_cost), "J_version0": metrics(l, 0.07),
            "C_final": metrics(l, 0), "R_final_with_L_final": metrics(r, r_cost)}
    return compute_bandit_verdict(metrics=base, config=CONFIG, max_cost_ratio=0.5)


def test_bandit_verdict_rows():
    rng = np.random.default_rng(0)
    base = rng.normal(15, 20, 1000)
    assert verdict(list(base), list(base))["verdict"] == "same_quality_half_cost"
    assert verdict(list(base), list(base), r_cost=1.4)["verdict"] == "same_quality_not_cheap_enough"
    assert verdict(list(base + 10), list(base))["verdict"] == "router_beats_llm"
    assert verdict(list(base - 10), list(base))["verdict"] == "routing_costs_quality"
    noise = rng.normal(0, 1, 1000)
    assert verdict(list(noise), list(noise))["verdict"] == "no_signal"
