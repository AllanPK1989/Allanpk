"""Runtime configuration, read from environment variables (see ../.env.example).

Plant-tunable values that admins change at runtime (shift calendar, thresholds, retention)
live in the `settings` table instead; see app/settings_store.py.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "Thunai"
    environment: str = "development"  # development | production
    database_url: str = "sqlite:///./thunai-dev.db"
    secret_key: str = "change-me-in-production"
    token_hours: int = 12
    public_base_url: str = "https://localhost"  # used inside QR codes
    plant_tz: str = "Asia/Kolkata"
    cors_origins: str = ""  # comma separated; empty = same origin only
    static_dir: str = ""  # optional: built frontend to serve from the API process

    # Files
    media_dir: Path = BACKEND_DIR / "media"
    max_upload_mb: int = 15

    # Background jobs: "sync" runs immediately (tests), "thread" runs after the response,
    # "rq" sends to the Redis worker.
    jobs_mode: str = "thread"
    redis_url: str = ""

    # AI
    ai_provider: str = "mock"  # mock | anthropic
    ai_model_diagnosis: str = "claude-opus-5-5"
    ai_model_extraction: str = "claude-haiku-5-5"
    ai_effort_diagnosis: str = "medium"
    ai_effort_extraction: str = "low"
    ai_refusal_fallback: bool = True  # server-side fallback on safety-classifier refusals
    ai_timeout_s: float = 90.0
    # USD per million tokens, "model=input/output" pairs, comma separated.
    ai_prices: str = (
        "claude-opus-5-5=4/20,claude-sonnet-5-5=2/10,claude-haiku-5-5=0.10/0.50,"
        "claude-fable-5-1=10/50"
    )
    prompts_dir: Path = BACKEND_DIR / "prompts"
    # Active prompt versions, "name=vN" pairs. Missing names use v1.
    prompt_versions: str = ""

    # Speech to text
    stt_provider: str = "mock"  # mock | openai_compat | sarvam | none
    stt_base_url: str = ""  # openai_compat: e.g. http://whisper:8000/v1
    stt_api_key: str = ""
    stt_model: str = "whisper-1"
    sarvam_api_key: str = ""
    sarvam_model: str = "saarika:v2.5"
    ffmpeg_path: str = "ffmpeg"

    # Sample data
    seed_sample_data: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def price_for(self, model: str) -> tuple[float, float]:
        for pair in self.ai_prices.split(","):
            if "=" not in pair:
                continue
            name, prices = pair.split("=", 1)
            if name.strip() == model:
                inp, out = prices.split("/")
                return float(inp), float(out)
        return 0.0, 0.0

    def prompt_version(self, name: str) -> str:
        for pair in self.prompt_versions.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                if key.strip() == name:
                    return value.strip()
        return "v1"


@lru_cache
def get_config() -> Config:
    return Config()
