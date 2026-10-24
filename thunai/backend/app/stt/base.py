"""Speech-to-text adapter interface. Pick a provider with STT_PROVIDER; benchmark before choosing."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class STTUnavailable(RuntimeError):
    """No provider configured or the provider failed; the UI asks the technician to type."""


@dataclass
class STTResult:
    text: str
    provider: str
    language: str = ""
    confidence: float | None = None


class STTProvider(Protocol):
    name: str

    def transcribe(self, audio: Path, language_hint: str) -> STTResult: ...
