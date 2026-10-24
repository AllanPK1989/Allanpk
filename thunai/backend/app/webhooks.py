"""Outbound events for the PM system, SAP middleware or a maintenance dashboard (SPEC 12.5).

Each event becomes one delivery per subscribed endpoint. The worker sends it, signed with the
endpoint's secret, and retries with backoff. The body is fixed at the first attempt, so every retry
sends exactly the same bytes and the receiver can de-duplicate on X-Thunai-Delivery.
"""
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import timedelta
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, jobs
from .config import get_config
from .models import WEBHOOK_EVENTS, BreakdownLog, Webhook, WebhookDelivery, User, utcnow

log = logging.getLogger("thunai.webhooks")

MAX_ATTEMPTS = 5
BACKOFF_MIN = (1, 5, 30, 120)  # wait before attempts 2, 3, 4 and 5
TEST_EVENT = "ping"


def serialize(w: Webhook) -> dict:
    return {"id": w.id, "name": w.name, "url": w.url, "events": w.events, "active": w.active, "created_at": w.created_at.isoformat()}


def serialize_delivery(d: WebhookDelivery) -> dict:
    return {
        "id": d.id,
        "webhook_id": d.webhook_id,
        "webhook": d.webhook.name or d.webhook.url,
        "event": d.event,
        "entity_id": d.entity_id,
        "status": d.status,
        "attempts": d.attempts,
        "next_attempt_at": d.next_attempt_at.isoformat() if d.next_attempt_at else None,
        "last_status": d.last_status,
        "last_error": d.last_error,
        "sent_at": d.sent_at.isoformat() if d.sent_at else None,
        "created_at": d.created_at.isoformat(),
    }


