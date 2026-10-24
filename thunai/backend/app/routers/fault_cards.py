"""Fault cards: supervisor review of AI drafts, approval, edits, versions and retirement."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import knowledge, serialize
from ..db import get_db
from ..models import BreakdownLog, FaultCard, Machine, MachineType, User
from ..schemas import FaultCardEdit, ReasonIn
from ..security import current_user, supervisor_or_admin

router = APIRouter(prefix="/api/fault-cards", tags=["fault-cards"])


def _load(db: Session, card_id: int) -> FaultCard:
    card = db.get(FaultCard, card_id)
    if card is None:
        raise HTTPException(404, "Fault card not found")
    return card


def _scope(db: Session, card: FaultCard) -> dict:
    if card.machine_id:
        m = db.get(Machine, card.machine_id)
        return {"scope": "machine", "machine_no": m.machine_no, "scope_name": m.name, "zone": m.zone}
    t = db.get(MachineType, card.machine_type_id) if card.machine_type_id else None
    return {"scope": "type", "machine_no": None, "scope_name": t.name if t else "", "zone": ""}


def _out(db: Session, card: FaultCard, with_logs: bool = False) -> dict:
    data = {**serialize.fault_card(card), **_scope(db, card)}
    if with_logs:
        ids = list({*(card.source_log_ids or []), *(card.flagged_log_ids or [])})
        logs = db.scalars(
            select(BreakdownLog)
            .where(BreakdownLog.id.in_(ids or [0]))
            .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.machine),
                     selectinload(BreakdownLog.technician), selectinload(BreakdownLog.verifier))
            .order_by(BreakdownLog.reported_at.desc())
        ).all()
        by_id = {l.id: serialize.log(l, full=False) for l in logs}
        data["source_logs"] = [by_id[i] for i in card.source_log_ids or [] if i in by_id]
        data["flagged_logs"] = [by_id[i] for i in card.flagged_log_ids or [] if i in by_id]
    return data


@router.get("")
def list_cards(status: str = "draft,needs_review", user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    cards = db.scalars(
        select(FaultCard).where(FaultCard.status.in_(status.split(","))).order_by(FaultCard.updated_at.desc()).limit(200)
    ).all()
    out = [_out(db, c) for c in cards]
    if user.role == "supervisor" and user.zone:
        out = [c for c in out if c["scope"] == "type" or c["zone"] == user.zone]
    return out


@router.get("/{card_id}")
def get_card(card_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    card = _load(db, card_id)
    if user.role == "technician" and card.status not in knowledge.LIVE_STATUSES:
        raise HTTPException(403, "Not available")
    return _out(db, card, with_logs=True)


@router.patch("/{card_id}")
def edit_card(card_id: int, body: FaultCardEdit, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    card = _load(db, card_id)
    changes = body.model_dump(exclude_unset=True, exclude={"causes"})
    if body.causes is not None:
        old = card.causes or []
        changes["causes"] = [
            {
                "cause": c.cause,
                "cause_ta": c.cause_ta,
                "count": old[i].get("count", 0) if i < len(old) else 0,
                "log_ids": old[i].get("log_ids", []) if i < len(old) else [],
            }
            for i, c in enumerate(body.causes)
        ]
    knowledge.edit(db, user, card, changes)
    db.commit()
    return _out(db, card, with_logs=True)


@router.post("/{card_id}/approve")
def approve(card_id: int, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    card = knowledge.approve(db, user, _load(db, card_id))
    db.commit()
    return _out(db, card, with_logs=True)


@router.post("/{card_id}/reject")
def reject(card_id: int, body: ReasonIn, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    card = knowledge.reject(db, user, _load(db, card_id), body.reason)
    db.commit()
    return _out(db, card, with_logs=True)


@router.post("/{card_id}/retire")
def retire(card_id: int, body: ReasonIn, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    card = knowledge.retire(db, user, _load(db, card_id), body.reason)
    db.commit()
    return _out(db, card, with_logs=True)


@router.post("/{card_id}/redraft")
def redraft(card_id: int, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    new = knowledge.redraft(db, user, _load(db, card_id))
    db.commit()
    return _out(db, new, with_logs=True)
