"""One entry point for all market data. Routes each symbol to the right provider."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

import pandas as pd

from ..config import get_settings
from . import fred
from .types import Quote, RawNews, SearchResult

log = logging.getLogger(__name__)

# What the market overview shows. symbol -> (label, group)
MACRO_TICKERS: dict[str, tuple[str, str]] = {
    "^NSEI": ("Nifty 50", "India"),
    "^BSESN": ("Sensex", "India"),
    "^NSEBANK": ("Bank Nifty", "India"),
    "^INDIAVIX": ("India VIX", "India"),
    "^GSPC": ("S&P 500", "Global"),
    "^IXIC": ("Nasdaq", "Global"),
    "^DJI": ("Dow Jones", "Global"),
    "^FTSE": ("FTSE 100", "Global"),
    "^N225": ("Nikkei 225", "Global"),
    "^HSI": ("Hang Seng", "Global"),
    "^VIX": ("US VIX", "Global"),
    "USDINR=X": ("USD/INR", "Currencies"),
    "EURINR=X": ("EUR/INR", "Currencies"),
    "GC=F": ("Gold $/oz", "Commodities"),
    "SI=F": ("Silver $/oz", "Commodities"),
    "CL=F": ("WTI crude $", "Commodities"),
    "BZ=F": ("Brent crude $", "Commodities"),
    "^TNX": ("US 10Y yield %", "Rates"),
    "CRYPTO:BTC_USDT": ("Bitcoin $", "Crypto"),
    "CRYPTO:ETH_USDT": ("Ethereum $", "Crypto"),
}
FRED_SERIES = ["DFF", "DGS10", "CPIAUCSL", "INDCPIALLMINMEI", "INDIRLTLT01STM"]


class MarketData:
    def __init__(self, demo: bool = False):
        self.demo = demo
        if demo:
            from .demo import DemoProvider

            self._demo = DemoProvider()
        else:
            from .cryptocom import CryptoComProvider
            from .mfapi import MfapiProvider
            from .yahoo import YahooProvider

            self._yahoo, self._mf, self._crypto = YahooProvider(), MfapiProvider(), CryptoComProvider()

    def _p(self, symbol: str):
        if self.demo:
            return self._demo
        if symbol.startswith("MF:"):
            return self._mf
        if symbol.startswith("CRYPTO:"):
            return self._crypto
        return self._yahoo

    # ---------- search ----------
    def search(self, query: str) -> list[SearchResult]:
        query = query.strip()[:80]
        if not query:
            return []
        if self.demo:
            return self._demo.search(query)
        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = [ex.submit(p.search, query) for p in (self._yahoo, self._mf, self._crypto)]
            groups = []
            for f in futs:
                try:
                    groups.append(f.result(timeout=20))
                except Exception as e:  # pragma: no cover - provider already logs
                    log.warning("search provider failed: %s", e)
                    groups.append([])
        yahoo, mf, crypto = groups
        # Yahoo first (stocks/ETFs/indices), then crypto pairs, then mutual funds.
        seen, out = set(), []
        for r in yahoo[:10] + crypto[:4] + mf[:10]:
            if r.symbol not in seen:
                seen.add(r.symbol)
                out.append(r)
        q = query.upper()
        out.sort(key=lambda r: 0 if r.symbol.upper().split(":")[-1].split(".")[0] == q else 1)
        return out

    # ---------- prices ----------
    def quote(self, symbol: str) -> Quote:
        return self._p(symbol).quote(symbol)

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        if self.demo:
            return self._demo.quotes(symbols)
        groups: dict[Any, list[str]] = {}
        for s in symbols:
            groups.setdefault(self._p(s), []).append(s)
        out: dict[str, Quote] = {}
        for provider, syms in groups.items():
            try:
                out.update(provider.quotes(syms))
            except Exception as e:
                log.warning("quotes failed: %s", e)
        return out

    def history(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        return self._p(symbol).history(symbol, period)

    def fundamentals(self, symbol: str) -> dict[str, Any]:
        try:
            return self._p(symbol).fundamentals(symbol)
        except Exception as e:
            log.warning("fundamentals %s failed: %s", symbol, e)
            return {"symbol": symbol, "info": {}, "income": {}, "cashflow": {}, "balance": {}}

    def news(self, symbol: str) -> list[RawNews]:
        try:
            return self._p(symbol).news(symbol)
        except Exception as e:
            log.info("provider news %s failed: %s", symbol, e)
            return []

    # ---------- FX ----------
    def fx_rate(self, from_ccy: str, to_ccy: str = "INR") -> float | None:
        from_ccy, to_ccy = (from_ccy or to_ccy).upper(), to_ccy.upper()
        if from_ccy == to_ccy:
            return 1.0
        if from_ccy == "USDT":
            from_ccy = "USD"
        if from_ccy == "GBX":  # London pence
            r = self.fx_rate("GBP", to_ccy)
            return r / 100 if r else None
        q = self.quote(f"{from_ccy}{to_ccy}=X")
        return q.price

    def fx_rates(self, currencies: set[str], to_ccy: str = "INR") -> dict[str, float]:
        out = {}
        for c in currencies:
            r = self.fx_rate(c, to_ccy)
            if r:
                out[(c or to_ccy).upper()] = r
        return out

    # ---------- macro ----------
    def macro_snapshot(self) -> dict[str, Any]:
        quotes = self.quotes(list(MACRO_TICKERS))
        rows = []
        for sym, (label, group) in MACRO_TICKERS.items():
            q = quotes.get(sym)
            rows.append({"symbol": sym, "label": label, "group": group,
                         "price": q.price if q else None, "change_pct": q.change_pct if q else None})
        rates = []
        if not self.demo:
            with ThreadPoolExecutor(max_workers=5) as ex:
                for r in ex.map(fred.latest, FRED_SERIES):
                    if r:
                        rates.append(r)
        else:
            rates = [
                {"id": "DFF", "label": "US Fed funds rate %", "value": 4.33, "date": "demo"},
                {"id": "CPIAUCSL", "label": "US CPI inflation % YoY", "value": 2.9, "date": "demo"},
                {"id": "INDCPIALLMINMEI", "label": "India CPI inflation % YoY", "value": 3.6, "date": "demo"},
            ]
        return {"markets": rows, "rates": rates, "demo": self.demo}


@lru_cache
def get_market() -> MarketData:
    return MarketData(demo=get_settings().data_mode == "demo")
