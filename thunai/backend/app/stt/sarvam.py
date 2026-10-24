"""Sarvam AI speech-to-text (Indian provider with Tamil and code-mixed speech support).

Written against Sarvam's published REST API (`POST /speech-to-text`, header
`api-subscription-key`, form fields `file`, `model`, `language_code`). Verify against the current
documentation during the provider benchmark (SPEC.md, question 8). Short clips only (the
synchronous endpoint limits clip length); the app records short voice notes.
"""
from pathlib import Path

import httpx

from ..config import Config
from .base import STTResult, STTUnavailable

URL = "https://api.sarvam.ai/speech-to-text"
LANGUAGE_CODES = {"en": "en-IN", "ta": "ta-IN"}


class SarvamSTT:
    name = "sarvam"

    def __init__(self, cfg: Config):
        if not cfg.sarvam_api_key:
            raise STTUnavailable("SARVAM_API_KEY is not set")
        self.key = cfg.sarvam_api_key
        self.model = cfg.sarvam_model

    def transcribe(self, audio: Path, language_hint: str) -> STTResult:
        data = {"model": self.model, "language_code": LANGUAGE_CODES.get(language_hint, "unknown")}
        try:
            with audio.open("rb") as f:
                response = httpx.post(
                    URL,
                    headers={"api-subscription-key": self.key},
                    data=data,
                    files={"file": (audio.name, f, "audio/wav")},
                    timeout=120,
                )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise STTUnavailable(f"Transcription failed: {e}") from e
        body = response.json()
        return STTResult(
            text=(body.get("transcript") or "").strip(),
            provider=self.name,
            language=body.get("language_code", ""),
        )
