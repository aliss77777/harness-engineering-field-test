"""Bench adapter, K-run runner and Phase 0 metrics. No model calls."""
import dataclasses
import json

import pytest

from jevloop import bench
from jevloop.agents import SIMPLE_3001_SOLUTION, DoNothingAgent, ScriptedAgent
from jevloop.feasibility import frame, go_no_go
from jevloop.log import JsonlLogger
from jevloop.runs import CandidateRun, ToolBox, run_candidates


@pytest.fixture(scope="module")
def all_tasks():
    return bench.load_tasks(bench.domains())


@pytest.fixture(scope="module")
def task_3001(all_tasks):
    return next(t for t in all_tasks if t.task_id == "simple:3001")


def test_all_tasks_load_with_unique_ids(all_tasks):
    counts = {d: sum(t.public.domain == d for t in all_tasks) for d in bench.SCORED_DOMAINS}
    assert counts == {d: 100 for d in bench.SCORED_DOMAINS}
    assert sum(t.public.domain == "simple" for t in all_tasks) == 200
    assert len({t.task_id for t in all_tasks}) == len(all_tasks)


def test_public_task_carries_no_grading_checks():
    names = {f.name for f in dataclasses.fields(bench.PublicTask)}
    assert names == {"task_id", "domain", "messages"}


def test_do_nothing_scores_zero_everywhere(all_tasks):
    runs = run_candidates(all_tasks, DoNothingAgent(), k=1)
    assert not any(r.passed for r in runs)
    assert max(r.partial_credit for r in runs) == 0.0


def test_scripted_solution_passes_and_candidates_get_fresh_worlds(task_3001):
    agent = ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION, []]})
    runs = run_candidates([task_3001], agent, k=4)
    assert [r.passed for r in runs] == [True, False, True, False]
    assert [r.candidate for r in runs] == [0, 1, 2, 3]
    assert runs[1].tool_calls == 0  # candidate 1 did nothing and saw no leftovers from 0


def test_tool_schemas_hide_the_world_argument():
    schemas = {s["function"]["name"]: s["function"] for s in ToolBox.schemas()}
    assert set(schemas) == {"api_search", "api_fetch", "base64_encode"}
    assert "world" not in json.dumps(schemas["api_fetch"]["parameters"])


def test_unknown_tool_and_bad_json_come_back_as_errors(task_3001):
    world = bench.new_world(task_3001)
    assert "error" in json.loads(bench.call_tool(world, "rm_rf", {}))
    bad = bench.call_tool(world, "api_fetch", {"method": "POST", "url": "https://x.example/y", "body": "{not json"})
    assert "error" in json.loads(bad)


def test_crashing_agent_is_graded_and_marked(task_3001):
    class Crash:
        name = "crash"

        def run(self, task, tools, candidate):
            raise RuntimeError("boom")

    (run,) = run_candidates([task_3001], Crash(), k=1)
    assert run.stop_reason == "error" and not run.passed


def test_results_do_not_depend_on_concurrency(all_tasks, task_3001):
    tasks = [task_3001] + [t for t in all_tasks if t.public.domain == "simple"][1:6]
    agent = ScriptedAgent({"simple:3001": [SIMPLE_3001_SOLUTION, []]})
    strip = lambda runs: [{k: v for k, v in r.record().items() if k != "seconds"} for r in runs]
    assert strip(run_candidates(tasks, agent, k=3)) == strip(run_candidates(tasks, agent, k=3, max_workers=4))


def test_runs_are_logged(tmp_path, task_3001):
    logger = JsonlLogger(tmp_path / "runs.jsonl")
    run_candidates([task_3001], DoNothingAgent(), k=2, logger=logger, run_id="t")
    lines = [json.loads(line) for line in (tmp_path / "runs.jsonl").read_text().splitlines()]
    assert [(e["event"], e["run_id"], e["candidate"]) for e in lines] == [("candidate_run", "t", 0), ("candidate_run", "t", 1)]


def _run(task, candidate, passed, credit, agent="cheap", cost=0.01):
    return CandidateRun(task, "simple", agent, candidate, credit, passed, 1, 0, cost, 1.0, "done", "")


