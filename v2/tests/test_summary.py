"""The run summary is what the Jev rubric reads; it must never carry the grading checks."""
import ast
import dataclasses
import inspect
import json
from pathlib import Path

import pytest

from jevloop import bench, summary
from jevloop.agents import SIMPLE_3001_SOLUTION, DoNothingAgent, ScriptedAgent
from jevloop.runs import ToolCall, run_candidates


@pytest.fixture(scope="module")
def all_tasks():
    return bench.load_tasks(bench.domains())


@pytest.fixture(scope="module")
def task_3001(all_tasks):
    return next(t for t in all_tasks if t.task_id == "simple:3001")


def test_summary_shows_trigger_actions_and_state_change(task_3001):
    (run,) = run_candidates([task_3001], ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION]}), k=1)
    assert run.summary.startswith("TRIGGER\nJordan Lee just emailed us")
    assert "ACTIONS (5 tool calls)" in run.summary
    assert "PATCH https://yourinstance.salesforce.com/services/data/v61.0/sobjects/Contact/003001" in run.summary
    assert "~ salesforce.contacts[003001] phone: +1-555-0000 -> +1-555-0101" in run.summary
    assert "last_modified_date" not in run.summary


def test_summary_is_deterministic(task_3001):
    agent = ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION]})
    assert run_candidates([task_3001], agent, k=1)[0].summary == run_candidates([task_3001], agent, k=1)[0].summary


def test_summary_does_not_depend_on_grading_checks(task_3001):
    """Same run, checks removed or replaced: the summary must be identical."""
    agent = ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION]})
    original = run_candidates([task_3001], agent, k=1)[0].summary
    decoy = ({"type": "salesforce_field_equals", "collection": "contacts", "record_id": "003001",
              "field": "phone", "value": "LEAK-CANARY-7731"},)
    for checks in ((), decoy):
        swapped = dataclasses.replace(task_3001, assertions=checks)
        assert run_candidates([swapped], agent, k=1)[0].summary == original


def test_no_grading_check_text_in_any_do_nothing_summary(all_tasks):
    """Across all 800 tasks: no check type names, and no expected values that the agent
    could not have seen (absent from the prompt and the starting world)."""
    runs = run_candidates(all_tasks, DoNothingAgent(), k=1)
    by_id = {t.task_id: t for t in all_tasks}
    for run in runs:
        task = by_id[run.task_id]
        visible = run.summary
        assert "assertion" not in visible.lower()
        for check in task.assertions:
            assert check["type"] not in visible
        seen = json.dumps(task.initial_state) + task.public.trigger
        for check in task.assertions:
            for value in check.values():
                if isinstance(value, str) and len(value) >= 6 and value not in seen:
                    assert value not in visible, (run.task_id, value)


def test_summarize_only_takes_public_inputs():
    assert list(inspect.signature(summary.summarize).parameters) == ["task", "calls", "before", "after"]
    source = Path(summary.__file__).read_text()
    imported = {
        (node.module or "") if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any("automationbench" in m or "bench" in m.split(".")[-1] for m in imported)
    assert ".assertions" not in source


def test_state_diff_records_added_removed_changed():
    before = {"meta": {"current_time": "t0"}, "crm": {"contacts": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}}
    after = {"meta": {"current_time": "t1"}, "crm": {"contacts": [
        {"id": 1, "name": "A2", "last_modified_date": "now"}, {"id": 3, "name": "C"}]}}
    assert summary.state_diff(before, after) == [
        '+ crm.contacts[3] {"id": 3, "name": "C"}',
        "- crm.contacts[2]",
        "~ crm.contacts[1] name: A -> A2",
    ]


def test_long_values_and_summaries_are_capped():
    task = bench.PublicTask("x:1", "simple", ({"role": "user", "content": "go"},))
    calls = [ToolCall("api_search", {"query": "q" * 1000}, "{}")] * 200
    text = summary.summarize(task, calls, {}, {})
    assert len(text) <= summary.MAX_CHARS
    assert "q" * (summary.MAX_VALUE_CHARS + 1) not in text


def test_long_runs_keep_every_state_change_and_every_write():
    """A1: a 50-call run with long arguments keeps STATE CHANGES and all record-changing calls."""
    task = bench.PublicTask("x:1", "finance", ({"role": "user", "content": "Reconcile the ledger."},))
    reads = [ToolCall("api_fetch", {"method": "GET", "url": f"https://api.example/items/{i}", "params": "p" * 400}, "{}")
             for i in range(45)]
    writes = [ToolCall("api_fetch", {"method": "PATCH", "url": f"https://api.example/rows/{i}", "body": '{"Status": "Done"}'}, "{}")
              for i in range(5)]
    before = {"sheets": {"rows": [{"id": i, "Status": "Open"} for i in range(30)]}}
    after = {"sheets": {"rows": [{"id": i, "Status": "Done"} for i in range(30)]}}
    text = summary.summarize(task, reads + writes, before, after)
    assert len(text) <= summary.MAX_CHARS
    assert "STATE CHANGES" in text
    assert all(f"~ sheets.rows[{i}] Status: Open -> Done" in text for i in range(30))
    assert all(f"PATCH https://api.example/rows/{i}" in text for i in range(5))
    assert "read calls omitted]" in text and "[truncated]" not in text
