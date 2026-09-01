"""The lot ledger.

Each buy is an independent lot with its own entry price, date and exit trigger. The
broker shows one aggregated holding per symbol; this ledger is authoritative for exit
decisions, and every sell is explicitly mapped to the lot it closes so the mapping can
be persisted and audited. FIFO is available for tax; decisions stay per lot.

Failures raise. Nothing returns a sentinel a caller could mistake for a valid state:
a missing mark price refuses rather than being treated as zero (which would report a
total loss) or as cost (which would hide a real one).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from nifty_shop.money import Paisa

#: Equity delivery settles T+1, so a lot bought today cannot be sold today.
SETTLEMENT_DAYS = 1


class LedgerError(Exception):
    """An operation the ledger refuses to perform."""


class ExitReason(StrEnum):
    TARGET = "target"
    RSI_EXIT = "rsi_exit"
    TIME_STOP = "time_stop"
    INDEX_REMOVAL = "index_removal"


@dataclass(frozen=True, slots=True)
class Lot:
    lot_id: int
    symbol: str
    entry_date: date
    qty: int
    entry_price: Paisa
    buy_charges: Paisa
    sellable_from: date

    @property
    def cost_basis(self) -> Paisa:
        """What the account actually had to find: consideration plus buy-side charges."""
        return Paisa(self.qty * int(self.entry_price) + int(self.buy_charges))

    def target_price(self, target_pct: float) -> Paisa:
        return Paisa(round(int(self.entry_price) * (1.0 + target_pct / 100.0)))


@dataclass(frozen=True, slots=True)
class ClosedLot:
    lot: Lot
    exit_date: date
    exit_price: Paisa
    sell_charges: Paisa
    reason: ExitReason

    @property
    def realised_pnl(self) -> Paisa:
        return Paisa(
            self.lot.qty * (int(self.exit_price) - int(self.lot.entry_price))
            - int(self.lot.buy_charges)
            - int(self.sell_charges)
        )

    @property
    def holding_sessions(self) -> int:
        return (self.exit_date - self.lot.entry_date).days


class LotLedger:
    def __init__(self) -> None:
        self._open: dict[int, Lot] = {}
        self._closed: list[ClosedLot] = []
        self._closed_ids: set[int] = set()
        self._next_id = 1

    def open_lot(
        self,
        symbol: str,
        on: date,
        qty: int,
        price: Paisa,
        charges: Paisa,
        sellable_from: date | None = None,
    ) -> Lot:
        if qty <= 0:
            raise LedgerError(f"refusing to open a lot of {qty} shares in {symbol}")
        lot = Lot(
            lot_id=self._next_id,
            symbol=symbol,
            entry_date=on,
            qty=qty,
            entry_price=price,
            buy_charges=charges,
            sellable_from=sellable_from or (on + timedelta(days=SETTLEMENT_DAYS)),
        )
        self._open[lot.lot_id] = lot
        self._next_id += 1
        return lot

    def close_lot(
        self, lot_id: int, on: date, price: Paisa, charges: Paisa, reason: ExitReason
    ) -> ClosedLot:
        if lot_id not in self._open:
            if lot_id in self._closed_ids:
                raise LedgerError(f"lot {lot_id} is already closed")
            raise LedgerError(f"lot {lot_id} does not exist")

        lot = self._open.pop(lot_id)
        closed = ClosedLot(
            lot=lot, exit_date=on, exit_price=price, sell_charges=charges, reason=reason
        )
        self._closed.append(closed)
        self._closed_ids.add(lot_id)
        return closed

    def is_sellable(self, lot: Lot, on: date) -> bool:
        return on >= lot.sellable_from

    def open_lots(self) -> tuple[Lot, ...]:
        return tuple(self._open[key] for key in sorted(self._open))

    def closed_lots(self) -> tuple[ClosedLot, ...]:
        return tuple(self._closed)

    def lots_for(self, symbol: str) -> tuple[Lot, ...]:
        return tuple(lot for lot in self.open_lots() if lot.symbol == symbol)

    def fifo_lots(self, symbol: str) -> tuple[Lot, ...]:
        """Oldest first, for tax reporting. Exit decisions do not use this order."""
        return tuple(
            sorted(self.lots_for(symbol), key=lambda lot: (lot.entry_date, lot.lot_id))
        )

    def holdings(self) -> dict[str, int]:
        """Aggregate quantity per symbol, i.e. what the broker should report."""
        counts: Counter[str] = Counter()
        for lot in self.open_lots():
            counts[lot.symbol] += lot.qty
        return dict(counts)

    def symbols_with_multiple_lots(self) -> dict[str, int]:
        """Symbols holding more than one open lot, for R7 exit batching."""
        counts: Counter[str] = Counter(lot.symbol for lot in self.open_lots())
        return {symbol: count for symbol, count in counts.items() if count > 1}

    def deployed_capital(self) -> Paisa:
        return Paisa(sum(int(lot.cost_basis) for lot in self.open_lots()))

    def realised(self) -> Paisa:
        return Paisa(sum(int(closed.realised_pnl) for closed in self._closed))

    def unrealised(self, marks: Mapping[str, Paisa]) -> Paisa:
        total = 0
        for lot in self.open_lots():
            if lot.symbol not in marks:
                raise LedgerError(
                    f"no mark price for {lot.symbol}; refusing to value the book on a guess"
                )
            total += lot.qty * (int(marks[lot.symbol]) - int(lot.entry_price))
            total -= int(lot.buy_charges)
        return Paisa(total)
