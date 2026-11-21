from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.analysis import fundamental, funds, planning, portfolio, tax, technical


def frame(values, start="2024-01-01", freq="B"):
    idx = pd.date_range(start, periods=len(values), freq=freq, name="date")
    v = np.asarray(values, dtype=float)
    return pd.DataFrame({"open": v, "high": v * 1.01, "low": v * 0.99, "close": v, "volume": 1000.0}, index=idx)


# ---------- technical ----------

def test_sma_and_rsi_basics():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert technical.sma(s, 3).iloc[-1] == pytest.approx(4.0)
    up = pd.Series(np.arange(1, 40, dtype=float))
    assert technical.rsi(up).iloc[-1] == pytest.approx(100.0)
    down = pd.Series(np.arange(40, 1, -1, dtype=float))
    assert technical.rsi(down).iloc[-1] == pytest.approx(0.0, abs=1e-9)


def test_rsi_matches_wilder_reference():
    # Classic Wilder example prices; reference RSI(14) on the 15th bar is ~70.5
    prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    r = technical.rsi(pd.Series(prices), 14)
    assert r.iloc[-1] == pytest.approx(70.5, abs=1.5)


def test_technical_summary_uptrend_is_bullish_and_downtrend_bearish():
    up = technical.technical_summary(frame(np.linspace(100, 200, 300)))
    down = technical.technical_summary(frame(np.linspace(200, 100, 300)))
    assert up["available"] and up["stance"] == "bullish" and up["score"] > 0
    assert down["stance"] == "bearish" and down["score"] < 0
    assert up["returns_pct"]["1m"] > 0
    assert technical.technical_summary(frame([1, 2, 3]))["available"] is False


def test_max_drawdown():
    assert technical.max_drawdown(pd.Series([100, 120, 60, 130.0])) == pytest.approx(-50.0)


def test_support_resistance_finds_levels_around_price():
    t = np.arange(300)
    prices = 100 + 10 * np.sin(t / 10)
    lv = technical.support_resistance(frame(prices))
    price = prices[-1]
    assert all(s < price for s in lv["support"]) and all(r > price for r in lv["resistance"])


# ---------- portfolio ----------

def test_fifo_realized_gain_and_remaining_lots():
    tx = [
        {"side": "buy", "quantity": 10, "price": 100, "trade_date": date(2023, 1, 1)},
        {"side": "buy", "quantity": 10, "price": 120, "trade_date": date(2023, 6, 1)},
        {"side": "sell", "quantity": 15, "price": 150, "trade_date": date(2024, 3, 1)},
    ]
    pos = portfolio.build_position(tx)
    assert pos.quantity == pytest.approx(5)
    assert pos.avg_cost == pytest.approx(120)
    gains = [r["gain"] for r in pos.realized]
    assert gains == pytest.approx([500, 150])


def test_xirr_simple_and_irregular():
    assert portfolio.xirr([(date(2023, 1, 1), -1000), (date(2024, 1, 1), 1100)]) == pytest.approx(0.10, abs=1e-3)
    r = portfolio.xirr([(date(2023, 1, 1), -1000), (date(2023, 7, 1), -1000), (date(2024, 1, 1), 2200)])
    assert 0.12 < r < 0.15
    assert portfolio.xirr([(date(2023, 1, 1), -1000)]) is None


def test_allocation_and_rebalance():
    alloc = portfolio.allocation({"equity_india": 60, "debt": 20, "hybrid": 20})
    assert alloc["equity_india"] == pytest.approx(70) and alloc["debt"] == pytest.approx(30)
    rb = portfolio.rebalance({"equity_india": 90, "debt": 10}, "moderate")
    eq = next(r for r in rb["rows"] if r["bucket"] == "equity_india")
    assert eq["needs_action"] and eq["action_amount"] < 0 and rb["needs_rebalance"]


def test_bucket_for():
    assert portfolio.bucket_for("etf", "IN", "Nippon India ETF Gold BeES") == "gold"
    assert portfolio.bucket_for("stock", "US", "Apple") == "equity_global"
    assert portfolio.bucket_for("mutual_fund", "IN", "x", {"bucket": "debt"}) == "debt"


