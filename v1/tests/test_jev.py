import httpx

from cache import DiskCache
from deciders import RubricQuestion
from jev import OpenRouterJevClient
from log import JsonlLogger


def test_jev_client_parses_noul_probabilities(tmp_path):
    def handler(request: httpx.Request):
        assert request.url.path == "/api/alpha/decisions"
        return httpx.Response(
            200,
            json={
                "model": "typesafe/jev-1.13-test",
                "provider": "TypeSafe",
                "answers": {"curious": {"type": "noul", "noul": 0.87}},
                "usage": {"input_tokens": 100, "output_tokens": 10, "cost": 0.0000042},
            },
        )

    client = OpenRouterJevClient(
        model="typesafe/jev-1.13",
        api_key="test-key",
        cache=DiskCache(tmp_path / "cache"),
        logger=JsonlLogger(tmp_path / "events.jsonl"),
        retries=1,
        backoff_seconds=0,
        expected_model="typesafe/jev-1.13-test",
        expected_provider="TypeSafe",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = client.evaluate(
        "A mysterious discovery",
        [RubricQuestion("curious", "Does it create curiosity?", "helps")],
        {"run_id": "test"},
    )
    assert result == {"curious": 0.87}


def test_jev_client_uses_cache(tmp_path):
    calls = 0

    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": "typesafe/jev-1.13-test",
                "provider": "TypeSafe",
                "answers": {"q": {"type": "noul", "noul": 0.5}},
                "usage": {},
            },
        )

    client = OpenRouterJevClient(
        model="typesafe/jev-1.13",
        api_key="test-key",
        cache=DiskCache(tmp_path / "cache"),
        logger=JsonlLogger(tmp_path / "events.jsonl"),
        retries=1,
        backoff_seconds=0,
        expected_model="typesafe/jev-1.13-test",
        expected_provider="TypeSafe",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    question = [RubricQuestion("q", "Question?", "helps")]
    client.evaluate("state", question, {"run_id": "one"})
    client.evaluate("state", question, {"run_id": "two"})
    assert calls == 1


def test_jev_client_can_bypass_cache(tmp_path):
    calls = 0

    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": "typesafe/jev-1.13-test",
                "provider": "TypeSafe",
                "answers": {"q": {"type": "noul", "noul": 0.5}},
                "usage": {},
            },
        )

    client = OpenRouterJevClient(
        model="typesafe/jev-1.13",
        api_key="test-key",
        cache=DiskCache(tmp_path / "cache"),
        logger=JsonlLogger(tmp_path / "events.jsonl"),
        retries=1,
        backoff_seconds=0,
        expected_model="typesafe/jev-1.13-test",
        expected_provider="TypeSafe",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    question = [RubricQuestion("q", "Question?", "helps")]
    client.evaluate("state", question, {"run_id": "one"}, use_cache=False)
    client.evaluate("state", question, {"run_id": "two"}, use_cache=False)
    assert calls == 2
