from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import excel, skills
from ..db import get_db
from ..models import User
from ..security import supervisor_or_admin

router = APIRouter(prefix="/api", tags=["skills"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _zone(user: User, zone: str) -> str:
    """Supervisors see their own zone only (per-person figures, SPEC 12.5); admins choose."""
    return user.zone if user.role == "supervisor" and user.zone else zone


@router.get("/skills")
def get_skills(
    days: int = Query(90, ge=7, le=366), zone: str = "", user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)
):
    return skills.build(db, days=days, zone=_zone(user, zone))


@router.get("/export/skills.xlsx")
def export_skills(
    days: int = Query(90, ge=7, le=366), zone: str = "", user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)
):
    zone = _zone(user, zone)
    content = excel.export_skills(skills.build(db, days=days, zone=zone))
    name = f"thunai-skills-{days}d{'-' + zone.replace(' ', '_') if zone else ''}.xlsx"
    return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})
