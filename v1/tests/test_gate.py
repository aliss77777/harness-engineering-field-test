from gate import gate_version


def test_gate_keeps_clearly_better_version():
    result = gate_version([False] * 10, [True] * 10, p_threshold=0.10)
    assert result.keep
    assert (result.b, result.c) == (10, 0)


def test_gate_rejects_no_change():
    result = gate_version([True, False], [True, False], p_threshold=0.10)
    assert not result.keep
    assert result.p_value == 1.0

