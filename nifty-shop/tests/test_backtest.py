from __future__ import annotations

from datetime import date, timedelta

import pytest

from nifty_shop.backtest import InMemoryMarket, run_backtest
from nifty_shop.config import (
    AppConfig,
    OnCashShortfall,
    OnExitPartialFill,
    OnIndexRemoval,
)
from nifty_shop.ledger import ExitReason

START = date(2026, 1, 1)
WARMUP = 260


def sessions(count: int) -> list[date]:
    return [START + timedelta(days=i) for i in range(count)]


def resolved_config(**overrides: object) -> AppConfig:
    """Every unresolved rule explicitly set. The engine refuses without this."""
    payload: dict[str, object] = {
        "rules": {
            "on_index_removal": OnIndexRemoval.HOLD_TO_TRIGGERS,
            "on_cash_shortfall": OnCashShortfall.TAKE_TOP_RANKED,
            "on_exit_partial_fill": OnExitPartialFill.RETRY_NEXT_SESSION,
        }
    }
    payload.update(overrides)
    return AppConfig.model_validate(payload)


def noisy_decline(
    start: float, down_pct: float, days: int, up_pct: float = 0.8, up_every: int = 3
) -> list[float]:
    """Long flat warm-up, then a decline with periodic up days.

    A *monotonic* decline is useless as a fixture: every change is a loss, so
    avg_gain is zero and RSI reads exactly 0, which is outside the 25-35 entry band.
    The strategy correctly buys nothing. Real declines have up days, and that is what
    puts RSI in the band, so the fixture has to as well.
    """
    series = [start] * WARMUP
    price = start
    for i in range(days):
        price *= (1.0 + up_pct / 100.0) if i % up_every == 0 else (1.0 - down_pct / 100.0)
        series.append(round(price, 2))
    return series


def rising(start: float, days: int) -> list[float]:
    series = [start] * WARMUP
    price = start
    for _ in range(days):
        price *= 1.01
        series.append(round(price, 2))
    return series


# --- refusals --------------------------------------------------------------------

def test_the_engine_refuses_while_any_rule_is_unspecified() -> None:
    """Phase 3 cannot run on an invented rule."""
    market = InMemoryMarket({"AAA": noisy_decline(100, 1.0, 20)}, sessions(WARMUP + 20))
    with pytest.raises(Exception, match="never specified"):
        run_backtest(market, AppConfig())


# --- entry ------------------------------------------------------------------------

def test_no_candidates_means_no_trades() -> None:
    """Everything above its SMA50: the pool is empty and the strategy sits out."""
    market = InMemoryMarket({"AAA": rising(100, 30)}, sessions(WARMUP + 30))
    result = run_backtest(market, resolved_config())
    assert result.ledger.open_lots() == ()
    assert result.ledger.closed_lots() == ()


def test_a_qualifying_symbol_is_bought_at_the_configured_notional() -> None:
    market = InMemoryMarket({"AAA": noisy_decline(100, 1.0, 40)}, sessions(WARMUP + 40))
    result = run_backtest(market, resolved_config())
    lots = result.all_lots()
    assert lots, "a declining symbol with RSI in band should have been bought"
    for lot in lots:
        assert lot.qty * int(lot.entry_price) <= 500_000
        assert lot.qty >= 1


def test_at_most_two_trades_a_day_and_always_distinct_symbols() -> None:
    """Hard cap of 2/day, and the second must be a different symbol."""
    series = {name: noisy_decline(100 + i, 1.0, 25) for i, name in enumerate("ABCDE")}
    market = InMemoryMarket(series, sessions(WARMUP + 25))
    result = run_backtest(market, resolved_config())

    by_day: dict[date, list[str]] = {}
    for lot in result.all_lots():
        by_day.setdefault(lot.entry_date, []).append(lot.symbol)
    for day, symbols in by_day.items():
        assert len(symbols) <= 2, day
        assert len(set(symbols)) == len(symbols), day


def test_the_lowest_rsi_candidate_is_taken_first() -> None:
    """Ranked by RSI ascending.

    Asserted as the rule rather than as a hardcoded winner: on each entry date, no
    other qualifying candidate may have had a lower RSI than the one taken.
    """
    from nifty_shop.indicators import sma, wilder_rsi

    series = {
        "STEEP": noisy_decline(100, 1.6, 40),
        "MID": noisy_decline(100, 1.0, 40),
        "MILD": noisy_decline(100, 0.6, 40),
    }
    market = InMemoryMarket(series, sessions(WARMUP + 40))
    result = run_backtest(market, resolved_config(strategy={"max_trades_per_day": 1}))
    assert result.all_lots()

    for lot in result.all_lots():
        qualifying: dict[str, float] = {}
        for symbol in series:
            closes = market.closes_upto(symbol, lot.entry_date)
            average = sma(closes, period=50)[-1]
            momentum = wilder_rsi(closes, period=14)[-1]
            if average is None or momentum is None:
                continue
            if closes[-1] < average and 25.0 <= momentum <= 35.0:
                qualifying[symbol] = momentum
        assert lot.symbol in qualifying
        assert qualifying[lot.symbol] == min(qualifying.values())


def test_a_share_priced_above_the_notional_is_skipped() -> None:
    """The configured resolution is SKIP, not 'buy one and exceed the budget'."""
    market = InMemoryMarket({"PRICEY": noisy_decline(20000, 1.0, 25)}, sessions(WARMUP + 25))
    result = run_backtest(market, resolved_config())
    assert result.all_lots() == ()


# --- exit -------------------------------------------------------------------------