def test_frame_controls_and_mixed_share():
    runs = [_run("a", 0, True, 1.0), _run("a", 1, False, 0.5),  # mixed
            _run("b", 0, False, 0.0), _run("b", 1, False, 0.2),  # all fail
            _run("c", 0, True, 1.0), _run("c", 1, True, 1.0)]  # all pass
    f = frame(runs)
    assert (f.tasks, f.k) == (3, 2)
    assert f.first_run_pass_rate == pytest.approx(2 / 3)
    assert f.random_pick_pass_rate == pytest.approx((0.5 + 0 + 1) / 3)
    assert f.oracle_pass_rate == pytest.approx(2 / 3)
    assert f.oracle_credit == pytest.approx((1.0 + 0.2 + 1.0) / 3)
    assert f.mixed_share == pytest.approx(1 / 3)


def test_frame_refuses_uneven_k_or_mixed_agents():
    with pytest.raises(ValueError):
        frame([_run("a", 0, True, 1), _run("a", 1, True, 1), _run("b", 0, True, 1)])
    with pytest.raises(ValueError):
        frame([_run("a", 0, True, 1), _run("b", 0, True, 1, agent="strong")])


def test_go_no_go_applies_the_brief_thresholds():
    runs = [_run(t, c, p, float(p)) for t, ps in {"a": (True, False), "b": (False, True), "c": (False, False)}.items()
            for c, p in enumerate(ps)]
    f = frame(runs)  # first-run pass 1/3, mixed 2/3
    assert go_no_go(f, projected_phase1_cost_usd=40, cap_usd=60).go
    result = go_no_go(f, projected_phase1_cost_usd=80, cap_usd=60)
    assert not result.go and not result.cost_ok and result.pass_rate_ok and result.mixed_ok
    none_mixed = frame([_run(t, c, True, 1.0) for t in "abc" for c in range(2)])
    assert not go_no_go(none_mixed, 1, 60).go


def test_export_ui_data_reads_insights_and_front_matter(tmp_path):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "export_ui_data", Path(__file__).resolve().parent.parent / "scripts" / "export_ui_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "story").mkdir()
    (tmp_path / "story" / "insights.yaml").write_text("- id: I1\n  headline: H\n  experiments: [v2-1, v2-9]\n")
    exp = tmp_path / "experiments" / "2026-10-20-v2-1"
    exp.mkdir(parents=True)
    (exp / "README.md").write_text("---\nid: v2-1\ninsights: [I1]\n---\n## Headline\n")
    data = module.build(tmp_path)
    assert data["experiments"] == [{"id": "v2-1", "insights": ["I1"], "folder": "2026-10-20-v2-1"}]
    assert data["insights"][0]["experiments_found"] == ["v2-1"]
    (exp / "README.md").write_text("---\nid: v2-1\ninsights: [I7]\n---\n")
    with pytest.raises(ValueError):
        module.build(tmp_path)


def test_in_flight_402_is_retried_but_a_real_402_is_fatal(tmp_path):
    import json as _json

    import httpx

    from jevloop.cache import DiskCache
    from jevloop.log import JsonlLogger
    from jevloop.openrouter import ChatClient, OutOfCreditsError

    in_flight = {"error": {"message": "This request would exceed your available credits given your current in-flight requests.",
                           "code": 402, "metadata": {"reason": "in_flight_budget_exhausted"}}}
    ok = {"model": "m", "provider": "P", "choices": [{"message": {"role": "assistant", "content": "done"}, "finish_reason": "stop"}],
          "usage": {"prompt_tokens": 5, "completion_tokens": 1, "cost": 0.0}}

    def client(responses):
        calls = iter(responses)
        transport = httpx.MockTransport(lambda req: next(calls))
        return ChatClient(model="m", provider="P", provider_tag="p", expected_model="m", api_key="k", cache=DiskCache(tmp_path / f"c{len(responses)}"),
                          logger=JsonlLogger(tmp_path / "log.jsonl"), spend=None, temperature=0.0, reasoning_effort=None, retries=3,
                          http_client=httpx.Client(transport=transport), sleep=lambda s: None)

    c = client([httpx.Response(402, json=in_flight), httpx.Response(200, json=ok)])
    assert c.complete([{"role": "user", "content": "x"}], [], cache_key={"k": 1}, event={})["message"]["content"] == "done"
    c2 = client([httpx.Response(402, json={"error": {"message": "Insufficient credits", "code": 402}})])
    with __import__("pytest").raises(OutOfCreditsError):
        c2.complete([{"role": "user", "content": "x"}], [], cache_key={"k": 2}, event={})
