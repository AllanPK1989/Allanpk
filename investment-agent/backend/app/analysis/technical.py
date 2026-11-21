"""Technical analysis on a daily OHLCV frame (columns open/high/low/close/volume)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI: seeded with a simple average of the first n changes, then smoothed by 1/n."""
    values = close.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) <= n:
        return pd.Series(out, index=close.index)
    delta = np.diff(values)
    gains, losses = np.clip(delta, 0, None), np.clip(-delta, 0, None)
    avg_g, avg_l = gains[:n].mean(), losses[:n].mean()

    def value(g: float, l: float) -> float:
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100 - 100 / (1 + g / l)

    out[n] = value(avg_g, avg_l)
    for i in range(n, len(delta)):
        avg_g = (avg_g * (n - 1) + gains[i]) / n
        avg_l = (avg_l * (n - 1) + losses[i]) / n
        out[i + 1] = value(avg_g, avg_l)
    return pd.Series(out, index=close.index)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * sd, "lower": mid - k * sd})


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def max_drawdown(close: pd.Series) -> float:
    if close.empty:
        return 0.0
    peak = close.cummax()
    return float(((close / peak) - 1).min() * 100)


def annual_volatility(close: pd.Series, periods_per_year: int = 252) -> float | None:
    r = close.pct_change().dropna()
    if len(r) < 10:
        return None
    return float(r.std() * math.sqrt(periods_per_year) * 100)


def period_return(close: pd.Series, days: int) -> float | None:
    if close.empty:
        return None
    end = close.index[-1]
    past = close[close.index <= end - pd.Timedelta(days=days)]
    if past.empty:
        return None
    return float((close.iloc[-1] / past.iloc[-1] - 1) * 100)


def support_resistance(df: pd.DataFrame, window: int = 5, lookback: int = 180, max_levels: int = 3) -> dict[str, list[float]]:
    """Swing pivots from the last `lookback` bars, clustered within 1.5%."""
    d = df.tail(lookback)
    if len(d) < window * 2 + 1:
        return {"support": [], "resistance": []}
    highs, lows = d["high"].values, d["low"].values
    piv_hi, piv_lo = [], []
    for i in range(window, len(d) - window):
        if highs[i] == highs[i - window:i + window + 1].max():
            piv_hi.append(highs[i])
        if lows[i] == lows[i - window:i + window + 1].min():
            piv_lo.append(lows[i])

    def cluster(levels: list[float]) -> list[tuple[float, int]]:
        out: list[list[float]] = []
        for lv in sorted(levels):
            if out and abs(lv / np.mean(out[-1]) - 1) < 0.015:
                out[-1].append(lv)
            else:
                out.append([lv])
        return [(float(np.mean(c)), len(c)) for c in out]

    price = float(d["close"].iloc[-1])
    sup = sorted([c for c in cluster(piv_lo) if c[0] < price], key=lambda c: (-c[1], price - c[0]))[:max_levels]
    res = sorted([c for c in cluster(piv_hi) if c[0] > price], key=lambda c: (-c[1], c[0] - price))[:max_levels]
    return {"support": sorted([round(c[0], 2) for c in sup], reverse=True),
            "resistance": sorted([round(c[0], 2) for c in res])}


def _r(v: Any, nd: int = 2) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, nd)


