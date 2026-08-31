"""Split and bonus adjustment, plus the unexplained-gap safety net.

Risk R-03: a missed 1:5 split puts a -80% bar into the series. SMA(50) and RSI(14) both
corrupt, and the system trades confidently and wrongly forever. Two defences:

1. Parse the corporate action purpose strings that are recognisable, and back-adjust.
2. Flag any move beyond a threshold that no known action explains. Anything the parser
   does not recognise returns None rather than a guess, so it surfaces here instead of
   being silently mis-applied.

Dividends are deliberately **not** price-adjusted. The independent reference charts the
Phase 2 gate validates against are not dividend-adjusted either, so adjusting for them
here would guarantee a mismatch that says nothing about indicator correctness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

#: "SPLIT FROM RS 10 TO RS 2", "FACE VALUE SPLIT FROM RS.10/- TO RS.1/-"
_SPLIT = re.compile(
    r"split\s+from\s+rs\.?\s*(?P<old>\d+(?:\.\d+)?)\s*/?-?\s*to\s+rs\.?\s*(?P<new>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

#: "BONUS 1:1", "Bonus issue 2:1" — a new shares for every b held.
_BONUS = re.compile(r"bonus[^0-9]*(?P<new>\d+)\s*:\s*(?P<held>\d+)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CorporateAction:
    symbol: str
    ex_date: date
    ratio: float
    purpose: str


@dataclass(frozen=True, slots=True)
class Bar:
    on: date
    close: float


@dataclass(frozen=True, slots=True)
class UnexplainedGap:
    on: date
    previous_close: float
    close: float
    move_pct: float

    def __str__(self) -> str:
        return (
            f"{self.on}: {self.previous_close} -> {self.close} "
            f"({self.move_pct:+.1f}%) with no corporate action"
        )


def ratio_from_purpose(purpose: str) -> float | None:
    """Price factor for prices before the ex-date, or None if not a price action.

    A face value split from 10 to 2 is a five-for-one split, so earlier prices are
    multiplied by 2/10. A bonus of `new:held` multiplies the share count by
    (new + held) / held, so earlier prices are multiplied by held / (new + held).
    """
    split = _SPLIT.search(purpose)
    if split is not None:
        old = float(split.group("old"))
        new = float(split.group("new"))
        if old > 0:
            return new / old

    bonus = _BONUS.search(purpose)
    if bonus is not None:
        new = float(bonus.group("new"))
        held = float(bonus.group("held"))
        if new + held > 0:
            return held / (new + held)

    return None


def back_adjust(bars: list[Bar], actions: list[CorporateAction]) -> list[Bar]:
    """Scale every close that precedes each action's ex-date.

    Actions compound: a bar before two later actions is scaled by both.
    """
    if not actions:
        return list(bars)

    adjusted: list[Bar] = []
    for bar in bars:
        factor = 1.0
        for action in actions:
            if bar.on < action.ex_date:
                factor *= action.ratio
        adjusted.append(Bar(on=bar.on, close=bar.close * factor))
    return adjusted


def detect_unexplained_gaps(
    bars: list[Bar], actions: list[CorporateAction], threshold_pct: float
) -> list[UnexplainedGap]:
    """Find day-on-day moves beyond the threshold that no known action explains.

    A non-positive price is always reported: it cannot be a real close, and it would
    make every downstream ratio meaningless.
    """
    ex_dates = {action.ex_date for action in actions}
    gaps: list[UnexplainedGap] = []

    for previous, current in pairwise(bars):
        if current.on in ex_dates:
            continue

        if previous.close <= 0 or current.close <= 0:
            gaps.append(
                UnexplainedGap(
                    on=current.on,
                    previous_close=previous.close,
                    close=current.close,
                    move_pct=0.0,
                )
            )
            continue

        move_pct = (current.close / previous.close - 1.0) * 100.0
        if abs(move_pct) > threshold_pct:
            gaps.append(
                UnexplainedGap(
                    on=current.on,
                    previous_close=previous.close,
                    close=current.close,
                    move_pct=move_pct,
                )
            )

    return gaps
