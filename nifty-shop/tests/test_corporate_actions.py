from __future__ import annotations

from datetime import date

import pytest

from nifty_shop.corporate_actions import (
    Bar,
    CorporateAction,
    back_adjust,
    detect_unexplained_gaps,
    ratio_from_purpose,
)


def bars(*pairs: tuple[str, float]) -> list[Bar]:
    return [Bar(on=date.fromisoformat(d), close=c) for d, c in pairs]


# --- parsing NSE purpose strings -------------------------------------------------

@pytest.mark.parametrize(
    ("purpose", "expected"),
    [
        ("SPLIT FROM RS 10 TO RS 2", 0.2),
        ("FACE VALUE SPLIT FROM RS.10/- TO RS.1/-", 0.1),
        ("Face Value Split From Rs 5 To Rs 1", 0.2),
        ("BONUS 1:1", 0.5),
        ("BONUS 1:2", pytest.approx(2 / 3)),
        ("Bonus issue 2:1", pytest.approx(1 / 3)),
    ],
)
def test_recognised_actions_yield_a_price_factor(purpose: str, expected: float) -> None:
    assert ratio_from_purpose(purpose) == expected


@pytest.mark.parametrize(
    "purpose",
    [
        "ANNUAL GENERAL MEETING",
        "DIVIDEND RS 5 PER SHARE",
        "INTERIM DIVIDEND",
        "SCHEME OF ARRANGEMENT",
        "",
    ],
)
def test_unrecognised_or_non_price_actions_return_none(purpose: str) -> None:
    """Dividends are deliberately not price-adjusted: the reference charts we validate
    against are not dividend-adjusted either. Anything unrecognised returns None so it
    surfaces through the gap detector instead of being silently mis-applied."""
    assert ratio_from_purpose(purpose) is None


# --- back adjustment -------------------------------------------------------------

def test_prices_before_the_ex_date_are_scaled_and_later_ones_are_not() -> None:
    series = bars(("2026-01-01", 1000.0), ("2026-01-02", 1000.0), ("2026-01-03", 200.0))
    action = CorporateAction(
        symbol="X", ex_date=date(2026, 1, 3), ratio=0.2, purpose="SPLIT FROM RS 10 TO RS 2"
    )
    assert [b.close for b in back_adjust(series, [action])] == [200.0, 200.0, 200.0]


def test_multiple_actions_compound() -> None:
    series = bars(("2026-01-01", 1000.0), ("2026-02-01", 500.0), ("2026-03-01", 100.0))
    actions = [
        CorporateAction("X", date(2026, 2, 1), 0.5, "BONUS 1:1"),
        CorporateAction("X", date(2026, 3, 1), 0.2, "SPLIT FROM RS 10 TO RS 2"),
    ]
    adjusted = [b.close for b in back_adjust(series, actions)]
    assert adjusted == [pytest.approx(100.0), pytest.approx(100.0), pytest.approx(100.0)]


def test_no_actions_leaves_the_series_untouched() -> None:
    series = bars(("2026-01-01", 10.0), ("2026-01-02", 11.0))
    assert [b.close for b in back_adjust(series, [])] == [10.0, 11.0]


# --- the safety net --------------------------------------------------------------

def test_an_unexplained_crash_is_flagged() -> None:
    """An 80% overnight fall with no corporate action is a missing split, not a stock."""
    series = bars(("2026-01-01", 1000.0), ("2026-01-02", 200.0))
    gaps = detect_unexplained_gaps(series, actions=[], threshold_pct=15.0)
    assert len(gaps) == 1
    assert gaps[0].on == date(2026, 1, 2)
    assert gaps[0].move_pct == pytest.approx(-80.0)


def test_the_same_crash_is_not_flagged_when_an_action_explains_it() -> None:
    series = bars(("2026-01-01", 1000.0), ("2026-01-02", 200.0))
    action = CorporateAction(
        symbol="X", ex_date=date(2026, 1, 2), ratio=0.2, purpose="SPLIT FROM RS 10 TO RS 2"
    )
    assert detect_unexplained_gaps(series, actions=[action], threshold_pct=15.0) == []


def test_ordinary_volatility_is_not_flagged() -> None:
    series = bars(("2026-01-01", 100.0), ("2026-01-02", 92.0), ("2026-01-03", 99.0))
    assert detect_unexplained_gaps(series, actions=[], threshold_pct=15.0) == []


def test_a_large_rise_is_flagged_too() -> None:
    """A missed reverse split looks like a huge rise."""
    series = bars(("2026-01-01", 100.0), ("2026-01-02", 500.0))
    gaps = detect_unexplained_gaps(series, actions=[], threshold_pct=15.0)
    assert len(gaps) == 1
    assert gaps[0].move_pct == pytest.approx(400.0)


def test_a_zero_or_negative_price_is_always_flagged() -> None:
    series = bars(("2026-01-01", 100.0), ("2026-01-02", 0.0))
    gaps = detect_unexplained_gaps(series, actions=[], threshold_pct=15.0)
    assert len(gaps) == 1
