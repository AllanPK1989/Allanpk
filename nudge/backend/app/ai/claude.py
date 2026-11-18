"""Claude API adapter (Anthropic Python SDK): one structured-JSON request per call."""
import json
import time as _time
from dataclasses import dataclass

import anthropic

from ..config import Config

# Server-side refusal fallback ("default" mode) is offered for these families on the Claude API.
_FALLBACK_PREFIXES = ("claude-opus-5", "claude-fable-5", "claude-sonnet-5-5")
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class AIResult:
    data: dict | None
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: str = ""


class ClaudeClient:
    def __init__(self, cfg: Config, client: anthropic.Anthropic | None = None):
        self.cfg = cfg
        # Credentials come from the environment (ANTHROPIC_API_KEY); never hard-coded.
        self.client = client or anthropic.Anthropic(timeout=cfg.ai_timeout_s, max_retries=2)

    def generate_json(self, *, system: str, user: str, schema: dict, max_tokens: int = 8000) -> AIResult:
        model = self.cfg.ai_model
        request = dict(
            model=model,
            max_tokens=max_tokens,
            # The instructions are the same on every call, so mark them for caching.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": self.cfg.ai_effort,
                "format": {"type": "json_schema", "schema": schema},
            },
        )
        started = _time.monotonic()
        try:
            if self.cfg.ai_refusal_fallback and model.startswith(_FALLBACK_PREFIXES):
                response = self.client.beta.messages.create(betas=[_FALLBACK_BETA], fallbacks="default", **request)
            else:
                response = self.client.messages.create(**request)
        except anthropic.AuthenticationError:
            return AIResult(None, model, error="auth_error: check ANTHROPIC_API_KEY")
        except anthropic.RateLimitError as e:
            return AIResult(None, model, error=f"rate_limited: {e.message}")
        except anthropic.APIStatusError as e:
            return AIResult(None, model, error=f"api_error {e.status_code}: {e.message}")
        except anthropic.APIConnectionError:
            return AIResult(None, model, error="connection_error")
        latency = int((_time.monotonic() - started) * 1000)

        usage = response.usage
        result = AIResult(
            data=None,
            model=response.model or model,
            input_tokens=(usage.input_tokens or 0) + (getattr(usage, "cache_read_input_tokens", 0) or 0)
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0),
            output_tokens=usage.output_tokens or 0,
            latency_ms=latency,
        )
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            result.error = f"refusal: {getattr(details, 'category', '') or ''}"
            return result
        if response.stop_reason == "max_tokens":
            result.error = "max_tokens"
            return result
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            result.data = json.loads(text)
        except json.JSONDecodeError as e:
            result.error = f"invalid_json: {e}"
        return result
