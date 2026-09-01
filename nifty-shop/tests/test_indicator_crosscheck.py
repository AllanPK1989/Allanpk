"""Cross-check the indicator engine against an independently-written library.

This is NOT the Phase 2 validation gate. That gate requires an external reference
captured from real market data (TradingView or similar), which also validates the price
pipeline feeding the indicators. This is narrower: it verifies the *maths* against a
second implementation nobody here wrote.

`ta` seeds its Wilder smoothing differently (a pandas ewm from the first observation,
rather than the mean of the first n changes). Both are legitimate seeds and they
converge exponentially, so agreement after a long warm-up is exactly what should be
expected — and demonstrating that convergence is itself the justification for the
spec's >=200 bar warm-up requirement.
"""

from __future__ import annotations

import random

import pandas as pd
import pytest
from ta.momentum import RSIIndicator

from nifty_shop.indicators import sma, wilder_rsi

PERIOD = 14


def synthetic_closes(seed: int, count: int = 600) -> list[float]:
    """Deterministic pseudo-random walk. Seeded, so the suite stays reproducible."""
    rng = random.Random(seed)
    price = 1000.0
    out = [price]
    for _ in range(count - 1):
        price = max(1.0, price * (1.0 + rng.gauss(0.0, 0.015)))
        out.append(round(price, 2))
    return out


@pytest.mark.parametrize("seed", [1, 2, 3, 7, 11, 42, 99, 1234])
def test_rsi_agrees_with_an_independent_library_after_warmup(seed: int) -> None:
    closes = synthetic_closes(seed)
    mine = wilder_rsi(closes, period=PERIOD)
    theirs = RSIIndicator(pd.Series(closes), window=PERIOD).rsi().tolist()

    ours_last = mine[-1]
    assert ours_last is not None
    assert ours_last == pytest.approx(theirs[-1], abs=0.10)


@pytest.mark.parametrize("seed", [5, 17, 23])
def test_rsi_agrees_across_the_whole_settled_series(seed: int) -> None:
    """Not just the final bar: every reading past the warm-up must agree."""
    closes = synthetic_closes(seed)
    mine = wilder_rsi(closes, period=PERIOD)
    theirs = RSIIndicator(pd.Series(closes), window=PERIOD).rsi().tolist()

    for index in range(200, len(closes)):
        assert mine[index] is not None
        assert mine[index] == pytest.approx(theirs[index], abs=0.10)


def test_the_two_seeds_converge_which_is_why_warmup_is_required() -> None:
    """Early bars legitimately differ; the gap decays. This is the evidence behind the
    200-bar warm-up, rather than the number being an unexplained constant."""
    closes = synthetic_closes(2024)
    mine = wilder_rsi(closes, period=PERIOD)
    theirs = RSIIndicator(pd.Series(closes), window=PERIOD).rsi().tolist()

    def gap(index: int) -> float:
        value = mine[index]
        assert value is not None
        return abs(value - theirs[index])

    early = max(gap(i) for i in range(PERIOD + 1, PERIOD + 15))
    settled = max(gap(i) for i in range(200, 260))
    assert settled < early
    assert settled < 0.01


@pytest.mark.parametrize("seed", [1, 42, 777])
def test_sma_agrees_with_pandas_rolling_mean(seed: int) -> None:
    closes = synthetic_closes(seed)
    mine = sma(closes, period=50)
    theirs = pd.Series(closes).rolling(window=50).mean().tolist()

    for index in range(49, len(closes)):
        assert mine[index] is not None
        assert mine[index] == pytest.approx(theirs[index], abs=1e-9)
