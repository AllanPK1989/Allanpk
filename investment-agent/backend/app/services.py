"""Business logic shared by the API, the chat agent and the scheduled jobs."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from .analysis import fundamental, funds, portfolio as pf, tax, technical
from .config import get_settings
from .data.market import MarketData, get_market
from .data.types import SearchResult
from .models import AppSetting, Instrument, Transaction, utcnow

log = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    "risk_profile": "moderate",  # conservative | moderate | aggressive
    "horizon_years": 10,
    "age": None,
    "tax_slab_pct": 30,
    "ltcg_exemption_used": 0,  # equity LTCG already booked this financial year (Rs)
    "risk_free_pct": 6.5,
    "rbi_repo_rate_pct": None,  # set manually; no free API publishes it
    "alert_pct": 3.0,
    "alert_pct_crypto": 6.0,
    "email_digests": True,
    "email_alerts": False,
    "push_digests": True,
    "push_alerts": True,
    "digests_enabled": {"morning": True, "evening": True, "weekly": True},
    "goals_notes": "",  # free text the agent reads: goals, preferences, things to avoid
}

BENCHMARKS = {"IN": "^NSEI", "US": "^GSPC", "GLOBAL": "^GSPC"}


# ---------- settings ----------

def get_all_settings(db: Session) -> dict[str, Any]:
    out = dict(DEFAULT_SETTINGS)
    for row in db.scalars(select(AppSetting)):
        if row.key in DEFAULT_SETTINGS:
            out[row.key] = row.value
    return out


def update_settings(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    for k, v in values.items():
        if k not in DEFAULT_SETTINGS:
            continue
        row = db.get(AppSetting, k)
        if row:
            row.value = v
        else:
            db.add(AppSetting(key=k, value=v))
    db.flush()
    return get_all_settings(db)


# ---------- instruments ----------

def get_instrument(db: Session, symbol: str) -> Instrument | None:
    return db.scalar(select(Instrument).where(Instrument.symbol == symbol))


def follow(db: Session, r: SearchResult | dict[str, Any], *, source: str = "search", market: MarketData | None = None) -> Instrument:
    """Create or refresh an instrument and mark it followed. Every searched item stays followed."""
    d = r.to_dict() if isinstance(r, SearchResult) else dict(r)
    inst = get_instrument(db, d["symbol"])
    if inst is None:
        inst = Instrument(symbol=d["symbol"], name=d.get("name") or d["symbol"], asset_class=d.get("asset_class") or "stock",
                          region=d.get("region") or "GLOBAL", exchange=d.get("exchange") or "",
                          currency=d.get("currency") or "", source=source, meta=d.get("meta") or {})
        db.add(inst)
        if inst.asset_class == "mutual_fund":
            # Category decides the allocation bucket and the tax treatment.
            info = (market or get_market()).fundamentals(inst.symbol).get("info", {})
            inst.meta = {**(inst.meta or {}), "category": info.get("category", ""), "bucket": info.get("bucket"),
                         "equityOriented": info.get("equityOriented", False), "fund_house": info.get("fundFamily")}
    inst.followed = True
    inst.search_count = (inst.search_count or 0) + 1
    inst.last_viewed_at = utcnow()
    db.flush()
    return inst


def resolve_symbol(db: Session, symbol_or_query: str, *, market: MarketData | None = None, source: str = "agent") -> Instrument | None:
    """Find an instrument by exact symbol, else search and follow the best match."""
    market = market or get_market()
    q = symbol_or_query.strip()
    inst = get_instrument(db, q) or get_instrument(db, q.upper())
    if inst:
        return inst
    results = market.search(q)
    exact = next((r for r in results if r.symbol.upper() == q.upper()), None)
    pick = exact or (results[0] if results else None)
    return follow(db, pick, source=source, market=market) if pick else None


def followed_instruments(db: Session) -> list[Instrument]:
    return list(db.scalars(select(Instrument).where(Instrument.followed.is_(True)).order_by(Instrument.pinned.desc(), Instrument.name)))


def instrument_dict(i: Instrument) -> dict[str, Any]:
    return {"id": i.id, "symbol": i.symbol, "name": i.name, "asset_class": i.asset_class, "region": i.region,
            "exchange": i.exchange, "currency": i.currency, "followed": i.followed, "pinned": i.pinned,
            "source": i.source, "alert_pct": i.alert_pct, "meta": i.meta or {}}


# ---------- single-instrument analysis ----------

def analyze_instrument(inst: Instrument, *, market: MarketData | None = None, period: str = "2y",
                       include_chart: bool = False, rf_pct: float = 6.5) -> dict[str, Any]:
    market = market or get_market()
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_hist = ex.submit(market.history, inst.symbol, "5y" if inst.asset_class in ("mutual_fund", "etf") else period)
        f_quote = ex.submit(market.quote, inst.symbol)
        f_fund = ex.submit(market.fundamentals, inst.symbol)
        hist, quote, fdata = f_hist.result(), f_quote.result(), f_fund.result()
    ppy = 365 if inst.asset_class == "crypto" else 252
    out: dict[str, Any] = {
        "instrument": instrument_dict(inst),
        "quote": quote.to_dict(),
        "technical": technical.technical_summary(hist.tail(504), periods_per_year=ppy),
        "fundamental": fundamental.analyze(fdata, region=inst.region, asset_class=inst.asset_class),
        "demo": market.demo,
    }
    if inst.asset_class in ("mutual_fund", "etf") and not hist.empty:
        bench_sym = BENCHMARKS.get(inst.region, "^GSPC")
        bench = market.history(bench_sym, "5y")["close"] if inst.meta.get("bucket", "equity_india") != "debt" else None
        out["fund"] = funds.fund_summary(hist["close"], benchmark=bench, rf_annual_pct=rf_pct,
                                         benchmark_name="Nifty 50" if bench_sym == "^NSEI" else "S&P 500")
    if include_chart:
        out["chart"] = technical.chart_series(hist.tail(504))
    return out


# ---------- portfolio ----------

def _tx_dicts(txs: list[Transaction]) -> list[dict[str, Any]]:
    return [{"side": t.side, "quantity": t.quantity, "price": t.price, "trade_date": t.trade_date, "fees": t.fees,
             "fx_rate": t.fx_rate} for t in txs]


def _inr_tx(t: dict[str, Any], current_fx: float) -> dict[str, Any]:
    fx = t.get("fx_rate") or current_fx
    return {**t, "price": t["price"] * fx, "fees": (t.get("fees") or 0) * fx}


def portfolio_snapshot(db: Session, *, market: MarketData | None = None) -> dict[str, Any]:
    """Holdings valued in INR with P&L, day change, XIRR and allocation."""
    market = market or get_market()
    insts = [i for i in db.scalars(select(Instrument)) if i.transactions]
    if not insts:
        return {"holdings": [], "totals": {"value": 0, "invested": 0, "pnl": 0, "pnl_pct": None, "day_change": 0,
                                            "realized": 0, "xirr_pct": None}, "allocation": {}, "demo": market.demo}
    quotes = market.quotes([i.symbol for i in insts])
    fx = market.fx_rates({(quotes.get(i.symbol).currency if quotes.get(i.symbol) else "") or i.currency or "INR" for i in insts})
    holdings, all_flows, by_bucket, weights = [], [], {}, {}
    tot_value = tot_invested = tot_day = tot_realized = 0.0
    today = date.today()
    for i in insts:
        q = quotes.get(i.symbol)
        ccy = ((q.currency if q else "") or i.currency or "INR").upper()
        rate = fx.get(ccy) or fx.get("USD" if ccy == "USDT" else ccy) or 1.0
        pos_inr = pf.build_position([_inr_tx(t, rate) for t in _tx_dicts(i.transactions)])
        realized = sum(r["gain"] for r in pos_inr.realized)
        tot_realized += realized
        price = q.price if q else None
        value = pos_inr.quantity * price * rate if price is not None else None
        day = (pos_inr.quantity * q.change * rate) if (q and q.change is not None) else 0.0
        flows = list(pos_inr.cash_flows)
        if value:
            flows.append((today, value))
        all_flows.extend(pos_inr.cash_flows)
        x = pf.xirr(flows) if pos_inr.quantity > 0 or pos_inr.realized else None
        bucket = pf.bucket_for(i.asset_class, i.region, i.name, i.meta)
        if pos_inr.quantity > 1e-9:
            tot_value += value or 0
            tot_invested += pos_inr.cost
            tot_day += day
            by_bucket[bucket] = by_bucket.get(bucket, 0.0) + (value or 0)
            weights[i.symbol] = value or 0
        holdings.append({
            "symbol": i.symbol, "name": i.name, "asset_class": i.asset_class, "region": i.region, "bucket": bucket,
            "currency": ccy, "quantity": round(pos_inr.quantity, 6), "price": price,
            "avg_cost": round(pos_inr.avg_cost / rate, 4) if pos_inr.quantity else None,
            "value": round(value, 2) if value is not None else None, "invested": round(pos_inr.cost, 2),
            "pnl": round(value - pos_inr.cost, 2) if value is not None else None,
            "pnl_pct": round((value / pos_inr.cost - 1) * 100, 2) if value and pos_inr.cost else None,
            "day_change": round(day, 2), "day_change_pct": q.change_pct if q else None,
            "realized": round(realized, 2), "xirr_pct": round(x * 100, 2) if x is not None else None,
            "open": pos_inr.quantity > 1e-9,
        })
    if tot_value:
        all_flows.append((today, tot_value))
    for h in holdings:
        h["weight_pct"] = round((h["value"] or 0) / tot_value * 100, 2) if tot_value and h["open"] else 0
    holdings.sort(key=lambda h: -(h["value"] or 0))
    px = pf.xirr(all_flows)
    return {
        "holdings": holdings,
        "totals": {"value": round(tot_value, 2), "invested": round(tot_invested, 2),
                   "pnl": round(tot_value - tot_invested, 2),
                   "pnl_pct": round((tot_value / tot_invested - 1) * 100, 2) if tot_invested else None,
                   "day_change": round(tot_day, 2),
                   "day_change_pct": round(tot_day / (tot_value - tot_day) * 100, 2) if tot_value - tot_day else None,
                   "realized": round(tot_realized, 2), "xirr_pct": round(px * 100, 2) if px is not None else None},
        "allocation": pf.allocation(by_bucket),
        "by_bucket_value": {k: round(v, 2) for k, v in by_bucket.items()},
        "concentration": pf.concentration(weights),
        "fx": fx, "demo": market.demo,
        "note": "Values in INR. Foreign holdings use the trade-date FX rate if you entered one, else today's rate.",
    }


def portfolio_risk(db: Session, *, market: MarketData | None = None) -> dict[str, Any]:
    market = market or get_market()
    snap = portfolio_snapshot(db, market=market)
    weights = {h["symbol"]: h["value"] for h in snap["holdings"] if h["open"] and h["value"]}
    if not weights:
        return {"available": False, "reason": "No open holdings."}
    with ThreadPoolExecutor(max_workers=6) as ex:
        hists = dict(zip(weights, ex.map(lambda s: market.history(s, "1y")["close"], weights)))
    bench = market.history("^NSEI", "1y")["close"]
    rf = get_all_settings(db)["risk_free_pct"]
    out = pf.portfolio_risk(weights, hists, benchmark=bench, rf_annual_pct=rf)
    out["benchmark"] = "Nifty 50"
    return out


def portfolio_tax(db: Session, *, market: MarketData | None = None) -> dict[str, Any]:
    market = market or get_market()
    settings = get_all_settings(db)
    slab = float(settings["tax_slab_pct"]) / 100
    insts = [i for i in db.scalars(select(Instrument)) if i.transactions]
    quotes = market.quotes([i.symbol for i in insts]) if insts else {}
    fx = market.fx_rates({(quotes[i.symbol].currency if i.symbol in quotes else "") or i.currency or "INR" for i in insts})
    today = date.today()
    fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    holdings, realized_fy = [], []
    for i in insts:
        q = quotes.get(i.symbol)
        ccy = ((q.currency if q else "") or i.currency or "INR").upper()
        rate = fx.get(ccy) or 1.0
        pos = pf.build_position([_inr_tx(t, rate) for t in _tx_dicts(i.transactions)])
        lots = [{"quantity": l.quantity, "price": l.price + (l.fees / l.quantity if l.quantity else 0), "buy_date": l.buy_date}
                for l in pos.lots]
        cls = tax.tax_class(i.asset_class, i.region, name=i.name, meta=i.meta,
                            buy_date=min((l.buy_date for l in pos.lots), default=today))
        if lots:
            holdings.append({"symbol": i.symbol, "name": i.name, "tax_class": cls,
                             "price": q.price * rate if q and q.price is not None else None, "lots": lots})
        for r in pos.realized:
            if r["sell_date"] >= fy_start:
                realized_fy.append({"tax_class": tax.tax_class(i.asset_class, i.region, name=i.name, meta=i.meta,
                                                               buy_date=r["buy_date"]),
                                    "buy_date": r["buy_date"], "sell_date": r["sell_date"], "gain": r["gain"],
                                    "symbol": i.symbol})
    booked = tax.estimate(realized_fy, slab_rate=slab, exemption_used=0)
    eq_lt_used = sum(r["exempt"] for r in booked["rows"] if r["tax_class"] == "listed_equity")
    used = max(float(settings["ltcg_exemption_used"] or 0), eq_lt_used)
    view = tax.unrealized_view(holdings, today=today, slab_rate=slab, exemption_used=used)
    view["realized_this_fy"] = booked
    view["slab_rate_pct"] = slab * 100
    return view


def rebalance_plan(db: Session, *, market: MarketData | None = None) -> dict[str, Any]:
    snap = portfolio_snapshot(db, market=market)
    profile = get_all_settings(db)["risk_profile"]
    return pf.rebalance(snap.get("by_bucket_value", {}), profile)


def add_transaction(db: Session, inst: Instrument, *, side: str, quantity: float, price: float, trade_date: date,
                    fees: float = 0.0, fx_rate: float | None = None, note: str = "") -> Transaction:
    if side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")
    if quantity <= 0 or price < 0 or fees < 0:
        raise ValueError("quantity must be positive; price and fees cannot be negative")
    if trade_date > date.today() + timedelta(days=1):
        raise ValueError("trade date is in the future")
    t = Transaction(instrument_id=inst.id, side=side, quantity=quantity, price=price, trade_date=trade_date,
                    fees=fees, fx_rate=fx_rate, note=note[:256])
    db.add(t)
    inst.followed = True
    if inst.source == "search":
        inst.source = "portfolio"
    db.flush()
    return t


def recent_change(market: MarketData, symbol: str, days: int) -> float | None:
    h = market.history(symbol, "1mo" if days <= 20 else "3mo")
    return technical.period_return(h["close"], days) if not h.empty else None


def now_local() -> datetime:
    from zoneinfo import ZoneInfo

    return datetime.now(timezone.utc).astimezone(ZoneInfo(get_settings().timezone))


def series_close(market: MarketData, symbol: str, period: str = "1y") -> pd.Series:
    h = market.history(symbol, period)
    return h["close"] if not h.empty else pd.Series(dtype=float)
