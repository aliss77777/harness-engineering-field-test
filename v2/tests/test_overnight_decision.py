"""The overnight driver's reading rule for adopting a replay winner (no model calls)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("overnight_phase1", ROOT / "scripts" / "overnight_phase1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def result(net, passes, keep=True, text="rule"):
    return {"edit": {"op": "add", "index": None, "text": text, "why": "", "target": "wrong_content"},
            "decision": {"keep": keep, "net_diff": net, "passes_diff": passes, "targeted_diff": 0.05}}


def test_adopts_only_a_clear_gain_with_passes_not_lower():
    mod = load()
    assert not mod.decide({"results": []})["adopt"]
    assert not mod.decide({"results": [result(0.04, 3), result(0.10, -1), result(0.12, 2, keep=False)]})["adopt"]  # under +0.07 / lost passes / failed margin test
    d = mod.decide({"results": [result(0.08, 1, text="a"), result(0.11, 0, text="b"), result(0.30, 5, keep=False, text="c")]})
    assert d["adopt"] and d["edit"]["text"] == "b"  # the largest credit gain among those that qualify
    assert mod.decide({"results": [result(0.07, 0)]})["adopt"]  # the boundary counts
