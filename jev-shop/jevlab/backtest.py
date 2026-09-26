"""Backtest: what the rules in strategy.py would have done over the last few years, with your
amounts, charges and capital cap. It runs the exact same decide() as the daily shop.

  uv run python -m jevlab backtest              # the last 5 years
  uv run python -m jevlab backtest --years 10   # as far back as Firstock's daily candles go

Uses Firstock's daily candles (needs today's login), cached in results/cache. Read the
result with care:
  * It uses TODAY's Nifty 50 for the whole period. Companies that dropped out of the
    index (often after falling a lot) are missing, which flatters a buy-the-dip strategy
    (survivorship bias). Treat the result as a best case.
  * Fills are at the day's close plus 0.1% slippage each way; the live shop trades at 15:18.
  * Splits and bonuses are detected from overnight price drops of about 1/2, 1/3, 1/5, 1/10
    and adjusted for. No dividends.
  * The news check can't be tested: there's no archive of old headlines.
"""

from __future__ import annotations

import csv
import json
import time
from datetime import date, timedelta

import pandas as pd

from . import strategy
from .core import RESULTS, console, header, inr, ist_now
from .firstock import FirstockError, SessionExpired, charges, daily_candles, load_session, trading_symbol
from .ledger import adjust_for_splits
from .shop import amounts
from .universe import nifty50

CACHE = RESULTS / "cache"
SLIPPAGE = 0.001


