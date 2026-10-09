"""Action masking (V2-5, work item C): the monitor, its wiring into the agent, and its leak rule. $0."""
import dataclasses
import json

import httpx
import pytest

from jevloop import bench
from jevloop.cache import DiskCache
from jevloop.llm_agent import LLMAgent
from jevloop.log import JsonlLogger
from jevloop.monitor import MAX_HOLDS_PER_RUN, MonitorContext, ReadPoliciesFirst, Verdict, company_data, policy_emails
from jevloop.openrouter import ChatClient
from jevloop.runs import run_candidates

MODEL = "m/x"


class FakeServer:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def __call__(self, request):
        self.requests.append(json.loads(request.content))
        return httpx.Response(200, json={"model": MODEL, "provider": "Host", "usage": {"cost": 0.001},
                                         "choices": [{"message": {"role": "assistant", **self.replies.pop(0)}}]})


def calls(*pairs):
    return {"content": None, "tool_calls": [{"id": f"c{i}", "type": "function",
                                             "function": {"name": n, "arguments": json.dumps(a)}} for i, (n, a) in enumerate(pairs)]}


def done(text="done"):
    return {"content": text}


def client(tmp_path, server):
    return ChatClient(model=MODEL, provider="Host", provider_tag="host/fp8", expected_model=MODEL, api_key="t",
                      cache=DiskCache(tmp_path / "c"), logger=JsonlLogger(tmp_path / "l.jsonl"), spend=None,
                      temperature=0.0, reasoning_effort="medium", http_client=httpx.Client(transport=httpx.MockTransport(server)),
                      sleep=lambda s: None)


@pytest.fixture(scope="module")
def task():
    return next(t for t in bench.load_tasks(["finance"]) if t.task_id == "finance:4001")


WRITE = ("api_fetch", {"method": "POST", "url": "https://sheets.googleapis.com/v4/spreadsheets/ss_inv_tracker/values/A1:append",
                       "body": json.dumps({"values": [["x"]]})})


