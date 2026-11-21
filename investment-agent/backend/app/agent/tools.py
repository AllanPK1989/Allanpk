"""Tools the chat agent can call. Each returns compact JSON; errors come back as is_error results."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Callable

from sqlalchemy.orm import Session

from .. import services
from ..analysis import fundamental, planning, portfolio as pf, tax, technical
from ..data.market import MarketData
from ..news import collect, query as news_query, summarize

log = logging.getLogger(__name__)
MAX_RESULT_CHARS = 14000


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"name": name, "description": description, "eager_input_streaming": True,
            "input_schema": {"type": "object", "properties": properties, "required": required or [],
                             "additionalProperties": False}}


SYMBOL = {"type": "string", "description": "App symbol: Yahoo symbol (RELIANCE.NS, AAPL, GC=F, USDINR=X, ^NSEI), "
                                           "MF:<AMFI code> for Indian mutual funds, CRYPTO:<PAIR> for crypto (CRYPTO:BTC_USDT)."}

TOOLS: list[dict[str, Any]] = [
    _tool("search_instruments", "Find stocks, ETFs, indices, Indian mutual funds, crypto pairs, commodities or FX by name or "
          "ticker. Returns symbols to use with the other tools.",
          {"query": {"type": "string", "description": "Company, fund, coin or ticker, e.g. 'HDFC Bank', 'parag parikh flexi', 'solana'."}},
          ["query"]),
    _tool("analyze_instrument", "Full current analysis of one instrument: live quote, technical summary, fundamentals and "
          "valuation (or fund statistics), recent triaged news, and the owner's position in it. Also follows the instrument "
          "so it appears in the owner's daily digests.",
          {"symbol": SYMBOL, "refresh_news": {"type": "boolean", "description": "Fetch fresh news first (slower). Default false."}},
          ["symbol"]),
    _tool("compare_instruments", "Side-by-side comparison of 2-6 instruments: returns, volatility, technical stance, "
          "valuation multiples, profitability, growth, plus a peer-relative valuation of the first one.",
          {"symbols": {"type": "array", "items": SYMBOL, "minItems": 2, "maxItems": 6}}, ["symbols"]),
    _tool("get_price_history", "Price history summary: period return, high/low, drawdown and monthly closes.",
          {"symbol": SYMBOL, "period": {"type": "string", "enum": ["3mo", "6mo", "1y", "2y", "5y"]}}, ["symbol"]),
    _tool("get_news", "Recent stored news with AI summaries, sentiment and impact. Filter by instrument, impact or "
          "keyword; with no filters returns the most important market news.",
          {"symbol": SYMBOL, "days": {"type": "integer", "minimum": 1, "maximum": 30},
           "impact": {"type": "string", "enum": ["high", "medium", "low"]},
           "keyword": {"type": "string", "description": "Text to look for in headlines."}}),
    _tool("get_market_overview", "Snapshot of Indian and global indices, VIX, USD/INR, gold, silver, crude, US yields, "
          "crypto, and macro rates (Fed funds, US and India CPI, India 10Y).", {}),
    _tool("get_portfolio", "The owner's holdings valued in INR: quantity, cost, value, P&L, XIRR, weights, allocation by "
          "asset bucket and concentration.", {}),
    _tool("get_portfolio_risk", "Risk of the current portfolio over the past year: volatility, Sharpe, max drawdown, "
          "1-day VaR, beta to Nifty 50, correlations and each holding's risk contribution.", {}),
    _tool("get_tax_view", "Indian capital-gains view of the portfolio: short/long-term gains per holding, tax if sold "
          "today, lots turning long-term soon, LTCG harvesting room and tax-loss candidates, plus gains booked this year.", {}),
    _tool("get_rebalance_plan", "Current allocation vs the model allocation for the owner's risk profile, with the "
          "amount to add or trim per bucket.", {}),
    _tool("estimate_sale_tax", "Estimate capital-gains tax (FIFO lots) if the owner sold some quantity of a holding now.",
          {"symbol": SYMBOL, "quantity": {"type": "number", "exclusiveMinimum": 0},
           "sell_price": {"type": "number", "description": "Per unit, in the instrument's currency. Default: current price."}},
          ["symbol", "quantity"]),
    _tool("plan_goal", "Monthly SIP needed for a goal, adjusted for inflation, with a year-by-year table.",
          {"target_amount_today": {"type": "number", "description": "Goal cost in today's rupees."},
           "years": {"type": "number", "exclusiveMinimum": 0},
           "inflation_pct": {"type": "number"}, "expected_return_pct": {"type": "number"},
           "current_savings": {"type": "number"}, "step_up_pct": {"type": "number", "description": "Yearly SIP increase %."}},
          ["target_amount_today", "years"]),
    _tool("plan_retirement", "Retirement corpus needed and the monthly SIP to get there.",
          {"current_age": {"type": "integer"}, "retire_age": {"type": "integer"},
           "monthly_expense_today": {"type": "number"}, "life_expectancy": {"type": "integer"},
           "inflation_pct": {"type": "number"}, "pre_return_pct": {"type": "number"},
           "post_return_pct": {"type": "number"}, "current_corpus": {"type": "number"},
           "step_up_pct": {"type": "number"}},
          ["current_age", "retire_age", "monthly_expense_today"]),
    _tool("get_watchlist", "All instruments the owner follows (searched, pinned or held) with today's move.", {}),
    _tool("follow_instrument", "Follow an instrument (its news goes into the digests) and optionally pin it to the watchlist.",
          {"symbol": SYMBOL, "pin": {"type": "boolean"}}, ["symbol"]),
]


# ---------- input validation (eager streaming means the server does not validate for us) ----------

_JSON_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}


def validate(name: str, args: Any) -> str | None:
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if spec is None:
        return f"Unknown tool '{name}'. Available: {', '.join(t['name'] for t in TOOLS)}"
    if not isinstance(args, dict):
        return "Tool input must be a JSON object."
    schema = spec["input_schema"]
    for r in schema["required"]:
        if r not in args:
            return f"Missing required field '{r}'."
    for k, v in args.items():
        prop = schema["properties"].get(k)
        if prop is None:
            return f"Unknown field '{k}'. Allowed: {', '.join(schema['properties'])}"
        typ = _JSON_TYPES.get(prop.get("type", ""))
        if typ and (not isinstance(v, typ) or (prop.get("type") in ("integer", "number") and isinstance(v, bool))):
            return f"Field '{k}' must be of type {prop['type']}."
        if "enum" in prop and v not in prop["enum"]:
            return f"Field '{k}' must be one of {prop['enum']}."
    return None


# ---------- helpers ----------

def _round(obj: Any, nd: int = 4) -> Any:
    if isinstance(obj, float):
        return round(obj, nd)
    if isinstance(obj, dict):
        return {k: _round(v, nd) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_round(v, nd) for v in obj]
    return obj


def _dump(obj: Any) -> str:
    s = json.dumps(_round(obj), default=str, ensure_ascii=False, separators=(",", ":"))
    if len(s) > MAX_RESULT_CHARS:
        s = s[:MAX_RESULT_CHARS] + '..."[truncated]"'
    return s


def _resolve(db: Session, market: MarketData, symbol: str):
    inst = services.resolve_symbol(db, symbol, market=market)
    if inst is None:
        raise LookupError(f"No instrument found for '{symbol}'. Try search_instruments.")
    return inst


def _position(db: Session, market: MarketData, symbol: str) -> dict[str, Any] | None:
    snap = services.portfolio_snapshot(db, market=market)
    h = next((h for h in snap["holdings"] if h["symbol"] == symbol and h["open"]), None)
    if h:
        h = {**h, "portfolio_value_inr": snap["totals"]["value"]}
    return h


def compact_analysis(a: dict[str, Any]) -> dict[str, Any]:
    t = a.get("technical") or {}
    if t.get("available"):
        t = {k: t[k] for k in ("as_of", "score", "stance", "indicators", "returns_pct", "high_52w", "low_52w",
                               "from_52w_high_pct", "volatility_annual_pct", "max_drawdown_1y_pct", "levels") if k in t} | {
            "signals": [s["text"] for s in t.get("signals", [])]}
    f = a.get("fundamental") or {}
    if f.get("kind") == "company":
        f = {k: f.get(k) for k in ("name", "sector", "industry", "summary", "metrics", "scores", "valuation", "next_earnings")}
        if f.get("summary"):
            f["summary"] = f["summary"][:400]
    return {"instrument": a["instrument"], "quote": a["quote"], "technical": t, "fundamental": f,
            "fund": a.get("fund"), "demo": a.get("demo")}


# ---------- tool implementations ----------

def t_search(db, market, args):
    return {"results": [r.to_dict() for r in market.search(args["query"])[:10]]}


def t_analyze(db, market, args):
    inst = _resolve(db, market, args["symbol"])
    if args.get("refresh_news"):
        collect.collect(db, market, [inst], market_feeds=False)
        summarize.summarize_pending(db, limit=40)
    settings = services.get_all_settings(db)
    a = compact_analysis(services.analyze_instrument(inst, market=market, rf_pct=settings["risk_free_pct"]))
    a["news_7d"] = [{k: n[k] for k in ("title", "source", "published_at", "summary", "sentiment", "impact")}
                    for n in news_query.top_for_instrument(db, inst, days=7, limit=8)]
    a["owner_position"] = _position(db, market, inst.symbol)
    return a


def t_compare(db, market, args):
    rows, metrics = [], {}
    for sym in args["symbols"][:6]:
        inst = _resolve(db, market, sym)
        a = services.analyze_instrument(inst, market=market)
        t, f = a["technical"], a["fundamental"]
        m = f.get("metrics", {}) if f.get("kind") == "company" else {}
        metrics[inst.symbol] = m
        rows.append({"symbol": inst.symbol, "name": inst.name, "class": inst.asset_class,
                     "price": a["quote"].get("price"), "currency": a["quote"].get("currency"),
                     "returns_pct": t.get("returns_pct"), "volatility_pct": t.get("volatility_annual_pct"),
                     "technical": f"{t.get('stance')} ({t.get('score')})" if t.get("available") else None,
                     "pe": m.get("pe"), "pb": m.get("pb"), "ev_ebitda": m.get("ev_ebitda"), "roe_pct": m.get("roe_pct"),
                     "net_margin_pct": m.get("net_margin_pct"), "revenue_growth_pct": m.get("revenue_growth_pct"),
                     "debt_to_equity": m.get("debt_to_equity"), "dividend_yield_pct": m.get("dividend_yield_pct"),
                     "scores": f.get("scores"), "fair_value": (f.get("valuation") or {}).get("fair_value"),
                     "fund_returns": (a.get("fund") or {}).get("returns_pct")})
    first = next(iter(metrics))
    rel = fundamental.relative_valuation(metrics[first], {k: v for k, v in metrics.items() if k != first}) if metrics[first] else None
    return {"rows": rows, "relative_valuation_of_first": rel, "demo": market.demo}


def t_history(db, market, args):
    inst = _resolve(db, market, args["symbol"])
    period = args.get("period", "1y")
    h = market.history(inst.symbol, period)
    if h.empty:
        return {"symbol": inst.symbol, "available": False}
    c = h["close"]
    monthly = c.resample("ME").last().tail(24)
    return {"symbol": inst.symbol, "period": period, "start": str(c.index[0].date()), "end": str(c.index[-1].date()),
            "first": float(c.iloc[0]), "last": float(c.iloc[-1]), "return_pct": float((c.iloc[-1] / c.iloc[0] - 1) * 100),
            "high": float(c.max()), "low": float(c.min()), "max_drawdown_pct": technical.max_drawdown(c),
            "monthly_closes": {str(d.date()): float(v) for d, v in monthly.items()}, "demo": market.demo}


def t_news(db, market, args):
    ids = None
    if args.get("symbol"):
        inst = _resolve(db, market, args["symbol"])
        ids = [inst.id]
        if not news_query.recent(db, instrument_ids=ids, days=args.get("days", 7), limit=1):
            collect.collect(db, market, [inst], market_feeds=False)
            summarize.summarize_pending(db, limit=40)
    items = news_query.recent(db, instrument_ids=ids, days=args.get("days", 3), impact=args.get("impact"),
                              q=args.get("keyword"), limit=25)
    if not ids and not args.get("impact"):
        items.sort(key=lambda n: (news_query.IMPACT_RANK.get(n.impact, 3), -n.published_at.timestamp()))
    return {"news": [{k: v for k, v in news_query.news_dict(n).items() if k not in ("id", "scope")} for n in items[:25]]}


def t_overview(db, market, args):
    return market.macro_snapshot()


def t_portfolio(db, market, args):
    snap = services.portfolio_snapshot(db, market=market)
    if not snap["holdings"]:
        return {"holdings": [], "note": "The owner has not added any holdings yet (Portfolio page or CSV import)."}
    return snap


def t_risk(db, market, args):
    return services.portfolio_risk(db, market=market)


def t_tax(db, market, args):
    v = services.portfolio_tax(db, market=market)
    v.pop("rules", None)
    return v


def t_rebalance(db, market, args):
    return services.rebalance_plan(db, market=market)


def t_sale_tax(db, market, args):
    inst = _resolve(db, market, args["symbol"])
    if not inst.transactions:
        return {"error": f"The owner holds no {inst.symbol}."}
    q = market.quote(inst.symbol)
    rate = market.fx_rate(q.currency or inst.currency or "INR") or 1.0
    price = float(args.get("sell_price") or q.price or 0)
    pos = pf.build_position([services._inr_tx(t, rate) for t in services._tx_dicts(inst.transactions)])
    qty = min(float(args["quantity"]), pos.quantity)
    today = date.today()
    gains, remaining = [], qty
    cls_base = dict(name=inst.name, meta=inst.meta)
    for lot in pos.lots:
        if remaining <= 0:
            break
        take = min(lot.quantity, remaining)
        cost = take * lot.price + lot.fees * (take / lot.quantity)
        gains.append({"tax_class": tax.tax_class(inst.asset_class, inst.region, buy_date=lot.buy_date, **cls_base),
                      "buy_date": lot.buy_date, "sell_date": today, "gain": take * price * rate - cost})
        remaining -= take
    settings = services.get_all_settings(db)
    est = tax.estimate(gains, slab_rate=float(settings["tax_slab_pct"]) / 100,
                       exemption_used=float(settings["ltcg_exemption_used"] or 0))
    return {"symbol": inst.symbol, "quantity": qty, "sell_price": price, "proceeds_inr": qty * price * rate,
            "lots_used": [{"buy_date": str(g["buy_date"]), "gain_inr": g["gain"],
                           "long_term": tax.is_long_term(g["tax_class"], g["buy_date"], today)} for g in gains],
            "estimate": est}


def t_goal(db, market, args):
    return planning.goal_plan(target_today=args["target_amount_today"], years=args["years"],
                              inflation_pct=args.get("inflation_pct", 6.0), expected_return_pct=args.get("expected_return_pct", 11.0),
                              current_savings=args.get("current_savings", 0.0), step_up_pct=args.get("step_up_pct", 0.0))


def t_retirement(db, market, args):
    return planning.retirement_plan(
        current_age=args["current_age"], retire_age=args["retire_age"], monthly_expense_today=args["monthly_expense_today"],
        life_expectancy=args.get("life_expectancy", 85), inflation_pct=args.get("inflation_pct", 6.0),
        pre_return_pct=args.get("pre_return_pct", 11.0), post_return_pct=args.get("post_return_pct", 7.5),
        current_corpus=args.get("current_corpus", 0.0), step_up_pct=args.get("step_up_pct", 10.0))


def t_watchlist(db, market, args):
    insts = services.followed_instruments(db)
    quotes = market.quotes([i.symbol for i in insts]) if insts else {}
    return {"watchlist": [{"symbol": i.symbol, "name": i.name, "class": i.asset_class, "pinned": i.pinned,
                           "price": quotes[i.symbol].price if i.symbol in quotes else None,
                           "change_pct": quotes[i.symbol].change_pct if i.symbol in quotes else None} for i in insts]}


def t_follow(db, market, args):
    inst = _resolve(db, market, args["symbol"])
    inst.followed = True
    if args.get("pin"):
        inst.pinned = True
    return {"followed": inst.symbol, "pinned": inst.pinned}


HANDLERS: dict[str, Callable[[Session, MarketData, dict[str, Any]], Any]] = {
    "search_instruments": t_search, "analyze_instrument": t_analyze, "compare_instruments": t_compare,
    "get_price_history": t_history, "get_news": t_news, "get_market_overview": t_overview,
    "get_portfolio": t_portfolio, "get_portfolio_risk": t_risk, "get_tax_view": t_tax,
    "get_rebalance_plan": t_rebalance, "estimate_sale_tax": t_sale_tax, "plan_goal": t_goal,
    "plan_retirement": t_retirement, "get_watchlist": t_watchlist, "follow_instrument": t_follow,
}


def execute(db: Session, market: MarketData, name: str, args: Any) -> tuple[str, bool]:
    """Run one tool. Returns (content, is_error). Near-miss names (letter case) are accepted."""
    if name not in HANDLERS:
        match = next((n for n in HANDLERS if n.lower() == str(name).lower()), None)
        if match is None:
            return f"Unknown tool '{name}'. Available: {', '.join(HANDLERS)}", True
        name = match
    err = validate(name, args)
    if err:
        return err, True
    try:
        result = HANDLERS[name](db, market, args)
        db.flush()
        return _dump(result), False
    except LookupError as e:
        return str(e), True
    except Exception as e:  # keep the conversation going; the model can recover
        log.exception("tool %s failed", name)
        return f"Tool failed: {type(e).__name__}: {e}"[:500], True
