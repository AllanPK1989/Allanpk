"""One place that runs AI calls: render prompt → call provider → validate → retry once → log cost."""
import logging
import time
from collections.abc import Callable
from functools import lru_cache

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ..config import get_config
from ..models import AICall, AISession
from . import prompts
from .base import AIProvider
from .schemas import strict_schema

log = logging.getLogger("thunai.ai")


class AIOutputError(ValueError):
    """Raised by a validator when the output breaks a rule (for example a safety rule)."""


@lru_cache
def get_provider() -> AIProvider:
    cfg = get_config()
    if cfg.ai_provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(cfg)
    from .mock_provider import MockProvider

    return MockProvider()


def cost_usd(model: str, input_tokens: int, output_tokens: int, cache_read: int, cache_write: int) -> float:
    price_in, price_out = get_config().price_for(model)
    billed_in = input_tokens + cache_write * 1.25 + cache_read * 0.1
    return round((billed_in * price_in + output_tokens * price_out) / 1_000_000, 6)


def call_json[T: BaseModel](
    db: Session,
    *,
    purpose: str,
    prompt_name: str,
    tier: str,
    variables: dict,
    out_model: type[T],
    max_tokens: int,
    hints: dict | None = None,
    session: AISession | None = None,
    log_id: int | None = None,
    validate: Callable[[T], T] | None = None,
    info: dict | None = None,
) -> tuple[T | None, str]:
    """Return (validated output, "") or (None, error). Invalid output is retried once.

    `info`, when given, receives the model and prompt version that produced the answer.
    """
    prompt = prompts.load(prompt_name)
    system, user = prompt.render(variables)
    schema = strict_schema(out_model)
    provider = get_provider()
    error = ""
    for attempt in range(2):
        message = user
        if attempt and error:
            message += (
                f"\n\n## Your previous answer was rejected\n{error}\n"
                "Answer again and follow every rule."
            )
        started = time.monotonic()
        result = provider.generate_json(
            tier=tier,
            purpose=purpose,
            system=system,
            user=message,
            schema=schema,
            max_tokens=max_tokens,
            hints=hints or {},
        )
        output: T | None = None
        error = result.error
        if not error:
            try:
                output = out_model.model_validate(result.data)
                if validate:
                    output = validate(output)
            except ValidationError as e:
                error = f"Output did not match the contract: {e.errors()[:3]}"
                output = None
            except AIOutputError as e:
                error = str(e)
                output = None
        cost = cost_usd(
            result.model,
            result.input_tokens,
            result.output_tokens,
            result.cache_read_tokens,
            result.cache_write_tokens,
        )
        db.add(
            AICall(
                purpose=purpose,
                provider=provider.name,
                model=result.model,
                prompt_version=prompt.tag,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cache_read_tokens=result.cache_read_tokens,
                cache_write_tokens=result.cache_write_tokens,
                cost_usd=cost,
                ok=output is not None,
                error=error[:2000],
                duration_ms=int((time.monotonic() - started) * 1000),
                ai_session_id=session.id if session else None,
                log_id=log_id,
            )
        )
        if session is not None:
            session.model = result.model
            session.prompt_version = prompt.tag
            session.input_tokens += result.input_tokens + result.cache_read_tokens + result.cache_write_tokens
            session.output_tokens += result.output_tokens
            session.cost_usd = round(session.cost_usd + cost, 6)
        if info is not None:
            info.update(model=result.model, prompt_version=prompt.tag)
        if output is not None:
            return output, ""
        log.warning("AI %s attempt %d failed: %s", purpose, attempt + 1, error)
        if error.startswith(("rate_limited", "connection_error", "api_error", "refusal")):
            break  # retrying the same request right away will not help
    return None, error or "unknown error"
