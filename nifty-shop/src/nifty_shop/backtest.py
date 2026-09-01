"""The baseline backtest engine.

The base strategy is implemented exactly as specified and nothing is added. Robustness
modules R1-R8 are not consulted here; they are Phase 4 and each must justify itself
against this baseline.

Daily, on each session:

1. Mark the book to the settled close.
2. Exit pass, per lot, against that lot's own entry: +5% gross OR RSI(14) above 50.
   Lots are only sellable from T+1.
3. Entry pass: resolve the point-in-time universe, keep symbols whose close is below
   SMA(50) with RSI(14) in [25, 35], rank by RSI ascending, take up to two distinct
   symbols at 5,000 notional each.
4. Record the session.

The engine refuses to run while any of the three rules the spec never specified is
still UNSPECIFIED. It will not invent one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from nifty_shop.config import AppConfig, PriceAboveNotional, assert_rules_resolved
from nifty_shop.costs import buy_charges, sell_charges
from nifty_shop.indicators import sma, wilder_rsi
from nifty_shop.kill_criteria import Breach, KillCriteria, evaluate, load_kill_criteria
from nifty_shop.ledger import ExitReason, Lot, LotLedger
from nifty_shop.metrics import BacktestMetrics, SessionRecord, compute_metrics, render_report
from nifty_shop.money import Paisa, rupees

#: The registered kill criteria live in exactly one place. Reading them here rather
#: than restating them means a private copy cannot drift from the registration.
KILL_CRITERIA_PATH = Path(__file__).resolve().parents[2] / "config" / "kill_criteria.toml"


class InMemoryMarket:
    """Deterministic market data for tests and for driving a real series in memory."""

    def __init__(
        self,
        series: Mapping[str, Sequence[float]],
        sessions: Sequence[date],
        universe: set[str] | None = None,
    ) -> None:
        self._series = {symbol: list(values) for symbol, values in series.items()}
        self._sessions = list(sessions)
        self._universe = universe
        self._index = {day: position for position, day in enumerate(self._sessions)}

    def sessions(self) -> list[date]:
        return list(self._sessions)

    def constituents_on(self, on: date) -> frozenset[str]:
        """Membership on a date.

        This in-memory market holds a single static universe, so `on` is accepted and
        ignored. The real implementation resolves it point-in-time via
        PointInTimeUniverse; the parameter exists so the two are interchangeable.
        """
        del on
        if self._universe is not None:
            return frozenset(self._universe)
        return frozenset(self._series)

    def closes_upto(self, symbol: str, on: date) -> list[float]:
        position = self._index.get(on)
        values = self._series.get(symbol)
        if position is None or values is None or position >= len(values):
            return []
        return values[: position + 1]

    def close_on(self, symbol: str, on: date) -> float | None:
        series = self.closes_upto(symbol, on)
        return series[-1] if series else None


@dataclass(frozen=True)
class Candidate:
    symbol: str
    close: float
    rsi: float


@dataclass
class BacktestResult:
    metrics: BacktestMetrics
    ledger: LotLedger
    records: list[SessionRecord] = field(default_factory=list)
    breaches: list[Breach] = field(default_factory=list)

    def render(self) -> str:
        """The full report. Breaches first, always."""
        return render_report(self.metrics, [breach.headline() for breach in self.breaches])

    def all_lots(self) -> tuple[Lot, ...]:
        """Every lot opened during the run, open or closed, in order."""
        closed = tuple(item.lot for item in self.ledger.closed_lots())
        combined = (*closed, *self.ledger.open_lots())
        return tuple(sorted(combined, key=lambda lot: lot.lot_id))

    def fingerprint(self) -> str:
        """Stable digest of the run, for the byte-identical determinism criterion."""
        parts = [
            f"{lot.lot_id}|{lot.symbol}|{lot.entry_date}|{lot.qty}|{int(lot.entry_price)}"
            for lot in self.all_lots()
        ]
        parts += [
            f"C{item.lot.lot_id}|{item.exit_date}|{int(item.exit_price)}|{item.reason}"
            for item in self.ledger.closed_lots()
        ]
        parts.append(self.metrics.headline())
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def _to_paisa(price: float) -> Paisa:
    return rupees(Decimal(str(round(price, 2))))


def criteria_for(config: AppConfig, path: Path = KILL_CRITERIA_PATH) -> KillCriteria:
    """The registered kill criteria, scaled to this run's allocation.

    Thresholds are percentages of allocated capital, so a run at a different size is
    still judged by the same registered rules.
    """
    registered = load_kill_criteria(path)
    return replace(registered, allocated_capital_inr=config.risk.allocated_capital_inr)


def run_backtest(market: InMemoryMarket, config: AppConfig) -> BacktestResult:
    assert_rules_resolved(config)

    strategy = config.strategy
    ledger = LotLedger()
    records: list[SessionRecord] = []
    days_to_target: list[int] = []
    wins = 0
    losses = 0

    allocated = rupees(str(config.risk.allocated_capital_inr))
    session_index = {day: position for position, day in enumerate(market.sessions())}

    for today in market.sessions():
        open_at_start = len(ledger.open_lots())

        marks: dict[str, Paisa] = {}
        rsi_today: dict[str, float] = {}
        for lot in ledger.open_lots():
            close = market.close_on(lot.symbol, today)
            if close is None:
                continue
            marks[lot.symbol] = _to_paisa(close)
            if lot.symbol not in rsi_today:
                series = market.closes_upto(lot.symbol, today)
                value = wilder_rsi(series, period=strategy.rsi_period)[-1]
                if value is not None:
                    rsi_today[lot.symbol] = value

        # --- exit pass, per lot, against that lot's own entry ---------------------
        closed_today = 0
        batched_dp: set[str] = set()
        for lot in ledger.open_lots():
            if lot.symbol not in marks or not ledger.is_sellable(lot, today):
                continue
            mark = marks[lot.symbol]
            reason: ExitReason | None = None
            if int(mark) >= int(lot.target_price(strategy.target_pct)):
                reason = ExitReason.TARGET
            elif rsi_today.get(lot.symbol, 0.0) > strategy.rsi_exit_above:
                reason = ExitReason.RSI_EXIT
            if reason is None:
                continue

            include_dp = lot.symbol not in batched_dp
            if config.robustness.r7_exit_batching_enabled:
                batched_dp.add(lot.symbol)
            notional = Paisa(lot.qty * int(mark))
            charges = sell_charges(notional, config.costs, include_dp=include_dp).total
            closed = ledger.close_lot(lot.lot_id, today, mark, charges, reason)
            closed_today += 1
            if reason is ExitReason.TARGET:
                held = session_index[today] - session_index[closed.lot.entry_date]
                days_to_target.append(held)
            if int(closed.realised_pnl) > 0:
                wins += 1
            else:
                losses += 1

        # --- entry pass ----------------------------------------------------------
        candidates: list[Candidate] = []
        for symbol in sorted(market.constituents_on(today)):
            series = market.closes_upto(symbol, today)
            if len(series) <= max(strategy.sma_period, strategy.rsi_period + 1):
                continue
            average = sma(series, period=strategy.sma_period)[-1]
            momentum = wilder_rsi(series, period=strategy.rsi_period)[-1]
            if average is None or momentum is None:
                continue
            close = series[-1]
            if close < average and strategy.rsi_low <= momentum <= strategy.rsi_high:
                candidates.append(Candidate(symbol, close, momentum))

        candidates.sort(key=lambda item: (item.rsi, item.symbol))

        taken = 0
        for candidate in candidates:
            if taken >= strategy.max_trades_per_day:
                break
            price = _to_paisa(candidate.close)
            notional_cap = rupees(str(strategy.lot_notional_inr))
            if int(price) > int(notional_cap):
                if strategy.price_above_notional is PriceAboveNotional.SKIP:
                    continue
                qty = 1
            else:
                qty = int(notional_cap) // int(price)
            if qty <= 0:
                continue

            consideration = Paisa(qty * int(price))
            charges = buy_charges(consideration, config.costs).total
            required = int(consideration) + int(charges)
            if int(ledger.deployed_capital()) + required > int(allocated):
                continue

            ledger.open_lot(candidate.symbol, today, qty, price, charges)
            taken += 1

        # --- record --------------------------------------------------------------
        settled_marks = dict(marks)
        for lot in ledger.open_lots():
            if lot.symbol not in settled_marks:
                close = market.close_on(lot.symbol, today)
                settled_marks[lot.symbol] = (
                    _to_paisa(close) if close is not None else lot.entry_price
                )
        equity = Paisa(
            int(allocated) + int(ledger.realised()) + int(ledger.unrealised(settled_marks))
        )

        records.append(
            SessionRecord(
                on=today,
                book_equity=equity,
                deployed_capital=ledger.deployed_capital(),
                open_lots=len(ledger.open_lots()),
                lots_closed=closed_today,
                open_at_start=open_at_start,
            )
        )

    metrics = compute_metrics(records, days_to_target, allocated, wins=wins, losses=losses)
    breaches = evaluate(
        criteria_for(config),
        max_book_drawdown_pct=metrics.max_book_drawdown_pct,
        longest_zero_exit_sessions=metrics.longest_zero_exit_sessions,
        peak_capital_deployed_inr=int(metrics.peak_capital_deployed) // 100,
    )
    return BacktestResult(
        metrics=metrics, ledger=ledger, records=records, breaches=breaches
    )
