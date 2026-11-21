"""Fundamental analysis and valuation from provider fundamentals (Yahoo `info` + statements)."""

from __future__ import annotations

import math
import statistics
from typing import Any

# Rough cost-of-equity / long-run growth assumptions by listing region (INR vs USD economies).
REGION_ASSUMPTIONS = {
    "IN": {"discount": 0.12, "terminal": 0.05, "default_growth": 0.09},
    "US": {"discount": 0.09, "terminal": 0.025, "default_growth": 0.06},
    "GLOBAL": {"discount": 0.10, "terminal": 0.03, "default_growth": 0.06},
}
FINANCIAL_SECTORS = {"financial services", "financial", "banks", "insurance"}


def _f(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _cagr(series: list[dict[str, Any]]) -> float | None:
    """series is newest-first [{'year','value'}]."""
    vals = [s["value"] for s in series if _f(s.get("value")) is not None]
    if len(vals) < 2 or vals[-1] <= 0 or vals[0] <= 0:
        return None
    years = len(vals) - 1
    return (vals[0] / vals[-1]) ** (1 / years) - 1


def _band(v: float | None, bands: list[tuple[float, int]], default: int = 50) -> int:
    """bands: [(upper_bound, score), ...] ascending; returns score of first band v falls under."""
    if v is None:
        return default
    for ub, sc in bands:
        if v < ub:
            return sc
    return bands[-1][1]


def _pct(v: float | None) -> float | None:
    return None if v is None else round(v * 100, 2)


def key_metrics(f: dict[str, Any]) -> dict[str, Any]:
    info = f.get("info") or {}
    price = _f(info.get("currentPrice"))
    de = _f(info.get("debtToEquity"))
    div_rate = _f(info.get("trailingAnnualDividendRate"))
    div_yield = (div_rate / price) if div_rate and price else _f(info.get("trailingAnnualDividendYield"))
    income, cash, bal = f.get("income") or {}, f.get("cashflow") or {}, f.get("balance") or {}
    op_inc = (income.get("Operating Income") or [{}])[0].get("value")
    int_exp = (income.get("Interest Expense") or [{}])[0].get("value")
    coverage = (abs(op_inc / int_exp) if op_inc and int_exp else None)
    return {
        "price": price,
        "market_cap": _f(info.get("marketCap")),
        "pe": _f(info.get("trailingPE")),
        "forward_pe": _f(info.get("forwardPE")),
        "pb": _f(info.get("priceToBook")),
        "ps": _f(info.get("priceToSalesTrailing12Months")),
        "ev_ebitda": _f(info.get("enterpriseToEbitda")),
        "peg": _f(info.get("trailingPegRatio")) or _f(info.get("pegRatio")),
        "dividend_yield_pct": _pct(div_yield),
        "roe_pct": _pct(_f(info.get("returnOnEquity"))),
        "roa_pct": _pct(_f(info.get("returnOnAssets"))),
        "net_margin_pct": _pct(_f(info.get("profitMargins"))),
        "operating_margin_pct": _pct(_f(info.get("operatingMargins"))),
        "revenue_growth_pct": _pct(_f(info.get("revenueGrowth"))),
        "earnings_growth_pct": _pct(_f(info.get("earningsGrowth"))),
        "revenue_cagr_pct": _pct(_cagr(income.get("Total Revenue") or [])),
        "net_income_cagr_pct": _pct(_cagr(income.get("Net Income") or [])),
        "fcf_cagr_pct": _pct(_cagr(cash.get("Free Cash Flow") or [])),
        # Yahoo reports debt/equity as a percentage (45 = 0.45x).
        "debt_to_equity": round(de / 100, 2) if de is not None else None,
        "current_ratio": _f(info.get("currentRatio")),
        "interest_coverage": round(coverage, 1) if coverage else None,
        "net_cash": (_f(info.get("totalCash")) or 0) - (_f(info.get("totalDebt")) or 0)
        if info.get("totalCash") is not None or info.get("totalDebt") is not None else None,
        "beta": _f(info.get("beta")),
        "analyst_target_mean": _f(info.get("targetMeanPrice")),
        "analyst_recommendation": info.get("recommendationKey"),
        "analyst_count": info.get("numberOfAnalystOpinions"),
        "equity": (bal.get("Stockholders Equity") or [{}])[0].get("value"),
    }


def scores(m: dict[str, Any], sector: str = "") -> dict[str, int]:
    financial = sector.lower() in FINANCIAL_SECTORS
    value = _band(m.get("pe"), [(0, 20), (12, 90), (18, 75), (25, 55), (40, 35), (1e9, 15)])
    if m.get("pe") is None and m.get("pb") is not None:
        value = _band(m["pb"], [(1, 85), (2, 70), (4, 50), (8, 35), (1e9, 20)])
    if m.get("peg") is not None and 0 < m["peg"] < 1:
        value = min(100, value + 10)
    quality = _band(m.get("roe_pct"), [(5, 20), (10, 40), (15, 55), (20, 70), (1e9, 85)])
    if m.get("net_margin_pct") is not None and m["net_margin_pct"] > 20:
        quality = min(100, quality + 10)
    g_parts = [x for x in (m.get("revenue_growth_pct"), m.get("earnings_growth_pct"), m.get("revenue_cagr_pct"))
               if x is not None]
    g = statistics.mean(g_parts) if g_parts else None
    growth = _band(g, [(0, 20), (5, 40), (10, 55), (20, 70), (1e9, 85)])
    if financial:
        health = 60
    else:
        health = _band(m.get("debt_to_equity"), [(0.3, 85), (1.0, 65), (2.0, 45), (1e9, 25)])
        if m.get("current_ratio") is not None and m["current_ratio"] < 1:
            health = max(0, health - 10)
        if m.get("interest_coverage") is not None and m["interest_coverage"] < 3:
            health = max(0, health - 15)
    overall = round(0.3 * value + 0.3 * quality + 0.2 * growth + 0.2 * health)
    return {"value": value, "quality": quality, "growth": growth, "health": health, "overall": overall}


def dcf(f: dict[str, Any], region: str = "IN", *, years: int = 10) -> dict[str, Any]:
    """Two-stage free-cash-flow DCF with bear/base/bull scenarios. Returns per-share fair values."""
    info = f.get("info") or {}
    fcf_series = [s["value"] for s in (f.get("cashflow") or {}).get("Free Cash Flow", []) if _f(s.get("value"))]
    base_fcf = _f(info.get("freeCashflow"))
    if fcf_series:
        recent = [v for v in fcf_series[:3]]
        avg = statistics.mean(recent)
        base_fcf = avg if avg > 0 else base_fcf
    shares = _f(info.get("sharesOutstanding"))
    price = _f(info.get("currentPrice"))
    if not base_fcf or base_fcf <= 0 or not shares:
        return {"available": False, "reason": "No positive free cash flow or share count, so a cash-flow DCF does not apply."}
    fin_ccy, ccy = info.get("financialCurrency"), info.get("currency")
    if fin_ccy and ccy and fin_ccy != ccy:
        return {"available": False, "reason": f"Financials are in {fin_ccy} but the share trades in {ccy}."}
    a = REGION_ASSUMPTIONS.get(region, REGION_ASSUMPTIONS["GLOBAL"])
    hist_g = [x for x in (_cagr((f.get("income") or {}).get("Total Revenue") or []),
                          _cagr((f.get("cashflow") or {}).get("Free Cash Flow") or []),
                          _f(info.get("earningsGrowth")), _f(info.get("revenueGrowth"))) if x is not None]
    g0 = statistics.median(hist_g) if hist_g else a["default_growth"]
    g0 = max(0.0, min(g0, 0.20))
    cash, debt = _f(info.get("totalCash")) or 0.0, _f(info.get("totalDebt")) or 0.0

    def run(g: float, r: float, tg: float) -> float:
        pv, fcf = 0.0, base_fcf
        for t in range(1, years + 1):
            gt = g + (tg - g) * (t - 1) / (years - 1)  # fade linearly to terminal growth
            fcf *= 1 + gt
            pv += fcf / (1 + r) ** t
        tv = fcf * (1 + tg) / (r - tg)
        pv += tv / (1 + r) ** years
        return (pv + cash - debt) / shares

    base = run(g0, a["discount"], a["terminal"])
    bear = run(g0 * 0.5, a["discount"] + 0.01, a["terminal"] - 0.005)
    bull = run(min(g0 * 1.3, 0.25), a["discount"] - 0.01, a["terminal"])
    out = {
        "available": True, "method": "Two-stage FCF DCF",
        "assumptions": {"base_fcf": round(base_fcf), "growth_start_pct": round(g0 * 100, 1),
                        "discount_rate_pct": a["discount"] * 100, "terminal_growth_pct": a["terminal"] * 100,
                        "years": years, "net_cash": round(cash - debt)},
        "fair_value": {"bear": round(bear, 2), "base": round(base, 2), "bull": round(bull, 2)},
    }
    if price:
        out["upside_pct"] = round((base / price - 1) * 100, 1)
    return out


def pb_roe_value(f: dict[str, Any], region: str = "IN") -> dict[str, Any]:
    """Justified price-to-book for banks/financials: P/B = (ROE - g) / (r - g)."""
    info = f.get("info") or {}
    roe, bvps, price = _f(info.get("returnOnEquity")), _f(info.get("bookValue")), _f(info.get("currentPrice"))
    pb = _f(info.get("priceToBook"))
    if bvps is None and price and pb:
        bvps = price / pb
    if not roe or not bvps:
        return {"available": False, "reason": "Needs return on equity and book value per share."}
    a = REGION_ASSUMPTIONS.get(region, REGION_ASSUMPTIONS["GLOBAL"])
    r, g = a["discount"], min(a["terminal"] + 0.02, a["discount"] - 0.02)

    def val(roe_x: float, r_x: float) -> float:
        return bvps * max(roe_x - g, 0) / (r_x - g)

    out = {"available": True, "method": "Justified P/B from ROE (for financials)",
           "assumptions": {"roe_pct": round(roe * 100, 1), "book_value_per_share": round(bvps, 2),
                           "cost_of_equity_pct": r * 100, "growth_pct": round(g * 100, 1)},
           "fair_value": {"bear": round(val(roe * 0.85, r + 0.01), 2), "base": round(val(roe, r), 2),
                          "bull": round(val(roe * 1.1, r - 0.01), 2)}}
    if price:
        out["upside_pct"] = round((out["fair_value"]["base"] / price - 1) * 100, 1)
    return out


def analyze(f: dict[str, Any], *, region: str = "IN", asset_class: str = "stock") -> dict[str, Any]:
    info = f.get("info") or {}
    if asset_class in ("mutual_fund", "etf"):
        return {"available": True, "kind": "fund", "name": info.get("longName"),
                "category": info.get("category"), "fund_house": info.get("fundFamily"),
                "expense_ratio_pct": _f(info.get("netExpenseRatio") or info.get("annualReportExpenseRatio")),
                "aum": _f(info.get("totalAssets")), "bucket": info.get("bucket"),
                "note": "Funds are judged on returns, risk, costs and category fit; see the fund analysis."}
    if asset_class != "stock":
        return {"available": False, "reason": f"Company fundamentals don't apply to {asset_class.replace('_', ' ')}."}
    if not info:
        return {"available": False, "reason": "No fundamentals returned by the data source."}
    sector = info.get("sector") or ""
    m = key_metrics(f)
    financial = sector.lower() in FINANCIAL_SECTORS
    valuation = pb_roe_value(f, region) if financial else dcf(f, region)
    return {
        "available": True, "kind": "company",
        "name": info.get("longName") or info.get("shortName"), "sector": sector, "industry": info.get("industry"),
        "summary": (info.get("longBusinessSummary") or "")[:800],
        "metrics": m, "scores": scores(m, sector), "valuation": valuation,
        "next_earnings": f.get("next_earnings"), "demo": bool(f.get("demo")),
    }


def relative_valuation(target: dict[str, Any], peers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compare a company's metrics with the median of its peers. Inputs are key_metrics() dicts."""
    out: dict[str, Any] = {"peers": list(peers), "metrics": {}}
    for k, label, lower_is_cheaper in (("pe", "P/E", True), ("pb", "P/B", True), ("ev_ebitda", "EV/EBITDA", True),
                                       ("roe_pct", "ROE %", False), ("net_margin_pct", "Net margin %", False),
                                       ("revenue_growth_pct", "Revenue growth %", False)):
        vals = [p.get(k) for p in peers.values() if p.get(k) is not None and p.get(k) > 0]
        t = target.get(k)
        if not vals or t is None:
            continue
        med = statistics.median(vals)
        diff = (t / med - 1) * 100 if med else None
        out["metrics"][k] = {"label": label, "company": round(t, 2), "peer_median": round(med, 2),
                             "difference_pct": round(diff, 1) if diff is not None else None,
                             "reading": (("cheaper" if diff < 0 else "pricier") if lower_is_cheaper
                                         else ("better" if diff > 0 else "weaker")) if diff is not None else None}
    return out
