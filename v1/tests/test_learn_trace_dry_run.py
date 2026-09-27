"""End-to-end dry run of experiment 3 learning with fake clients (no API calls)."""
import copy
import json
import random
import threading

import pandas as pd
import yaml

from fakes import FakeJevClient
from learn_trace import TraceRunner
from log import JsonlLogger
from telemetry import Telemetry
from workspace import ROOT, Workspace


class FakeEditor:
    """Proposes seeded rubric edits and rewordings in the real schemas."""

    def __init__(self):
        self._local = threading.local()
        self.calls = 0
        self.prompts = []

    @property
    def last_call(self):
        return getattr(self._local, "last_call", {})

    @last_call.setter
    def last_call(self, value):
        self._local.last_call = value

    def generate_json(self, *, prompt, schema, event):
        self.calls += 1
        self.last_call = {"model": "fake", "cached": False, "cost": 0.0}
        if "rewordings" in schema["properties"]:
            return {"rewordings": ["Is it deep?", "Is it thorough?"]}
        self.prompts.append(prompt)
        rng = random.Random(self.calls)
        return {"candidates": [
            {"operation": "add", "question_id": f"new_{self.calls}_{i}", "text": f"Criterion {self.calls}.{i}?",
             "direction": rng.choice(["helps", "hurts"]), "reason": "trace shows a gap"}
            for i in range(4)
        ] + [{"operation": "flip", "question_id": "q0", "text": "", "direction": "helps", "reason": "decisive and wrong"}]}


def test_trace_runner_dry_run(tmp_path):
    import pytest
    if not (ROOT / "data" / "arena3" / "pairs" / "practice.csv").exists():
        pytest.skip("needs local Arena pairs (run prep_arena3.py)")
    config = yaml.safe_load((ROOT / "config_arena3.yaml").read_text())
    task = yaml.safe_load((ROOT / "task_arena3.yaml").read_text())
    config = copy.deepcopy(config)
    config["learning"]["rounds"] = 2
    config["learning"]["question_check_items"] = 2
    config["api"].update(jev_workers=2)
    task["paths"] = {"pairs": "pairs", "splits": "splits", "results": "results", "logs": "logs"}
    ws = Workspace(tmp_path, config, task)
    source = pd.read_csv(ROOT / "data" / "arena3" / "pairs" / "practice.csv", dtype={"pair_id": str})
    source.head(30).to_csv(ws.path("pairs") / "practice.csv", index=False)
    source.tail(40).to_csv(ws.path("pairs") / "gate.csv", index=False)
    rubric = [{"question_id": f"q{i}", "text": f"Q{i}?", "direction": "helps"} for i in range(3)]
    telemetry = Telemetry(ws.path("results"), "dry")
    editor = FakeEditor()
    for arm in ("Bp", "Bw"):
        runner = TraceRunner(ws, arm, run_id="dry", llm=editor, jev=FakeJevClient(1),
                             logger=JsonlLogger(ws.path("logs") / "dry.jsonl"), telemetry=telemetry)
        final = runner.run({"rubric_questions": rubric})
        statuses = [h["status"] for h in runner.history]
        assert runner.candidate_count == 10
        assert len([s for s in statuses if s in ("kept", "rejected", "passed_not_best")]) <= 6
        assert all(s in {"kept", "rejected", "passed_not_best", "not_selected_by_prescreen",
                         "refused_duplicate_of_rejected", "failed_question_check", "invalid"} for s in statuses)
        assert ("weights" in final) == (arm == "Bw")
        assert "HOW TO READ THE DECISION TRACE" in editor.prompts[-1]
        assert '"trace"' in editor.prompts[-1] and "aggregate_trace" in editor.prompts[-1]
    summary = json.loads((ws.path("results") / "wip_summary.json").read_text())
    assert {e["loop"] for e in summary["evaluations"]} == {"Bp", "Bw"}