def _history(session, sym: str, tsym: str, start: date) -> pd.Series:
    """Daily closes for one stock, from the cache when it's fresh enough."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{sym}.csv"
    today = ist_now().date()
    if path.exists():
        df = pd.read_csv(path, parse_dates=["day"])
        s = pd.Series(df["close"].values, index=[d.date() for d in df["day"]])
        if len(s) and s.index[0] <= start + timedelta(days=10) and (today - s.index[-1]).days <= 4:
            return s[s.index >= start]
    df = daily_candles(session, tsym, start, today - timedelta(days=1))
    df[["close"]].rename_axis("day").to_csv(path)
    time.sleep(0.1)
    return df["close"]


def _adjust_splits(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return pd.Series(adjust_for_splits(list(s.values)), index=s.index)


def simulate(closes: pd.DataFrame, buy_amount: float, avg_amount: float, cap: float) -> dict:
    n = strategy.SETTINGS["dma_days"]
    dma = closes.rolling(n, min_periods=n).mean()
    lots: dict[str, list[dict]] = {}
    last_px: dict[str, float] = {}
    realised = fees = 0.0
    trades, curve = [], []
    buys = {"new": 0, "average": 0}
    for day in closes.index:
        row, drow = closes.loc[day], dma.loc[day]
        for sym, p in row.items():
            if pd.notna(p):
                last_px[sym] = float(p)
        scan = sorted(({"symbol": s, "ltp": float(row[s]), "dma": float(drow[s]), "gap": float(row[s] / drow[s] - 1)}
                       for s in closes.columns if pd.notna(row[s]) and pd.notna(drow[s])), key=lambda x: x["gap"])
        if not scan:
            continue
        held = {}
        for sym, ls in lots.items():
            qty = sum(l["qty"] for l in ls)
            cost = sum(l["qty"] * l["price"] for l in ls)
            held[sym] = {"qty": qty, "avg": cost / qty, "cost": cost, "last_buy": ls[-1]["price"], "lots": len(ls),
                         "ltp": last_px.get(sym)}
        d = strategy.decide(scan, held, buy_amount, avg_amount)
        if d["sell"]:
            sym = d["sell"]["symbol"]
            h, px = held[sym], held[sym]["ltp"] * (1 - SLIPPAGE)
            fee = charges("sell", h["qty"] * px)
            buy_fees = sum(l["fees"] for l in lots[sym])
            pnl = h["qty"] * px - h["cost"] - buy_fees - fee
            realised += pnl
            fees += fee
            trades.append({"symbol": sym, "bought": lots[sym][0]["date"], "sold": day, "lots": h["lots"], "qty": h["qty"],
                           "avg": round(h["avg"], 2), "price": round(px, 2), "pnl": round(pnl, 2),
                           "days": (day - lots[sym][0]["date"]).days})
            del lots[sym]
        invested = sum(l["qty"] * l["price"] for ls in lots.values() for l in ls)
        for b in d["buys"]:
            ltp = last_px[b["symbol"]]
            qty = int(b["amount"] // ltp)
            if qty < 1:
                continue
            px = ltp * (1 + SLIPPAGE)
            if invested + qty * px > cap:
                break
            fee = charges("buy", qty * px)
            fees += fee
            lots.setdefault(b["symbol"], []).append({"date": day, "qty": qty, "price": px, "fees": fee})
            buys[b["kind"]] += 1
            break
        invested = sum(l["qty"] * l["price"] for ls in lots.values() for l in ls)
        open_pnl = sum(l["qty"] * (last_px[s] - l["price"]) - l["fees"] for s, ls in lots.items() for l in ls)
        curve.append((day, invested, realised + open_pnl))

    if not curve:
        raise SystemExit("  not enough history to backtest")
    first, last = curve[0][0], curve[-1][0]
    years = max((last - first).days / 365.25, 1 / 365)
    peak = max(c[1] for c in curve) or 1.0
    total = curve[-1][2]
    running, max_dd = float("-inf"), 0.0
    for _, _, pnl in curve:
        running = max(running, pnl)
        max_dd = max(max_dd, running - pnl)
    open_pos = []
    for sym, ls in lots.items():
        qty = sum(l["qty"] for l in ls)
        cost = sum(l["qty"] * l["price"] for l in ls)
        open_pos.append({"symbol": sym, "lots": len(ls), "cost": round(cost, 2), "change": round(last_px[sym] * qty / cost - 1, 4),
                         "days": (last - ls[0]["date"]).days})
    wins = [t for t in trades if t["pnl"] > 0]
    days_held = sorted(t["days"] for t in trades)
    return {
        "from": str(first), "to": str(last), "years": round(years, 2), "stocks": len(closes.columns),
        "buy_amount": buy_amount, "average_amount": avg_amount, "max_capital": cap,
        "new_buys": buys["new"], "averages": buys["average"], "sells": len(trades),
        "win_rate": round(len(wins) / len(trades), 3) if trades else None,
        "median_days_held": days_held[len(days_held) // 2] if days_held else None,
        "realised": round(realised, 2), "open_pnl": round(total - realised, 2), "total_pnl": round(total, 2),
        "charges": round(fees, 2), "peak_invested": round(peak, 2),
        "return_on_peak": round(total / peak, 4),
        "annualised_on_peak": round((1 + total / peak) ** (1 / years) - 1, 4) if total > -peak else -1.0,
        "max_drawdown": round(max_dd, 2), "max_drawdown_on_peak": round(max_dd / peak, 4),
        "open_positions": sorted(open_pos, key=lambda x: x["change"]),
        "curve": [[str(d), round(i, 2), round(p, 2)] for d, i, p in curve[::5]],
        "trades": trades,
    }


def run_backtest(years: float) -> None:
    buy_amount, avg_amount, cap = amounts()
    header("NIFTY SHOP BACKTEST", f"{strategy.DESCRIPTION} · {inr(buy_amount)} a buy, {inr(avg_amount)} an average · "
           f"capital cap {inr(cap)} · last {years:g} years · closes + 0.1% slippage · delivery charges")
    session = load_session()
    if not session:
        raise SystemExit("  not logged in to Firstock today (the price history comes from Firstock). "
                         "Run: uv run python -m jevlab login")
    universe, source = nifty50()
    start = ist_now().date() - timedelta(days=int(years * 365.25) + 3 * strategy.SETTINGS["dma_days"])
    console.print(f"  loading daily history for {len(universe)} stocks ({source})…")
    series, missing = {}, []
    try:
        for sym in sorted(universe):
            try:
                s = _history(session, sym, trading_symbol(sym), start)
            except SessionExpired:
                raise
            except FirstockError as exc:
                missing.append(f"{sym} ({str(exc)[:40]})")
                continue
            if len(s) > strategy.SETTINGS["dma_days"]:
                series[sym] = _adjust_splits(s)
        try:
            nifty = _history(session, "NIFTY", "NIFTY", start)
        except FirstockError:
            nifty = pd.Series(dtype=float)
    except SessionExpired:
        raise SystemExit("  your Firstock session has ended. Log in again and re-run.")
    if not series:
        raise SystemExit("  no price history came back from Firstock")
    closes = pd.DataFrame(series).sort_index()
    r = simulate(closes, buy_amount, avg_amount, cap)
    if len(nifty) > 1:
        nifty = nifty[nifty.index >= date.fromisoformat(r["from"])]
        if len(nifty) > 1:
            r["nifty_change"] = round(float(nifty.iloc[-1] / nifty.iloc[0] - 1), 4)
            r["nifty_annualised"] = round(float((nifty.iloc[-1] / nifty.iloc[0]) ** (1 / r["years"]) - 1), 4)
    r["missing"], r["universe_source"] = missing, source

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "backtest.json").write_text(json.dumps({k: v for k, v in r.items() if k != "trades"}, default=str))
    with open(RESULTS / "backtest_trades.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "bought", "sold", "days", "lots", "qty", "avg", "price", "pnl"])
        w.writeheader()
        w.writerows(r["trades"])

    console.print(f"\n  {r['from']} → {r['to']} ({r['years']} years) · {r['stocks']} stocks")
    console.print(f"  {r['new_buys']} new buys · {r['averages']} averages · {r['sells']} sells · "
                  f"win rate {r['win_rate']:.0%}" if r["win_rate"] is not None else "  no completed trades")
    console.print(f"  profit booked {inr(r['realised'], True)} · still open {inr(r['open_pnl'], True)} · "
                  f"total [bold]{inr(r['total_pnl'], True)}[/] after {inr(r['charges'])} of charges")
    console.print(f"  most money ever invested at once {inr(r['peak_invested'])} · return on that "
                  f"{r['return_on_peak']:+.1%} · about {r['annualised_on_peak']:+.1%} a year")
    console.print(f"  worst drawdown {inr(r['max_drawdown'])} ({r['max_drawdown_on_peak']:.1%} of the peak invested) · "
                  f"median holding {r['median_days_held']} days")
    if "nifty_annualised" in r:
        console.print(f"  NIFTY itself over the same period: {r['nifty_change']:+.1%} (about {r['nifty_annualised']:+.1%} a year, "
                      "before dividends)")
    stuck = [p for p in r["open_positions"] if p["change"] < -0.1]
    if stuck:
        console.print("  still stuck at the end: " + ", ".join(f"{p['symbol']} {p['change']:+.0%} ({p['lots']} lots, "
                                                               f"{p['days']} days)" for p in stuck[:6]))
    if missing:
        console.print(f"  [dim]no history for: {', '.join(missing[:6])}[/]")
    console.print("  [dim]today's Nifty 50 used for the whole period: a best case (survivorship bias). "
                  "Trades: results/backtest_trades.csv[/]")
