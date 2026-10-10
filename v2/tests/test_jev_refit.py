"""Jev refit (stage B1): metrics and the cross-validation split (no model calls)."""
import importlib.util
import random
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("jev_refit", ROOT / "scripts" / "jev_refit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_auc_and_gap_basics():
    m = load()
    assert m.auc([0.1, 0.2, 0.8, 0.9], [False, False, True, True]) == 1.0
    assert m.auc([0.9, 0.8, 0.2, 0.1], [False, False, True, True]) == 0.0
    assert m.auc([0.5, 0.5], [False, True]) == 0.5
    g = m.lowest_share_gap([0.1, 0.2, 0.3, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.95], [0.1, 0.2, 0.3, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.95], share=0.3)
    assert g["n_low"] == 3 and g["gap"] == pytest.approx(4.85 / 7 - 0.2)


def test_folds_keep_a_task_together_and_are_seeded():
    m = load()
    tasks = [f"t{i}" for i in range(20)] * 4  # a task repeats under several playbooks
    f1, f2 = m.fold_of(tasks, folds=5, seed=1), m.fold_of(tasks, folds=5, seed=1)
    assert f1 == f2 and set(f1.values()) == {0, 1, 2, 3, 4} and len(f1) == 20


def make_rows(signal: float, n_tasks=60, reps=4, seed=0):
    from jevloop.rubric import Question
    qs = (Question("q1", "a", "helps"), Question("q2", "b", "helps"))
    rng = random.Random(seed)
    rows = []
    for t in range(n_tasks):
        for r in range(reps):
            credit = rng.random()
            noise = lambda: min(1.0, max(0.0, 0.5 + signal * (credit - 0.5) + rng.gauss(0, 0.25)))  # noqa: E731
            rows.append({"task": f"t{t}", "credit": credit, "probs": {"q1": noise(), "q2": noise()}, "test": r == 0})
    return qs, rows


def test_cross_validation_finds_real_signal_and_no_signal():
    m = load()
    qs, rows = make_rows(signal=1.0)
    scores, full = m.cross_validated_scores(rows, qs)
    credits = [r["credit"] for r in rows if r["test"]]
    assert len(scores) == len(credits) == 60
    assert m.metrics(scores, credits)["auc"] > 0.75
    qs0, rows0 = make_rows(signal=0.0, seed=3)
    s0, _ = m.cross_validated_scores(rows0, qs0)
    c0 = [r["credit"] for r in rows0 if r["test"]]
    assert 0.3 < m.metrics(s0, c0)["auc"] < 0.7  # nothing to find: no apparent skill out of fold


def test_bar_needs_auc_lower_bound_and_gap():
    m = load()
    ok = {"auc": 0.7, "auc_ci95": [0.6, 0.8], "gap": 0.12}
    assert m.bar_met(ok)
    assert not m.bar_met({**ok, "auc": 0.64})
    assert not m.bar_met({**ok, "auc_ci95": [0.48, 0.8]})
    assert not m.bar_met({**ok, "gap": 0.09})
