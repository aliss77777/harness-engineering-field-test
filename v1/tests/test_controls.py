import pandas as pd

from controls import difference_features, fake_accuracy, headline_features


def test_headline_features_are_exactly_the_six_registered_features():
    features = headline_features("You Won't Believe My 3 Questions!")
    assert set(features) == {
        "length", "question_mark", "number", "you", "i_or_me", "exclamation_mark"
    }
    assert features["number"] == 1
    assert features["you"] == 1


def test_difference_features_are_x_minus_y():
    row = pd.Series({"headline_x": "You?", "headline_y": "Plain"})
    assert difference_features(row)["question_mark"] == 1


def test_fake_decider_is_reproducible():
    frame = pd.DataFrame({"winner": ["X", "Y"] * 100})
    assert fake_accuracy(frame, 7) == fake_accuracy(frame, 7)
    assert 0.4 <= fake_accuracy(frame, 7) <= 0.6
