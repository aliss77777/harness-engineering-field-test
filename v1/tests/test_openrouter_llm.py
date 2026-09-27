import json

import httpx
import pytest

from cache import DiskCache
from log import JsonlLogger
from openrouter_llm import OpenRouterJsonClient


SCHEMA = {
    "type": "object",
    "properties": {"status": {"type": "string"}},
    "required": ["status"],
    "additionalProperties": False,
}


def test_openrouter_json_client_uses_structured_output_and_parses_usage(tmp_path):
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["model"] == "google/gemini-3.8-flash"
        assert body["response_format"]["type"] == "json_schema"
        assert body["provider"]["require_parameters"] is True
        return httpx.Response(
            200,
            json={
                "model": "google/gemini-3.8-flash",
                "provider": "Google AI Studio",
                "choices": [{"message": {"content": '{"status":"OK"}'}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "completion_tokens_details": {"reasoning_tokens": 2},
                    "cost": 0.00002625,
                },
            },
        )

    client = OpenRouterJsonClient(
        model="google/gemini-3.8-flash",
        api_key="test",
        cache=DiskCache(tmp_path / "cache"),
        logger=JsonlLogger(tmp_path / "events.jsonl"),
        retries=1,
        backoff_seconds=0,
        temperature=0,
        reasoning_effort="medium",
        expected_model="google/gemini-3.8-flash",
        expected_provider="Google AI Studio",
        allow_fallbacks=False,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert client.generate_json(prompt="test", schema=SCHEMA, event={"run_id": "test"}) == {
        "status": "OK"
    }
    event = json.loads((tmp_path / "events.jsonl").read_text())
    assert event["reasoning_tokens"] == 2
    assert event["cost"] == 0.00002625


def test_openrouter_json_client_uses_cache(tmp_path):
    calls = 0

    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": "google/gemini-3.8-flash",
                "provider": "Google AI Studio",
                "choices": [{"message": {"content": '{"status":"OK"}'}}],
                "usage": {},
            },
        )

    client = OpenRouterJsonClient(
        model="google/gemini-3.8-flash",
        api_key="test",
        cache=DiskCache(tmp_path / "cache"),
        logger=JsonlLogger(tmp_path / "events.jsonl"),
        retries=1,
        backoff_seconds=0,
        temperature=0,
        reasoning_effort="medium",
        expected_model="google/gemini-3.8-flash",
        expected_provider="Google AI Studio",
        allow_fallbacks=False,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client.generate_json(prompt="test", schema=SCHEMA, event={"run_id": "one"})
    client.generate_json(prompt="test", schema=SCHEMA, event={"run_id": "two"})
    assert calls == 1


def test_openrouter_route_mismatch_stops_without_retry(tmp_path):
    calls = 0
    def handler(_request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"model": "wrong", "provider": "Wrong"})
    client = OpenRouterJsonClient(
        model="google/gemini-3.8-flash", api_key="test", cache=DiskCache(tmp_path / "cache"),
        logger=JsonlLogger(tmp_path / "events.jsonl"), retries=3, backoff_seconds=0,
        temperature=0, reasoning_effort="medium", expected_model="google/gemini-3.8-flash",
        expected_provider="Google AI Studio", allow_fallbacks=False,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(RuntimeError, match="served model changed"):
        client.generate_json(prompt="test", schema=SCHEMA, event={"run_id": "test"})
    assert calls == 1


def test_error_body_without_model_is_retried_not_a_route_change(tmp_path):
    import httpx
    from cache import DiskCache
    from log import JsonlLogger
    from openrouter_llm import OpenRouterJsonClient

    responses = iter([
        httpx.Response(200, json={"error": {"code": 429, "message": "rate limited"}}),
        httpx.Response(200, json={
            "model": "google/gemini-test", "provider": "Google AI Studio",
            "choices": [{"message": {"content": '{"status": "OK"}'}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.0},
        }),
    ])
    client = OpenRouterJsonClient(
        model="google/gemini-test", api_key="k", cache=DiskCache(tmp_path / "c"),
        logger=JsonlLogger(tmp_path / "l.jsonl"), retries=2, backoff_seconds=0, temperature=0,
        reasoning_effort="medium", expected_model="google/gemini-test",
        expected_provider="Google AI Studio", allow_fallbacks=False,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda request: next(responses))),
    )
    assert client.generate_json(prompt="p", schema={}, event={}) == {"status": "OK"}
    assert "IncompleteResponseError" in (tmp_path / "l.jsonl").read_text()


def test_out_of_credit_is_fatal_and_not_retried(tmp_path):
    import httpx
    import pytest
    from cache import DiskCache
    from log import JsonlLogger
    from openrouter_llm import OpenRouterJsonClient, OutOfCreditsError

    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(402, json={"error": {"code": 402, "message": "Insufficient credits"}})

    client = OpenRouterJsonClient(
        model="m", api_key="k", cache=DiskCache(tmp_path / "c"), logger=JsonlLogger(tmp_path / "l.jsonl"),
        retries=5, backoff_seconds=0, temperature=0, reasoning_effort="medium", expected_model="m",
        expected_provider="p", allow_fallbacks=False,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(OutOfCreditsError):
        client.generate_json(prompt="p", schema={}, event={})
    assert len(calls) == 1
