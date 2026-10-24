from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import machines_service, parts
from ..db import get_db
from ..models import SparePart, User
from ..security import admin_only, current_user

router = APIRouter(prefix="/api", tags=["spare-parts"])


@router.get("/parts")
def search_parts(
    q: str = "",
    machine_no: str = "",
    limit: int = Query(20, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Parts picker: search by part number or description; this machine's parts first."""
    machine = machines_service.get_machine(db, machine_no) if machine_no else None
    return [parts.info(p) for p in parts.search(db, q, machine, limit)]


@router.get("/admin/parts")
def list_parts(
    q: str = "",
    include_inactive: bool = False,
    limit: int = Query(200, le=1000),
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    query = select(SparePart).options(selectinload(SparePart.fits)).order_by(SparePart.part_no).limit(limit)
    if not include_inactive:
        query = query.where(SparePart.active.is_(True))
    if q.strip():
        query = query.where(SparePart.match_keys.contains(q.strip().upper(), autoescape=True) | SparePart.description.icontains(q.strip(), autoescape=True))
    return [parts.serialize(p) for p in db.scalars(query)]


class ActiveIn(BaseModel):
    active: bool


@router.patch("/admin/parts/{part_id}")
def set_part_active(part_id: int, body: ActiveIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    part = db.get(SparePart, part_id)
    if part is None:
        raise HTTPException(404, "Part not found")
    parts.set_active(db, user, part, body.active)
    db.commit()
    return parts.serialize(part)
