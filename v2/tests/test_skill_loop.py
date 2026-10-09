"""Phase 1 split, check-level grading, and the Agent skill loop's pieces ($0)."""
import json
import random

import httpx
import pytest

from jevloop import bench
from jevloop.agents import SIMPLE_3001_SOLUTION, DoNothingAgent, ScriptedAgent
from jevloop.cache import DiskCache
from jevloop.diagnostics import behaviour
from jevloop.llm_agent import LLMAgent
from jevloop.log import JsonlLogger
from jevloop.openrouter import ChatClient
from jevloop.runs import CandidateRun, run_candidates
from jevloop.skill_loop import (Edit, SkillEditor, apply_edit, best_passing, check_edit, gate_decision,
                                mistakes_report, parse_edits, skill_text, version_id)
from jevloop.splits import phase1_split


@pytest.fixture(scope="module")
def task_3001():
    return next(t for t in bench.load_tasks(["simple"]) if t.task_id == "simple:3001")


def test_split_sizes_strata_and_phase0_tasks_never_sealed():
    ids = {"finance": [f"finance:{i}" for i in range(4001, 4101)], "hr": [f"hr:{i}" for i in range(5001, 5101)]}
    phase0 = set(ids["finance"][:25] + ids["hr"][:25])
    s = phase1_split(ids, phase0, seed=20261007)
    assert {k: len(v) for k, v in s.items()} == {"practice": 60, "gate": 60, "sealed": 80}
    assert sum(t.startswith("hr:") for t in s["sealed"]) == 40 and sum(t.startswith("hr:") for t in s["gate"]) == 30
    assert not phase0 & set(s["sealed"])
    assert len(set().union(*map(set, s.values()))) == 200
    assert s == phase1_split(ids, phase0, seed=20261007)


def test_grade_lists_missed_checks_but_summary_does_not(task_3001):
    (run,) = run_candidates([task_3001], DoNothingAgent(), k=1)
    assert run.missed_checks and run.missed_checks[0]["type"] == "salesforce_field_equals"
    assert "salesforce_field_equals" not in run.summary
    (good,) = run_candidates([task_3001], ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION]}), k=1)
    assert good.missed_checks == []


def test_behaviour_counts_broken_must_not_checks(task_3001):
    out = behaviour(task_3001, [], [{"type": "x", "negative": True}, {"type": "y", "negative": False}])
    assert out["broken_must_not"] == 1


def test_skill_text_and_versions():
    assert skill_text(()) == "" and version_id(()) == "v0"
    rules = ("Read every policy email before acting.",)
    assert "1. Read every policy email" in skill_text(rules)
    assert version_id(rules) != version_id(rules + ("Handle every item.",))


def test_apply_edit_ops():
    rules = ("a rule", "b rule")
    assert apply_edit(rules, Edit("add", None, "c rule")) == ("a rule", "b rule", "c rule")
    assert apply_edit(rules, Edit("replace", 2, "B rule")) == ("a rule", "B rule")
    assert apply_edit(rules, Edit("remove", 1, "")) == ("b rule",)


def test_check_edit_refuses_specific_or_repeated_rules():
    rules = ("Read every policy email in the inbox before acting.",)
    rejected = [Edit("add", None, "Always double-check totals before sending a summary email.")]
    assert check_edit(Edit("add", None, "Email ap@acme.com first."), rules, rejected)
    assert check_edit(Edit("add", None, "Skip invoice 88210."), rules, rejected)
    assert check_edit(Edit("add", None, "Read every policy email in the inbox before acting!"), rules, rejected)
    assert check_edit(Edit("add", None, "Always double-check totals before sending a summary email"), rules, rejected)
    assert check_edit(Edit("replace", 5, "x"), rules, rejected)
    assert check_edit(Edit("add", None, "Handle every item in the request before you stop."), rules, rejected) is None


def test_gate_keeps_clear_improvement_and_rejects_noise():
    current = {f"t{i}": 0.4 for i in range(40)}
    better = {t: (0.8 if i < 20 else 0.4) for i, t in enumerate(current)}
    d = gate_decision(current, better, p_threshold=0.10)
    assert d.keep and d.better == 20 and d.worse == 0
    same = gate_decision(current, dict(current), p_threshold=0.10)
    assert not same.keep and same.p_value == 1.0
    mixed = {t: (0.5 if i % 2 else 0.3) for i, t in enumerate(current)}
    assert not gate_decision(current, mixed, p_threshold=0.10).keep
    picked = best_passing([(Edit("add", None, "x"), d), (Edit("add", None, "y"), same)])
    assert picked[0].text == "x"


