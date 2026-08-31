"""SMA and Wilder-smoothed RSI.

A silently wrong RSI produces a system that trades confidently and wrongly forever, so
this module is deliberately small, has no dependencies, and is pinned by both
hand-worked examples and an independent-reference validation gate.

Numeric policy: indicators use float. Money is integer paisa (see money.py) and never
touches this module. Indicators are compared against an external reference within a
stated tolerance, so float is appropriate; float arithmetic is deterministic for
identical inputs, which the byte-identical-backtest requirement needs.

Warm-up is returned as None rather than 0.0 or a repeated first value. A caller that
mistakes a warm-up placeholder for a real reading would generate signals out of
nothing, so the type makes that impossible to do by accident.
"""

from __future__ import annotations

from collections.abc import Sequence


class InsufficientHistoryError(Exception):
    """Fewer bars supplied than the configured warm-up requires."""


def sma(values: Sequence[float], period: int) -> list[float | None]:
    """Simple moving average. Positions before the window fills are None."""
    if period <= 0:
        raise ValueError("period must be positive")

    out: list[float | None] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= period:
            running -= values[index - period]
        out.append(running / period if index >= period - 1 else None)
    return out


def wilder_rsi(
    closes: Sequence[float], period: int, min_warmup: int | None = None
) -> list[float | None]:
    """RSI using Wilder's smoothing.

    The seed is the arithmetic mean of the first `period` changes. Every later value
    carries the whole history forward as
    `avg = (prev_avg * (period - 1) + current) / period`, which is what distinguishes
    Wilder's RSI from an RSI built on a simple moving average of changes.

    Edge cases, chosen deliberately and documented rather than left implicit:

    * `avg_loss == 0` with `avg_gain > 0` -> 100.0, the standard convention.
    * `avg_gain == 0` with `avg_loss > 0` -> 0.0.
    * both zero, i.e. a perfectly flat series -> **50.0**, not 100.0. A dead stock has
      no directional pressure, and 50 keeps it out of the 25-35 entry band by design
      instead of by luck.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if min_warmup is not None and len(closes) < min_warmup:
        raise InsufficientHistoryError(
            f"{len(closes)} bars supplied, warm-up requires at least {min_warmup}"
        )

    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out

    gains = 0.0
    losses = 0.0
    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change

    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)

    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[index] = _rsi_from(avg_gain, avg_loss)

    return out


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0.0:
        # A flat series has no direction; 100 would overstate it.
        return 100.0 if avg_gain > 0.0 else 50.0
    if avg_gain == 0.0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
