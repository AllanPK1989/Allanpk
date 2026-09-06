"""Live quote sourcing.

The app never calls a quote API from the browser — cross-origin rules make that
unreliable and a published page's content policy forbids it outright. Fetching
happens here, server-side, behind a cache.

Two independent sources are tried in order. If the first is unreachable or has
changed its shape, the second answers, and the response always says which one
served each quote so a silent downgrade is visible rather than hidden.
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import time
from dataclasses import dataclass, field, asdict

import httpx

log = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


@dataclass
class Quote:
    ticker: str
    price: float
    prev_close: float | None = None
    low52: float | None = None
    high52: float | None = None
    closes: list[float] = field(default_factory=list)   # daily closes, oldest first
    source: str = ""
    fetched_at: float = 0.0

    @property
    def day_pct(self) -> float | None:
        if not self.prev_close:
            return None
        return (self.price / self.prev_close - 1) * 100

    def to_dict(self) -> dict:
        d = asdict(self)
        d["day_pct"] = self.day_pct
        d["closes"] = self.closes[-260:]
        return d


class Provider:
    name = "base"

    async def fetch(self, client: httpx.AsyncClient,
                    tickers: list[str]) -> dict[str, Quote]:
        raise NotImplementedError


class YahooProvider(Provider):
    """Per-ticker chart endpoint. Gives a full year of closes, so the moving
    averages and RSI are computed from real history rather than estimated."""
    name = "yahoo"
    URL = "https://query1.finance.yahoo.com/v8/finance/chart/{t}"

    async def _one(self, client: httpx.AsyncClient, t: str) -> Quote | None:
        r = await client.get(self.URL.format(t=t),
                             params={"range": "1y", "interval": "1d"},
                             headers={"User-Agent": UA, "Accept": "application/json"})
        r.raise_for_status()
        result = (r.json().get("chart") or {}).get("result") or []
        if not result:
            return None
        res = result[0]
        meta = res.get("meta") or {}
        quote = ((res.get("indicators") or {}).get("quote") or [{}])[0]
        closes = [c for c in (quote.get("close") or []) if isinstance(c, (int, float))]
        price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
        if price is None:
            return None
        return Quote(ticker=t, price=float(price),
                     prev_close=meta.get("chartPreviousClose"),
                     low52=meta.get("fiftyTwoWeekLow"),
                     high52=meta.get("fiftyTwoWeekHigh"),
                     closes=closes, source=self.name, fetched_at=time.time())

    async def fetch(self, client, tickers):
        async def guarded(t):
            try:
                return await self._one(client, t)
            except Exception as e:                       # noqa: BLE001
                log.debug("yahoo %s: %s", t, e)
                return None
        results = await asyncio.gather(*(guarded(t) for t in tickers))
        return {q.ticker: q for q in results if q}


class StooqProvider(Provider):
    """CSV, many symbols per request, no key. Last-resort price only — it
    carries no 52-week range and no history, so indicators fall back to
    whatever the reference data already holds."""
    name = "stooq"
    URL = "https://stooq.com/q/l/"

    async def fetch(self, client, tickers):
        out: dict[str, Quote] = {}
        for i in range(0, len(tickers), 20):
            batch = tickers[i:i + 20]
            syms = ",".join(f"{t.lower()}.us" for t in batch)
            try:
                r = await client.get(self.URL,
                                     params={"s": syms, "f": "sd2t2ohlc", "h": "", "e": "csv"},
                                     headers={"User-Agent": UA})
                r.raise_for_status()
                for row in csv.DictReader(io.StringIO(r.text)):
                    sym = (row.get("Symbol") or "").split(".")[0].upper()
                    close = row.get("Close")
                    openp = row.get("Open")
                    if not sym or close in (None, "", "N/D"):
                        continue
                    out[sym] = Quote(ticker=sym, price=float(close),
                                     prev_close=float(openp) if openp not in (None, "", "N/D") else None,
                                     source=self.name, fetched_at=time.time())
            except Exception as e:                       # noqa: BLE001
                log.debug("stooq batch %s: %s", batch, e)
        return out


class QuoteService:
    """Provider chain plus a TTL cache.

    On a total outage the last good quotes are served rather than nothing, and
    their age is reported so the page can show that they are stale.
    """

    def __init__(self, providers: list[Provider] | None = None, ttl: float = 60.0):
        self.providers = providers if providers is not None else [YahooProvider(), StooqProvider()]
        self.ttl = ttl
        self._cache: dict[str, Quote] = {}
        self._lock = asyncio.Lock()
        self.last_error: str | None = None
        self.last_attempt: float = 0.0

    def _fresh(self, tickers: list[str]) -> bool:
        if not self._cache:
            return False
        now = time.time()
        have = [self._cache[t] for t in tickers if t in self._cache]
        if len(have) < len(tickers) * 0.6:
            return False
        return all(now - q.fetched_at < self.ttl for q in have)

    async def get(self, tickers: list[str], force: bool = False) -> dict[str, Quote]:
        async with self._lock:
            if not force and self._fresh(tickers):
                return {t: self._cache[t] for t in tickers if t in self._cache}

            self.last_attempt = time.time()
            missing = list(tickers)
            errors: list[str] = []
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                for p in self.providers:
                    if not missing:
                        break
                    try:
                        got = await p.fetch(client, missing)
                    except Exception as e:               # noqa: BLE001
                        errors.append(f"{p.name}: {type(e).__name__}: {e}")
                        continue
                    if got:
                        self._cache.update(got)
                        missing = [t for t in missing if t not in got]
                    else:
                        errors.append(f"{p.name}: returned nothing")

            self.last_error = "; ".join(errors) if missing and errors else None
            if missing:
                log.warning("no quote for %d tickers: %s", len(missing), ", ".join(missing[:8]))
            return {t: self._cache[t] for t in tickers if t in self._cache}

    def health(self) -> dict:
        now = time.time()
        ages = [now - q.fetched_at for q in self._cache.values()]
        return {
            "providers": [p.name for p in self.providers],
            "cached_tickers": len(self._cache),
            "oldest_seconds": round(max(ages), 1) if ages else None,
            "newest_seconds": round(min(ages), 1) if ages else None,
            "last_error": self.last_error,
            "ttl_seconds": self.ttl,
        }
