from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import machines_service, serialize, tips
from ..db import get_db
from ..models import ExpertTip, User
from ..schemas import ReasonIn, TipIn
from ..security import current_user, supervisor_or_admin

router = APIRouter(prefix="/api/tips", tags=["expert-tips"])


def _load(db: Session, tip_id: int) -> ExpertTip:
    tip = db.scalar(
        select(ExpertTip).where(ExpertTip.id == tip_id).options(selectinload(ExpertTip.machine), selectinload(ExpertTip.author))
    )
    if tip is None:
        raise HTTPException(404, "Tip not found")
    return tip


@router.post("")
def create(body: TipIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.get_machine(db, body.machine_no)
    tip = tips.create(db, user, machine, body.text, body.media_id)
    db.commit()
    return serialize.tip(_load(db, tip.id))


@router.get("")
def list_tips(status: str = "pending", mine: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = (
        select(ExpertTip)
        .where(ExpertTip.status.in_(status.split(",")))
        .options(selectinload(ExpertTip.machine), selectinload(ExpertTip.author))
        .order_by(ExpertTip.created_at.desc())
        .limit(200)
    )
    if mine or user.role == "technician":
        q = q.where(ExpertTip.author_id == user.id)
    out = [serialize.tip(t) for t in db.scalars(q)]
    if user.role == "supervisor" and user.zone and not mine:
        out = [t for t in out if _zone(db, t) == user.zone]
    return out


def _zone(db: Session, t: dict) -> str:
    return machines_service.get_machine(db, t["machine_no"]).zone


@router.post("/{tip_id}/approve")
def approve(tip_id: int, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    tip = tips.review(db, user, _load(db, tip_id), approve=True)
    db.commit()
    return serialize.tip(_load(db, tip.id))


@router.post("/{tip_id}/reject")
def reject(tip_id: int, body: ReasonIn, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    tip = tips.review(db, user, _load(db, tip_id), approve=False, reason=body.reason)
    db.commit()
    return serialize.tip(_load(db, tip.id))
