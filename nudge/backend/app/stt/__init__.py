"""Speech to text. Pick a provider with STT_PROVIDER (openai_compat | mock | none)."""
from dataclasses import dataclass

import httpx

from ..config import Config, get_config

DEMO_TRANSCRIPT = ("Call the vendor about the bearing quote tomorrow at 11, send the PM report by Friday, "
                   "and follow up with Ravi on the spares next Tuesday.")


class STTUnavailable(RuntimeError):
    """No provider, or it failed. The app asks the user to type instead."""


@dataclass
class STTResult:
    text: str
    provider: str


class MockSTT:
    """For tests and screenshots: returns a fixed sample sentence."""

    name = "mock"

    def transcribe(self, audio: bytes, filename: str, content_type: str, prompt: str = "") -> STTResult:
        if len(audio) < 200:
            raise STTUnavailable("Recording too short")
        return STTResult(DEMO_TRANSCRIPT, self.name)


class OpenAICompatSTT:
    """Any server with an OpenAI-style POST /audio/transcriptions endpoint.

    The bundled Whisper container (../stt) is one; it keeps recordings on your own server.
    """

    name = "openai_compat"

    def __init__(self, cfg: Config):
        if not cfg.stt_base_url:
            raise STTUnavailable("STT_BASE_URL is not set")
        self.url = cfg.stt_base_url.rstrip("/") + "/audio/transcriptions"
        self.model = cfg.stt_model
        self.timeout = cfg.stt_timeout_s
        self.headers = {"Authorization": f"Bearer {cfg.stt_api_key}"} if cfg.stt_api_key else {}

    def transcribe(self, audio: bytes, filename: str, content_type: str, prompt: str = "") -> STTResult:
        data = {"model": self.model, "response_format": "json", "language": "en"}
        if prompt:
            data["prompt"] = prompt[:800]  # names and words to expect, which helps with spelling
        try:
            response = httpx.post(self.url, headers=self.headers, data=data,
                                  files={"file": (filename, audio, content_type or "application/octet-stream")},
                                  timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise STTUnavailable(f"Transcription failed: {e}") from e
        return STTResult((response.json().get("text") or "").strip(), self.name)

    def ready(self) -> bool:
        try:
            r = httpx.get(self.url.rsplit("/audio/", 1)[0].rsplit("/v1", 1)[0] + "/health", timeout=3)
            return r.status_code == 200 and bool(r.json().get("ready", True))
        except (httpx.HTTPError, ValueError):
            return False


def get_stt():
    cfg = get_config()
    if cfg.stt_provider == "mock":
        return MockSTT()
    if cfg.stt_provider == "openai_compat":
        return OpenAICompatSTT(cfg)
    raise STTUnavailable("Voice input is turned off (STT_PROVIDER=none)")


def status() -> dict:
    cfg = get_config()
    if cfg.stt_provider == "mock":
        return {"provider": "mock", "ready": True}
    if cfg.stt_provider == "openai_compat" and cfg.stt_base_url:
        try:
            return {"provider": "whisper", "model": cfg.stt_model, "ready": OpenAICompatSTT(cfg).ready()}
        except STTUnavailable:
            pass
    return {"provider": "none", "ready": False}
