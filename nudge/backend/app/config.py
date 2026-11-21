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
    # The interactive API page loads its scripts from a public CDN, so it is off unless you ask.
    api_docs: bool = False
    session_days: int = 90
    max_upload_mb: int = 15

    # Demo: fill an empty database with sample tasks and PIN 1234.
    seed_sample_data: bool = False
    initial_pin: str = ""  # used once, when no PIN has been set yet

    # Background scheduler (reminders, digests, backups). Off in tests.
    scheduler_enabled: bool = True
    scheduler_interval_s: int = 30
    backup_keep: int = 14

    # Speech to text: "openai_compat" talks to the bundled Whisper container (or any server with
    # an OpenAI-style /audio/transcriptions endpoint). "mock" is for tests.
    stt_provider: str = "mock"
    stt_base_url: str = ""
    stt_api_key: str = ""
    stt_model: str = "small.en"
    stt_timeout_s: float = 120.0

    # Web push. Keys are generated on first start when left empty.
    vapid_private_key: str = ""  # PEM
    # Sent to push services as a contact. A placeholder works; you don't need to give your address.
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
        return self.seed_sample_data


@lru_cache
def get_config() -> Config:
    cfg = Config()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    return cfg