def test_portfolio_risk_runs():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2024-01-01", periods=260, freq="B")
    a = pd.Series(100 * np.cumprod(1 + rng.normal(0.0005, 0.01, 260)), index=idx)
    b = pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.02, 260)), index=idx)
    out = portfolio.portfolio_risk({"A": 0.6, "B": 0.4}, {"A": a, "B": b}, benchmark=a)
    assert out["available"] and out["volatility_pct"] > 0 and "beta" in out
    assert sum(out["risk_contribution_pct"].values()) == pytest.approx(100, abs=0.5)


# ---------- tax ----------

def test_equity_ltcg_exemption_and_stcg_rate():
    gains = [
        {"tax_class": "listed_equity", "buy_date": date(2023, 1, 1), "sell_date": date(2025, 6, 1), "gain": 200_000},
        {"tax_class": "listed_equity", "buy_date": date(2025, 1, 1), "sell_date": date(2025, 6, 1), "gain": 50_000},
    ]
    est = tax.estimate(gains, slab_rate=0.3)
    lt = next(r for r in est["rows"] if r["term"] == "LT")
    st = next(r for r in est["rows"] if r["term"] == "ST")
    assert lt["exempt"] == 125_000
    assert lt["tax_incl_cess"] == pytest.approx(75_000 * 0.125 * 1.04)
    assert st["tax_incl_cess"] == pytest.approx(50_000 * 0.20 * 1.04)


def test_holding_period_boundary_is_more_than_12_months():
    assert not tax.is_long_term("listed_equity", date(2024, 3, 1), date(2025, 3, 1))
    assert tax.is_long_term("listed_equity", date(2024, 3, 1), date(2025, 3, 2))
    assert not tax.is_long_term("foreign_equity", date(2024, 3, 1), date(2025, 6, 1))


def test_specified_debt_fund_is_slab_and_crypto_losses_do_not_offset():
    gains = [
        {"tax_class": "specified_mf", "buy_date": date(2023, 5, 1), "sell_date": date(2026, 6, 1), "gain": 100_000},
        {"tax_class": "vda", "buy_date": date(2025, 1, 1), "sell_date": date(2025, 6, 1), "gain": -50_000},
        {"tax_class": "vda", "buy_date": date(2025, 1, 1), "sell_date": date(2025, 7, 1), "gain": 10_000},
    ]
    est = tax.estimate(gains, slab_rate=0.2)
    mf = next(r for r in est["rows"] if r["tax_class"] == "specified_mf")
    vda = next(r for r in est["rows"] if r["tax_class"] == "vda")
    assert mf["rate_pct"] == 20 and mf["tax_incl_cess"] == pytest.approx(20_800)
    assert vda["taxable_after_setoff"] == 10_000 and vda["rate_pct"] == 30


def test_short_term_loss_offsets_highest_rate_gain_first():
    gains = [
        {"tax_class": "listed_equity", "buy_date": date(2025, 1, 1), "sell_date": date(2025, 6, 1), "gain": -30_000},
        {"tax_class": "foreign_equity", "buy_date": date(2025, 1, 1), "sell_date": date(2025, 6, 1), "gain": 40_000},
        {"tax_class": "listed_equity", "buy_date": date(2025, 2, 1), "sell_date": date(2025, 6, 1), "gain": 40_000},
    ]
    est = tax.estimate(gains, slab_rate=0.3)
    foreign = next(r for r in est["rows"] if r["tax_class"] == "foreign_equity")
    assert foreign["taxable_after_setoff"] == pytest.approx(10_000)


def test_tax_class_mapping():
    assert tax.tax_class("stock", "IN") == "listed_equity"
    assert tax.tax_class("stock", "US") == "foreign_equity"
    assert tax.tax_class("crypto", "GLOBAL") == "vda"
    assert tax.tax_class("mutual_fund", "IN", meta={"bucket": "debt"}, buy_date=date(2022, 1, 1)) == "debt_mf_old"
    assert tax.tax_class("etf", "IN", name="Gold BeES") == "listed_other"


