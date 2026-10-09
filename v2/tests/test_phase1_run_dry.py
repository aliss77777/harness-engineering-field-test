"""End-to-end dry run of scripts/phase1_run.py: all five stages against fake models, tiny sizes, $0."""
import importlib.util
import json
import types
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent


def load_script():
    spec = importlib.util.spec_from_file_location("phase1_run", ROOT / "scripts" / "phase1_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_chat_transport(model_name: str):
    def handler(request):
        body = json.loads(request.content)
        if "tools" in body:  # an agent turn: finish immediately (a do-nothing run)
            msg = {"role": "assistant", "content": "done"}
        elif "checklist" in body["messages"][0]["content"]:  # the rubric editor
            msg = {"role": "assistant", "content": json.dumps({"edits": [
                {"op": "add", "question_id": "checked_totals", "text": "Did the agent re-check totals before sending?", "direction": "helps"}]})}
        else:  # the skill editor
            msg = {"role": "assistant", "content": json.dumps({"edits": [
                {"op": "add", "index": None, "text": "Read every policy email before acting.", "why": "w", "target": "rule_broken"},
                {"op": "add", "index": None, "text": "Handle every item before you stop.", "why": "w", "target": "action_missed"}]})}
        return httpx.Response(200, json={"model": model_name, "provider": {"minimax/minimax-m3": "Minimax"}.get(model_name, "Google AI Studio"),
                                         "usage": {"cost": 0.0001, "prompt_tokens": 10, "completion_tokens": 5},
                                         "choices": [{"message": msg, "finish_reason": "stop"}]})
    return httpx.MockTransport(handler)


def fake_jev_transport():
    def handler(request):
        body = json.loads(request.content)
        answers = {q: {"noul": 0.3 + 0.4 * (hash(body["state"] + q) % 2)} for q in body["questions"]}
        return httpx.Response(200, json={"model": "typesafe/jev-1.13-20260917", "provider": "TypeSafe", "answers": answers,
                                         "usage": {"cost": 0.00001}})
    return httpx.MockTransport(handler)


@pytest.fixture()
def script(tmp_path, monkeypatch):
    mod = load_script()
    mod.RUN["approved"] = True
    monkeypatch.setattr(mod, "api_key", lambda: "test-key")
    mod.RUN["spend_cap_usd"] = 1.0
    mod.RUN["workers"] = 2
    mod.RUN["skill_loop"].update(rounds=1, practice_per_round=2, test_bench_tasks=3)
    mod.RUN["rubric_loop"].update(rounds=1)
    monkeypatch.setattr(mod, "OUT", tmp_path / "out")
    monkeypatch.setattr(mod, "LOGS", tmp_path / "logs")
    sets = {"practice": ["finance:4001", "hr:5023", "finance:4009"], "gate": ["finance:4010", "hr:5028", "finance:4011"],
            "sealed": ["finance:4012", "hr:5029"]}
    monkeypatch.setattr(mod, "split", lambda name: sets[name])
    original = mod.Phase1.__init__

    def init(self, *, paid=True):
        original(self, paid=paid)
        self.spend.path = tmp_path / "spend.json"
        self.spend.total_usd = 0.0
        for c in (self.minimax, self.editor_client):
            c.http = httpx.Client(transport=fake_chat_transport("minimax/minimax-m3"))
        self.gemini.http = httpx.Client(transport=fake_chat_transport("google/gemini-3.8-flash"))
        self.jev.http = httpx.Client(transport=fake_jev_transport())
        from jevloop.cache import DiskCache
        for c in (self.minimax, self.editor_client, self.gemini):
            c.cache = DiskCache(tmp_path / "cache")
        self.jev.cache = DiskCache(tmp_path / "jevcache")

    monkeypatch.setattr(mod.Phase1, "__init__", init)
    return mod


def test_all_stages_run_end_to_end_on_fakes(script, tmp_path):
    script.stage_skill(types.SimpleNamespace())
    hist = json.loads((tmp_path / "out" / "skill_history.json").read_text())
    assert hist[0]["edits"] and {d["edit"]["target"] for d in hist[0]["decisions"]} == {"rule_broken", "action_missed"}
    assert (tmp_path / "out" / "skill_final.json").exists()
    script.stage_jevdata(types.SimpleNamespace())
    script.stage_rubric(types.SimpleNamespace())
    rb = json.loads((tmp_path / "out" / "rubric_final.json").read_text())
    assert rb["questions"] and "v0" in rb
    script.stage_tau(types.SimpleNamespace())
    assert "tau" in json.loads((tmp_path / "out" / "tau.json").read_text())
    with pytest.raises(SystemExit):  # sealed is held without a release
        script.stage_sealed(types.SimpleNamespace(release_confirmed=False))


def test_sealed_stage_runs_with_release(script, tmp_path, monkeypatch):
    for stage in ("stage_skill", "stage_jevdata", "stage_rubric", "stage_tau"):
        getattr(script, stage)(types.SimpleNamespace())
    release = tmp_path / "SEALED_RELEASE.md"
    release.write_text("released for the test")
    script.RUN["sealed"]["release_file"] = str(release)  # an absolute path; the real file stays absent
    script.stage_sealed(types.SimpleNamespace(release_confirmed=True))
    out = json.loads((tmp_path / "out" / "sealed_results.json").read_text())
    for key in ("V2-1_starting_line", "V2-2a_did_minimax_learn", "V2-2b_did_jev_learn", "V2-3_main_comparison",
                "V2-5_checkpoint_extra", "extra_column_final_playbook_checkpoint_off", "main_comparison"):
        assert key in out


def test_unapproved_run_refuses(tmp_path):
    mod = load_script()
    mod.RUN["approved"] = False
    with pytest.raises(SystemExit):
        mod.Phase1()