def technical_summary(df: pd.DataFrame, *, periods_per_year: int = 252) -> dict[str, Any]:
    """Indicator values, plain-English signals and an overall score from -100 (bearish) to +100 (bullish)."""
    if df is None or len(df) < 30:
        return {"available": False, "reason": "Not enough price history (need 30+ days)."}
    close = df["close"]
    price = float(close.iloc[-1])
    s20, s50, s200 = sma(close, 20), sma(close, 50), sma(close, 200)
    e20 = ema(close, 20)
    r = rsi(close)
    m = macd(close)
    bb = bollinger(close)
    a = atr(df) if {"high", "low"} <= set(df.columns) else pd.Series(dtype=float)
    vol20 = df["volume"].rolling(20).mean() if "volume" in df.columns else None

    signals: list[dict[str, Any]] = []
    score = 0.0

    def sig(name: str, value: float, text: str):
        nonlocal score
        score += value
        signals.append({"name": name, "effect": "bullish" if value > 0 else "bearish" if value < 0 else "neutral",
                        "text": text})

    last = lambda s: (None if s is None or s.dropna().empty else float(s.dropna().iloc[-1]))  # noqa: E731
    v50, v200, v20 = last(s50), last(s200), last(s20)
    if v200:
        sig("Long-term trend", 20 if price > v200 else -20,
            f"Price is {'above' if price > v200 else 'below'} its 200-day average ({v200:,.2f}).")
    if v50:
        sig("Medium-term trend", 15 if price > v50 else -15,
            f"Price is {'above' if price > v50 else 'below'} its 50-day average ({v50:,.2f}).")
    if v50 and v200 and len(s50.dropna()) > 5 and len(s200.dropna()) > 5:
        cross_now = s50.iloc[-1] > s200.iloc[-1]
        recent = (s50 > s200).tail(20)
        if recent.nunique() > 1:
            sig("Moving-average cross", 15 if cross_now else -15,
                "Golden cross in the last 20 sessions (50-day crossed above 200-day)." if cross_now
                else "Death cross in the last 20 sessions (50-day crossed below 200-day).")
    rv = last(r)
    if rv is not None:
        if rv >= 70:
            sig("RSI(14)", -10, f"RSI {rv:.0f}: overbought, pullback risk is higher.")
        elif rv <= 30:
            sig("RSI(14)", 10, f"RSI {rv:.0f}: oversold, a bounce is more likely.")
        else:
            sig("RSI(14)", 5 if rv > 50 else -5, f"RSI {rv:.0f}: {'positive' if rv > 50 else 'weak'} momentum.")
    mh = m["hist"].dropna()
    if len(mh) > 2:
        crossed = (np.sign(mh.iloc[-1]) != np.sign(mh.iloc[-3]))
        txt = "MACD above its signal line" if mh.iloc[-1] > 0 else "MACD below its signal line"
        if crossed:
            txt += " (fresh crossover)"
        sig("MACD", 10 if mh.iloc[-1] > 0 else -10, txt + ".")
    bu, bl = last(bb["upper"]), last(bb["lower"])
    if bu and bl:
        if price > bu:
            sig("Bollinger bands", -5, "Closed above the upper band: stretched in the short term.")
        elif price < bl:
            sig("Bollinger bands", 5, "Closed below the lower band: stretched to the downside.")
    ret_1m, ret_3m = period_return(close, 30), period_return(close, 91)
    if ret_3m is not None:
        sig("3-month momentum", 10 if ret_3m > 5 else -10 if ret_3m < -5 else 0, f"{ret_3m:+.1f}% over 3 months.")
    if vol20 is not None and len(df) > 21 and last(vol20):
        vratio = float(df["volume"].iloc[-1]) / last(vol20) if last(vol20) else None
        if vratio and vratio > 1.8:
            up = close.iloc[-1] >= close.iloc[-2]
            sig("Volume", 5 if up else -5, f"Volume {vratio:.1f}x its 20-day average on an {'up' if up else 'down'} day.")

    score = max(-100.0, min(100.0, score))
    stance = "bullish" if score >= 25 else "bearish" if score <= -25 else "neutral"
    year = close[close.index >= close.index[-1] - pd.Timedelta(days=365)]
    levels = support_resistance(df) if {"high", "low"} <= set(df.columns) else {"support": [], "resistance": []}
    atr_v = last(a)
    return {
        "available": True,
        "price": _r(price),
        "as_of": str(close.index[-1].date()),
        "score": round(score),
        "stance": stance,
        "signals": signals,
        "indicators": {
            "sma20": _r(v20), "sma50": _r(v50), "sma200": _r(v200), "ema20": _r(last(e20)),
            "rsi14": _r(rv, 1), "macd": _r(last(m["macd"]), 3), "macd_signal": _r(last(m["signal"]), 3),
            "bb_upper": _r(bu), "bb_lower": _r(bl), "atr14": _r(atr_v),
            "atr_pct": _r(atr_v / price * 100 if atr_v else None),
        },
        "returns_pct": {
            "1w": _r(period_return(close, 7)), "1m": _r(ret_1m), "3m": _r(ret_3m),
            "6m": _r(period_return(close, 182)), "1y": _r(period_return(close, 365)),
        },
        "high_52w": _r(year.max()), "low_52w": _r(year.min()),
        "from_52w_high_pct": _r((price / year.max() - 1) * 100) if len(year) else None,
        "volatility_annual_pct": _r(annual_volatility(close.tail(252), periods_per_year)),
        "max_drawdown_1y_pct": _r(max_drawdown(year)),
        "levels": levels,
    }


def chart_series(df: pd.DataFrame, max_points: int = 400) -> dict[str, Any]:
    """Compact series for the frontend chart: close plus 50/200-day averages."""
    if df is None or df.empty:
        return {"dates": [], "close": [], "sma50": [], "sma200": []}
    close = df["close"]
    s50, s200 = sma(close, 50), sma(close, 200)
    step = max(1, len(df) // max_points)
    idx = list(range(len(df) - 1, -1, -step))[::-1]
    pick = lambda s: [None if pd.isna(s.iloc[i]) else round(float(s.iloc[i]), 4) for i in idx]  # noqa: E731
    return {"dates": [str(df.index[i].date()) for i in idx], "close": pick(close), "sma50": pick(s50),
            "sma200": pick(s200)}
