"""The India side of the book.

Prices come from different places than the US side, so the marking lives here
rather than in book.py:

  mutual funds  AMFI publishes every scheme's NAV daily as one plain-text file,
                keyed by ISIN. Free, no key, one request for all 28 holdings.
  listed ETFs   NSE lines quote on Yahoo under a .NS suffix, so they go through
                the existing quote chain.
  pre-IPO       there is no market price for an unlisted holding. These stay at
                the statement value and are labelled, never estimated.
"""
from __future__ import annotations

import json
import logging
import pathlib
import time

import httpx

log = logging.getLogger(__name__)

DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "india.json"
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"


class AmfiNavs:
    """Daily scheme NAVs from AMFI, cached. ISIN -> (nav, date).

    AMFI publishes every scheme in the country as one plain-text file, several
    megabytes of it. This streams the response and keeps only the ISINs the
    book actually holds — 28 rather than roughly thirty thousand — because
    buffering the whole file and indexing all of it spikes memory on a small
    instance, and an out-of-memory restart loop looks exactly like the site
    being down.
    """

    MAX_BYTES = 24 * 1024 * 1024          # hard stop; the file is far smaller

    def __init__(self, ttl: float = 3600.0):
        self.ttl = ttl
        self._navs: dict[str, tuple[float, str]] = {}
        self._fetched = 0.0
        self.last_error: str | None = None
        self.cooldown_until = 0.0

    @property
    def fresh(self) -> bool:
        return bool(self._navs) and time.time() - self._fetched < self.ttl

    @staticmethod
    def _row(line: str, wanted: set[str] | None) -> list[tuple[str, float, str]]:
        # Scheme Code;ISIN Growth;ISIN Reinvest;Scheme Name;NAV;Date
        parts = line.split(";")
        if len(parts) < 6:
            return []
        try:
            nav = float(parts[4].strip())
        except ValueError:
            return []                                         # header or "N.A."
        date_s = parts[5].strip()
        out = []
        for isin in (parts[1].strip().upper(), parts[2].strip().upper()):
            if not isin or isin in ("", "-", "N.A."):
                continue
            if wanted is None or isin in wanted:
                out.append((isin, nav, date_s))
        return out

    async def load(self, force: bool = False,
                   wanted: set[str] | None = None) -> dict[str, tuple[float, str]]:
        if self.fresh and not force:
            return self._navs
        if time.time() < self.cooldown_until:
            return self._navs

        navs: dict[str, tuple[float, str]] = {}
        seen = 0
        try:
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as c:
                async with c.stream("GET", AMFI_URL,
                                    headers={"User-Agent": "Mozilla/5.0"}) as r:
                    r.raise_for_status()
                    tail = ""
                    async for chunk in r.aiter_text(chunk_size=65536):
                        seen += len(chunk)
                        if seen > self.MAX_BYTES:
                            raise ValueError("AMFI response exceeded the size cap")
                        tail += chunk
                        lines = tail.split("\n")
                        tail = lines.pop()                    # keep the partial line
                        for line in lines:
                            for isin, nav, date_s in self._row(line, wanted):
                                navs[isin] = (nav, date_s)
                    for isin, nav, date_s in self._row(tail, wanted):
                        navs[isin] = (nav, date_s)
        except Exception as e:                                # noqa: BLE001
            self.last_error = f"{type(e).__name__}: {e}"
            self.cooldown_until = time.time() + 900
            log.warning("AMFI NAV fetch failed, keeping previous values: %s", e)
            return self._navs

        if navs:
            self._navs, self._fetched, self.last_error = navs, time.time(), None
            log.info("AMFI: kept %d of the schemes we hold from %.1f MB",
                     len(navs), seen / 1e6)
        else:
            self.last_error = "AMFI returned no parseable rows"
        return self._navs

    def health(self) -> dict:
        return {"schemes": len(self._navs),
                "age_seconds": round(time.time() - self._fetched, 1) if self._fetched else None,
                "last_error": self.last_error}


class IndiaBook:
    def __init__(self, path: pathlib.Path = DATA):
        self.base = json.loads(path.read_text())

    @property
    def fund_isins(self) -> set[str]:
        """Only these are worth keeping out of the national NAV file."""
        return {(h.get("isin") or "").upper() for h in self.base["holdings"]
                if h["kind"] == "mutual_fund" and h.get("isin")}

    @property
    def etf_symbols(self) -> list[str]:
        return [h["quote_symbol"] for h in self.base["holdings"] if h.get("quote_symbol")]

    def mark(self, navs: dict[str, tuple[float, str]], etf_quotes: dict) -> dict:
        """Return the India book marked to whatever live data arrived, falling
        back per holding to the statement figure."""
        book = json.loads(json.dumps(self.base))
        live = 0
        for h in book["holdings"]:
            if h["kind"] == "mutual_fund":
                got = navs.get((h.get("isin") or "").upper())
                if got and got[0] > 0:
                    h["price"], h["priced_on"] = round(got[0], 4), got[1]
                    h["value"] = round(h["units"] * got[0], 2)
                    h["live"] = True
                    live += 1
            elif h["kind"] == "etf":
                q = etf_quotes.get(h.get("quote_symbol"))
                if q and getattr(q, "price", None):
                    h["price"] = round(q.price, 4)
                    h["value"] = round(h["units"] * q.price, 2)
                    h["live"] = True
                    h["quote_source"] = q.source
                    live += 1
            h["pl"] = round(h["value"] - h["cost"], 2)
            h["pl_pct"] = round((h["value"] / h["cost"] - 1) * 100, 2) if h["cost"] else None

        _rollup(book)
        book["live_count"] = live
        book["priceable"] = sum(1 for h in book["holdings"] if h["kind"] != "pre_ipo")
        return book


def _rollup(book: dict) -> None:
    by_account, by_class, by_sub = {}, {}, {}
    for h in book["holdings"]:
        for bucket, key in ((by_account, h["account"]), (by_class, h["asset_class"]),
                            (by_sub, h["sub_class"])):
            b = bucket.setdefault(key, {"value": 0.0, "cost": 0.0, "n": 0})
            b["value"] += h["value"]; b["cost"] += h["cost"]; b["n"] += 1
    for bucket in (by_account, by_class, by_sub):
        for b in bucket.values():
            b["value"] = round(b["value"], 2); b["cost"] = round(b["cost"], 2)
            b["pl"] = round(b["value"] - b["cost"], 2)
            b["pl_pct"] = round((b["value"] / b["cost"] - 1) * 100, 2) if b["cost"] else None
    value = round(sum(h["value"] for h in book["holdings"]), 2)
    cost = round(sum(h["cost"] for h in book["holdings"]), 2)
    book["totals"] = dict(value=value, cost=cost, pl=round(value - cost, 2),
                          pl_pct=round((value / cost - 1) * 100, 2) if cost else None,
                          holdings=len(book["holdings"]))
    srt = lambda d: dict(sorted(d.items(), key=lambda kv: -kv[1]["value"]))
    book["by_account"], book["by_class"], book["by_sub"] = srt(by_account), srt(by_class), srt(by_sub)
    book["holdings"].sort(key=lambda h: -h["value"])
