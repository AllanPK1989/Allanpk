"""Connection points for the PM system, SAP or stores, and PLC/SCADA gateways (SPEC 12.1).

Inbound calls use an integration key (X-Thunai-Key); the admin endpoints that manage keys and
webhooks use the normal admin login.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import alarm_feed, audit, integrations, parts, pm, webhooks
from ..db import get_db
from ..models import BreakdownLog, IntegrationKey, Webhook, WebhookDelivery, User
from ..security import admin_only

router = APIRouter(tags=["integrations"])
MAX_ROWS = 1000


# ---- inbound (integration key) -------------------------------------------------------------------
class AlarmEvent(BaseModel):
    machine_no: str
    code: str = Field(min_length=1, max_length=60)
    message: str = Field(default="", max_length=1000)
    raised_at: datetime
    cleared_at: datetime | None = None
    event_id: str | None = Field(default=None, max_length=120)


class AlarmBatch(BaseModel):
    events: list[AlarmEvent] = Field(max_length=MAX_ROWS)


@router.post("/api/integrations/alarms")
def post_alarms(body: AlarmBatch, key: IntegrationKey = Depends(integrations.require_scope("alarms")), db: Session = Depends(get_db)):
    """PLC or SCADA alarm events. Repeats are skipped; a repeat may add the cleared time."""
    result = alarm_feed.ingest(db, [e.model_dump() for e in body.events], f"api:{key.name}")
    db.commit()
    return result


class PartRow(BaseModel):
    part_no: str = Field(min_length=1, max_length=80)
    description: str = ""
    unit: str = ""
    stock_qty: float | None = None
    min_qty: float | None = None
    location: str = ""
    alt_part_nos: list[str] = []
    machine_nos: list[str] = []
    machine_types: list[str] = []
    stock_at: datetime | None = None


class PartBatch(BaseModel):
    parts: list[PartRow] = Field(max_length=MAX_ROWS)


@router.put("/api/integrations/parts")
def put_parts(body: PartBatch, key: IntegrationKey = Depends(integrations.require_scope("parts")), db: Session = Depends(get_db)):
    """Spare-parts stock from the stores system, matched by part number."""
    result = parts.upsert(db, None, [(i, r.model_dump()) for i, r in enumerate(body.parts)], f"api:{key.name}")
    db.commit()
    return result


class PMRow(BaseModel):
    machine_no: str
    task_code: str = Field(min_length=1, max_length=80)
    title: str = ""
    frequency_days: int | None = None
    last_done_on: str | None = None
    next_due_on: str | None = None


class PMBatch(BaseModel):
    tasks: list[PMRow] = Field(max_length=MAX_ROWS)


@router.put("/api/integrations/pm-tasks")
def put_pm_tasks(body: PMBatch, key: IntegrationKey = Depends(integrations.require_scope("pm")), db: Session = Depends(get_db)):
    """The PM plan, matched by machine and task code."""
    result = pm.upsert(db, None, [(i, r.model_dump()) for i, r in enumerate(body.tasks)], f"api:{key.name}")
    db.commit()
    return result


@router.get("/api/integrations/logs")
def poll_logs(
    since: datetime,
    limit: int = Query(200, le=1000),
    key: IntegrationKey = Depends(integrations.require_scope("logs")),
    db: Session = Depends(get_db),
):
    """Closed and verified logs changed since a time, oldest first. Pass `next_since` back next time."""
    rows = db.scalars(
        select(BreakdownLog)
        .where(BreakdownLog.status.in_(("closed", "verified")), BreakdownLog.updated_at > since)
        .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.parts), selectinload(BreakdownLog.machine), selectinload(BreakdownLog.technician))
        .order_by(BreakdownLog.updated_at, BreakdownLog.id)
        .limit(limit)
    ).all()
    db.commit()  # saves the key's last-used time
    return {
        "logs": [webhooks.log_payload(l) for l in rows],
        "next_since": rows[-1].updated_at.isoformat() if rows else since.isoformat(),
    }


class ExternalRefIn(BaseModel):
    external_ref: str = Field(max_length=80)


@router.patch("/api/integrations/logs/{log_no}")
def set_external_ref(
    log_no: str, body: ExternalRefIn, key: IntegrationKey = Depends(integrations.require_scope("logs")), db: Session = Depends(get_db)
):
    """Write back a reference from another system, for example an SAP notification number."""
    lg = db.scalar(select(BreakdownLog).where(func.upper(BreakdownLog.log_no) == log_no.strip().upper()))
    if lg is None:
        raise HTTPException(404, "Log not found")
    before = {"external_ref": lg.external_ref}
    lg.external_ref = body.external_ref.strip()
    audit.record(db, None, "breakdown_log", lg.id, "update", before, {"external_ref": lg.external_ref, "by_key": key.name})
    db.commit()
    return {"log_no": lg.log_no, "external_ref": lg.external_ref}


# ---- admin: keys, webhooks, deliveries -----------------------------------------------------------
class KeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str]


class ActiveIn(BaseModel):
    active: bool


@router.get("/api/admin/integration-keys")
def list_keys(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [integrations.serialize(k) for k in db.scalars(select(IntegrationKey).order_by(IntegrationKey.id))]


@router.post("/api/admin/integration-keys")
def create_key(body: KeyIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    key, token = integrations.create_key(db, user, body.name, body.scopes)
    db.commit()
    return {**integrations.serialize(key), "token": token}  # shown once


@router.patch("/api/admin/integration-keys/{key_id}")
def update_key(key_id: int, body: ActiveIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    key = db.get(IntegrationKey, key_id)
    if key is None:
        raise HTTPException(404, "Key not found")
    integrations.set_active(db, user, key, body.active)
    db.commit()
    return integrations.serialize(key)


class WebhookIn(BaseModel):
    name: str = Field(default="", max_length=120)
    url: str = Field(min_length=8, max_length=500)
    events: list[str]


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=500)
    events: list[str] | None = None
    active: bool | None = None


def _webhook(db: Session, webhook_id: int) -> Webhook:
    w = db.get(Webhook, webhook_id)
    if w is None:
        raise HTTPException(404, "Webhook not found")
    return w


@router.get("/api/admin/webhooks")
def list_webhooks(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [webhooks.serialize(w) for w in db.scalars(select(Webhook).order_by(Webhook.id))]


@router.post("/api/admin/webhooks")
def create_webhook(body: WebhookIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    w, secret = webhooks.create(db, user, body.name, body.url, body.events)
    db.commit()
    return {**webhooks.serialize(w), "secret": secret}  # shown once


@router.patch("/api/admin/webhooks/{webhook_id}")
def update_webhook(webhook_id: int, body: WebhookUpdate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    w = webhooks.update(db, user, _webhook(db, webhook_id), url=body.url, events=body.events, active=body.active)
    db.commit()
    return webhooks.serialize(w)


@router.post("/api/admin/webhooks/{webhook_id}/rotate-secret")
def rotate_secret(webhook_id: int, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    secret = webhooks.rotate_secret(db, user, _webhook(db, webhook_id))
    db.commit()
    return {"secret": secret}


@router.post("/api/admin/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: int, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    d = webhooks.test(db, _webhook(db, webhook_id))
    db.commit()
    return {"delivery_id": d.id}


@router.get("/api/admin/webhook-deliveries")
def list_deliveries(
    status: str = "", limit: int = Query(50, le=500), user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    q = select(WebhookDelivery).options(selectinload(WebhookDelivery.webhook)).order_by(WebhookDelivery.id.desc()).limit(limit)
    if status:
        q = q.where(WebhookDelivery.status.in_(status.split(",")))
    return [webhooks.serialize_delivery(d) for d in db.scalars(q)]


@router.post("/api/admin/webhook-deliveries/{delivery_id}/retry")
def retry_delivery(delivery_id: int, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    d = db.get(WebhookDelivery, delivery_id)
    if d is None:
        raise HTTPException(404, "Delivery not found")
    webhooks.retry(db, user, d)
    db.commit()
    return webhooks.serialize_delivery(d)
