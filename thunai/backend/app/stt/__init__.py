from ..config import get_config
from .base import STTProvider, STTResult, STTUnavailable


def get_stt() -> STTProvider:
    cfg = get_config()
    if cfg.stt_provider == "openai_compat":
        from .openai_compat import OpenAICompatSTT

        return OpenAICompatSTT(cfg)
    if cfg.stt_provider == "sarvam":
        from .sarvam import SarvamSTT

        return SarvamSTT(cfg)
    if cfg.stt_provider == "mock":
        from .mock import MockSTT

        return MockSTT()
    raise STTUnavailable("Speech-to-text is switched off")


__all__ = ["STTProvider", "STTResult", "STTUnavailable", "get_stt"]
