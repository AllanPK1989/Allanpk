"""The Claude adapter, run through the real Anthropic SDK against a fake HTTP transport."""
import json

import anthropic
import httpx2

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.schemas import ExplainOut, strict_schema
from app.config import Config


def provider_with(handler) -> tuple[AnthropicProvider, list]:
    seen = []

    def record(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    p = AnthropicProvider(Config(ai_provider="anthropic"))
    p.client = anthropic.Anthropic(
        api_key="test-key",
        base_url="http://claude.test",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(record)),
        max_retries=0,
    )
    return p, seen


def message(text: str, stop_reason: str = "end_turn", model: str = "claude-opus-5-5") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 1200, "output_tokens": 300, "cache_read_input_tokens": 800, "cache_creation_input_tokens": 0},
    }


def call(p: AnthropicProvider, tier: str):
    return p.generate_json(
        tier=tier, purpose="explain", system="rules", user="question",
        schema=strict_schema(ExplainOut), max_tokens=2000, hints={},
    )


def test_diagnosis_call_uses_structured_output_effort_and_fallback():
    out = {"text_en": "Because the coil drives the valve.", "text_ta": "Coil தான் valve-ஐ இயக்குது."}
    p, seen = provider_with(lambda r: httpx2.Response(200, json=message(json.dumps(out))))
    result = call(p, "diagnosis")
    assert result.error == "" and result.data == out
    assert (result.input_tokens, result.output_tokens, result.cache_read_tokens) == (1200, 300, 800)
    body = json.loads(seen[0].content)
    assert body["model"] == "claude-opus-5-5"
    assert body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in seen[0].headers["anthropic-beta"]
    assert "temperature" not in body and "thinking" not in body


def test_extraction_call_uses_small_model_without_fallback():
    p, seen = provider_with(lambda r: httpx2.Response(200, json=message('{"text_en": "a", "text_ta": "b"}', model="claude-haiku-5-5")))
    result = call(p, "extraction")
    body = json.loads(seen[0].content)
    assert body["model"] == "claude-haiku-5-5" and body["output_config"]["effort"] == "low"
    assert "fallbacks" not in body and "anthropic-beta" not in seen[0].headers
    assert result.model == "claude-haiku-5-5"


def test_refusal_and_truncation_are_errors_not_data():
    p, _ = provider_with(lambda r: httpx2.Response(200, json=message("", stop_reason="refusal")))
    assert call(p, "diagnosis").error.startswith("refusal")
    p, _ = provider_with(lambda r: httpx2.Response(200, json=message('{"text_en": "cut', stop_reason="max_tokens")))
    assert call(p, "diagnosis").error == "max_tokens"


def test_api_errors_are_reported():
    p, _ = provider_with(lambda r: httpx2.Response(429, json={"type": "error", "error": {"type": "rate_limit_error", "message": "slow down"}}))
    assert call(p, "diagnosis").error.startswith("rate_limited")
    p, _ = provider_with(lambda r: httpx2.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "bad"}}))
    assert call(p, "diagnosis").error.startswith("api_error 400")
