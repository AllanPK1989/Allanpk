"""USD/INR, needed to state one net worth across two currencies.

The rate is part of the return on the US book for someone whose liabilities are
in rupees, so it is fetched rather than pinned, and the page always shows which
rate it used and where it came from.
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

log = logging.getLogger(__name__)

FALLBACK = 94.38          # 4 Sep 2026, the rate the static build shipped with


class FxRate:
    def __init__(self, ttl: float = 3600.0):
        self.ttl = ttl
        self.rate = FALLBACK
        self.source = "fallback"
        self.fetched_at = 0.0
        self._bg: asyncio.Task | None = None
        self._tried = 0.0
        self.last_error: str | None = None

    @property
    def fresh(self) -> bool:
        return self.source != "fallback" and time.time() - self.fetched_at < self.ttl

    async def get(self, force: bool = False, wait: bool = False) -> float:
        """The cached rate, refreshed behind the response unless asked to wait."""
        if self.fresh and not force:
            return self.rate
        if not force and not wait:
            if (not (self._bg and not self._bg.done())
                    and time.time() - self._tried > 120):
                self._tried = time.time()
                try:
                    self._bg = asyncio.get_running_loop().create_task(self._fetch())
                except RuntimeError:
                    pass
            return self.rate
        return await self._fetch()

    async def _fetch(self) -> float:
        attempts = (
            ("yahoo", "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X",
             lambda j: j["chart"]["result"][0]["meta"]["regularMarketPrice"]),
            ("frankfurter", "https://api.frankfurter.app/latest?from=USD&to=INR",
             lambda j: j["rates"]["INR"]),
            ("erapi", "https://open.er-api.com/v6/latest/USD",
             lambda j: j["rates"]["INR"]),
        )
        errs = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
            for name, url, pick in attempts:
                try:
                    r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    r.raise_for_status()
                    rate = float(pick(r.json()))
                    if 50 < rate < 200:          # a sane USD/INR, not a parse artefact
                        self.rate, self.source = round(rate, 4), name
                        self.fetched_at, self.last_error = time.time(), None
                        return self.rate
                    errs.append(f"{name}: implausible rate {rate}")
                except Exception as e:           # noqa: BLE001
                    errs.append(f"{name}: {type(e).__name__}")
        self.last_error = "; ".join(errs)
        log.warning("FX unavailable, using %s %.4f: %s", self.source, self.rate, self.last_error)
        return self.rate

    def health(self) -> dict:
        return {"rate": self.rate, "source": self.source,
                "age_seconds": round(time.time() - self.fetched_at, 1) if self.fetched_at else None,
                "last_error": self.last_error}
