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
