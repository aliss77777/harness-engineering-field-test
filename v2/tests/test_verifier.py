"""The Jev verifier's state builder, question parsing and ranking statistics (no model calls)."""
import json

import pytest

from jevloop import evalstats
from jevloop.verifier import build_state, parse_questions, policy_text, verifier_score

INITIAL = {"meta": {"allowed_services": ["secret-from-grader"]},
           "gmail": {"messages": [{"id": "m1", "subject": "AP policy update", "body_plain": "Do not pay vendors on hold."},
                                  {"id": "m2", "subject": "Lunch", "body_plain": "Pizza at noon?"}]}}
CALLS = [{"name": "api_search", "args": {"query": "x"}, "result": "API DOCS SHOULD NOT APPEAR"},
         {"name": "api_fetch", "args": {"method": "GET", "url": "https://x/vendors"}, "result": '{"vendors": ["Acme (hold)"]}'},
         {"name": "api_fetch", "args": {"method": "POST", "url": "https://x/send", "body": {"to": "a@b.c"}}, "result": '{"ok": true}'}]
SUMMARY = "TRIGGER\nreq\n\nACTIONS (3 tool calls)\n1. x\n\nSTATE CHANGES\n+ gmail.messages[9] {'to': 'a@b.c'}"


def test_state_has_policy_reads_writes_and_diff_but_no_meta_or_api_docs():
    s = build_state("Pay vendors.", INITIAL, CALLS, SUMMARY)
    assert "AP policy update" in s and "Do not pay vendors on hold" in s
    assert "Pizza at noon" not in s  # not policy-like
    assert "Acme (hold)" in s and "POST https://x/send" in s and "gmail.messages[9]" in s
    assert "API DOCS SHOULD NOT APPEAR" not in s and "secret-from-grader" not in s


def test_policy_text_drops_meta():
    assert [m["subject"] for m in policy_text(INITIAL)] == ["AP policy update"]


def test_parse_questions_handles_fences_and_rejects_junk():
    content = "```json\n" + json.dumps({"questions": [{"text": "Did the agent skip every vendor on hold?"}, "Was each amount copied exactly?",
                                                       {"text": "Was a notice sent to each affected owner?"}]}) + "\n```"
    assert len(parse_questions(content)) == 3
    with pytest.raises(ValueError):
        parse_questions(json.dumps({"questions": ["too short"]}))


def test_score_is_mean_probability_of_yes():
    assert verifier_score({"q1": 1.0, "q2": 0.5, "q3": 0.0}) == pytest.approx(0.5)


def rows(scores, credits, group="v", task=None):
    return [{"task": task or f"t{i}", "group": group, "score": s, "credit": c} for i, (s, c) in enumerate(zip(scores, credits))]


def test_grouped_auc_only_compares_within_groups():
    # group b scores higher than group a overall; within each group the ranking is reversed
    r = rows([0.1, 0.2], [0.9, 0.1], group="a") + rows([0.8, 0.9], [0.9, 0.1], group="b")
    assert evalstats.grouped_auc(r, "group") == 0.0
    assert evalstats.auc([x["score"] for x in r], [x["credit"] >= 0.8 for x in r]) == pytest.approx(0.25)
    # a group that only separates good from bad by group membership has no within-group signal
    r2 = rows([0.1, 0.1], [0.1, 0.1], group="a") + rows([0.9, 0.9], [0.9, 0.9], group="b")
    assert evalstats.grouped_auc(r2, "group") != evalstats.grouped_auc(r2, "group")  # nan: no good/bad pair in any group


def test_gap_and_bar():
    r = rows([i / 10 for i in range(10)], [0.2, 0.3, 0.9, 0.8, 0.9, 1.0, 0.9, 0.8, 1.0, 0.9])
    g = evalstats.lowest_share_gap(r, 0.3)
    assert g["n_low"] == 3 and g["gap"] > 0.4
    m = {"auc_within_playbook": 0.7, "auc_ci95": [0.6, 0.8], "gap": 0.12}
    assert evalstats.bar_met(m) and not evalstats.bar_met({**m, "auc_ci95": [0.45, 0.8]})
