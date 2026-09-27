import pytest

from verdict import compute_verdict, paired_test


CONFIG = {
    "alpha": 0.05,
    "equivalence_margin": 0.03,
    "max_cost_ratio": 0.20,
    "memorization_accuracy": 0.70,
    "mcnemar_exact_max_discordant": 25,
}


def vector(correct: int, total: int = 200):
    return [True] * correct + [False] * (total - correct)


def verdict(a0, af, b0, bf, a_cost=1.0, b_cost=0.1):
    return compute_verdict(
        a_version0=a0,
        a_final=af,
        b_version0=b0,
        b_final=bf,
        a_cost_per_1000=a_cost,
        b_cost_per_1000=b_cost,
        config=CONFIG,
    )


def test_no_signal_is_first_match():
    result = verdict(vector(100), vector(100), vector(100), vector(100))
    assert result["verdict"] == "no_signal"


def test_jev_loop_learns_better():
    result = verdict(vector(120), vector(120), vector(110), vector(160))
    assert result["verdict"] == "jev_loop_learns_better"
    assert result["checks"]["b_learned"]
    assert result["checks"]["b_better"]


def test_learns_as_well_far_cheaper():
    final = vector(140)
    result = verdict(vector(130), final, vector(100), final, a_cost=1.0, b_cost=0.2)
    assert result["verdict"] == "learns_as_well_far_cheaper"
    assert result["checks"]["same_quality"]
    assert result["checks"]["cheaper"]


def test_hypothesis_weakened():
    result = verdict(vector(140), vector(165), vector(120), vector(120))
    assert result["verdict"] == "hypothesis_weakened"
    assert result["checks"]["a_better"]


def test_inconclusive():
    result = verdict(vector(120), vector(125), vector(120), vector(125))
    assert result["verdict"] == "inconclusive"


def test_memorization_flag_is_strictly_above_threshold():
    at_threshold = verdict(vector(140), vector(140), vector(140), vector(140))
    above = verdict(vector(141), vector(141), vector(140), vector(140))
    assert not at_threshold["checks"]["memorization_flag"]
    assert above["checks"]["memorization_flag"]


def test_mcnemar_uses_exact_for_few_disagreements():
    result = paired_test(
        [False] * 10 + [True] * 10,
        [True] * 10 + [True] * 10,
        exact_max_discordant=25,
    )
    assert result.method == "exact"
    assert result.p_value == pytest.approx(0.001953125)


def test_mcnemar_uses_corrected_chi_square_for_many_disagreements():
    result = paired_test(
        [False] * 40 + [True] * 10,
        [True] * 40 + [True] * 10,
        exact_max_discordant=25,
    )
    assert result.method == "chi_square_continuity_corrected"
    assert result.p_value < 0.05


ARENA = {**CONFIG, "rules_version": "arena_v2"}


def arena_verdict(a0, af, b0, bf, baseline=None):
    return compute_verdict(
        a_version0=a0, a_final=af, b_version0=b0, b_final=bf,
        a_cost_per_1000=1.0, b_cost_per_1000=0.1, config=ARENA, baseline=baseline,
    )


def test_arena_neither_loop_learned_precedes_a_vs_b():
    # Under the MVP rules this is "hypothesis weakened"; Arena rules stop at row 2.
    assert verdict(vector(140), vector(140), vector(120), vector(120))["verdict"] == "hypothesis_weakened"
    result = arena_verdict(vector(140), vector(140), vector(120), vector(120))
    assert result["verdict"] == "neither_loop_learned"
    assert result["rules_version"] == "arena_v2"


def test_arena_only_jev_loop_learned_precedes_hypothesis_weakened():
    result = arena_verdict(vector(150), vector(150), vector(100), vector(140))
    assert result["checks"]["b_learned"] and not result["checks"]["a_learned"]
    assert result["checks"]["a_better"]
    assert result["verdict"] == "only_jev_loop_learned"


def test_arena_keeps_mvp_rows_when_both_learn():
    result = arena_verdict(vector(120), vector(150), vector(110), vector(170))
    assert result["verdict"] == "jev_loop_learns_better"


def test_b_vs_code_baseline_is_reported_not_a_verdict_row():
    result = arena_verdict(vector(140), vector(140), vector(120), vector(150), baseline=vector(120))
    assert result["tests"]["b_vs_baseline"]["b"] == 30
    assert result["checks"]["b_beats_baseline"]
    assert result["accuracy"]["code_baseline"] == 0.6


def test_unknown_rules_version_is_rejected():
    with pytest.raises(ValueError, match="rules_version"):
        compute_verdict(a_version0=vector(1, 2), a_final=vector(1, 2), b_version0=vector(1, 2),
                        b_final=vector(1, 2), a_cost_per_1000=1, b_cost_per_1000=1,
                        config={**CONFIG, "rules_version": "v9"})
