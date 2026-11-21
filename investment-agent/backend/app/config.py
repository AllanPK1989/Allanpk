"""App settings, read from environment variables (or a .env file next to the backend)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Investment Analyst"
    environment: Literal["development", "production", "test"] = "development"

    # Storage: SQLite for local use, a Neon/any Postgres URL in the cloud.
    database_url: str = "sqlite:///./data/invest.db"

    # Login (single owner). Prefer OWNER_PASSWORD_HASH (python -m app.jobs hash-password).
    secret_key: str = ""
    owner_password: str = ""
    owner_password_hash: str = ""
    session_days: int = 30

    # Public URL of the app, used in email/push links and for the secure-cookie flag.
    base_url: str = "http://localhost:8000"

    # "live" uses Yahoo Finance / mfapi.in / Crypto.com / FRED / RSS.
    # "demo" uses made-up, clearly labelled data so the app runs offline.
    data_mode: Literal["live", "demo"] = "live"

    # Claude. Without a key the app runs, but AI text is replaced by templates.
    anthropic_api_key: str = ""
    analysis_model: str = "claude-sonnet-5-5"
    news_model: str = "claude-haiku-5-5"
    analysis_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    chat_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"

    # Email (Gmail SMTP with an app password).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    gmail_user: str = ""
    gmail_app_password: str = ""
    digest_to: str = ""  # defaults to gmail_user

    # Web push (generate with: python -m app.jobs vapid-keys)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""  # mailto:you@example.com

    timezone: str = "Asia/Kolkata"
    base_currency: str = "INR"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def email_enabled(self) -> bool:
        return bool(self.gmail_user and self.gmail_app_password)

    @property
    def email_to(self) -> str:
        return self.digest_to or self.gmail_user

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    @property
    def cookie_secure(self) -> bool:
        return self.base_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def check_production_settings(s: Settings) -> list[str]:
    """Problems that must stop a production start."""
    problems = []
    if len(s.secret_key) < 32:
        problems.append("SECRET_KEY must be set to a random string of at least 32 characters")
    if not (s.owner_password_hash or s.owner_password):
        problems.append("OWNER_PASSWORD_HASH (or OWNER_PASSWORD) must be set")
    if s.owner_password and len(s.owner_password) < 10 and not s.owner_password_hash:
        problems.append("OWNER_PASSWORD must be at least 10 characters")
    if s.database_url.startswith("sqlite") and s.data_mode == "live":
        problems.append("DATABASE_URL should point to Postgres (e.g. Neon) in production; SQLite is lost on restart")
    return problems
