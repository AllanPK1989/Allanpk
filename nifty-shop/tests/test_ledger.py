from __future__ import annotations

from datetime import date

import pytest

from nifty_shop.ledger import ExitReason, LedgerError, LotLedger
from nifty_shop.money import rupees

D1, D2, D3 = date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)


def ledger_with_two_lots() -> LotLedger:
    ledger = LotLedger()
    ledger.open_lot("RELIANCE", on=D1, qty=2, price=rupees("2500"), charges=rupees("6"))
    ledger.open_lot("RELIANCE", on=D2, qty=2, price=rupees("2400"), charges=rupees("6"))
    return ledger


def test_each_buy_is_an_independent_lot_with_its_own_entry() -> None:
    """The broker shows one aggregated holding; the ledger is authoritative per lot."""
    lots = ledger_with_two_lots().open_lots()
    assert [lot.lot_id for lot in lots] == [1, 2]
    assert [int(lot.entry_price) for lot in lots] == [250_000, 240_000]


def test_cost_basis_includes_buy_charges() -> None:
    ledger = LotLedger()
    lot = ledger.open_lot("X", on=D1, qty=2, price=rupees("2500"), charges=rupees("6"))
    assert int(lot.cost_basis) == 2 * 250_000 + 600


def test_deployed_capital_is_the_sum_of_open_cost_bases() -> None:
    assert int(ledger_with_two_lots().deployed_capital()) == (2 * 250_000 + 600) + (
        2 * 240_000 + 600
    )


def test_a_lot_bought_today_is_not_sellable_today() -> None:
    """T+1 settlement. A lot that somehow hits target on day zero still cannot exit."""
    ledger = LotLedger()
    lot = ledger.open_lot("X", on=D1, qty=1, price=rupees("100"), charges=rupees("1"))
    assert ledger.is_sellable(lot, on=D1) is False
    assert ledger.is_sellable(lot, on=D2) is True


def test_closing_maps_the_sell_to_a_specific_lot() -> None:
    ledger = ledger_with_two_lots()
    closed = ledger.close_lot(
        2, on=D3, price=rupees("2520"), charges=rupees("21"), reason=ExitReason.TARGET
    )
    assert closed.lot.lot_id == 2
    assert int(closed.lot.entry_price) == 240_000
    assert [lot.lot_id for lot in ledger.open_lots()] == [1]
    assert [c.lot.lot_id for c in ledger.closed_lots()] == [2]


def test_realised_pnl_is_net_of_both_legs_of_charges() -> None:
    ledger = LotLedger()
    ledger.open_lot("X", on=D1, qty=2, price=rupees("1000"), charges=rupees("6"))
    closed = ledger.close_lot(
        1, on=D3, price=rupees("1050"), charges=rupees("21"), reason=ExitReason.TARGET
    )
    assert int(closed.realised_pnl) == 2 * (105_000 - 100_000) - 600 - 2100


def test_closing_an_unknown_lot_refuses() -> None:
    with pytest.raises(LedgerError, match="99"):
        LotLedger().close_lot(
            99, on=D3, price=rupees("1"), charges=rupees("0"), reason=ExitReason.TARGET
        )


def test_closing_a_lot_twice_refuses() -> None:
    """A double-close would book the same gain twice and lose a real position."""
    ledger = ledger_with_two_lots()
    ledger.close_lot(
        1, on=D3, price=rupees("2600"), charges=rupees("21"), reason=ExitReason.TARGET
    )
    with pytest.raises(LedgerError, match="already closed"):
        ledger.close_lot(
            1, on=D3, price=rupees("2600"), charges=rupees("21"), reason=ExitReason.TARGET
        )


def test_unrealised_marks_open_lots_to_market() -> None:
    ledger = ledger_with_two_lots()
    marks = {"RELIANCE": rupees("2450")}
    expected = (2 * (245_000 - 250_000) - 600) + (2 * (245_000 - 240_000) - 600)
    assert int(ledger.unrealised(marks)) == expected


def test_unrealised_refuses_when_a_held_symbol_has_no_mark() -> None:
    """Fail closed: silently treating a missing price as zero would report a total
    loss, and treating it as cost would hide one."""
    with pytest.raises(LedgerError, match="RELIANCE"):
        ledger_with_two_lots().unrealised({})


def test_holdings_aggregate_to_what_the_broker_would_show() -> None:
    """The morning reconciliation compares exactly this against the broker."""
    assert ledger_with_two_lots().holdings() == {"RELIANCE": 4}


def test_fifo_order_is_available_for_tax_while_decisions_stay_per_lot() -> None:
    ledger = ledger_with_two_lots()
    ledger.open_lot("RELIANCE", on=D3, qty=1, price=rupees("2300"), charges=rupees("6"))
    assert [lot.lot_id for lot in ledger.fifo_lots("RELIANCE")] == [1, 2, 3]


def test_lots_for_a_symbol_excludes_closed_ones() -> None:
    ledger = ledger_with_two_lots()
    ledger.close_lot(
        1, on=D3, price=rupees("2600"), charges=rupees("21"), reason=ExitReason.TARGET
    )
    assert [lot.lot_id for lot in ledger.lots_for("RELIANCE")] == [2]


def test_same_day_exits_of_one_symbol_are_reported_for_batching() -> None:
    """R7 needs to know which lots share a symbol on an exit day so the DP charge is
    paid once."""
    ledger = ledger_with_two_lots()
    assert ledger.symbols_with_multiple_lots() == {"RELIANCE": 2}
