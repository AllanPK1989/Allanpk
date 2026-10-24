"""Provider-agnostic AI interface. Swap providers with AI_PROVIDER; no other code changes."""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class AIResult:
    data: dict | None
    model: str
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    stop_reason: str = ""
    error: str = ""
    extra: dict = field(default_factory=dict)


class AIProvider(Protocol):
    name: str

    def generate_json(
        self,
        *,
        tier: str,  # "diagnosis" (larger model) or "extraction" (smaller model)
        purpose: str,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int,
        hints: dict,  # raw context; only the mock provider reads it
        images: list[tuple[str, str]] | None = None,  # (media type, base64) photos, placed before the text
    ) -> AIResult: ...
