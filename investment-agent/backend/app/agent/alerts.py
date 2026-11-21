"""Breaking alerts: sharp price moves and high-impact news on followed instruments."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..config import get_settings
from ..data.market import MarketData
from ..models import AlertLog, Digest, NewsItem
from ..news import query as news_query
from ..notify import email, push
from ..render import email_html, fmt_num, md_escape, to_html

log = logging.getLogger(__name__)


def _exists(db: Session, key: str) -> bool:
    return db.scalar(select(AlertLog.id).where(AlertLog.key == key)) is not None


def check(db: Session, market: MarketData) -> list[AlertLog]:
    settings = services.get_all_settings(db)
    insts = services.followed_instruments(db)
    if not insts:
        return []
    quotes = market.quotes([i.symbol for i in insts])
    today = services.now_local().date().isoformat()
    new: list[AlertLog] = []
    for i in insts:
        q = quotes.get(i.symbol)
        if not q or q.change_pct is None or (i.asset_class == "index" and i.symbol not in ("^NSEI", "^BSESN", "^GSPC")):
            continue
        threshold = i.alert_pct or float(settings["alert_pct_crypto"] if i.asset_class == "crypto" else settings["alert_pct"])
        if threshold <= 0 or abs(q.change_pct) < threshold:
            continue
        band = int(abs(q.change_pct) // threshold)  # alert again at 2x, 3x the threshold
        direction = "up" if q.change_pct > 0 else "down"
        key = f"price:{i.symbol}:{today}:{direction}{band}"
        if _exists(db, key):
            continue
        a = AlertLog(key=key, kind="price", instrument_id=i.id,
                     title=f"{i.name} {direction} {abs(q.change_pct):.1f}%",
                     body=f"{i.symbol} at {fmt_num(q.price)} {q.currency or ''} ({q.change_pct:+.2f}% vs previous close).",
                     url=f"/instrument/{i.symbol}")
        db.add(a)
        new.append(a)

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    followed_ids = [i.id for i in insts]
    for n in news_query.recent(db, instrument_ids=followed_ids, since=since, impact="high", limit=30):
        if n.alerted:
            continue
        n.alerted = True
        key = f"news:{n.id}"
        if _exists(db, key):
            continue
        names = ", ".join(x.name for x in n.instruments[:2])
        a = AlertLog(key=key, kind="news", instrument_id=n.instruments[0].id if n.instruments else None,
                     title=f"News: {names}" if names else "Market news", body=f"{n.title} ({n.source})", url=n.url)
        db.add(a)
        new.append(a)
    db.flush()
    return new


def deliver(db: Session, alerts: list[AlertLog]) -> dict[str, Any]:
    if not alerts:
        return {"pushed": 0, "emailed": False}
    s = get_settings()
    settings = services.get_all_settings(db)
    pushed = 0
    if settings.get("push_alerts", True):
        if len(alerts) <= 3:
            for a in alerts:
                pushed += push.send_all(db, title=a.title, body=a.body, url=a.url if a.url.startswith("/") else "/alerts",
                                        tag=a.key[:60])
        else:
            pushed += push.send_all(db, title=f"{len(alerts)} new alerts",
                                    body="; ".join(a.title for a in alerts[:4]), url="/alerts", tag="alerts")
    emailed = False
    lines = [f"- **{md_escape(a.title)}** — {md_escape(a.body)}" + (f" [link]({a.url})" if a.url.startswith("http") else "")
             for a in alerts]
    markdown = "## New alerts\n" + "\n".join(lines)
    title = f"Alerts · {services.now_local().strftime('%d %b %H:%M')}: " + ", ".join(a.title for a in alerts[:2])
    digest = Digest(kind="alert", title=title[:250], markdown=markdown, html=to_html(markdown), data={"count": len(alerts)})
    db.add(digest)
    db.flush()
    if settings.get("email_alerts", False):
        html = email_html(title, digest.html, app_url=f"{s.base_url.rstrip('/')}/alerts",
                          footer="Alerts from your investment app.")
        emailed = email.send(title, html, markdown)
    return {"pushed": pushed, "emailed": emailed, "digest_id": digest.id}


def recent_alerts(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.scalars(select(AlertLog).order_by(AlertLog.created_at.desc()).limit(limit))
    return [{"id": a.id, "kind": a.kind, "title": a.title, "body": a.body, "url": a.url,
             "created_at": a.created_at.isoformat()} for a in rows]


def mark_news_seen(db: Session, items: list[NewsItem]) -> None:
    for n in items:
        n.alerted = True