def test_a_lot_exits_on_a_five_percent_gross_gain_from_its_own_entry() -> None:
    prices = noisy_decline(100, 1.0, 40)
    prices += [round(prices[-1] * 1.20, 2)] * 3  # a jump well past +5%, held
    market = InMemoryMarket({"AAA": prices}, sessions(len(prices)))
    result = run_backtest(market, resolved_config())
    reasons = {c.reason for c in result.ledger.closed_lots()}
    assert ExitReason.TARGET in reasons


def test_a_lot_bought_today_cannot_exit_today() -> None:
    """T+1. Even a 20% same-session jump cannot close a lot opened that session."""
    prices = noisy_decline(100, 1.0, 25)
    market = InMemoryMarket({"AAA": prices}, sessions(len(prices)))
    result = run_backtest(market, resolved_config())
    for closed in result.ledger.closed_lots():
        assert closed.exit_date > closed.lot.entry_date


def test_exits_are_recorded_with_the_reason() -> None:
    prices = noisy_decline(100, 1.0, 40)
    # a long recovery lifts RSI past the exit threshold
    prices += [round(prices[-1] * (1.03**i), 2) for i in range(1, 40)]
    market = InMemoryMarket({"AAA": prices}, sessions(len(prices)))
    result = run_backtest(market, resolved_config())
    assert result.ledger.closed_lots()
    assert all(c.reason in tuple(ExitReason) for c in result.ledger.closed_lots())


# --- accounting -------------------------------------------------------------------

def test_charges_are_applied_to_both_legs() -> None:
    prices = noisy_decline(100, 1.0, 40)
    prices += [round(prices[-1] * 1.20, 2)] * 3
    market = InMemoryMarket({"AAA": prices}, sessions(len(prices)))
    result = run_backtest(market, resolved_config())
    for closed in result.ledger.closed_lots():
        assert int(closed.lot.buy_charges) > 0
        assert int(closed.sell_charges) > 0


def test_the_run_never_deploys_more_than_the_allocated_capital() -> None:
    series = {
        name: noisy_decline(100 + i, 1.2, 30) for i, name in enumerate("ABCDEFGH")
    }
    market = InMemoryMarket(series, sessions(WARMUP + 30))
    config = resolved_config(risk={"allocated_capital_inr": 20_000})
    result = run_backtest(market, config)
    assert int(result.metrics.peak_capital_deployed) <= 20_000 * 100


def test_metrics_and_breaches_come_back_with_the_result() -> None:
    market = InMemoryMarket({"AAA": noisy_decline(100, 1.0, 25)}, sessions(WARMUP + 25))
    result = run_backtest(market, resolved_config())
    assert result.metrics.sessions > 0
    assert isinstance(result.breaches, list)


def test_the_backtest_is_deterministic() -> None:
    """An acceptance criterion: identical inputs, byte-identical output."""
    series = {name: noisy_decline(100 + i, 1.1, 30) for i, name in enumerate("ABCD")}
    days = sessions(WARMUP + 30)
    one = run_backtest(InMemoryMarket(series, days), resolved_config())
    two = run_backtest(InMemoryMarket(series, days), resolved_config())
    assert one.fingerprint() == two.fingerprint()


def test_a_symbol_outside_the_universe_is_never_bought() -> None:
    market = InMemoryMarket(
        {"IN": noisy_decline(100, 1.0, 25), "OUT": noisy_decline(100, 2.0, 25)},
        sessions(WARMUP + 25),
        universe={"IN"},
    )
    result = run_backtest(market, resolved_config())
    assert {lot.symbol for lot in result.all_lots()} <= {"IN"}


def test_the_engine_evaluates_the_kill_criteria_itself() -> None:
    """Breach detection must not depend on a caller remembering to check.

    Allocated capital of 5,000 with a 4,000 rupee KC-3 threshold: a single lot
    breaches it immediately.
    """
    market = InMemoryMarket({"AAA": noisy_decline(100, 1.0, 40)}, sessions(WARMUP + 40))
    result = run_backtest(market, resolved_config(risk={"allocated_capital_inr": 5_000}))
    assert result.all_lots(), "need at least one lot for the capital criterion to bite"
    assert result.breaches, "a run deploying ~100% of allocation must breach KC-3"
    assert any("KC-3" in str(b) for b in result.breaches)


def test_a_report_puts_breaches_before_the_headline() -> None:
    market = InMemoryMarket({"AAA": noisy_decline(100, 1.0, 40)}, sessions(WARMUP + 40))
    result = run_backtest(market, resolved_config(risk={"allocated_capital_inr": 5_000}))
    report = result.render()
    assert report.index("BREACHED") < report.index("return on allocated capital")


def test_the_engine_uses_the_registered_criteria_not_a_private_copy() -> None:
    """A second copy of the thresholds could drift from the registration and nobody
    would know. The engine must read the file the registration is mirrored in."""
    from pathlib import Path

    from nifty_shop.backtest import criteria_for
    from nifty_shop.kill_criteria import load_kill_criteria

    registered = load_kill_criteria(Path(__file__).parents[1] / "config" / "kill_criteria.toml")
    used = criteria_for(resolved_config())

    assert used.max_drawdown_pct == registered.max_drawdown_pct
    assert used.max_zero_exit_sessions == registered.max_zero_exit_sessions
    assert used.max_peak_capital_pct == registered.max_peak_capital_pct
    assert used.registered_on == registered.registered_on


def test_criteria_scale_to_the_runs_allocation() -> None:
    """Thresholds are percentages, so a smaller run is judged by the same rules."""
    from nifty_shop.backtest import criteria_for

    small = criteria_for(resolved_config(risk={"allocated_capital_inr": 5_000}))
    assert small.peak_capital_threshold_inr == 4_000
