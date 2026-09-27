import numpy as np
import pytest

from hybrid import choose_cascade_threshold, features, fit_stacker, matrix, predict
from verdict_hybrid import compute_hybrid_verdict

QUESTIONS = [{"question_id": "depth", "text": "Deep?", "direction": "helps"},
             {"question_id": "padded", "text": "Padded?", "direction": "hurts"}]


def j(pid, depth, padded, winner, prediction="X"):
    return {"pair_id": pid, "winner": winner, "prediction": prediction, "questions": {
        "depth": {"x_yes_probability": depth[0], "y_yes_probability": depth[1]},
        "padded": {"x_yes_probability": padded[0], "y_yes_probability": padded[1]}}}


def a(pid, prediction, winner, blocked=False):
    return {"pair_id": pid, "prediction": prediction, "winner": winner, "blocked": blocked}


def test_features_encode_llm_pick_and_signed_jev_parts():
    row = features(a("1", "Y", "Y"), j("1", (0.9, 0.1), (0.2, 0.6), "Y"), QUESTIONS, {"depth": 2.0, "padded": 1.0})
    assert row == pytest.approx([-1.0, 1.6, 0.4, 2.0])
    assert features(a("1", "Y", "Y", blocked=True), j("1", (0.5, 0.5), (0.5, 0.5), "Y"), QUESTIONS, None)[0] == 0.0


def test_matrix_requires_aligned_pairs():
    with pytest.raises(ValueError):
        matrix([a("1", "X", "X")], [j("2", (0.5, 0.5), (0.5, 0.5), "X")], QUESTIONS, None)


def test_stacker_learns_to_trust_the_informative_signal():
    rng = np.random.default_rng(0)
    rows_a, rows_j = [], []
    for i in range(400):
        winner = "X" if i % 2 else "Y"
        llm_right = rng.random() < 0.8
        pick = winner if llm_right else ("Y" if winner == "X" else "X")
        noise = rng.random(2)
        rows_a.append(a(str(i), pick, winner))
        rows_j.append(j(str(i), (noise[0], noise[1]), (0.5, 0.5), winner))
    x, y, blocked = matrix(rows_a, rows_j, QUESTIONS, None)
    fit = fit_stacker(x, y, c_grid=[0.1, 1.0], folds=5, seed=1)
    assert fit["coef"][0] > 0.5 and abs(fit["coef"][1]) < fit["coef"][0]
    preds = predict(fit["coef"], x, [r["pair_id"] for r in rows_a], blocked, [r["prediction"] for r in rows_j], seed=1)
    assert np.mean([p == r["winner"] for p, r in zip(preds, rows_a)]) > 0.75


def test_blocked_pairs_fall_back_to_jev_pick():
    x = np.array([[0.0, 5.0, 0.0, 5.0]])
    assert predict([1.0, 1.0, 1.0, 1.0], x, ["p"], [True], ["Y"], seed=1) == ["Y"]


def test_cascade_threshold_respects_llm_share_cap():
    margins = [0.1, 0.2, 0.9, 1.0]
    out = choose_cascade_threshold(margins, jev_correct=[False, False, True, True],
                                   llm_correct=[True, True, False, False], max_llm_share=0.5)
    assert out["llm_share"] == 0.5 and out["accuracy"] == 1.0


def v(n_correct, total=1000):
    return [True] * n_correct + [False] * (total - n_correct)


CONFIG = {"alpha": 0.05, "equivalence_margin": 0.03, "mcnemar_exact_max_discordant": 25, "memorization_accuracy": 0.7}


def test_hybrid_verdict_rows():
    costs = {"llm": 1.5, "jev": 0.06, "hybrid": 1.56}
    assert compute_hybrid_verdict(llm=v(700), jev=v(650), hybrid=v(760), baseline=v(600),
                                  costs_per_1000=costs, config=CONFIG)["verdict"] == "hybrid_beats_llm"
    assert compute_hybrid_verdict(llm=v(760), jev=v(650), hybrid=v(700), baseline=None,
                                  costs_per_1000=costs, config=CONFIG)["verdict"] == "combination_hurts"
    same = compute_hybrid_verdict(llm=v(750), jev=v(650), hybrid=v(750), baseline=None, costs_per_1000=costs, config=CONFIG)
    assert same["verdict"] == "no_meaningful_gain"
    llm = v(740)
    hybrid = [True] * 700 + [False] * 40 + [True] * 55 + [False] * 205  # +15 net, 95 discordant
    result = compute_hybrid_verdict(llm=llm, jev=v(650), hybrid=hybrid, baseline=None, costs_per_1000=costs, config=CONFIG)
    assert result["verdict"] == "inconclusive"
