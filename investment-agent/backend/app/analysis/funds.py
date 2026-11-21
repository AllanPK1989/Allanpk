"""Mutual fund / ETF analysis from NAV or price history."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .technical import max_drawdown


def cagr(close: pd.Series, years: float) -> float | None:
    if close.empty:
        return None
    end = close.index[-1]
    past = close[close.index <= end - pd.Timedelta(days=round(365.25 * years))]
    if past.empty:
        return None
    return float(((close.iloc[-1] / past.iloc[-1]) ** (1 / years) - 1) * 100)


def rolling_returns(close: pd.Series, years: int = 1) -> dict[str, Any] | None:
    s = close.resample("D").last().ffill()
    window = int(365 * years)
    if len(s) <= window + 30:
        return None
    rr = (s / s.shift(window)) ** (1 / years) - 1
    rr = rr.dropna() * 100
    return {"years": years, "min": round(float(rr.min()), 2), "median": round(float(rr.median()), 2),
            "max": round(float(rr.max()), 2), "positive_pct": round(float((rr > 0).mean() * 100), 1),
            "samples": int(len(rr))}


def risk_stats(close: pd.Series, rf_annual_pct: float = 6.5, benchmark: pd.Series | None = None) -> dict[str, Any]:
    r = close.pct_change().dropna()
    if len(r) < 30:
        return {}
    ppy = 252
    vol = float(r.std() * math.sqrt(ppy))
    ann = float((1 + r.mean()) ** ppy - 1)
    rf = rf_annual_pct / 100
    downside = r[r < 0].std() * math.sqrt(ppy)
    out = {
        "volatility_pct": round(vol * 100, 2),
        "sharpe": round((ann - rf) / vol, 2) if vol else None,
        "sortino": round((ann - rf) / downside, 2) if downside and not np.isnan(downside) else None,
        "max_drawdown_pct": round(max_drawdown(close), 2),
    }
    if benchmark is not None and not benchmark.empty:
        b = benchmark.pct_change()
        joined = pd.concat([r, b], axis=1, join="inner").dropna()
        if len(joined) > 30:
            cov = np.cov(joined.iloc[:, 0], joined.iloc[:, 1])
            beta = cov[0, 1] / cov[1, 1] if cov[1, 1] else None
            bench_ann = (1 + joined.iloc[:, 1].mean()) ** ppy - 1
            port_ann = (1 + joined.iloc[:, 0].mean()) ** ppy - 1
            out["beta"] = round(float(beta), 2) if beta is not None else None
            if beta is not None:
                out["alpha_pct"] = round(float((port_ann - (rf + beta * (bench_ann - rf))) * 100), 2)
            out["correlation"] = round(float(joined.corr().iloc[0, 1]), 2)
    return out


def fund_summary(close: pd.Series, *, benchmark: pd.Series | None = None, rf_annual_pct: float = 6.5,
                 benchmark_name: str = "") -> dict[str, Any]:
    if close is None or len(close) < 30:
        return {"available": False, "reason": "Not enough NAV history."}
    out: dict[str, Any] = {
        "available": True,
        "nav": round(float(close.iloc[-1]), 4),
        "as_of": str(close.index[-1].date()),
        "returns_pct": {k: (round(v, 2) if v is not None else None) for k, v in
                        {"1y": cagr(close, 1), "3y_cagr": cagr(close, 3), "5y_cagr": cagr(close, 5)}.items()},
        "rolling_1y": rolling_returns(close, 1),
        "rolling_3y": rolling_returns(close, 3),
        "risk": risk_stats(close, rf_annual_pct, benchmark),
    }
    if benchmark is not None and not benchmark.empty:
        out["benchmark"] = {"name": benchmark_name,
                            "returns_pct": {k: (round(v, 2) if v is not None else None) for k, v in
                                            {"1y": cagr(benchmark, 1), "3y_cagr": cagr(benchmark, 3),
                                             "5y_cagr": cagr(benchmark, 5)}.items()}}
    return out
