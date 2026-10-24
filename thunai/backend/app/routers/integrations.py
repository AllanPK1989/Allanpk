"""Connection points for PLC/SCADA gateways and the stores system (SPEC 12.1).

Inbound calls use an integration key (X-Thunai-Key); the admin endpoints that manage keys use the
normal admin login.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import alarm_feed, integrations, parts
from ..db import get_db
from ..models import IntegrationKey, User
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


# ---- admin: keys ------------------------------------------------------------------------------------
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