def test_unrealized_view_flags_lots_turning_long_term():
    today = date(2026, 1, 10)
    h = [{"symbol": "X.NS", "name": "X", "tax_class": "listed_equity", "price": 200.0,
          "lots": [{"quantity": 10, "price": 100.0, "buy_date": date(2025, 1, 20)}]}]
    view = tax.unrealized_view(h, today=today)
    assert view["turning_long_term_soon"][0]["days_left"] == 11
    assert view["turning_long_term_soon"][0]["tax_saved_by_waiting"] > 0
    assert tax.financial_year(today) == "FY2025-26"


# ---------- planning ----------

def test_sip_future_value_matches_closed_form():
    r = (1.12) ** (1 / 12) - 1
    expected = 10_000 * (((1 + r) ** 120 - 1) / r) * (1 + r)
    assert planning.sip_future_value(10_000, 12, 10) == pytest.approx(expected, rel=1e-9)


def test_required_sip_inverts_future_value():
    sip = planning.required_sip(1_00_00_000, 11, 15, step_up_pct=10)
    assert planning.sip_future_value(sip, 11, 15, step_up_pct=10) == pytest.approx(1_00_00_000, rel=1e-6)


def test_goal_and_retirement_plans():
    g = planning.goal_plan(target_today=20_00_000, years=10, inflation_pct=6, expected_return_pct=11)
    assert g["future_target"] == pytest.approx(20_00_000 * 1.06**10, rel=1e-3)
    assert g["monthly_sip"] > 0 and len(g["table"]) == 10
    ret = planning.retirement_plan(current_age=35, retire_age=60, monthly_expense_today=50_000)
    assert ret["corpus_needed"] > ret["monthly_expense_at_retirement"] * 12 * 10
    assert ret["monthly_sip"] > 0


# ---------- fundamentals ----------

def company(**info):
    base = {"currentPrice": 100.0, "sharesOutstanding": 1e9, "freeCashflow": 5e9, "totalCash": 1e10, "totalDebt": 5e9,
            "trailingPE": 20.0, "returnOnEquity": 0.18, "profitMargins": 0.12, "revenueGrowth": 0.1,
            "earningsGrowth": 0.12, "debtToEquity": 40.0, "currentRatio": 1.5, "sector": "Industrials"}
    base.update(info)
    return {"info": base, "income": {}, "cashflow": {}, "balance": {}}


def test_dcf_scenarios_are_ordered_and_reasonable():
    out = fundamental.dcf(company(), "IN")
    fv = out["fair_value"]
    assert out["available"] and fv["bear"] < fv["base"] < fv["bull"]
    assert 20 < fv["base"] < 500


def test_dcf_not_available_without_fcf():
    assert fundamental.dcf(company(freeCashflow=-1.0), "IN")["available"] is False


def test_bank_uses_pb_roe_model_and_scores_exist():
    out = fundamental.analyze(company(sector="Financial Services", bookValue=60.0, returnOnEquity=0.16), region="IN")
    assert out["valuation"]["method"].startswith("Justified P/B")
    assert set(out["scores"]) == {"value", "quality", "growth", "health", "overall"}
    assert out["metrics"]["debt_to_equity"] == pytest.approx(0.4)


def test_relative_valuation():
    t = fundamental.key_metrics(company(trailingPE=15.0))
    peers = {"A": fundamental.key_metrics(company(trailingPE=20.0)), "B": fundamental.key_metrics(company(trailingPE=30.0))}
    rv = fundamental.relative_valuation(t, peers)
    assert rv["metrics"]["pe"]["reading"] == "cheaper" and rv["metrics"]["pe"]["peer_median"] == 25


def test_fund_summary():
    idx = pd.date_range("2020-01-01", periods=1500, freq="B")
    nav = pd.Series(10 * np.cumprod(np.full(1500, 1.0004)), index=idx)
    out = funds.fund_summary(nav, benchmark=nav * 1.0, benchmark_name="Nifty 50")
    assert out["available"] and out["returns_pct"]["3y_cagr"] > 0 and out["rolling_1y"]["positive_pct"] == 100
