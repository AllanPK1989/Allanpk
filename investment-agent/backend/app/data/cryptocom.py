"""Crypto prices from the Crypto.com Exchange public API (no key).

Symbols look like "CRYPTO:BTC_USDT". The REST API uses short keys (a = last, c = 24h change...);
the parser also accepts long names in case the format is expanded.
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
BASE = "https://api.crypto.com/exchange/v1/public"

COIN_NAMES = {
    "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "XRP", "BNB": "BNB", "ADA": "Cardano",
    "DOGE": "Dogecoin", "DOT": "Polkadot", "AVAX": "Avalanche", "LINK": "Chainlink", "MATIC": "Polygon",
    "POL": "Polygon", "LTC": "Litecoin", "TRX": "TRON", "TON": "Toncoin", "SHIB": "Shiba Inu", "CRO": "Cronos",
    "USDC": "USD Coin", "ATOM": "Cosmos", "NEAR": "NEAR Protocol", "UNI": "Uniswap", "SUI": "Sui",
}


def pair_of(symbol: str) -> str:
    return symbol.split(":", 1)[1] if symbol.startswith("CRYPTO:") else symbol


def _f(d: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        if d.get(k) not in (None, ""):
            try:
                return float(d[k])
            except (TypeError, ValueError):
                pass
    return None


def parse_ticker(symbol: str, t: dict[str, Any]) -> Quote:
    last = _f(t, "a", "last")
    change = _f(t, "c", "change")  # 24h change as a fraction, e.g. -0.0517
    prev = last / (1 + change) if last is not None and change is not None and change > -1 else None
    ts = t.get("t") or t.get("timestamp")
    if isinstance(ts, (int, float)):
        as_of = datetime.fromtimestamp(ts / 1000, timezone.utc)
    elif isinstance(ts, str):
        as_of = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        as_of = datetime.now(timezone.utc)
    return Quote(symbol=symbol, price=last, prev_close=prev, currency="USD", day_high=_f(t, "h", "high"),
                 day_low=_f(t, "l", "low"), volume=_f(t, "vv", "volume_value"), as_of=as_of)


def parse_candles(rows: list[dict[str, Any]]) -> pd.DataFrame:
    recs = []
    for r in rows:
        ts = r.get("t") or r.get("timestamp")
        if isinstance(ts, (int, float)):
            d = datetime.fromtimestamp(ts / 1000, timezone.utc)
        elif isinstance(ts, str):
            d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            continue
        recs.append({"date": d.replace(tzinfo=None), "open": _f(r, "o", "open"), "high": _f(r, "h", "high"),
                     "low": _f(r, "l", "low"), "close": _f(r, "c", "close"), "volume": _f(r, "v", "volume") or 0.0})
    if not recs:
        return empty_history()
    df = pd.DataFrame(recs).set_index("date").sort_index()
    df.index = pd.DatetimeIndex(df.index, name="date").normalize()
    return df[~df.index.duplicated(keep="last")].dropna(subset=["close"]).astype(float)


class CryptoComProvider:
    def _get(self, path: str, **params) -> dict[str, Any]:
        r = http.client().get(f"{BASE}/{path}", params=params)
        r.raise_for_status()
        body = r.json()
        if body.get("code") not in (0, None):
            raise ValueError(f"crypto.com error code {body.get('code')}")
        return body.get("result") or {}

    @ttl_cache(6 * 3600)
    def _spot_pairs(self) -> list[dict[str, Any]]:
        try:
            data = self._get("get-instruments").get("data") or []
        except Exception as e:
            log.warning("crypto.com instruments failed: %s", e)
            return []
        return [d for d in data if (d.get("inst_type") or "").upper() == "CCY_PAIR"]

    def search(self, query: str) -> list[SearchResult]:
        q = query.strip().upper()
        if not q:
            return []
        # Match by ticker or by well-known coin name.
        bases = {b for b, n in COIN_NAMES.items() if q in n.upper() or q == b}
        pairs = self._spot_pairs()
        out = []
        for p in pairs:
            base, quote = (p.get("base_ccy") or "").upper(), (p.get("quote_ccy") or "").upper()
            if quote not in ("USDT", "USD") or not (base in bases or base == q):
                continue
            sym = p.get("symbol") or f"{base}_{quote}"
            out.append(SearchResult(symbol=f"CRYPTO:{sym}", name=f"{COIN_NAMES.get(base, base)} ({base}/{quote})",
                                    asset_class="crypto", region="GLOBAL", exchange="Crypto.com", currency="USD",
                                    meta={"base": base}))
        if not out and not pairs and (bases or len(q) <= 6):
            # instruments list unavailable: offer the USDT pair for known coins
            for b in sorted(bases or {q}):
                out.append(SearchResult(symbol=f"CRYPTO:{b}_USDT", name=f"{COIN_NAMES.get(b, b)} ({b}/USDT)",
                                        asset_class="crypto", region="GLOBAL", exchange="Crypto.com", currency="USD",
                                        meta={"base": b}))
        out.sort(key=lambda r: (0 if r.symbol.endswith("_USDT") else 1, r.symbol))
        return out[:6]

    @ttl_cache(60)
    def quote(self, symbol: str) -> Quote:
        try:
            data = self._get("get-tickers", instrument_name=pair_of(symbol)).get("data") or []
        except Exception as e:
            log.warning("crypto.com ticker %s failed: %s", symbol, e)
            return Quote(symbol=symbol, price=None, currency="USD")
        return parse_ticker(symbol, data[0]) if data else Quote(symbol=symbol, price=None, currency="USD")

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: self.quote(s) for s in symbols}

    @ttl_cache(900)
    def history(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        from .types import PERIOD_DAYS

        count = min(PERIOD_DAYS.get(period, 366), 1500)
        try:
            data = self._get("get-candlestick", instrument_name=pair_of(symbol), timeframe="1D", count=count)
        except Exception as e:
            log.warning("crypto.com candles %s failed: %s", symbol, e)
            return empty_history()
        return parse_candles(data.get("data") or [])

    def fundamentals(self, symbol: str) -> dict[str, Any]:
        base = pair_of(symbol).split("_")[0]
        return {"symbol": symbol, "info": {"longName": COIN_NAMES.get(base, base), "base": base},
                "income": {}, "cashflow": {}, "balance": {}}

    def news(self, symbol: str) -> list[RawNews]:
        return []