def read(msg_id):
    return ("api_fetch", {"method": "GET", "url": f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"})


def test_no_monitor_is_identical_to_before(tmp_path, task):
    script = [calls(WRITE), done()]
    s1, s2 = FakeServer(list(script)), FakeServer(list(script))
    plain = run_candidates([task], LLMAgent("a", client(tmp_path / "1", s1)), k=1)[0]
    explicit = run_candidates([task], LLMAgent("a", client(tmp_path / "2", s2), monitor=None), k=1)[0]
    assert s1.requests == s2.requests
    assert plain.partial_credit == explicit.partial_credit and plain.holds == explicit.holds == 0
    assert plain.monitor_events == []


def test_an_allow_all_monitor_changes_nothing(tmp_path, task):
    class AllowAll:
        name = "allow"

        def before_write(self, ctx):
            return Verdict("allow")

    script = [calls(WRITE), done()]
    s1, s2 = FakeServer(list(script)), FakeServer(list(script))
    run_candidates([task], LLMAgent("a", client(tmp_path / "1", s1)), k=1)
    run_candidates([task], LLMAgent("a", client(tmp_path / "2", s2), monitor=AllowAll(),
                                    company_data={task.task_id: company_data(task.initial_state)}), k=1)
    assert s1.requests == s2.requests


def test_write_before_reading_policy_is_held_then_allowed_after_reading(tmp_path, task):
    data = company_data(task.initial_state)
    policy = [m["id"] for m in policy_emails(data)]
    assert policy
    server = FakeServer([calls(WRITE), calls(*[read(m) for m in policy]), calls(WRITE), done()])
    agent = LLMAgent("a", client(tmp_path, server), monitor=ReadPoliciesFirst(), company_data={task.task_id: data})
    (run,) = run_candidates([task], agent, k=1)
    assert run.holds == 1 and run.flagged
    held = json.loads(server.requests[1]["messages"][-1]["content"])
    assert held["held"] is True and policy[0] in held["message"]
    writes = [c for c in run.calls if c["args"].get("method") == "POST"]
    assert len(writes) == 1  # the held write never ran; the second one did
    assert [e["verdict"] for e in run.monitor_events] == ["hold", "allow"]
    assert run.monitor_events[0]["executed"] is False and run.monitor_events[1]["executed"] is True


def test_hold_cap_then_allow_and_log(tmp_path, task):
    server = FakeServer([calls(WRITE)] * (MAX_HOLDS_PER_RUN + 1) + [done()])
    agent = LLMAgent("a", client(tmp_path, server), monitor=ReadPoliciesFirst(),
                     company_data={task.task_id: company_data(task.initial_state)})
    (run,) = run_candidates([task], agent, k=1)
    assert run.holds == MAX_HOLDS_PER_RUN
    last = run.monitor_events[-1]
    assert last["verdict"] == "allow" and last["evidence"].get("would_hold") and last["executed"]


def test_reads_are_never_checked(tmp_path, task):
    server = FakeServer([calls(read("x")), done()])
    agent = LLMAgent("a", client(tmp_path, server), monitor=ReadPoliciesFirst(),
                     company_data={task.task_id: company_data(task.initial_state)})
    (run,) = run_candidates([task], agent, k=1)
    assert run.monitor_events == [] and run.holds == 0


def test_monitor_never_sees_grading_checks_or_meta(task):
    fields = {f.name for f in dataclasses.fields(MonitorContext)}
    assert fields == {"task_id", "request", "calls", "proposed", "company_data"}
    data = company_data(task.initial_state)
    assert "meta" not in data
    blob = json.dumps(data)
    assert "allowed_services" not in blob
    for check in task.assertions:
        assert check["type"] not in blob  # no grading-check text
    # the agent's own run record keeps grading data out of what the monitor receives
    seen = []

    class Spy:
        name = "spy"

        def before_write(self, ctx):
            seen.append(ctx)
            return Verdict("allow")

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        server = FakeServer([calls(WRITE), done()])
        run_candidates([task], LLMAgent("a", client(Path(d), server), monitor=Spy(),
                                        company_data={task.task_id: data}), k=1)
    ctx = seen[0]
    text = json.dumps(dataclasses.asdict(ctx), default=str)
    assert "meta" not in ctx.company_data and "assertion" not in text.lower()
    for check in task.assertions:
        assert check["type"] not in text


def _r(task, credit, broken, holds=0):
    from jevloop.runs import CandidateRun
    checks = [{"type": "x", "kind": "rule_broken", "passed": i >= broken} for i in range(3)]
    return CandidateRun(task, "finance", "m", 0, credit, credit == 1.0, 3, 1, 0.01, 1.0, "done", "", checks=checks, holds=holds)


def test_v2_5a_verdict_rules():
    from jevloop.masking import verdict
    ids = [f"t{i}" for i in range(20)]
    off = {t: _r(t, 0.5, 2) for t in ids}
    good = {t: _r(t, 0.6, 1, holds=1) for t in ids}
    v = verdict(off, good, [True] * 18 + [False] * 2)
    assert v["worth_keeping"] and v["primary_broken_must_not_per_run"]["diff"] == -1.0
    assert v["sanity_read_policies_before_first_write"]["ok"]  # 90%
    costly = {t: _r(t, 0.4, 1, holds=1) for t in ids}
    assert verdict(off, costly, [True])["outcome_label"] == "the gate changes behaviour but costs credit"
    noisy = {t: _r(t, 0.6, 1, holds=3) for t in ids}
    assert not verdict(off, noisy, [True])["worth_keeping"]  # too many holds
    same = {t: _r(t, 0.5, 2) for t in ids}
    assert verdict(off, same, [])["outcome_label"] == "gate not worth keeping"
    wrong = verdict(off, good, [True])["silent_and_caught_wrong"]
    assert wrong["off"]["silent_wrong"] == 1.0 and wrong["on"]["caught_wrong"] == 1.0
