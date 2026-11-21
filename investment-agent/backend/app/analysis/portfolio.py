"""Portfolio maths: FIFO lots, P&L, XIRR, allocation, risk and rebalancing."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

# ---------- lots ----------


@dataclass
class Lot:
    quantity: float
    price: float
    buy_date: date
    fees: float = 0.0


@dataclass
class Position:
    quantity: float = 0.0
    lots: list[Lot] = field(default_factory=list)
    realized: list[dict[str, Any]] = field(default_factory=list)
    cash_flows: list[tuple[date, float]] = field(default_factory=list)  # negative = money in

    @property
    def cost(self) -> float:
        return sum(l.quantity * l.price + l.fees for l in self.lots)

    @property
    def avg_cost(self) -> float:
        return self.cost / self.quantity if self.quantity > 1e-12 else 0.0


def build_position(transactions: list[dict[str, Any]]) -> Position:
    """transactions: [{side, quantity, price, trade_date, fees}] for ONE instrument. FIFO matching."""
    pos = Position()
    for t in sorted(transactions, key=lambda t: (t["trade_date"], 0 if t["side"] == "buy" else 1)):
        q, px, d, fees = float(t["quantity"]), float(t["price"]), t["trade_date"], float(t.get("fees") or 0)
        if q <= 0:
            continue
        if t["side"] == "buy":
            pos.lots.append(Lot(q, px, d, fees))
            pos.quantity += q
            pos.cash_flows.append((d, -(q * px + fees)))
        else:
            remaining = min(q, pos.quantity)
            sell_fees_left = fees
            pos.cash_flows.append((d, q * px - fees))
            while remaining > 1e-12 and pos.lots:
                lot = pos.lots[0]
                take = min(lot.quantity, remaining)
                frac = take / lot.quantity
                buy_fee = lot.fees * frac
                sell_fee = fees * (take / q)
                pos.realized.append({
                    "quantity": take, "buy_date": lot.buy_date, "sell_date": d, "buy_price": lot.price,
                    "sell_price": px, "gain": take * (px - lot.price) - buy_fee - sell_fee,
                })
                sell_fees_left -= sell_fee
                lot.quantity -= take
                lot.fees -= buy_fee
                remaining -= take
                pos.quantity -= take
                if lot.quantity <= 1e-12:
                    pos.lots.pop(0)
    return pos


# ---------- XIRR ----------


def xirr(cash_flows: list[tuple[date, float]]) -> float | None:
    """Annualised internal rate of return for irregular cash flows. Returns a fraction (0.12 = 12%)."""
    flows = [(d, a) for d, a in cash_flows if abs(a) > 1e-9]
    if len(flows) < 2 or not (any(a < 0 for _, a in flows) and any(a > 0 for _, a in flows)):
        return None
    d0 = min(d for d, _ in flows)
    ts = [((d - d0).days / 365.0, a) for d, a in flows]
    if max(t for t, _ in ts) < 1 / 365:
        return None

    def npv(r: float) -> float:
        return sum(a / (1 + r) ** t for t, a in ts)

    def dnpv(r: float) -> float:
        return sum(-t * a / (1 + r) ** (t + 1) for t, a in ts)

    r = 0.1
    for _ in range(100):
        f, df = npv(r), dnpv(r)
        if df == 0:
            break
        nr = r - f / df
        if nr <= -0.9999 or math.isnan(nr):
            break
        if abs(nr - r) < 1e-9:
            return nr
        r = nr
    lo, hi = -0.9999, 100.0  # bisection fallback
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if abs(fm) < 1e-7:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


# ---------- allocation ----------

BUCKETS = ["equity_india", "equity_global", "debt", "gold", "crypto", "commodities", "cash"]
BUCKET_LABELS = {"equity_india": "Indian equity", "equity_global": "Global equity", "debt": "Debt",
                 "gold": "Gold & silver", "crypto": "Crypto", "commodities": "Other commodities", "cash": "Cash/FX",
                 "hybrid": "Hybrid funds"}

# Model allocations (percent) by risk profile. A starting point, not a rule.
PROFILE_TARGETS = {
    "conservative": {"equity_india": 25, "equity_global": 5, "debt": 55, "gold": 10, "crypto": 0, "commodities": 0, "cash": 5},
    "moderate": {"equity_india": 45, "equity_global": 12, "debt": 28, "gold": 10, "crypto": 2, "commodities": 0, "cash": 3},
    "aggressive": {"equity_india": 58, "equity_global": 17, "debt": 12, "gold": 8, "crypto": 5, "commodities": 0, "cash": 0},
}


def bucket_for(asset_class: str, region: str, name: str = "", meta: dict[str, Any] | None = None) -> str:
    n = (name or "").lower()
    meta = meta or {}
    if asset_class == "crypto":
        return "crypto"
    if asset_class == "mutual_fund":
        return meta.get("bucket") or "equity_india"
    if asset_class == "etf":
        if "gold" in n or "silver" in n:
            return "gold"
        if any(k in n for k in ("liquid", "bond", "gilt", "bharat bond", "g-sec", "treasury", "debt")):
            return "debt"
        return "equity_india" if region == "IN" else "equity_global"
    if asset_class == "commodity":
        return "gold" if any(k in n for k in ("gold", "silver")) else "commodities"
    if asset_class == "bond":
        return "debt"
    if asset_class == "forex":
        return "cash"
    return "equity_india" if region == "IN" else "equity_global"


def allocation(values_by_bucket: dict[str, float]) -> dict[str, float]:
    """Split hybrid funds 50/50 equity/debt and return percentages per bucket."""
    v = dict(values_by_bucket)
    h = v.pop("hybrid", 0.0)
    if h:
        v["equity_india"] = v.get("equity_india", 0.0) + h / 2
        v["debt"] = v.get("debt", 0.0) + h / 2
    total = sum(v.values())
    if total <= 0:
        return {}
    return {k: round(val / total * 100, 2) for k, val in sorted(v.items(), key=lambda kv: -kv[1]) if val > 0}


def rebalance(values_by_bucket: dict[str, float], profile: str, threshold_pts: float = 5.0) -> dict[str, Any]:
    targets = PROFILE_TARGETS.get(profile, PROFILE_TARGETS["moderate"])
    actual = allocation(values_by_bucket)
    total = sum(values_by_bucket.values())
    rows = []
    for b in BUCKETS:
        t, a = float(targets.get(b, 0)), float(actual.get(b, 0.0))
        if t == 0 and a == 0:
            continue
        drift = a - t
        rows.append({"bucket": b, "label": BUCKET_LABELS[b], "target_pct": t, "actual_pct": round(a, 2),
                     "drift_pts": round(drift, 2), "action_amount": round((t - a) / 100 * total, 2),
                     "needs_action": abs(drift) >= threshold_pts})
    return {"profile": profile, "total_value": round(total, 2), "rows": rows,
            "needs_rebalance": any(r["needs_action"] for r in rows)}


def concentration(weights: dict[str, float]) -> dict[str, Any]:
    if not weights:
        return {}
    w = np.array(list(weights.values()))
    w = w / w.sum()
    hhi = float((w**2).sum())
    top = sorted(weights.items(), key=lambda kv: -kv[1])[:5]
    return {"hhi": round(hhi, 3), "effective_holdings": round(1 / hhi, 1) if hhi else None,
            "top5_pct": round(sum(v for _, v in top) / sum(weights.values()) * 100, 1),
            "largest": top[0][0], "largest_pct": round(top[0][1] / sum(weights.values()) * 100, 1)}


# ---------- risk ----------


def portfolio_risk(weights: dict[str, float], closes: dict[str, pd.Series], *, benchmark: pd.Series | None = None,
                   rf_annual_pct: float = 6.5) -> dict[str, Any]:
    """Risk of the CURRENT weights applied to the past year of daily returns (all in local currency)."""
    syms = [s for s in weights if s in closes and len(closes[s]) > 30]
    if not syms:
        return {"available": False, "reason": "Not enough price history for the holdings."}
    frame = pd.concat({s: closes[s] for s in syms}, axis=1).sort_index()
    frame = frame.ffill().dropna(how="any")
    rets = frame.pct_change().dropna()
    if len(rets) < 30:
        return {"available": False, "reason": "Holdings have too little overlapping history."}
    w = np.array([weights[s] for s in syms], dtype=float)
    w = w / w.sum()
    pr = rets.values @ w
    pr_s = pd.Series(pr, index=rets.index)
    ppy = 252
    vol = float(pr_s.std() * math.sqrt(ppy))
    ann = float((1 + pr_s.mean()) ** ppy - 1)
    curve = (1 + pr_s).cumprod()
    mdd = float((curve / curve.cummax() - 1).min() * 100)
    out: dict[str, Any] = {
        "available": True, "days": int(len(pr_s)),
        "annual_return_pct": round(ann * 100, 2), "volatility_pct": round(vol * 100, 2),
        "sharpe": round((ann - rf_annual_pct / 100) / vol, 2) if vol else None,
        "max_drawdown_pct": round(mdd, 2),
        "var95_1d_pct": round(float(np.percentile(pr, 5) * 100), 2),
    }
    if benchmark is not None and len(benchmark) > 30:
        b = benchmark.pct_change().rename("b")
        j = pd.concat([pr_s.rename("p"), b], axis=1, join="inner").dropna()
        if len(j) > 30 and j["b"].var() > 0:
            out["beta"] = round(float(j["p"].cov(j["b"]) / j["b"].var()), 2)
            out["correlation_to_benchmark"] = round(float(j.corr().iloc[0, 1]), 2)
    top = sorted(syms, key=lambda s: -weights[s])[:8]
    if len(top) > 1:
        c = rets[top].corr().round(2)
        out["correlation"] = {"symbols": top, "matrix": c.values.tolist()}
        # risk contribution by holding
        cov = rets[syms].cov().values * ppy
        port_var = float(w @ cov @ w)
        if port_var > 0:
            contrib = w * (cov @ w) / port_var * 100
            out["risk_contribution_pct"] = {s: round(float(c_), 1) for s, c_ in zip(syms, contrib)}
    return out
