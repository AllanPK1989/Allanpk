"""Runtime configuration, read from environment variables (see ../.env.example).

Plant-tunable values that admins change at runtime (shift calendar, thresholds, retention)
live in the `settings` table instead; see app/settings_store.py.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Prompts whose newest version is the default. v1 files stay for comparison (PROMPT_VERSIONS).
DEFAULT_PROMPT_VERSIONS = {"troubleshoot": "v2", "clarify": "v2"}


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
    max_document_mb: int = 50

    # Background jobs: "sync" runs immediately (tests), "thread" runs after the response,
    # "rq" sends to the Redis worker.
    jobs_mode: str = "thread"
    redis_url: str = ""

    # AI: Thunai's rules engine is the only provider. Conversation, photos and translation run in the
    # Microsoft Copilot agent (SPEC 13); the Claude adapter was removed on 25 Oct 2026.
    ai_provider: str = "rules"
    prompts_dir: Path = BACKEND_DIR / "prompts"
    # Active prompt versions, "name=vN" pairs. Missing names use DEFAULT_PROMPT_VERSIONS, then v1.
    prompt_versions: str = ""

    # Speech to text
    stt_provider: str = "mock"  # mock | openai_compat | sarvam | none
    stt_base_url: str = ""  # openai_compat: e.g. http://whisper:8000/v1
    stt_api_key: str = ""
    stt_model: str = "whisper-1"
    sarvam_api_key: str = ""
    sarvam_model: str = "saarika:v2.5"
    ffmpeg_path: str = "ffmpeg"

    # Optional embeddings for similarity search (SPEC 11.5): none | openai_compat
    embeddings_provider: str = "none"
    embeddings_base_url: str = ""
    embeddings_model: str = "multilingual-e5-base"
    embeddings_api_key: str = ""

    # Microsoft Copilot agent (SPEC 13). Tokens are Microsoft Entra ID access tokens for the Thunai API app.
    copilot_enabled: bool = False
    entra_tenant_id: str = ""  # directory (tenant) ID, a GUID
    entra_audience: str = ""  # comma separated: the Thunai API app's Application ID URI and/or client ID
    entra_scope: str = "Thunai.Use"  # delegated scope the connector requests
    entra_jwks_url: str = ""  # default: https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys
    copilot_teams_url: str = ""  # optional link to the agent in Teams, shown on the PWA home screen

    # Sample data
    seed_sample_data: bool = True

    @field_validator("ai_provider")
    @classmethod
    def _rules_only(cls, value: str) -> str:
        value = value.strip().lower()
        if value in ("rules", "mock"):  # "mock" was the old name of the rules engine
            return "rules"
        raise ValueError(
            f"AI_PROVIDER={value} is not available: the Claude adapter was removed (SPEC 13). Use AI_PROVIDER=rules."
        )

    @property
    def entra_audiences(self) -> list[str]:
        return [a.strip() for a in self.entra_audience.split(",") if a.strip()]

    @property
    def copilot_ready(self) -> bool:
        return self.copilot_enabled and bool(self.entra_tenant_id and self.entra_audiences)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def prompt_version(self, name: str) -> str:
        for pair in self.prompt_versions.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                if key.strip() == name:
                    return value.strip()
        return DEFAULT_PROMPT_VERSIONS.get(name, "v1")


@lru_cache
def get_config() -> Config:
    return Config()
