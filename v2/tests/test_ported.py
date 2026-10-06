"""v1's tests for the modules ported unchanged (v1/tests/test_cache.py, test_gate.py, test_log.py, test_run.py)."""
import json

import pytest

from jevloop.cache import DiskCache
from jevloop.gate import gate_version
from jevloop.log import JsonlLogger, token_cost
from jevloop.spend import SpendCapExceeded, SpendTracker


def test_cache_key_is_stable_across_dict_order():
    assert DiskCache.key({"a": 1, "b": 2}) == DiskCache.key({"b": 2, "a": 1})


def test_cache_round_trip(tmp_path):
    cache = DiskCache(tmp_path)
    payload = {"model": "test", "input": "hello"}
    cache.put(payload, {"text": "world"})
    assert cache.get(payload) == {"text": "world"}


def test_gate_keeps_clearly_better_version():
    result = gate_version([False] * 10, [True] * 10, p_threshold=0.10)
    assert result.keep
    assert (result.b, result.c) == (10, 0)


def test_gate_rejects_no_change():
    result = gate_version([True, False], [True, False], p_threshold=0.10)
    assert not result.keep
    assert result.p_value == 1.0


def test_token_cost():
    assert token_cost(1_000_000, 500_000, 2.0, 4.0) == 4.0


def test_jsonl_logger_appends(tmp_path):
    path = tmp_path / "events.jsonl"
    logger = JsonlLogger(path)
    logger.write({"run_id": "one"})
    logger.write({"run_id": "two"})
    assert len(path.read_text().splitlines()) == 2


def test_spend_cap_stops_new_calls(tmp_path):
    spend = SpendTracker(tmp_path / "spend.json", cap_usd=1.0)
    spend.record(0.6)
    spend.check()
    spend.record(0.5)
    with pytest.raises(SpendCapExceeded):
        spend.check()
    assert json.loads((tmp_path / "spend.json").read_text())["total_usd"] == pytest.approx(1.1)
    assert SpendTracker(tmp_path / "spend.json", cap_usd=5).total_usd == pytest.approx(1.1)
