from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from nifty_shop.session import IST, SessionExpiredError, SessionManager

MORNING = datetime(2026, 8, 31, 9, 30, tzinfo=IST)
AFTERNOON = datetime(2026, 8, 31, 15, 20, tzinfo=IST)
NEXT_DAY = datetime(2026, 9, 1, 9, 30, tzinfo=IST)


class FakeClient:
    def __init__(self) -> None:
        self.logins = 0
        self.logouts = 0
        self.credentials: list[tuple[str, str]] = []
        self._logged_in = False

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    def login(self, password: str, totp: str) -> None:
        self.logins += 1
        self.credentials.append((password, totp))
        self._logged_in = True

    def logout(self) -> None:
        self.logouts += 1
        self._logged_in = False


def make(client: FakeClient, now: datetime) -> SessionManager:
    clock = iter([now])
    return SessionManager(
        client=client,
        password="p",
        totp_provider=lambda: "123456",
        clock=lambda: next(clock, now),
    )


def test_first_call_logs_in_once() -> None:
    client = FakeClient()
    manager = make(client, MORNING)
    manager.ensure_session()
    assert client.logins == 1


def test_repeated_calls_in_the_same_session_do_not_re_login() -> None:
    client = FakeClient()
    manager = make(client, MORNING)
    manager.ensure_session()
    manager.ensure_session()
    manager.ensure_session()
    assert client.logins == 1


def test_a_new_ist_trading_day_forces_a_fresh_login() -> None:
    """The spec assumes no persistent session across days."""
    client = FakeClient()
    times = iter([MORNING, AFTERNOON, NEXT_DAY])
    manager = SessionManager(
        client=client,
        password="p",
        totp_provider=lambda: "1",
        clock=lambda: next(times),
    )
    manager.ensure_session()
    manager.ensure_session()
    assert client.logins == 1
    manager.ensure_session()
    assert client.logins == 2


def test_the_ist_day_is_what_rolls_not_the_utc_day() -> None:
    """20:00 UTC is already the next day in IST; a UTC-based check would miss it."""
    client = FakeClient()
    before = datetime(2026, 8, 31, 20, 0, tzinfo=UTC)  # 01:30 IST on 1 Sep
    same_ist_day = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)  # 15:30 IST on 31 Aug
    times = iter([same_ist_day, before])
    manager = SessionManager(
        client=client,
        password="p",
        totp_provider=lambda: "1",
        clock=lambda: next(times),
    )
    manager.ensure_session()
    manager.ensure_session()
    assert client.logins == 2


def test_session_dying_mid_run_is_detected() -> None:
    client = FakeClient()
    manager = make(client, MORNING)
    manager.ensure_session()
    client._logged_in = False  # broker dropped it
    with pytest.raises(SessionExpiredError):
        manager.assert_live()


def test_naive_clock_is_rejected() -> None:
    client = FakeClient()
    manager = SessionManager(
        client=client,
        password="p",
        totp_provider=lambda: "1",
        clock=lambda: datetime(2026, 8, 31, 9, 30),  # noqa: DTZ001
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        manager.ensure_session()


def test_totp_is_requested_fresh_for_every_login() -> None:
    """A reused TOTP code is rejected by the broker; it must be generated per login."""
    client = FakeClient()
    codes = iter(["111111", "222222"])
    requested: list[str] = []

    def totp() -> str:
        code = next(codes)
        requested.append(code)
        return code

    times = iter([MORNING, NEXT_DAY])
    manager = SessionManager(
        client=client, password="p", totp_provider=totp, clock=lambda: next(times)
    )
    manager.ensure_session()
    manager.ensure_session()
    assert requested == ["111111", "222222"]


def test_ist_is_asia_kolkata() -> None:
    assert ZoneInfo("Asia/Kolkata") == IST


def test_the_configured_password_reaches_the_client() -> None:
    client = FakeClient()
    make(client, MORNING).ensure_session()
    assert client.credentials == [("p", "123456")]
