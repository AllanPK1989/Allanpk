from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from nifty_shop.download import (
    build_fixture,
    closes_from_cache,
    parse_date_range,
    weekdays_between,
)


def test_weekdays_between_skips_weekends() -> None:
    """Weekends are never trading days, so they are not even requested."""
    days = weekdays_between(date(2026, 1, 1), date(2026, 1, 7))
    assert date(2026, 1, 3) not in days  # Saturday
    assert date(2026, 1, 4) not in days  # Sunday
    assert len(days) == 5


def test_weekdays_between_is_inclusive_of_both_ends() -> None:
    days = weekdays_between(date(2026, 1, 5), date(2026, 1, 6))
    assert days == [date(2026, 1, 5), date(2026, 1, 6)]


def test_a_backwards_range_refuses() -> None:
    with pytest.raises(ValueError, match="before"):
        weekdays_between(date(2026, 2, 1), date(2026, 1, 1))


def test_parse_date_range_accepts_iso_dates() -> None:
    start, end = parse_date_range("2015-01-01", "2026-08-31")
    assert start == date(2015, 1, 1)
    assert end == date(2026, 8, 31)


def test_parse_date_range_rejects_a_malformed_date() -> None:
    with pytest.raises(ValueError, match="01-01-2015"):
        parse_date_range("01-01-2015", "2026-08-31")


# --- fixture building -------------------------------------------------------------

LEGACY_ROW = (
    "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,"
    "TIMESTAMP,TOTALTRADES,ISIN\n"
)


def write_day(cache: Path, on: date, symbol: str, close: float) -> None:
    path = cache / f"{on:%Y}" / f"bhav-{on:%Y-%m-%d}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        LEGACY_ROW
        + f"{symbol},EQ,1,1,1,{close},{close},1,1,1,{on:%d-%b-%Y}".upper()
        + ",1,INE002A01018\n"
    )


def test_closes_from_cache_returns_the_series_in_date_order(tmp_path: Path) -> None:
    for i, close in enumerate([101.0, 102.0, 103.0]):
        write_day(tmp_path, date(2026, 1, 5 + i), "RELIANCE", close)
    series = closes_from_cache(tmp_path, "RELIANCE", upto=date(2026, 1, 7))
    assert series == [101.0, 102.0, 103.0]


def test_closes_from_cache_stops_at_the_requested_date(tmp_path: Path) -> None:
    for i, close in enumerate([101.0, 102.0, 103.0]):
        write_day(tmp_path, date(2026, 1, 5 + i), "RELIANCE", close)
    assert closes_from_cache(tmp_path, "RELIANCE", upto=date(2026, 1, 6)) == [101.0, 102.0]


def test_closes_from_cache_ignores_other_symbols(tmp_path: Path) -> None:
    write_day(tmp_path, date(2026, 1, 5), "RELIANCE", 101.0)
    write_day(tmp_path, date(2026, 1, 6), "INFY", 55.0)
    assert closes_from_cache(tmp_path, "RELIANCE", upto=date(2026, 1, 6)) == [101.0]


def test_build_fixture_refuses_without_enough_warmup(tmp_path: Path) -> None:
    """A fixture with too little history would compare an unsettled RSI and tell you
    nothing about correctness."""
    write_day(tmp_path, date(2026, 1, 5), "RELIANCE", 101.0)
    with pytest.raises(ValueError, match="200"):
        build_fixture(
            tmp_path, "RELIANCE", date(2026, 1, 5),
            expected_rsi=50.0, expected_sma=100.0, source="TradingView",
        )


def test_build_fixture_refuses_without_a_source(tmp_path: Path) -> None:
    from datetime import timedelta

    for i in range(260):
        write_day(tmp_path, date(2025, 1, 1) + timedelta(days=i), "R", 100.0 + i)
    with pytest.raises(ValueError, match="source"):
        build_fixture(
            tmp_path, "R", date(2025, 1, 1) + timedelta(days=259),
            expected_rsi=50.0, expected_sma=100.0, source="   ",
        )


def test_build_fixture_emits_the_documented_shape(tmp_path: Path) -> None:
    from datetime import timedelta

    for i in range(260):
        write_day(tmp_path, date(2025, 1, 1) + timedelta(days=i), "R", 100.0 + i)
    as_of = date(2025, 1, 1) + timedelta(days=259)
    payload = build_fixture(
        tmp_path, "R", as_of, expected_rsi=100.0, expected_sma=234.5, source="TradingView NSE:R"
    )
    assert payload["symbol"] == "R"
    assert payload["as_of"] == as_of.isoformat()
    assert len(payload["closes"]) >= 200
    assert payload["expected_rsi_14"] == 100.0
    assert payload["source"] == "TradingView NSE:R"
