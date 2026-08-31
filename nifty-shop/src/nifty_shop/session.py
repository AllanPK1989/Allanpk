"""Daily session lifecycle.

The regulatory model in force since 1 April 2026 assumes one authenticated session per
trading day, with no persistent-session assumption across days. The trading day that
matters is the IST one, so the roll is computed in Asia/Kolkata rather than UTC.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class SessionError(Exception):
    """Base class for session failures."""


class SessionExpiredError(SessionError):
    """The broker session is no longer live."""


class SessionClient(Protocol):
    """The slice of the broker client this manager needs."""

    @property
    def is_logged_in(self) -> bool: ...

    def login(self, password: str, totp: str) -> None: ...

    def logout(self) -> None: ...


class SessionManager:
    """Logs in once per IST trading day and re-authenticates when the day rolls."""

    def __init__(
        self,
        client: SessionClient,
        password: str,
        totp_provider: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        self._client = client
        self._password = password
        self._totp_provider = totp_provider
        self._clock = clock
        self._session_day: date | None = None

    def __repr__(self) -> str:
        """Never renders the password or a TOTP code."""
        return f"SessionManager(session_day={self._session_day!r})"

    @property
    def session_day(self) -> date | None:
        return self._session_day

    def ensure_session(self) -> None:
        """Log in if there is no live session for the current IST trading day."""
        today = self._ist_today()
        if self._client.is_logged_in and self._session_day == today:
            return

        # A stale session from a previous day is closed before opening a new one.
        if self._client.is_logged_in:
            self._client.logout()

        # Fresh TOTP per login: the broker rejects a reused code.
        self._client.login(password=self._password, totp=self._totp_provider())
        self._session_day = today

    def assert_live(self) -> None:
        """Raise if the session died mid-run, so the caller can freeze rather than guess."""
        if not self._client.is_logged_in or self._session_day != self._ist_today():
            raise SessionExpiredError("broker session is no longer live for today")

    def _ist_today(self) -> date:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now.astimezone(IST).date()
