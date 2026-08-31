"""Phase 2 indicator validation gate.

The spec: RSI(14) and SMA(50) must match an independent reference for at least five
symbols across at least three dates, within a stated tolerance, as committed fixtures.
Nothing proceeds past Phase 2 until this passes.

The gate is deliberately built to fail when unsatisfied rather than to skip. A skipped
gate is a gate nobody notices, and the failure this guards against — a silently wrong
RSI — produces a system that trades confidently and wrongly forever.

Reference values must be captured from an external tool (TradingView or similar) and
committed as JSON. Every fixture must name its `source`; an unsourced number is an
assertion, not a reference.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from nifty_shop.indicators import sma, wilder_rsi

RSI_PERIOD = 14
SMA_PERIOD = 50

#: Stated tolerances. RSI converges from its seed, so a long warm-up should bring any
#: correct implementation well inside this. SMA is exact given identical closes; its
#: tolerance covers only price-source rounding.
DEFAULT_RSI_TOLERANCE = 0.10
DEFAULT_SMA_TOLERANCE = 0.01

#: Wilder's RSI needs a long warm-up before it is trustworthy.
MIN_WARMUP_BARS = 200

MIN_SYMBOLS = 5
MIN_DATES = 3


class ValidationGateNotSatisfiedError(Exception):
    """The indicator engine has not been validated against an independent reference."""


@dataclass(frozen=True, slots=True)
class ReferencePoint:
    symbol: str
    as_of: date
    closes: tuple[float, ...]
    expected_rsi_14: float
    expected_sma_50: float
    source: str


@dataclass(frozen=True, slots=True)
class Discrepancy:
    symbol: str
    as_of: date
    metric: str
    expected: float | None
    computed: float | None
    detail: str = ""

    def __str__(self) -> str:
        if self.detail:
            return f"{self.symbol} {self.as_of} {self.metric}: {self.detail}"
        return (
            f"{self.symbol} {self.as_of} {self.metric}: "
            f"expected {self.expected}, computed {self.computed}"
        )


def load_reference_points(directory: Path) -> list[ReferencePoint]:
    """Load every committed reference fixture from a directory of JSON files."""
    if not directory.is_dir():
        return []

    points: list[ReferencePoint] = []
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        source = str(raw.get("source", "")).strip()
        if not source:
            raise ValueError(f"{path.name} states no source; an unsourced value is not a reference")
        points.append(
            ReferencePoint(
                symbol=str(raw["symbol"]),
                as_of=date.fromisoformat(str(raw["as_of"])),
                closes=tuple(float(value) for value in raw["closes"]),
                expected_rsi_14=float(raw["expected_rsi_14"]),
                expected_sma_50=float(raw["expected_sma_50"]),
                source=source,
            )
        )
    return points


def check(
    points: list[ReferencePoint],
    rsi_tolerance: float = DEFAULT_RSI_TOLERANCE,
    sma_tolerance: float = DEFAULT_SMA_TOLERANCE,
) -> list[Discrepancy]:
    """Compare computed indicators against every reference point."""
    found: list[Discrepancy] = []

    for point in points:
        if len(point.closes) < MIN_WARMUP_BARS:
            found.append(
                Discrepancy(
                    symbol=point.symbol,
                    as_of=point.as_of,
                    metric="warm-up",
                    expected=None,
                    computed=None,
                    detail=(
                        f"only {len(point.closes)} bars supplied; "
                        f"warm-up requires at least {MIN_WARMUP_BARS}"
                    ),
                )
            )
            continue

        computed_rsi = wilder_rsi(point.closes, period=RSI_PERIOD)[-1]
        computed_sma = sma(point.closes, period=SMA_PERIOD)[-1]

        for metric, expected, computed, tolerance in (
            ("RSI(14)", point.expected_rsi_14, computed_rsi, rsi_tolerance),
            ("SMA(50)", point.expected_sma_50, computed_sma, sma_tolerance),
        ):
            if computed is None or abs(computed - expected) > tolerance:
                found.append(
                    Discrepancy(
                        symbol=point.symbol,
                        as_of=point.as_of,
                        metric=metric,
                        expected=expected,
                        computed=computed,
                    )
                )

    return found


def assert_gate_satisfied(
    points: list[ReferencePoint],
    rsi_tolerance: float = DEFAULT_RSI_TOLERANCE,
    sma_tolerance: float = DEFAULT_SMA_TOLERANCE,
) -> None:
    """Raise unless coverage and accuracy both hold."""
    if not points:
        raise ValidationGateNotSatisfiedError(
            "no reference fixtures committed. Capture RSI(14) and SMA(50) from an "
            f"independent tool for at least {MIN_SYMBOLS} symbols across "
            f"{MIN_DATES} distinct dates, with at least {MIN_WARMUP_BARS} bars of "
            "closes each, and commit them to tests/fixtures/reference/. "
            "See that directory's README for the format."
        )

    symbols = {point.symbol for point in points}
    if len(symbols) < MIN_SYMBOLS:
        raise ValidationGateNotSatisfiedError(
            f"reference covers {len(symbols)} symbols; the gate requires {MIN_SYMBOLS} symbols"
        )

    dates = {point.as_of for point in points}
    if len(dates) < MIN_DATES:
        raise ValidationGateNotSatisfiedError(
            f"reference covers {len(dates)} dates; the gate requires {MIN_DATES} distinct dates"
        )

    discrepancies = check(points, rsi_tolerance, sma_tolerance)
    if discrepancies:
        rendered = "\n  ".join(str(item) for item in discrepancies)
        raise ValidationGateNotSatisfiedError(
            f"{len(discrepancies)} indicator discrepancies against the reference:\n  {rendered}"
        )
