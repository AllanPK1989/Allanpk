"""Indian mutual funds via mfapi.in (free mirror of AMFI's daily NAV data).

Symbols look like "MF:122639" (AMFI scheme code).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from . import http
from .cache import ttl_cache
from .types import Quote, RawNews, SearchResult, empty_history

log = logging.getLogger(__name__)
BASE = "https://api.mfapi.in/mf"


def code_of(symbol: str) -> str:
    return symbol.split(":", 1)[1] if symbol.startswith("MF:") else symbol


def bucket_for_category(category: str) -> str:
    """Map an AMFI scheme category to an allocation bucket."""
    c = (category or "").lower()
    if "gold" in c or "silver" in c:
        return "gold"
    if any(k in c for k in ("overseas", "international", "global", "us equity", "nasdaq")):
        return "equity_global"
    if any(k in c for k in ("debt", "liquid", "gilt", "money market", "overnight", "bond", "duration",
                            "credit risk", "banking and psu", "floater", "corporate")):
        return "debt"
    if any(k in c for k in ("hybrid", "balanced", "asset allocation", "arbitrage", "equity savings")):
        return "hybrid"
    return "equity_india"


def is_equity_oriented(category: str) -> bool:
    """For tax: equity-oriented funds (>=65% domestic equity)."""
    c = (category or "").lower()
    if bucket_for_category(c) == "equity_india":
        return True
    return any(k in c for k in ("arbitrage", "equity savings", "aggressive hybrid", "balanced advantage", "dynamic asset"))


def parse_nav_history(payload: dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("data") or []
    if not rows:
        return empty_history()
    recs = []
    for r in rows:
        try:
            d = datetime.strptime(r["date"], "%d-%m-%Y")
            v = float(r["nav"])
        except (KeyError, ValueError, TypeError):
            continue
        recs.append((d, v))
    if not recs:
        return empty_history()
    s = pd.Series({d: v for d, v in recs}).sort_index()
    df = pd.DataFrame({"open": s, "high": s, "low": s, "close": s, "volume": 0.0})
    df.index = pd.DatetimeIndex(df.index, name="date")
    return df


class MfapiProvider:
    @ttl_cache(3600)
    def search(self, query: str) -> list[SearchResult]:
        try:
            r = http.client().get(f"{BASE}/search", params={"q": query})
            r.raise_for_status()
            items = r.json() or []
        except Exception as e:
            log.warning("mfapi search failed: %s", e)
            return []
        # Prefer Direct-Growth plans first (lower costs), then the rest.
        def rank(it):
            n = (it.get("schemeName") or "").lower()
            return (0 if "direct" in n else 1, 0 if "growth" in n else 1, n)

        out = []
        for it in sorted(items, key=rank)[:15]:
            code, name = it.get("schemeCode"), it.get("schemeName")
            if code and name:
                out.append(SearchResult(symbol=f"MF:{code}", name=name, asset_class="mutual_fund", region="IN",
                                        exchange="AMFI", currency="INR"))
        return out

    @ttl_cache(3 * 3600)
    def _payload(self, code: str) -> dict[str, Any]:
        r = http.client().get(f"{BASE}/{code}")
        r.raise_for_status()
        data = r.json()
        if data.get("status") not in (None, "SUCCESS"):
            raise ValueError(f"mfapi status {data.get('status')}")
        return data

    def history(self, symbol: str, period: str = "5y") -> pd.DataFrame:
        try:
            df = parse_nav_history(self._payload(code_of(symbol)))
        except Exception as e:
            log.warning("mfapi history %s failed: %s", symbol, e)
            return empty_history()
        from .types import PERIOD_DAYS

        days = PERIOD_DAYS.get(period, 366)
        if len(df):
            df = df[df.index >= df.index[-1] - pd.Timedelta(days=days)]
        return df

    def quote(self, symbol: str) -> Quote:
        df = self.history(symbol, "1mo")
        if df.empty:
            return Quote(symbol=symbol, price=None, currency="INR")
        closes = df["close"]
        return Quote(symbol=symbol, price=float(closes.iloc[-1]),
                     prev_close=float(closes.iloc[-2]) if len(closes) > 1 else None, currency="INR",
                     as_of=closes.index[-1].to_pydatetime().replace(tzinfo=timezone.utc))

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: self.quote(s) for s in symbols}

    def fundamentals(self, symbol: str) -> dict[str, Any]:
        try:
            meta = self._payload(code_of(symbol)).get("meta") or {}
        except Exception as e:
            log.warning("mfapi meta %s failed: %s", symbol, e)
            meta = {}
        category = meta.get("scheme_category", "")
        return {
            "symbol": symbol,
            "info": {
                "longName": meta.get("scheme_name"),
                "fundFamily": meta.get("fund_house"),
                "category": category,
                "schemeType": meta.get("scheme_type"),
                "isin": meta.get("isin_growth") or meta.get("isin_div_reinvestment"),
                "bucket": bucket_for_category(category),
                "equityOriented": is_equity_oriented(category),
            },
            "income": {}, "cashflow": {}, "balance": {},
        }

    def news(self, symbol: str) -> list[RawNews]:
        return []
