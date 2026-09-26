from log import JsonlLogger, token_cost


def test_token_cost():
    assert token_cost(1_000_000, 500_000, 2.0, 4.0) == 4.0


def test_jsonl_logger_appends(tmp_path):
    path = tmp_path / "events.jsonl"
    logger = JsonlLogger(path)
    logger.write({"run_id": "one"})
    logger.write({"run_id": "two"})
    assert len(path.read_text().splitlines()) == 2
