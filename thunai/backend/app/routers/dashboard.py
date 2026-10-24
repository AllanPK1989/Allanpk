from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import dashboard, excel
from ..db import get_db
from ..models import User
from ..security import supervisor_or_admin

router = APIRouter(prefix="/api", tags=["dashboard"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/dashboard")
def get_dashboard(
    days: int = Query(30, ge=1, le=366), zone: str = "", user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)
):
    return dashboard.build(db, days=days, zone=zone)


@router.get("/export/dashboard.xlsx")
def export_dashboard(
    days: int = Query(30, ge=1, le=366), zone: str = "", user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)
):
    content = excel.export_dashboard(dashboard.build(db, days=days, zone=zone))
    name = f"thunai-dashboard-{days}d{'-' + zone.replace(' ', '_') if zone else ''}.xlsx"
    return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})
