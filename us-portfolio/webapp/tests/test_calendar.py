import datetime as dt
from zoneinfo import ZoneInfo

from app import calendar_us as c

ET = ZoneInfo("America/New_York")


def test_labor_day_is_closed_and_points_at_the_next_session():
    s = c.status(dt.datetime(2026, 9, 7, 11, 0, tzinfo=ET))
    assert s["phase"] == "closed"
    assert "holiday" in s["label"].lower()
    assert s["last_session"] == "2026-09-04"
    assert s["next_session"] == "2026-09-08"


def test_weekend_is_closed():
    s = c.status(dt.datetime(2026, 9, 6, 12, 0, tzinfo=ET))
    assert s["phase"] == "closed" and "Weekend" in s["label"]


def test_phases_across_a_trading_day():
    day = lambda h, m=0: c.status(dt.datetime(2026, 9, 8, h, m, tzinfo=ET))
    assert day(7)["phase"] == "pre"
    assert day(10)["phase"] == "open" and day(10)["is_open"]
    assert day(17)["phase"] == "post"
    assert day(22)["phase"] == "closed"


def test_before_the_bell_the_reference_close_is_the_previous_session():
    s = c.status(dt.datetime(2026, 9, 8, 7, 0, tzinfo=ET))
    assert s["last_session"] == "2026-09-04"      # Fri, across the long weekend


def test_half_day_closes_early():
    s = c.status(dt.datetime(2026, 11, 27, 14, 0, tzinfo=ET))
    assert s["phase"] == "post"                   # 1pm close, so 2pm is after hours
    assert c.status(dt.datetime(2026, 11, 27, 12, 0, tzinfo=ET))["phase"] == "open"


def test_open_market_polls_faster_than_a_shut_one():
    assert (c.status(dt.datetime(2026, 9, 8, 10, tzinfo=ET))["poll_seconds"]
            < c.status(dt.datetime(2026, 9, 6, 10, tzinfo=ET))["poll_seconds"])