def _check(url: str, events: list[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(422, "The URL must start with http:// or https://")
    bad = [e for e in events if e not in WEBHOOK_EVENTS]
    if bad or not events:
        raise HTTPException(422, f"Events must be some of {', '.join(WEBHOOK_EVENTS)}")


def create(db: Session, user: User, name: str, url: str, events: list[str]) -> tuple[Webhook, str]:
    _check(url, events)
    secret = secrets.token_urlsafe(32)
    w = Webhook(name=name.strip()[:120], url=url.strip(), events=sorted(set(events)), secret=secret, created_by=user.id)
    db.add(w)
    db.flush()
    audit.record(db, user, "webhook", w.id, "create", None, serialize(w))
    return w, secret


def update(db: Session, user: User, w: Webhook, *, url: str | None, events: list[str] | None, active: bool | None) -> Webhook:
    before = serialize(w)
    _check(url or w.url, events if events is not None else w.events)
    if url is not None:
        w.url = url.strip()
    if events is not None:
        w.events = sorted(set(events))
    if active is not None:
        w.active = active
    audit.record(db, user, "webhook", w.id, "update", before, serialize(w))
    return w


def rotate_secret(db: Session, user: User, w: Webhook) -> str:
    w.secret = secrets.token_urlsafe(32)
    audit.record(db, user, "webhook", w.id, "rotate_secret", None, {"rotated": True})
    return w.secret


def sign(secret: str, timestamp: str, body: bytes) -> str:
    """HMAC-SHA256 over "<timestamp>.<body>", hex. Receivers recompute it and compare."""
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def log_payload(lg: BreakdownLog) -> dict:
    """A breakdown log as other systems see it: English where available, the original always."""

    def text(field: str) -> dict:
        return {"original": lg.original(field), "en": lg.text(field, "en")}

    return {
        "log_no": lg.log_no,
        "machine_no": lg.machine.machine_no,
        "machine_name": lg.machine.name,
        "zone": lg.zone,
        "status": lg.status,
        "shift": lg.shift,
        "shift_date": lg.shift_date.isoformat() if lg.shift_date else None,
        "reported_at": lg.reported_at.isoformat(),
        "start_at": lg.start_at.isoformat() if lg.start_at else None,
        "end_at": lg.end_at.isoformat() if lg.end_at else None,
        "downtime_min": lg.downtime_min,
        "alarm_code": lg.alarm_code,
        "issue": text("issue"),
        "root_cause": text("root_cause"),
        "corrective_action": text("corrective_action"),
        "parts": [{"part_no": p.part_no, "description": p.description, "qty": p.qty} for p in lg.parts],
        "technician_employee_id": lg.technician.employee_id if lg.technician else "",
        "technician_name": lg.technician.name if lg.technician else lg.technician_name,
        "verified_at": lg.verified_at.isoformat() if lg.verified_at else None,
        "external_ref": lg.external_ref,
        "updated_at": lg.updated_at.isoformat() if lg.updated_at else None,
    }


def emit(db: Session, event: str, lg: BreakdownLog) -> int:
    """Queue `event` for every active endpoint subscribed to it. The body is built when first sent,
    after the log's translation job, so it carries the English text."""
    hooks = [w for w in db.scalars(select(Webhook).where(Webhook.active.is_(True))) if event in (w.events or [])]
    for w in hooks:
        d = WebhookDelivery(webhook_id=w.id, event=event, entity_id=lg.log_no or str(lg.id), payload={"log_id": lg.id},
                            next_attempt_at=utcnow())
        db.add(d)
        db.flush()
        jobs.enqueue(db, "deliver_webhook", delivery_id=d.id)
    return len(hooks)


def test(db: Session, w: Webhook) -> WebhookDelivery:
    d = WebhookDelivery(webhook_id=w.id, event=TEST_EVENT, entity_id="", payload={"body": {"event": TEST_EVENT, "message": "Thunai test event"}},
                        next_attempt_at=utcnow())
    db.add(d)
    db.flush()
    jobs.enqueue(db, "deliver_webhook", delivery_id=d.id)
    return d


def _body(db: Session, d: WebhookDelivery) -> dict:
    if "body" in (d.payload or {}):
        return d.payload["body"]
    lg = db.get(BreakdownLog, d.payload.get("log_id"))
    body = {"event": d.event, "delivery_id": d.id, "created_at": d.created_at.isoformat(), "log": log_payload(lg) if lg else None}
    d.payload = {"body": body}  # frozen: retries send the same bytes
    return body


def deliver(db: Session, d: WebhookDelivery) -> WebhookDelivery:
    if d.status == "sent":
        return d
    w = d.webhook
    if not w.active:
        d.status, d.next_attempt_at, d.last_error = "failed", None, "Endpoint deactivated"
        return d
    raw = json.dumps(_body(db, d), separators=(",", ":"), ensure_ascii=False).encode()
    stamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Thunai-Webhooks/1",
        "X-Thunai-Event": d.event,
        "X-Thunai-Delivery": str(d.id),
        "X-Thunai-Timestamp": stamp,
        "X-Thunai-Signature": f"sha256={sign(w.secret, stamp, raw)}",
    }
    d.attempts += 1
    try:
        with httpx.Client(timeout=get_config().webhook_timeout_s, follow_redirects=False) as client:
            response = client.post(w.url, content=raw, headers=headers)
        d.last_status = response.status_code
        ok = 200 <= response.status_code < 300
        d.last_error = "" if ok else f"HTTP {response.status_code}: {response.text[:300]}"
    except httpx.HTTPError as e:
        ok = False
        d.last_status = None
        d.last_error = f"{type(e).__name__}: {str(e)[:300]}"
    if ok:
        d.status, d.sent_at, d.next_attempt_at = "sent", utcnow(), None
    elif d.attempts >= MAX_ATTEMPTS:
        d.status, d.next_attempt_at = "failed", None
        log.warning("Webhook delivery %s failed for good: %s", d.id, d.last_error)
    else:
        d.status = "pending"
        d.next_attempt_at = utcnow() + timedelta(minutes=BACKOFF_MIN[d.attempts - 1])
    return d


def retry(db: Session, user: User, d: WebhookDelivery) -> WebhookDelivery:
    """Admin retry: one more attempt now, also for a delivery that already failed for good."""
    if d.status == "sent":
        raise HTTPException(409, "Already delivered")
    d.status = "pending"
    d.attempts = min(d.attempts, MAX_ATTEMPTS - 1)
    d.next_attempt_at = utcnow()
    audit.record(db, user, "webhook_delivery", d.id, "retry", None, {"event": d.event})
    jobs.enqueue(db, "deliver_webhook", delivery_id=d.id)
    return d


def due(db: Session, limit: int = 100) -> list[WebhookDelivery]:
    return list(
        db.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.status == "pending", WebhookDelivery.next_attempt_at <= utcnow())
            .order_by(WebhookDelivery.id)
            .limit(limit)
        )
    )
