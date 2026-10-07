"""OpenRouter client, LLM agent and comparability rule, against fake HTTP responses ($0)."""
import json

import httpx
import pytest

from jevloop import bench
from jevloop.agents import SIMPLE_3001_SOLUTION
from jevloop.cache import DiskCache
from jevloop.feasibility import comparability, paired_bootstrap_interval, select_tasks
from jevloop.llm_agent import LLMAgent
from jevloop.log import JsonlLogger
from jevloop.openrouter import ChatClient, OutOfCreditsError, RouteMismatchError
from jevloop.runs import CandidateRun, run_candidates
from jevloop.spend import SpendCapExceeded, SpendTracker

MODEL, PROVIDER = "vendor/model-x", "HostCo"


def reply(message, *, model=MODEL, provider=PROVIDER, cost=0.001):
    return {"model": model, "provider": provider, "choices": [{"message": {"role": "assistant", **message}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": cost}}


def tool_reply(calls, **kw):
    return reply({"content": None, "tool_calls": [
        {"id": f"c{i}", "type": "function", "function": {"name": name, "arguments": args if isinstance(args, str) else json.dumps(args)}}
        for i, (name, args) in enumerate(calls)]}, **kw)


class FakeServer:
    """Serves a scripted sequence of responses and records every request body."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body)


def client(tmp_path, server, *, spend=None, **kw):
    return ChatClient(model=MODEL, provider=PROVIDER, provider_tag="hostco/bf16", expected_model=MODEL, api_key="test",
                      cache=DiskCache(tmp_path / "cache"), logger=JsonlLogger(tmp_path / "calls.jsonl"),
                      spend=spend, temperature=0.7, reasoning_effort="medium",
                      http_client=httpx.Client(transport=httpx.MockTransport(server)), sleep=lambda s: None, **kw)


@pytest.fixture(scope="module")
def task_3001():
    return next(t for t in bench.load_tasks(["simple"]) if t.task_id == "simple:3001")


def test_request_pins_provider_and_settings(tmp_path):
    server = FakeServer([(200, reply({"content": "hi"}))])
    client(tmp_path, server).complete([{"role": "user", "content": "x"}], [], cache_key={"c": 0}, event={})
    body = server.requests[0]
    assert body["provider"] == {"order": ["hostco/bf16"], "allow_fallbacks": False, "require_parameters": True}
    assert body["temperature"] == 0.7 and body["reasoning"] == {"effort": "medium"}


def test_cache_replays_and_candidate_index_is_part_of_the_key(tmp_path):
    server = FakeServer([(200, reply({"content": "a"})), (200, reply({"content": "b"}))])
    c = client(tmp_path, server)
    msgs = [{"role": "user", "content": "same prompt"}]
    first = c.complete(msgs, [], cache_key={"candidate": 0}, event={})
    again = c.complete(msgs, [], cache_key={"candidate": 0}, event={})
    other = c.complete(msgs, [], cache_key={"candidate": 1}, event={})
    assert (first["cached"], again["cached"], other["cached"]) == (False, True, False)
    assert again["message"]["content"] == "a" and other["message"]["content"] == "b"
    assert len(server.requests) == 2


def test_route_mismatch_is_fatal(tmp_path):
    server = FakeServer([(200, reply({"content": "x"}, provider="OtherHost"))])
    with pytest.raises(RouteMismatchError):
        client(tmp_path, server).complete([], [], cache_key={}, event={})


def test_402_is_fatal_and_not_retried(tmp_path):
    server = FakeServer([(402, {"error": {"code": 402}}), (200, reply({"content": "x"}))])
    with pytest.raises(OutOfCreditsError):
        client(tmp_path, server).complete([], [], cache_key={}, event={})
    assert len(server.requests) == 1


def test_rate_limits_are_retried(tmp_path):
    server = FakeServer([(429, {"error": "slow down"}), (503, {"error": "busy"}), (200, reply({"content": "ok"}))])
    out = client(tmp_path, server).complete([], [], cache_key={}, event={})
    assert out["message"]["content"] == "ok" and len(server.requests) == 3


def test_spend_cap_blocks_new_calls_but_not_cache(tmp_path):
    tracker = SpendTracker(tmp_path / "spend.json", cap_usd=0.0015, flush_seconds=0)
    server = FakeServer([(200, reply({"content": "x"}, cost=0.002))])
    c = client(tmp_path, server, spend=tracker)
    c.complete([], [], cache_key={"n": 1}, event={})
    assert c.complete([], [], cache_key={"n": 1}, event={})["cached"]  # replay still allowed
    with pytest.raises(SpendCapExceeded):
        c.complete([], [], cache_key={"n": 2}, event={})


def test_agent_solves_task_through_tool_calls(tmp_path, task_3001):
    server = FakeServer([(200, tool_reply(SIMPLE_3001_SOLUTION[:3])), (200, tool_reply(SIMPLE_3001_SOLUTION[3:])),
                         (200, reply({"content": "Updated Jordan's phone."}))])
    (run,) = run_candidates([task_3001], LLMAgent("cheap", client(tmp_path, server)), k=1)
    assert run.passed and run.stop_reason == "done" and run.steps == 3 and run.model_calls == 3
    assert run.tool_calls == 5 and run.parse_errors == 0 and not run.failed
    assert run.cost_usd == pytest.approx(0.003) and run.input_tokens == 300
    second = server.requests[1]["messages"]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "tool", "tool", "tool"]
    assert second[0]["content"] == task_3001.public.messages[0]["content"]  # version 0: the bench's own prompt


def test_reasoning_details_are_sent_back(tmp_path, task_3001):
    first = tool_reply([("api_search", {"query": "gmail"})])
    first["choices"][0]["message"]["reasoning_details"] = [{"type": "reasoning.encrypted", "data": "sig"}]
    server = FakeServer([(200, first), (200, reply({"content": "done"}))])
    run_candidates([task_3001], LLMAgent("cheap", client(tmp_path, server)), k=1)
    assistant = server.requests[1]["messages"][2]
    assert assistant["reasoning_details"] == [{"type": "reasoning.encrypted", "data": "sig"}]


def test_unparseable_arguments_count_as_failure(tmp_path, task_3001):
    server = FakeServer([(200, tool_reply([("api_fetch", "{not json")])), (200, reply({"content": "gave up"}))])
    (run,) = run_candidates([task_3001], LLMAgent("cheap", client(tmp_path, server)), k=1)
    assert run.parse_errors == 1 and run.failed and not run.passed


def test_step_cap_ends_the_run_and_counts_as_failure(tmp_path, task_3001):
    server = FakeServer([(200, tool_reply([("api_search", {"query": f"q{i}"})])) for i in range(3)])
    (run,) = run_candidates([task_3001], LLMAgent("cheap", client(tmp_path, server), max_steps=3), k=1)
    assert run.stop_reason == "max_steps" and run.steps == 3 and run.failed


def test_infrastructure_errors_stop_the_run_instead_of_being_graded(tmp_path, task_3001):
    server = FakeServer([(402, {"error": {"code": 402}})])
    with pytest.raises(OutOfCreditsError):
        run_candidates([task_3001], LLMAgent("cheap", client(tmp_path, server)), k=1)


def test_task_selection_is_fixed_and_balanced():
    ids = {"finance": [f"finance:{i}" for i in range(4001, 4101)], "hr": [f"hr:{i}" for i in range(5001, 5101)]}
    first = select_tasks(ids, 25, seed=20261006)
    assert first == select_tasks(ids, 25, seed=20261006)
    assert sum(t.startswith("finance:") for t in first) == 25 and len(set(first)) == 50


def _run(task, agent, credit, *, stop="done", parse_errors=0):
    return CandidateRun(task, "finance", agent, 0, credit, credit == 1.0, 5, 3, 0.01, 1.0, stop, "",
                        steps=4, parse_errors=parse_errors)


def test_comparability_rule():
    tasks = [f"finance:{i}" for i in range(50)]
    gemini = [_run(t, "gemini", 0.6) for t in tasks]
    close = [_run(t, "nemotron", 0.55) for t in tasks]
    assert comparability(gemini, close).comparable  # 5 points below
    far = [_run(t, "nemotron", 0.45) for t in tasks]
    result = comparability(gemini, far)
    assert not result.comparable and not result.credit_ok  # 15 points below
    flaky = [_run(t, "nemotron", 0.6, stop="max_steps" if i < 5 else "done") for i, t in enumerate(tasks)]
    result = comparability(gemini, flaky)
    assert not result.comparable and result.credit_ok and not result.failures_ok  # 5 of 50 failed = 10%
    with pytest.raises(ValueError):
        comparability(gemini, close[:-1])


def test_bootstrap_interval_brackets_the_mean():
    diffs = [0.1, -0.2, 0.0, 0.3, -0.1] * 10
    lo, hi = paired_bootstrap_interval(diffs)
    assert lo < sum(diffs) / len(diffs) < hi


def test_empty_reply_is_retried_not_treated_as_done(tmp_path):
    empty = reply({"content": None, "reasoning": "thinking only"})
    empty["usage"] = {}
    server = FakeServer([(200, empty), (200, reply({"content": "real answer"}))])
    out = client(tmp_path, server).complete([], [], cache_key={}, event={})
    assert out["message"]["content"] == "real answer" and len(server.requests) == 2
