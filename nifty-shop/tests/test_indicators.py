from __future__ import annotations

import pytest

from nifty_shop.indicators import InsufficientHistoryError, sma, wilder_rsi


def test_sma_warms_up_then_tracks_the_window() -> None:
    assert sma([1.0, 2.0, 3.0, 4.0], period=2) == [None, 1.5, 2.5, 3.5]


def test_sma_of_a_flat_series_is_that_value() -> None:
    assert sma([7.0] * 5, period=3) == [None, None, 7.0, 7.0, 7.0]


def test_sma_agrees_with_a_naive_mean_over_every_window() -> None:
    """Independent check: a separate, obviously-correct implementation."""
    values = [float(v) for v in (3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5)]
    period = 4
    got = sma(values, period=period)
    for i, value in enumerate(got):
        if i < period - 1:
            assert value is None
        else:
            window = values[i - period + 1 : i + 1]
            assert value == pytest.approx(sum(window) / period)


def test_sma_rejects_a_non_positive_period() -> None:
    with pytest.raises(ValueError, match="positive"):
        sma([1.0, 2.0], period=0)


def test_sma_with_too_little_history_is_all_none() -> None:
    assert sma([1.0, 2.0], period=5) == [None, None]


def test_wilder_rsi_hand_worked_example() -> None:
    """period=2 over [10, 11, 12, 11], computed by hand.

    changes: +1, +1, -1
    seed (mean of first 2 changes): avg_gain=1.0, avg_loss=0.0 -> RSI 100
    next: gain=0, loss=1
      avg_gain = (1.0*1 + 0)/2 = 0.5
      avg_loss = (0.0*1 + 1)/2 = 0.5
      RS = 1.0 -> RSI = 50
    """
    assert wilder_rsi([10.0, 11.0, 12.0, 11.0], period=2) == [None, None, 100.0, 50.0]


def test_wilder_rsi_is_100_while_every_change_is_a_gain() -> None:
    assert wilder_rsi([1.0, 2.0, 3.0, 4.0], period=3) == [None, None, None, 100.0]


def test_wilder_rsi_is_0_while_every_change_is_a_loss() -> None:
    assert wilder_rsi([4.0, 3.0, 2.0, 1.0], period=3) == [None, None, None, 0.0]


def test_a_flat_series_gives_50_not_100() -> None:
    """No directional pressure. 100 would be a lie, and would also be outside the
    25-35 entry band only by luck; 50 keeps a dead stock out of the pool by design."""
    result = wilder_rsi([5.0] * 6, period=3)
    assert result[-1] == 50.0


def test_wilder_rsi_stays_within_bounds_on_a_noisy_series() -> None:
    values = [100.0]
    for step in (3, -7, 2, 9, -4, -1, 6, -8, 5, 2, -3, 7, -6, 1, 4, -2, 8, -5):
        values.append(values[-1] + step)
    for value in wilder_rsi(values, period=14):
        if value is not None:
            assert 0.0 <= value <= 100.0


def test_wilder_smoothing_remembers_losses_that_left_the_window() -> None:
    """The common bug is a simple mean of the last n changes.

    Here the only loss (-2) has fallen out of the trailing 3-change window, so a
    simple-mean RSI would read exactly 100. Wilder's smoothing carries that loss
    forward and must read lower.

    changes: -2, +1, +1, +1, +1 with period=3
    seed:  avg_gain=2/3,   avg_loss=2/3
    then:  avg_gain=7/9,   avg_loss=4/9
    then:  avg_gain=23/27, avg_loss=8/27  -> RS=23/8=2.875 -> RSI=100-100/3.875
    """
    values = [10.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    wilder = wilder_rsi(values, period=3)[-1]
    assert wilder is not None
    assert wilder < 100.0
    assert wilder == pytest.approx(100.0 - 100.0 / 3.875)


def test_the_seed_is_the_mean_of_the_first_n_changes() -> None:
    """period=3 over changes +2, +4, -3: avg_gain=2.0, avg_loss=1.0, RS=2, RSI=200/3."""
    result = wilder_rsi([10.0, 12.0, 16.0, 13.0], period=3)
    assert result[-1] == pytest.approx(100.0 - 100.0 / 3.0)


def test_wilder_rsi_needs_period_plus_one_prices() -> None:
    assert wilder_rsi([1.0, 2.0, 3.0], period=3) == [None, None, None]


def test_wilder_rsi_rejects_a_non_positive_period() -> None:
    with pytest.raises(ValueError, match="positive"):
        wilder_rsi([1.0, 2.0], period=0)


def test_warm_up_guard_refuses_a_short_series_when_asked_to() -> None:
    """The spec wants at least 200 bars of warm-up before a live RSI is trusted."""
    with pytest.raises(InsufficientHistoryError, match="200"):
        wilder_rsi([float(i) for i in range(50)], period=14, min_warmup=200)
