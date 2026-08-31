"""Currency as integer paisa.

The acceptance criteria require reconciliation to a real contract note to the paisa.
Binary floating point cannot represent 0.05 exactly, so floats are rejected at the
boundary rather than tolerated and rounded later.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NewType

Paisa = NewType("Paisa", int)

_ONE = Decimal("1")
_HUNDRED = Decimal("100")


def rupees(amount: str | int | Decimal) -> Paisa:
    """Convert a rupee amount to integer paisa, rounding half-up at the paisa."""
    if isinstance(amount, float):
        raise TypeError("float is not an accepted money input; pass str, int or Decimal")
    value = amount if isinstance(amount, Decimal) else Decimal(amount)
    return Paisa(int((value * _HUNDRED).quantize(_ONE, rounding=ROUND_HALF_UP)))


def format_rupees(paisa: Paisa) -> str:
    """Render paisa as a rupee string with exactly two decimals."""
    sign = "-" if paisa < 0 else ""
    magnitude = abs(int(paisa))
    return f"{sign}{magnitude // 100}.{magnitude % 100:02d}"


def pct_of(paisa: Paisa, pct: Decimal) -> Paisa:
    """Percentage of an amount, rounded half-up at the paisa."""
    return Paisa(int((Decimal(int(paisa)) * pct / _HUNDRED).quantize(_ONE, rounding=ROUND_HALF_UP)))
