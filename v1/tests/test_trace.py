import pytest

from trace import aggregate_trace, contributions, fit_weights, mistake_trace, rescore, rich_evidence
from verdict_trace import compute_trace_verdict, holm


QUESTIONS = [
    {"question_id": "depth", "text": "Deep?", "direction": "helps"},
    {"question_id": "padded", "text": "Padded?", "direction": "hurts"},
]
LABELS = {"x": "1", "y": "2"}


def record(pid, depth, padded, winner, prediction=None):
    rec = {"pair_id": pid, "winner": winner, "questions": {
        "depth": {"x_yes_probability": depth[0], "y_yes_probability": depth[1]},
        "padded": {"x_yes_probability": padded[0], "y_yes_probability": padded[1]}}}
    total = sum(contributions(rec, QUESTIONS).values())
    rec["prediction"] = prediction or ("X" if total > 0 else "Y")
    rec["correct"] = rec["prediction"] == winner
    return rec


def test_contributions_sum_to_the_rubric_score_difference():
    rec = record("1", (0.9, 0.2), (0.8, 0.1), "Y")
    parts = contributions(rec, QUESTIONS)
    assert parts["depth"] == pytest.approx(0.7)
    assert parts["padded"] == pytest.approx(-0.7)  # "hurts": more padding in X pushes toward Y


def test_mistake_trace_names_the_question_that_pushed_toward_the_loser():
    rec = record("1", (0.9, 0.1), (0.5, 0.5), "Y")  # depth pushed X, Y won
    assert not rec["correct"]
    top = mistake_trace(rec, QUESTIONS, LABELS)[0]
    assert top["question_id"] == "depth"
    assert top["pushed_toward"] == "1"
    assert top["pushed_toward_winner"] is False


def test_aggregate_trace_counts_decisive_wrong_pushes():
    records = [record("1", (0.9, 0.1), (0.5, 0.5), "Y"), record("2", (0.9, 0.1), (0.5, 0.5), "X")]
    rows = {row["question_id"]: row for row in aggregate_trace(records, QUESTIONS)}
    assert rows["depth"]["mistakes_pushed_toward_loser"] == 1
    assert rows["depth"]["decisive_and_wrong"] == 1 and rows["depth"]["decisive_and_right"] == 1
    assert rows["padded"]["decisive_pairs"] == 0


def test_rich_evidence_bins_by_gap_and_flags_overlap():
    records = [record(str(i), (0.9, 0.1) if i % 2 else (0.1, 0.9), (0.1, 0.9) if i % 2 else (0.9, 0.1),
                      "X" if i % 2 else "Y") for i in range(10)]
    out = rich_evidence(records, QUESTIONS, [0.2, 0.5], 0.6)
    depth_bins = out["win_rate_by_gap"][0]["by_gap"]
    assert depth_bins[-1]["pairs"] == 10 and depth_bins[-1]["win_rate"] == 1.0
    assert out["overlapping_questions"][0]["questions"] == ["depth", "padded"]


def test_fitted_weights_learn_a_backwards_direction_and_rescore():
    # "padded" is marked hurts, but here the padded response always wins.
    records = [record(str(i), (0.5, 0.5), (0.9, 0.1) if i % 2 else (0.1, 0.9), "X" if i % 2 else "Y")
               for i in range(40)]
    weights = fit_weights(records, QUESTIONS, c=1.0, seed=1)
    assert weights["padded"] < 0
    rescored = rescore(records, QUESTIONS, weights, seed=1, label="t")
    assert all(r["correct"] for r in rescored)
    assert sum(r["correct"] for r in records) == 0


def test_holm_step_down():
    assert holm({"a": 0.01, "b": 0.04}, 0.05) == {"a": True, "b": True}
    assert holm({"a": 0.03, "b": 0.04}, 0.05) == {"a": False, "b": False}


def v(correct, total=400):
    return [True] * correct + [False] * (total - correct)


def test_trace_verdict_primary_answers():
    config = {"alpha": 0.05, "trace_primary_alpha": 0.05, "equivalence_margin": 0.03, "max_cost_ratio": 0.2,
              "memorization_accuracy": 0.7, "mcnemar_exact_max_discordant": 25, "rules_version": "arena_v2"}
    vectors = {"a_version0": v(300), "a_final": v(300), "b_version0": v(260), "b_final": v(270),
               "bp_final": v(300), "bw_final": v(300), "bw_version0": v(265), "baseline": v(250)}
    out = compute_trace_verdict(vectors=vectors, costs_per_1000={"a_final": 1.0, "bp_final": 0.05, "bw_final": 0.05},
                                config=config)
    assert out["primary"] == {"trace": "helps", "weights": "no_detectable_difference"}
    assert out["learning_checks"]["bp_final_vs_version0"]["learned"]
    assert out["headline_arena_v2"]["primary_bp"]["verdict"] == "learns_as_well_far_cheaper"
