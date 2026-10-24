"""Claude API adapter (Anthropic Python SDK)."""
import json

import anthropic

from ..config import Config
from .base import AIResult

# Server-side refusal fallback ("default" mode) is available for these model families on the
# Claude API. Haiku has no server-side fallback.
_FALLBACK_PREFIXES = ("claude-opus-5", "claude-fable-5", "claude-sonnet-5-5")
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        # Credentials come from ANTHROPIC_API_KEY (never hard-coded).
        self.client = anthropic.Anthropic(timeout=cfg.ai_timeout_s, max_retries=2)

    def _model_and_effort(self, tier: str) -> tuple[str, str]:
        if tier == "diagnosis":
            return self.cfg.ai_model_diagnosis, self.cfg.ai_effort_diagnosis
        return self.cfg.ai_model_extraction, self.cfg.ai_effort_extraction

    def generate_json(self, *, tier, purpose, system, user, schema, max_tokens, hints) -> AIResult:
        model, effort = self._model_and_effort(tier)
        request = dict(
            model=model,
            max_tokens=max_tokens,
            # The rules prompt is identical across calls, so cache it.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": effort,
                "format": {"type": "json_schema", "schema": schema},
            },
        )
        try:
            if self.cfg.ai_refusal_fallback and model.startswith(_FALLBACK_PREFIXES):
                response = self.client.beta.messages.create(
                    betas=[_FALLBACK_BETA], fallbacks="default", **request
                )
            else:
                response = self.client.messages.create(**request)
        except anthropic.RateLimitError as e:
            return AIResult(None, model, error=f"rate_limited: {e.message}")
        except anthropic.APIStatusError as e:
            return AIResult(None, model, error=f"api_error {e.status_code}: {e.message}")
        except anthropic.APIConnectionError:
            return AIResult(None, model, error="connection_error")

        usage = response.usage
        result = AIResult(
            data=None,
            model=response.model or model,
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            stop_reason=response.stop_reason or "",
        )
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            result.error = f"refusal: {getattr(details, 'category', '') or ''}"
            return result
        if response.stop_reason == "max_tokens":
            result.error = "max_tokens"
            return result
        text = next((b.text for b in response.content if b.type == "text"), "")
        result.text = text
        try:
            result.data = json.loads(text)
        except json.JSONDecodeError as e:
            result.error = f"invalid_json: {e}"
        return result
