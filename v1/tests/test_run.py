import json

import pandas as pd
import pytest

from evaluation import batched, evaluate_loop_a, evaluate_loop_b, summarize
from fakes import FakeJevClient, FakeLLMClient
from log import JsonlLogger
from spend import SpendCapExceeded, SpendTracker
from telemetry import Telemetry
from workspace import Workspace


def test_batched_preserves_all_items():
    items = [{"pair_id": str(i)} for i in range(5)]
    assert list(batched(items, 2)) == [items[:2], items[2:4], items[4:]]


def workspace(tmp_path, workers=4):
    config = {"seed": 1, "api": {"batch_size": 3, "llm_workers": workers, "jev_workers": workers},
              "models": {"llm_expected_served": "llm", "jev_expected_served": "jev"}}
    task = {"columns": {"context": "prompt", "x": "response_x", "y": "response_y"},
            "labels": {"x": "1", "y": "2"},
            "wording": {"item": "response", "context": "user request",
                        "decider_question": "Which?", "outcome": "which won"},
            "jev_state_template": "REQ: {context}\nRESP: {item}"}
    return Workspace(tmp_path, config, task)


def frame(n=40):
    return pd.DataFrame({
        "pair_id": [str(i) for i in range(n)], "prompt": ["p"] * n,
        "response_x": [f"x{i}" for i in range(n)], "response_y": [f"y{i}" for i in range(n)],
        "winner": ["X" if i % 2 else "Y" for i in range(n)],
    })


def test_concurrent_evaluation_is_deterministic_and_in_frame_order(tmp_path):
    rubric = [{"question_id": "q", "text": "Q?", "direction": "helps"}]
    runs = []
    for workers in (1, 8):
        ws = workspace(tmp_path, workers)
        logger = JsonlLogger(tmp_path / f"log{workers}.jsonl")
        common = dict(logger=logger, run_id="t", round_number=1, set_name="gate", version_id="v")
        a = evaluate_loop_a(ws, frame(), "x", client=FakeLLMClient(3), **common)
        b = evaluate_loop_b(ws, frame(), rubric, client=FakeJevClient(3), **common)
        runs.append(([r["prediction"] for r in a], [r["prediction"] for r in b]))
        assert [r["pair_id"] for r in a] == [str(i) for i in range(40)]
    assert runs[0] == runs[1]
    assert set(runs[0][0]) == {"X", "Y"}


def test_records_never_contain_texts(tmp_path):
    ws = workspace(tmp_path)
    logger = JsonlLogger(tmp_path / "log.jsonl")
    evaluate_loop_a(ws, frame(6), "x", client=FakeLLMClient(3), logger=logger, run_id="t",
                    round_number=1, set_name="practice", version_id="v")
    text = (tmp_path / "log.jsonl").read_text()
    assert "x1" not in text and "response_x" not in text


def test_spend_cap_stops_new_calls(tmp_path):
    spend = SpendTracker(tmp_path / "spend.json", cap_usd=1.0)
    spend.record(0.6)
    spend.check()
    spend.record(0.5)
    with pytest.raises(SpendCapExceeded):
        spend.check()
    assert json.loads((tmp_path / "spend.json").read_text())["total_usd"] == pytest.approx(1.1)
    assert SpendTracker(tmp_path / "spend.json", cap_usd=5).total_usd == pytest.approx(1.1)


def test_telemetry_writes_status_and_summary(tmp_path):
    telemetry = Telemetry(tmp_path, "run", SpendTracker(tmp_path / "spend.json", 10))
    telemetry.stage("A", stage="evaluate", round=1, set="gate", completed=5, total=10)
    telemetry.evaluation(loop="A", round_number=1, set_name="gate", version_id="A-v0",
                         summary={"pairs": 10, "accuracy": 0.6})
    status = json.loads((tmp_path / "run_status.json").read_text())
    summary = json.loads((tmp_path / "wip_summary.json").read_text())
    assert status["loops"]["A"]["completed"] == 5
    assert summary["evaluations"][0]["accuracy"] == 0.6


def test_content_blocked_pair_gets_seeded_coin_flip_and_flag(tmp_path):
    from openrouter_llm import ContentBlockedError

    class BlockingLLM(FakeLLMClient):
        def generate_json(self, *, prompt, schema, event):
            if "7" in event["pair_id"]:
                self.last_call = {}
                raise ContentBlockedError("PROHIBITED_CONTENT")
            return super().generate_json(prompt=prompt, schema=schema, event=event)

    ws = workspace(tmp_path)
    runs = []
    for _ in range(2):
        records = evaluate_loop_a(ws, frame(12), "x", client=BlockingLLM(3), logger=JsonlLogger(tmp_path / "l.jsonl"),
                                  run_id="t", round_number=1, set_name="gate", version_id="v")
        runs.append([r["prediction"] for r in records])
        assert [r["pair_id"] for r in records if r["blocked"]] == ["7"]
        assert summarize(records)["blocked"] == 1
        assert len(records) == 12
    assert runs[0] == runs[1]


def test_failfast_pool_cancels_queued_work():
    import threading
    import time
    from evaluation import failfast_pool

    started = []
    lock = threading.Lock()

    def job(i):
        with lock:
            started.append(i)
        if i == 0:
            raise RuntimeError("boom")
        time.sleep(0.05)

    with pytest.raises(RuntimeError, match="boom"):
        with failfast_pool(1) as pool:
            futures = [pool.submit(job, i) for i in range(50)]
            for future in futures:
                future.result()
    assert len(started) < 5


def test_read_pairs_keeps_literal_na_text(tmp_path):
    from workspace import read_pairs
    path = tmp_path / "pairs.csv"
    pd.DataFrame({"pair_id": ["001"], "prompt": ["Say N/A"], "response_x": ["N/A"],
                  "response_y": ["null"], "winner": ["X"]}).to_csv(path, index=False)
    row = read_pairs(path).iloc[0]
    assert row["pair_id"] == "001" and row["response_x"] == "N/A" and row["response_y"] == "null"
