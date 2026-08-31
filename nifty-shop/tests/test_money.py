from __future__ import annotations

from decimal import Decimal

import pytest

from nifty_shop.money import Paisa, format_rupees, pct_of, rupees


def test_whole_rupees() -> None:
    assert rupees("5000") == 500_000
    assert rupees(5000) == 500_000


def test_paise_precision() -> None:
    assert rupees("13.50") == 1350
    assert rupees(Decimal("13.50")) == 1350


def test_rounds_half_up_at_the_paisa() -> None:
    assert rupees("0.005") == 1
    assert rupees("0.004") == 0


def test_float_is_rejected_outright() -> None:
    """0.1 is not 0.1 in binary; money must never accept one."""
    with pytest.raises(TypeError, match="float"):
        rupees(0.1)  # type: ignore[arg-type]


def test_format_is_always_two_decimals() -> None:
    assert format_rupees(Paisa(1350)) == "13.50"
    assert format_rupees(Paisa(500_000)) == "5000.00"
    assert format_rupees(Paisa(-1350)) == "-13.50"
    assert format_rupees(Paisa(5)) == "0.05"


def test_pct_of_matches_the_spec_cost_table() -> None:
    """STT at 0.1% on a 5,000 rupee buy is 5.00; both legs give the ~10.30 in the spec."""
    notional = rupees("5000")
    assert pct_of(notional, Decimal("0.1")) == 500
    assert format_rupees(pct_of(notional, Decimal("0.015"))) == "0.75"
