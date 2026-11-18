"""Runtime configuration from environment variables (see ../.env.example).

Things you change from the app (times, quiet hours, baskets, PIN) live in the database instead;
see app/settings_store.py.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Nudge"
    environment: str = "development"  # development | production
    data_dir: Path = BACKEND_DIR / "data"
    database_url: str = ""  # default: sqlite file inside data_dir
    secret_key: str = ""  # default: generated once and kept in data_dir/secret_key
    public_base_url: str = "https://localhost"  # links inside e-mails
    default_timezone: str = "Asia/Kolkata"
    static_dir: str = ""  # optional: serve the built frontend from the API process
    session_days: int = 90
    max_upload_mb: int = 15

    # Demo: fill an empty database with sample tasks and PIN 1234.
    seed_sample_data: bool = False
    initial_pin: str = ""  # used once, when no PIN has been set yet

    # Background scheduler (reminders, digests, backups). Off in tests.
    scheduler_enabled: bool = True
    scheduler_interval_s: int = 30
    backup_keep: int = 14

    # AI: "mock" uses the built-in rules (no key needed), "anthropic" uses Claude.
    ai_provider: str = "mock"
    ai_model: str = "claude-opus-5-5"
    ai_effort: str = "low"  # reading a short voice note is a light task
    ai_refusal_fallback: bool = True
    ai_timeout_s: float = 60.0
    # USD per million tokens for the cost estimate in Settings, "model=input/output" pairs.
    ai_prices: str = "claude-opus-5-5=4/20,claude-sonnet-5-5=2/10,claude-haiku-5-5=0.10/0.50"

    # Speech to text: "openai_compat" talks to the bundled Whisper container (or any server with
    # an OpenAI-style /audio/transcriptions endpoint). "mock" is for tests.
    stt_provider: str = "mock"
    stt_base_url: str = ""
    stt_api_key: str = ""
    stt_model: str = "small.en"
    stt_timeout_s: float = 120.0

    # Web push. Keys are generated on first start when left empty.
    vapid_private_key: str = ""  # PEM
    vapid_subject: str = "mailto:nudge-reminders@example.com"

    # E-mail digest. With no SMTP_HOST, e-mails are written to data_dir/outbox for preview.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_security: str = "starttls"  # starttls | ssl | none
    digest_to: str = ""  # default recipient; can be changed in Settings

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{self.data_dir / 'nudge.db'}"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def demo_mode(self) -> bool:
        return self.ai_provider == "mock"

    def price(self, model: str) -> tuple[float, float]:
        for pair in self.ai_prices.split(","):
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            if name.strip() == model:
                try:
                    i, o = value.split("/")
                    return float(i), float(o)
                except ValueError:
                    return 0.0, 0.0
        return 0.0, 0.0


@lru_cache
def get_config() -> Config:
    cfg = Config()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    return cfg
