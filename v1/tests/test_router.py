import pytest

from router import route, tau_for_share
from verdict_router import compute_router_verdict


def test_tau_sends_the_target_share_to_the_llm():
    margins = [i / 10 for i in range(10)]
    tau = tau_for_share(margins, 0.4)
    assert sum(m < tau for m in margins) == 4


def rec(pid, prediction, winner, cost=0.0, blocked=False):
    return {"pair_id": pid, "prediction": prediction, "winner": winner, "cost": cost, "latency_ms": 10, "blocked": blocked}


def test_route_uses_jev_when_confident_llm_otherwise_and_jev_if_blocked():
    jev = [rec("1", "X", "X", 0.1), rec("2", "X", "Y", 0.1), rec("3", "Y", "Y", 0.1)]
    llm = [rec("1", "Y", "X", 1.0), rec("2", "Y", "Y", 1.0), rec("3", "X", "Y", 1.0, blocked=True)]
    out = route([0.9, 0.1, 0.1], jev, llm, tau=0.5)
    assert [r["decided_by"] for r in out] == ["jev", "llm", "jev"]
    assert [r["correct"] for r in out] == [True, True, True]
    assert [r["cost"] for r in out] == pytest.approx([0.1, 1.1, 1.1])  # routed pairs pay for the LLM call


def test_route_rejects_misaligned_records():
    with pytest.raises(ValueError):
        route([0.1], [rec("1", "X", "X")], [rec("2", "X", "X")], tau=0.5)


def v(n, total=1000):
    return [True] * n + [False] * (total - n)


CONFIG = {"alpha": 0.05, "equivalence_margin": 0.03, "mcnemar_exact_max_discordant": 25, "memorization_accuracy": 0.7}


def verdict(llm, router, cost_router):
    return compute_router_verdict(llm=llm, jev=v(700), router=router, baseline=None,
                                  costs_per_1000={"llm": 1.5, "jev": 0.06, "router": cost_router},
                                  config=CONFIG, max_cost_ratio=0.5)["verdict"]


def test_router_verdict_rows():
    assert verdict(v(740), v(800), 0.7) == "router_beats_llm"
    assert verdict(v(750), v(745), 0.7) == "same_quality_half_cost"
    assert verdict(v(750), v(745), 1.0) == "same_quality_not_cheap_enough"
    assert verdict(v(780), v(700), 0.7) == "routing_costs_accuracy"
    # -2 points with 100 discordant pairs: p 0.057 and interval (-4.0, -0.0) crosses -3
    unclear = [True] * 700 + [False] * 60 + [True] * 40 + [False] * 200
    assert verdict(v(760), unclear, 0.7) == "inconclusive"
