from __future__ import annotations

from datetime import date

import pytest

from nifty_shop.bhavcopy import UnknownBhavcopyLayoutError, parse_bhavcopy

LEGACY = (
    "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,"
    "TIMESTAMP,TOTALTRADES,ISIN\n"
    "RELIANCE,EQ,100,110,99,105,105,98,1000,100000,01-JAN-2008,50,INE002A01018\n"
    "SOMEBOND,N1,100,110,99,105,105,98,10,1000,01-JAN-2008,5,INE111A07018\n"
)

CURRENT = (
    " SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE,"
    " LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS,"
    " NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
    "RELIANCE, EQ, 02-Jan-2024, 2500.00, 2510.00, 2540.00, 2495.00, 2530.00,"
    " 2535.50, 2537.00, 1000, 250.00, 500, 400, 40.00\n"
    "SOMEETF, EQ, 02-Jan-2024, 10.00, 10.10, 10.20, 10.00, 10.15, 10.15,"
    " 10.10, 100, 1.00, 10, 5, 5.00\n"
)


def test_parses_the_legacy_zip_era_layout() -> None:
    rows = parse_bhavcopy(LEGACY)
    assert len(rows) == 1
    row = rows[0]
    assert row.symbol == "RELIANCE"
    assert row.series == "EQ"
    assert row.on == date(2008, 1, 1)
    assert row.close == 105.0
    assert row.prev_close == 98.0
    assert row.isin == "INE002A01018"


def test_parses_the_current_full_bhavdata_layout() -> None:
    rows = parse_bhavcopy(CURRENT)
    assert [r.symbol for r in rows] == ["RELIANCE", "SOMEETF"]
    assert rows[0].on == date(2024, 1, 2)
    assert rows[0].close == 2535.50
    assert rows[0].prev_close == 2500.00


def test_close_is_taken_from_close_price_not_last_price() -> None:
    """In this layout LAST_PRICE (2530.00) sits immediately before CLOSE_PRICE
    (2535.50). A position-driven parser silently takes the wrong one; indicators
    computed on LAST_PRICE would be subtly and permanently wrong."""
    row = parse_bhavcopy(CURRENT)[0]
    assert row.close == 2535.50
    assert row.close != 2530.00


def test_non_eq_series_is_dropped() -> None:
    """The risk gate rejects non-EQ series; they must never enter the universe."""
    assert all(row.series == "EQ" for row in parse_bhavcopy(LEGACY))


def test_headers_with_stray_whitespace_still_match() -> None:
    """The current NSE file ships leading spaces in its header names."""
    assert parse_bhavcopy(CURRENT)


def test_an_unrecognised_layout_fails_loudly_and_names_the_headers() -> None:
    """Silently mis-parsing a changed NSE layout is the failure this prevents."""
    with pytest.raises(UnknownBhavcopyLayoutError) as exc:
        parse_bhavcopy("TICKER,PRICE,WHEN\nRELIANCE,100,2024-01-02\n")
    message = str(exc.value)
    assert "TICKER" in message
    assert "PRICE" in message


def test_an_empty_file_fails_rather_than_returning_no_rows() -> None:
    with pytest.raises(UnknownBhavcopyLayoutError):
        parse_bhavcopy("")


def test_a_row_with_an_unparseable_price_raises() -> None:
    broken = LEGACY.replace(",105,105,98,", ",N/A,105,98,")
    with pytest.raises(ValueError, match="RELIANCE"):
        parse_bhavcopy(broken)
