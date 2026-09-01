from __future__ import annotations

from datetime import date, timedelta

from nifty_shop.metrics import SessionRecord, compute_metrics
from nifty_shop.money import rupees

ALLOCATED = rupees("1000000")  # 10,00,000


def records(*rows: tuple[int, int, int, int, int]) -> list[SessionRecord]:
    """(equity_rupees, deployed_rupees, open_lots, lots_closed, open_at_start)"""
    start = date(2026, 1, 1)
    return [
        SessionRecord(
            on=start + timedelta(days=i),
            book_equity=rupees(str(equity)),
            deployed_capital=rupees(str(deployed)),
            open_lots=open_lots,
            lots_closed=closed,
            open_at_start=at_start,
        )
        for i, (equity, deployed, open_lots, closed, at_start) in enumerate(rows)
    ]


def test_return_is_measured_on_allocated_capital_not_deployed() -> None:
    """Metric 1. The book was only ever 20,000 deployed, but the denominator is the
    full 10,00,000 allocation — which is the number that makes this strategy look
    honest rather than spectacular."""
    m = compute_metrics(records((1000000, 0, 0, 0, 0), (1010000, 20000, 4, 0, 4)), [], ALLOCATED)
    assert m.return_on_allocated_pct == 1.0
    assert m.return_on_deployed_pct > m.return_on_allocated_pct


def test_drawdown_is_measured_from_the_running_high_water_mark() -> None:
    """Metric 2. Peak 11,00,000, trough 8,80,000 -> 20% off the peak, not off the
    starting allocation."""
    m = compute_metrics(
        records(
            (1000000, 0, 0, 0, 0),
            (1100000, 50000, 10, 0, 10),
            (880000, 50000, 10, 0, 10),
            (900000, 50000, 10, 0, 10),
        ),
        [],
        ALLOCATED,
    )
    assert m.max_book_drawdown_pct == 20.0


def test_peak_lots_and_peak_capital_are_the_true_requirement() -> None:
    """Metric 3. Both are maxima over the whole run, not end-of-run values."""
    m = compute_metrics(
        records(
            (1000000, 40000, 8, 0, 8),
            (1000000, 320000, 64, 0, 64),
            (1000000, 15000, 3, 5, 8),
        ),
        [],
        ALLOCATED,
    )
    assert m.peak_open_lots == 64
    assert int(m.peak_capital_deployed) == 32000000
    assert m.peak_capital_pct_of_allocated == 32.0


def test_zero_exit_stretch_counts_only_sessions_with_something_held() -> None:
    """Metric 4, using the definition pre-registered in the kill criteria file: the
    counter runs only while at least one lot is open, and any exit resets it."""
    m = compute_metrics(
        records(
            (1000000, 0, 0, 0, 0),      # nothing held, does not count
            (1000000, 5000, 1, 0, 1),   # 1
            (1000000, 10000, 2, 0, 2),  # 2
            (1000000, 15000, 3, 0, 3),  # 3
            (1000000, 10000, 2, 1, 3),  # exit resets
            (1000000, 15000, 3, 0, 3),  # 1
        ),
        [],
        ALLOCATED,
    )
    assert m.longest_zero_exit_sessions == 3


def test_an_empty_book_breaks_the_zero_exit_streak() -> None:
    m = compute_metrics(
        records(
            (1000000, 5000, 1, 0, 1),
            (1000000, 10000, 2, 0, 2),
            (1000000, 0, 0, 0, 0),      # nothing held: streak resets
            (1000000, 5000, 1, 0, 1),
        ),
        [],
        ALLOCATED,
    )
    assert m.longest_zero_exit_sessions == 2


def test_days_to_target_reports_a_distribution_not_just_a_mean() -> None:
    """Metric 5. The mean hides the tail, and the tail is where capital freezes."""
    m = compute_metrics(records((1000000, 0, 0, 0, 0)), [3, 5, 8, 13, 21, 34, 200], ALLOCATED)
    assert m.days_to_target_median == 13
    assert m.days_to_target_p90 >= 34
    assert m.days_to_target_max == 200
    # A single 200-session lot drags the mean (40.57) ABOVE the p90 (34), so the
    # average describes almost none of the trades. This is exactly why the spec
    # demands the distribution rather than the average.
    assert m.days_to_target_mean > m.days_to_target_p90
    assert m.days_to_target_mean > 2 * m.days_to_target_median


def test_no_target_exits_reports_zeroes_rather_than_dividing_by_zero() -> None:
    m = compute_metrics(records((1000000, 0, 0, 0, 0)), [], ALLOCATED)
    assert m.target_exit_count == 0
    assert m.days_to_target_median == 0


def test_win_rate_is_computed_but_never_the_headline() -> None:
    """The spec forbids reporting it as a headline. It is still computed, because
    seeing a 95% win rate next to a 25% drawdown is the point."""
    m = compute_metrics(records((1000000, 0, 0, 0, 0)), [], ALLOCATED, wins=19, losses=1)
    assert m.win_rate_pct == 95.0
    assert "win rate" not in m.headline().lower()


def test_the_headline_carries_the_capital_requirement_beside_the_return() -> None:
    """An acceptance criterion: every performance report carries the capital
    requirement model alongside it."""
    m = compute_metrics(
        records((1000000, 0, 0, 0, 0), (1050000, 200000, 40, 0, 40)), [7], ALLOCATED
    )
    headline = m.headline()
    assert "5.0" in headline
    assert "40" in headline
    assert "2,00,000" in headline or "200000" in headline
