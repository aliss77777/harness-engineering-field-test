"""Jev client (ported from v1), the rubric and its learning pieces, and the cascade Router. $0."""
import json

import httpx
import pytest

from jevloop.cache import DiskCache
from jevloop.cascade import route, set_tau, v2_3_verdict
from jevloop.jev import JevClient
from jevloop.log import JsonlLogger
from jevloop.openrouter import OutOfCreditsError, RouteMismatchError
from jevloop.rubric import (STARTING_RUBRIC, Question, RubricEdit, apply_rubric_edit, check_rubric_edit, classify,
                            fit_weights, keep_rubric_edit, parse_rubric_edits, score)
from jevloop.spend import SpendCapExceeded, SpendTracker

QS = (Question("a", "Did it read the policy?", "helps"), Question("b", "Did it email someone excluded?", "hurts"))


class Server:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def __call__(self, request):
        self.requests.append(json.loads(request.content))
        status, body = self.replies.pop(0)
        return httpx.Response(status, json=body)


def ok(probs, model="typesafe/jev-1.13-20260917", provider="TypeSafe", cost=0.0001):
    return 200, {"model": model, "provider": provider, "answers": {k: {"noul": v} for k, v in probs.items()},
                 "usage": {"input_tokens": 500, "output_tokens": 0, "cost": cost}}


def client(tmp_path, server, spend=None):
    return JevClient(model="typesafe/jev-1.13", expected_model="typesafe/jev-1.13-20260917", expected_provider="TypeSafe",
                     api_key="t", cache=DiskCache(tmp_path / "c"), logger=JsonlLogger(tmp_path / "l.jsonl"), spend=spend,
                     http_client=httpx.Client(transport=httpx.MockTransport(server)), sleep=lambda s: None)


def test_jev_request_format_matches_v1_and_caches(tmp_path):
    s = Server([ok({"a": 0.9, "b": 0.2})])
    c = client(tmp_path, s)
    out = c.evaluate("RUN SUMMARY", list(QS), {})
    assert out["probabilities"] == {"a": 0.9, "b": 0.2} and not out["cached"]
    body = s.requests[0]
    assert body == {"model": "typesafe/jev-1.13", "state": "RUN SUMMARY",
                    "questions": {"a": {"type": "noul", "instructions": QS[0].text}, "b": {"type": "noul", "instructions": QS[1].text}}}
    assert c.evaluate("RUN SUMMARY", list(QS), {})["cached"] and len(s.requests) == 1


def test_jev_route_402_retry_and_spend_cap(tmp_path):
    with pytest.raises(RouteMismatchError):
        client(tmp_path / "1", Server([ok({"a": .5, "b": .5}, provider="Other")])).evaluate("x", list(QS), {})
    with pytest.raises(OutOfCreditsError):
        client(tmp_path / "2", Server([(402, {})])).evaluate("x", list(QS), {})
    assert client(tmp_path / "3", Server([(429, {}), ok({"a": .5, "b": .5})])).evaluate("x", list(QS), {})["probabilities"]["a"] == .5
    tracker = SpendTracker(tmp_path / "s.json", cap_usd=0.00005, flush_seconds=0)
    c = client(tmp_path / "4", Server([ok({"a": .5, "b": .5})]), spend=tracker)
    c.evaluate("x", list(QS), {})
    with pytest.raises(SpendCapExceeded):
        c.evaluate("y", list(QS), {})


def test_score_signs_by_direction_and_weights():
    assert score({"a": 0.9, "b": 0.2}, QS, None) == pytest.approx(0.7)
    assert score({"a": 0.9, "b": 0.2}, QS, {"a": 2.0, "b": 1.0}) == pytest.approx(1.6)


def test_fit_weights_learns_which_questions_separate_good_runs():
    good = [{"a": 0.9, "b": 0.1}] * 20
    bad = [{"a": 0.1, "b": 0.9}] * 20
    w, b = fit_weights(good + bad, [1.0] * 20 + [0.2] * 20, QS)
    assert w["a"] > 0 and w["b"] > 0  # both contributions point the stated way
    assert classify({"a": 0.9, "b": 0.1}, QS, w, b) and not classify({"a": 0.1, "b": 0.9}, QS, w, b)
    assert fit_weights(good, [1.0] * 20, QS) == ({"a": 1.0, "b": 1.0}, 0.0)  # one class only


def test_rubric_edits_apply_and_are_checked():
    add = RubricEdit("add", "verified_totals", "Did it re-check totals before sending?", "helps")
    assert len(apply_rubric_edit(STARTING_RUBRIC, add)) == len(STARTING_RUBRIC) + 1
    assert check_rubric_edit(add, STARTING_RUBRIC, []) is None
    assert check_rubric_edit(RubricEdit("add", "read_policies", "Dup id?", "helps"), STARTING_RUBRIC, [])
    assert check_rubric_edit(RubricEdit("add", "x_y", "Email ap@x.com?", "hurts"), STARTING_RUBRIC, [])
    assert check_rubric_edit(RubricEdit("replace", "nope", "Is it?", "helps"), STARTING_RUBRIC, [])
    assert check_rubric_edit(add, STARTING_RUBRIC, [add])  # already rejected
    (e,) = parse_rubric_edits('```json\n{"edits":[{"op":"remove","question_id":"errors_ignored","why":"noise"}]}\n```')
    assert e.op == "remove" and e.question_id == "errors_ignored"


def test_keep_rubric_edit_uses_v1_mcnemar():
    assert keep_rubric_edit([False] * 12, [True] * 12).keep
    assert not keep_rubric_edit([True, False], [True, False]).keep


def test_cascade_tau_routing_and_verdict():
    assert set_tau([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]) == 0.4  # 30% below
    tasks = [f"t{i}" for i in range(10)]
    scores = {t: i / 10 for i, t in enumerate(tasks)}
    cheap = {t: {"credit": 0.74, "cost_usd": 0.05, "seconds": 100} for t in tasks}
    strong = {t: {"credit": 0.75, "cost_usd": 0.30, "seconds": 200} for t in tasks}
    routed = route(tasks, scores, 0.3, cheap, strong, {t: 0.001 for t in tasks})
    assert sum(not r["kept"] for r in routed.values()) == 3
    v = v2_3_verdict(routed, strong)
    assert v["kept_share"] == 0.7 and v["credit"]["within_3_points"] and v["cost_per_task"]["half_or_less"] and v["chefs_kiss"]


def test_cascade_verdict_fails_when_credit_gap_exceeds_3_points():
    tasks = [f"t{i}" for i in range(10)]
    cheap = {t: {"credit": 0.70, "cost_usd": 0.05, "seconds": 100} for t in tasks}
    strong = {t: {"credit": 0.75, "cost_usd": 0.30, "seconds": 200} for t in tasks}
    routed = route(tasks, {t: i / 10 for i, t in enumerate(tasks)}, 0.3, cheap, strong, {})
    assert not v2_3_verdict(routed, strong)["chefs_kiss"]  # 0.715 vs 0.75
