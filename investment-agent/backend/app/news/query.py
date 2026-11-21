"""Reading stored news."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Instrument, NewsItem, news_instruments

IMPACT_RANK = {"high": 0, "medium": 1, "low": 2, "": 3}


def news_dict(n: NewsItem) -> dict[str, Any]:
    return {"id": n.id, "title": n.title, "url": n.url, "source": n.source,
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "summary": n.summary or n.snippet, "sentiment": n.sentiment, "impact": n.impact, "category": n.category,
            "scope": n.scope, "symbols": [i.symbol for i in n.instruments]}


def recent(db: Session, *, instrument_ids: list[int] | None = None, since: datetime | None = None, days: int = 3,
           impact: str | None = None, scope: str | None = None, limit: int = 50, q: str | None = None) -> list[NewsItem]:
    since = since or datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(NewsItem).options(selectinload(NewsItem.instruments)).where(NewsItem.published_at >= since)
    if instrument_ids:
        stmt = stmt.where(NewsItem.id.in_(select(news_instruments.c.news_id)
                                           .where(news_instruments.c.instrument_id.in_(instrument_ids))))
    if impact:
        stmt = stmt.where(NewsItem.impact == impact)
    if scope:
        stmt = stmt.where(NewsItem.scope == scope)
    if q:
        stmt = stmt.where(NewsItem.title.ilike(f"%{q[:60]}%"))
    stmt = stmt.order_by(NewsItem.published_at.desc()).limit(limit * 3 if impact is None else limit)
    items = list(db.scalars(stmt))
    return items[:limit]


def top_for_instrument(db: Session, inst: Instrument, *, days: int = 7, limit: int = 8) -> list[dict[str, Any]]:
    items = recent(db, instrument_ids=[inst.id], days=days, limit=40)
    items.sort(key=lambda n: (IMPACT_RANK.get(n.impact, 3), -n.published_at.timestamp()))
    return [news_dict(n) for n in items[:limit]]