def _run(task, credit, missed=()):
    return CandidateRun(task, "finance", "m", 0, credit, credit == 1.0, 3, 2, 0.01, 1.0, "done",
                        f"TRIGGER\nDo the {task} thing\n\nACTIONS (2 tool calls)\n1. x\n\nSTATE CHANGES\n(no changes)",
                        missed_checks=list(missed))


def test_mistakes_report_shows_failed_practice_runs_with_missed_checks():
    runs = [_run("finance:1", 1.0), _run("finance:2", 0.5, [{"type": "gmail_message_not_sent_to", "params": {"to": "x"}, "negative": True}])]
    report = mistakes_report(runs, limit=5, rng=random.Random(0))
    assert [r["task_id"] for r in report] == ["finance:2"]
    assert report[0]["request"] == "Do the finance:2 thing"
    assert report[0]["missed_checks"][0].startswith("MUST NOT (broken): gmail_message_not_sent_to")


def test_parse_edits_handles_fences():
    content = 'Here you go:\n```json\n{"edits": [{"op": "add", "index": null, "text": "Read policies first.", "why": "w"}]}\n```'
    (edit,) = parse_edits(content)
    assert edit.op == "add" and edit.index is None and edit.text == "Read policies first."


class FakeServer:
    def __init__(self, contents):
        self.contents, self.requests = list(contents), []

    def __call__(self, request):
        self.requests.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "m/x", "provider": "Host", "usage": {"cost": 0.001},
                                         "choices": [{"message": {"role": "assistant", "content": self.contents.pop(0)}}]})


def _client(tmp_path, server):
    return ChatClient(model="m/x", provider="Host", provider_tag="host/fp8", expected_model="m/x", api_key="t",
                      cache=DiskCache(tmp_path / "c"), logger=JsonlLogger(tmp_path / "l.jsonl"), spend=None,
                      temperature=0.7, reasoning_effort="medium", http_client=httpx.Client(transport=httpx.MockTransport(server)),
                      sleep=lambda s: None)


def test_editor_drops_refused_edits_and_asks_again(tmp_path):
    first = json.dumps({"edits": [{"op": "add", "index": None, "text": "Email boss@corp.com.", "why": ""},
                                  {"op": "add", "index": None, "text": "Read every policy email before acting.", "why": ""}]})
    second = json.dumps({"edits": [{"op": "add", "index": None, "text": "Handle every item before you stop.", "why": ""}]})
    server = FakeServer([first, second])
    edits, refused = SkillEditor(_client(tmp_path, server)).propose((), [], [], n=2, round_number=1)
    assert [e.text for e in edits] == ["Read every policy email before acting.", "Handle every item before you stop."]
    assert refused and "general" in refused[0]["reason"]
    assert "tools" not in server.requests[0]  # the editor has no tools


def test_skill_goes_into_the_system_prompt(tmp_path, task_3001):
    server = FakeServer(["done"])
    run_candidates([task_3001], LLMAgent("m", _client(tmp_path, server), skill=skill_text(("Rule one.",))), k=1)
    assert server.requests[0]["messages"][0]["content"].endswith("1. Rule one.")


