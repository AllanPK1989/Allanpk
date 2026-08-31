"""NSE trading calendar, derived from the sessions that actually exist.

A date with a bhavcopy is a trading day; a weekday without one was a holiday. Deriving
the calendar from the data means no separately-maintained holiday list has to be
trusted, and special sessions (Muhurat) are included automatically.

Queries outside the known range refuse. Answering "not a trading day" for a date the
calendar has never seen would silently skip real sessions, which is precisely the
fail-open behaviour the spec forbids.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Iterable
from datetime import date


class OutsideCalendarRangeError(Exception):
    """The date falls outside the range this calendar covers."""


class TradingCalendar:
    def __init__(self, sessions: tuple[date, ...]) -> None:
        if not sessions:
            raise ValueError("a trading calendar needs at least one session")
        self._sessions = sessions
        self._lookup = frozenset(sessions)

    @classmethod
    def from_session_dates(cls, dates: Iterable[date]) -> TradingCalendar:
        return cls(tuple(sorted(set(dates))))

    @property
    def sessions(self) -> tuple[date, ...]:
        return self._sessions

    @property
    def first(self) -> date:
        return self._sessions[0]

    @property
    def last(self) -> date:
        return self._sessions[-1]

    def _require_in_range(self, on: date) -> None:
        if on < self.first or on > self.last:
            raise OutsideCalendarRangeError(
                f"{on} is outside the calendar range {self.first}..{self.last}"
            )

    def is_trading_day(self, on: date) -> bool:
        self._require_in_range(on)
        return on in self._lookup

    def sessions_between(self, start: date, end: date) -> list[date]:
        self._require_in_range(start)
        self._require_in_range(end)
        return [session for session in self._sessions if start <= session <= end]

    def previous_session(self, on: date) -> date:
        self._require_in_range(on)
        position = bisect_left(self._sessions, on)
        if position == 0:
            raise OutsideCalendarRangeError(f"no session precedes {on} in this calendar")
        return self._sessions[position - 1]
