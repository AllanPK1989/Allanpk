"""Demo speech-to-text. Returns a fixed, clearly labelled sample so the voice flow can be shown
without a provider. Tests may put a <audio>.txt file next to the audio to control the text."""
from pathlib import Path

from .base import STTResult

DEMO_TEXT = "[Demo transcript] Cylinder return aagala, solenoid coil burnt, coil maathiten, 10 cycle check OK."


class MockSTT:
    name = "mock"

    def transcribe(self, audio: Path, language_hint: str) -> STTResult:
        sidecar = audio.with_suffix(audio.suffix + ".txt")
        text = sidecar.read_text(encoding="utf-8").strip() if sidecar.exists() else DEMO_TEXT
        return STTResult(text=text, provider=self.name, language=language_hint, confidence=None)