def test_read_policy_before_first_write_uses_call_order():
    from jevloop.diagnostics import read_policy_before_first_write
    task = next(t for t in bench.load_tasks(["finance"]) if t.task_id == "finance:4001")
    from jevloop.diagnostics import policy_messages
    policy = policy_messages(task)
    assert policy, "finance:4001 has a collections/AP policy email"
    read = [{"name": "api_fetch", "args": {"method": "GET", "url": f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m}"}} for m in policy]
    write = {"name": "api_fetch", "args": {"method": "POST", "url": "https://sheets.example/append"}}
    assert read_policy_before_first_write(task, read + [write]) is True
    assert read_policy_before_first_write(task, [write] + read) is False
    assert read_policy_before_first_write(task, read[:-1] + [write]) is (len(policy) == 0)


def _checks_run(task, credit, checks):
    return CandidateRun(task, "finance", "m", 0, credit, credit == 1.0, len(checks), 1, 0.01, 1.0, "done", "",
                        checks=[{"type": "x", "kind": k, "passed": ok} for k, ok in checks])


def test_grade_records_every_scored_check_with_its_kind(task_3001):
    (run,) = run_candidates([task_3001], DoNothingAgent(), k=1)
    assert run.checks == [{"type": "salesforce_field_equals", "kind": "wrong_content", "passed": False}]


def test_keep_rule_targets_checks_and_guards_credit():
    from jevloop.skill_loop import keep_rule
    tasks = [f"t{i}" for i in range(30)]
    cur = {t: _checks_run(t, 0.5, [("rule_broken", False), ("action_missed", True)]) for t in tasks}
    fixed = {t: _checks_run(t, 0.6 if i < 15 else 0.5, [("rule_broken", i < 15), ("action_missed", True)]) for i, t in enumerate(tasks)}
    d = keep_rule(cur, fixed, kind="rule_broken", regression=[])
    assert d.keep and d.targeted_tasks == 30 and d.targeted_diff == 0.5
    costly = {t: _checks_run(t, 0.4, [("rule_broken", i < 15), ("action_missed", False)]) for i, t in enumerate(tasks)}
    d2 = keep_rule(cur, costly, kind="rule_broken", regression=[])
    assert d2.targeted_ok and not d2.net_ok and not d2.keep  # targeted checks improved but it cost credit
    assert not keep_rule(cur, dict(cur), kind="rule_broken", regression=[]).keep


def test_failure_profile_counts_kinds_and_steps():
    from jevloop.skill_loop import failure_profile
    runs = [_checks_run("a", 0.5, [("rule_broken", False), ("wrong_content", False)]), _checks_run("b", 1.0, [("rule_broken", True)])]
    prof = failure_profile(runs, [{"read_policy_before_first_write": False}, {"read_policy_before_first_write": None}])
    assert prof["missed_checks_by_kind"] == {"rule_broken": 1, "action_missed": 0, "wrong_content": 1}
    assert prof["policy_emails_read_before_first_write"] == "0 of 1 runs with policy emails"


def test_redesigned_editor_requires_a_target_and_sees_the_profile(tmp_path):
    first = json.dumps({"edits": [{"op": "add", "index": None, "text": "Read every policy email before acting.", "why": ""},
                                  {"op": "add", "index": None, "text": "Handle every item before you stop.", "why": "", "target": "action_missed"}]})
    second = json.dumps({"edits": [{"op": "add", "index": None, "text": "Check exclusions before each email.", "why": "", "target": "rule_broken"}]})
    server = FakeServer([first, second])
    edits, refused = SkillEditor(_client(tmp_path, server)).propose((), [], [], n=2, round_number=1,
                                                                   profile={"missed_checks_by_kind": {"rule_broken": 19}})
    assert [e.target for e in edits] == ["action_missed", "rule_broken"]
    assert "check kind" in refused[0]["reason"]
    assert "FAILURE PROFILE" in server.requests[0]["messages"][1]["content"]
    assert '"target"' in server.requests[0]["messages"][0]["content"]


def test_near_misses_reach_the_editor():
    passed_but_held = CandidateRun("finance:9", "finance", "m", 0, 1.0, True, 3, 2, 0.01, 1.0, "done",
                                   "TRIGGER\nDo it\n\nACTIONS (1 tool calls)\n1. x\n\nSTATE CHANGES\n(no changes)", holds=1,
                                   monitor_events=[{"verdict": "hold", "message": "read the policy first"}])
    clean_pass = _run("finance:1", 1.0)
    report = mistakes_report([passed_but_held, clean_pass], limit=5, rng=random.Random(0))
    assert [r["task_id"] for r in report] == ["finance:9"]
    assert report[0]["near_miss"] is True and report[0]["held_by_gate"] == ["read the policy first"]
    from jevloop.skill_loop import failure_profile
    prof = failure_profile([passed_but_held, clean_pass], [{}, {}])
    assert prof["near_misses"] == 1 and prof["gate_holds_per_100_runs"] == 50.0
