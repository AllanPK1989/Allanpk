"""Collect news for followed instruments and the market, store it de-duplicated."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..data import http
from ..data.market import MarketData
from ..data.types import RawNews
from ..models import Instrument, NewsItem
from . import feeds

log = logging.getLogger(__name__)


def _fetch(url: str, source: str) -> list[RawNews]:
    try:
        r = http.client().get(url)
        r.raise_for_status()
        return feeds.parse_feed(r.content, source)
    except Exception as e:
        log.warning("feed %s failed: %s", source or url, e)
        return []


def _instrument_news(inst: dict[str, Any], market: MarketData, per_instrument: int, days: int) -> list[RawNews]:
    if market.demo:
        return market.news(inst["symbol"])[:per_instrument]
    q = feeds.news_query(inst["symbol"], inst["name"], inst["asset_class"])
    items = _fetch(feeds.google_news_url(q, days), "")
    if inst["asset_class"] in ("stock", "etf"):
        items += market.news(inst["symbol"])
    items.sort(key=lambda n: n.published_at, reverse=True)
    return items[: per_instrument * 2]


def collect(db: Session, market: MarketData, instruments: list[Instrument] | None = None, *,
            per_instrument: int = 6, days: int = 2, market_feeds: bool = True) -> dict[str, Any]:
    if instruments is None:
        instruments = list(db.scalars(select(Instrument).where(Instrument.followed.is_(True))))
    insts = [{"id": i.id, "symbol": i.symbol, "name": i.name, "asset_class": i.asset_class} for i in instruments]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days + 1)

    with ThreadPoolExecutor(max_workers=6) as ex:
        per_inst = list(ex.map(lambda i: _instrument_news(i, market, per_instrument, days), insts))
        market_items: list[RawNews] = []
        if market_feeds and not market.demo:
            for items in ex.map(lambda f: _fetch(f[1], f[0]), feeds.MARKET_FEEDS):
                market_items.extend(items)

    by_id = {i.id: i for i in instruments}
    keywords = {i["id"]: feeds.match_keywords(i["symbol"], i["name"], i["asset_class"]) for i in insts}
    new_count = 0
    seen: dict[str, NewsItem] = {}

    def store(raw: RawNews, scope: str, inst_ids: set[int]) -> None:
        nonlocal new_count
        pub = raw.published_at if raw.published_at.tzinfo else raw.published_at.replace(tzinfo=timezone.utc)
        if pub < cutoff:
            return
        key = feeds.news_key(raw.title)
        item = seen.get(key) or db.scalar(select(NewsItem).where(NewsItem.key == key))
        if item is None:
            item = NewsItem(key=key, url=raw.url, title=raw.title, source=raw.source, published_at=pub,
                            snippet=raw.snippet, scope=scope)
            db.add(item)
            new_count += 1
        seen[key] = item
        if inst_ids:
            item.scope = "instrument"
        for iid in inst_ids:
            inst = by_id[iid]
            if inst not in item.instruments:
                item.instruments.append(inst)

    for meta, items in zip(insts, per_inst):
        for raw in items[:per_instrument]:
            store(raw, "instrument", {meta["id"]})
    for raw in market_items:
        text = f"{raw.title} {raw.snippet}"
        hits = {iid for iid, kws in keywords.items() if kws and feeds.keyword_hit(text, kws)}
        store(raw, "instrument" if hits else "market", hits)
    db.flush()
    return {"new": new_count, "instruments": len(insts), "market_items": len(market_items)}
