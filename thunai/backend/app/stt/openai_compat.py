"""Any server that implements the OpenAI-style `POST /audio/transcriptions` endpoint.

This includes self-hosted Whisper servers (for example faster-whisper based servers), which keep
audio on the plant network. Set STT_BASE_URL (e.g. http://whisper:8000/v1), STT_MODEL and, if the
server needs one, STT_API_KEY.
"""
from pathlib import Path

import httpx

from ..config import Config
from .base import STTResult, STTUnavailable


class OpenAICompatSTT:
    name = "openai_compat"

    def __init__(self, cfg: Config):
        if not cfg.stt_base_url:
            raise STTUnavailable("STT_BASE_URL is not set")
        self.url = cfg.stt_base_url.rstrip("/") + "/audio/transcriptions"
        self.model = cfg.stt_model
        self.headers = {"Authorization": f"Bearer {cfg.stt_api_key}"} if cfg.stt_api_key else {}

    def transcribe(self, audio: Path, language_hint: str) -> STTResult:
        data = {"model": self.model, "response_format": "json"}
        if language_hint in ("en", "ta"):
            data["language"] = language_hint  # omit for mixed speech; the model detects it
        try:
            with audio.open("rb") as f:
                response = httpx.post(
                    self.url,
                    headers=self.headers,
                    data=data,
                    files={"file": (audio.name, f, "audio/wav")},
                    timeout=120,
                )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise STTUnavailable(f"Transcription failed: {e}") from e
        body = response.json()
        return STTResult(text=(body.get("text") or "").strip(), provider=self.name, language=body.get("language", ""))
