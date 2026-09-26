from prep import clean_text, two_proportion_z


def test_clean_text_strips_html_and_whitespace():
    assert clean_text("<b>Hello</b>\n world &amp; friends") == "Hello world & friends"


def test_two_proportion_z_is_symmetric_and_positive():
    forward = two_proportion_z(20, 1000, 10, 1000)
    reverse = two_proportion_z(10, 1000, 20, 1000)
    assert forward == reverse
    assert forward > 0


def test_two_proportion_z_handles_no_clicks():
    assert two_proportion_z(0, 1000, 0, 1000) == 0

