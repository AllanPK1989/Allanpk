from __future__ import annotations

from datetime import date

import pytest

from nifty_shop.trading_calendar import OutsideCalendarRangeError, TradingCalendar

SESSIONS = [
    date(2026, 1, 1),
    date(2026, 1, 2),
    date(2026, 1, 5),  # 3rd and 4th are the weekend
    date(2026, 1, 6),
    date(2026, 1, 8),  # 7th was a holiday
]


def cal() -> TradingCalendar:
    return TradingCalendar.from_session_dates(SESSIONS)


def test_a_date_with_a_session_is_a_trading_day() -> None:
    assert cal().is_trading_day(date(2026, 1, 2)) is True


def test_a_weekend_is_not_a_trading_day() -> None:
    assert cal().is_trading_day(date(2026, 1, 3)) is False


def test_a_mid_week_holiday_is_not_a_trading_day() -> None:
    """Derived from the data itself: no bhavcopy means no session. No holiday list
    has to be trusted or invented."""
    assert cal().is_trading_day(date(2026, 1, 7)) is False


def test_a_date_outside_the_known_range_refuses_rather_than_guessing() -> None:
    """Fail closed: answering 'not a trading day' for an unknown future date would
    silently skip real sessions."""
    with pytest.raises(OutsideCalendarRangeError):
        cal().is_trading_day(date(2027, 1, 4))
    with pytest.raises(OutsideCalendarRangeError):
        cal().is_trading_day(date(2025, 1, 4))


def test_sessions_between_is_inclusive_and_ordered() -> None:
    assert cal().sessions_between(date(2026, 1, 2), date(2026, 1, 6)) == [
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]


def test_previous_session_skips_non_trading_days() -> None:
    assert cal().previous_session(date(2026, 1, 8)) == date(2026, 1, 6)


def test_previous_session_before_the_first_refuses() -> None:
    with pytest.raises(OutsideCalendarRangeError):
        cal().previous_session(date(2026, 1, 1))


def test_sessions_are_deduplicated_and_sorted() -> None:
    scrambled = TradingCalendar.from_session_dates(
        [date(2026, 1, 5), date(2026, 1, 2), date(2026, 1, 2)]
    )
    assert scrambled.sessions == (date(2026, 1, 2), date(2026, 1, 5))


def test_an_empty_calendar_refuses_to_be_built() -> None:
    with pytest.raises(ValueError, match="at least one session"):
        TradingCalendar.from_session_dates([])
