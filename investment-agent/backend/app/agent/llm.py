"""Claude client and small helpers shared by the chat agent, the digest writer and news triage."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import anthropic

from ..config import get_settings

log = logging.getLogger(__name__)

# Server-side refusal fallback (beta). Supported on the Sonnet/Opus/Fable lines, not on Haiku.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_FALLBACK_MODELS = ("claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-fable-5-2")


@lru_cache
def client() -> anthropic.Anthropic:
    s = get_settings()
    return anthropic.Anthropic(api_key=s.anthropic_api_key or None, max_retries=3, timeout=300.0)


def ai_enabled() -> bool:
    return get_settings().ai_enabled


def fallback_kwargs(model: str) -> dict[str, Any]:
    """Opt into server-side refusal fallback where the model supports it."""
    if model.startswith(_FALLBACK_MODELS):
        return {"betas": [FALLBACK_BETA], "fallbacks": "default"}
    return {}


def text_of(message: Any) -> str:
    return "".join(b.text for b in message.content if getattr(b, "type", "") == "text").strip()


def write(system: str, prompt: str, *, model: str | None = None, effort: str | None = None,
          max_tokens: int = 32000) -> str | None:
    """One streamed request that returns the reply text, or None if AI is off / the call failed / it was declined."""
    if not ai_enabled():
        return None
    s = get_settings()
    model = model or s.analysis_model
    try:
        with client().beta.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": effort or s.analysis_effort},
            **fallback_kwargs(model),
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.RateLimitError as e:
        log.warning("Claude rate limited: %s", e)
        return None
    except anthropic.APIStatusError as e:
        log.error("Claude API error %s: %s", e.status_code, e.message)
        return None
    except anthropic.APIConnectionError as e:
        log.error("Claude connection error: %s", e)
        return None
    if msg.stop_reason == "refusal":
        details = getattr(msg, "stop_details", None)
        log.warning("Claude declined (category=%s)", getattr(details, "category", None))
        return None
    if msg.stop_reason == "max_tokens":
        log.warning("Claude reply hit max_tokens; using what arrived")
    return text_of(msg) or None
