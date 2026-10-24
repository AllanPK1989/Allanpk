from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from .. import audit, excel, serialize, settings_store
from ..db import get_db
from ..models import AICall, AISession, AuditLog, Glossary, User
from ..schemas import GlossaryIn, PinReset, SettingIn, UserIn, UserUpdate
from ..security import admin_only, current_user, hash_pin, supervisor_or_admin, valid_pin
from ..shifts import parse_hhmm

router = APIRouter(prefix="/api", tags=["admin"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---- users ---------------------------------------------------------------------------------------
@router.get("/admin/users")
def list_users(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [serialize.user(u) for u in db.scalars(select(User).order_by(User.employee_id))]


@router.post("/admin/users")
def create_user(body: UserIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    if not valid_pin(body.pin):
        raise HTTPException(422, "PIN must be 4 digits")
    emp = body.employee_id.strip().upper()
    if db.scalar(select(User).where(func.upper(User.employee_id) == emp)):
        raise HTTPException(409, "Employee ID already exists")
    new = User(**body.model_dump(exclude={"pin", "employee_id"}), employee_id=emp, pin_hash=hash_pin(body.pin))
    db.add(new)
    db.flush()
    audit.record(db, user, "user", new.employee_id, "create", None, audit.snapshot(new))
    db.commit()
    return serialize.user(new)


@router.patch("/admin/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if target.id == user.id and (body.active is False or (body.role and body.role != "admin")):
        raise HTTPException(409, "You cannot remove your own admin access")
    before = audit.snapshot(target)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(target, key, value)
    audit.record(db, user, "user", target.employee_id, "update", before, audit.snapshot(target))
    db.commit()
    return serialize.user(target)


@router.post("/admin/users/{user_id}/pin")
def reset_pin(user_id: int, body: PinReset, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if not valid_pin(body.pin):
        raise HTTPException(422, "PIN must be 4 digits")
    target.pin_hash = hash_pin(body.pin)
    target.failed_attempts = 0
    target.locked_until = None
    audit.record(db, user, "user", target.employee_id, "pin_reset", None, None)
    db.commit()
    return {"ok": True}


# ---- glossary ------------------------------------------------------------------------------------
@router.get("/glossary")
def list_glossary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [serialize.glossary(g) for g in db.scalars(select(Glossary).order_by(Glossary.term_en))]


@router.post("/admin/glossary")
def add_term(body: GlossaryIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    g = Glossary(**body.model_dump())
    db.add(g)
    db.flush()
    audit.record(db, user, "glossary", g.id, "create", None, audit.snapshot(g))
    db.commit()
    return serialize.glossary(g)


@router.patch("/admin/glossary/{term_id}")
def edit_term(term_id: int, body: GlossaryIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    g = db.get(Glossary, term_id)
    if g is None:
        raise HTTPException(404, "Term not found")
    before = audit.snapshot(g)
    for key, value in body.model_dump().items():
        setattr(g, key, value)
    audit.record(db, user, "glossary", g.id, "update", before, audit.snapshot(g))
    db.commit()
    return serialize.glossary(g)


# ---- settings and audit --------------------------------------------------------------------------
@router.get("/admin/settings")
def get_settings(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return settings_store.all_settings(db)


@router.put("/admin/settings/{key}")
def put_setting(key: str, body: SettingIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    if key not in settings_store.DEFAULTS:
        raise HTTPException(404, "Unknown setting")
    default = settings_store.DEFAULTS[key]
    if isinstance(default, (int, float)) and not isinstance(body.value, (int, float)):
        raise HTTPException(422, f"{key} must be a number")
    if key == "shifts":
        _check_shifts(body.value)
    settings_store.put(db, user, key, body.value)
    db.commit()
    return settings_store.all_settings(db)


def _check_shifts(value) -> None:
    if not isinstance(value, list) or not value:
        raise HTTPException(422, "shifts must be a list")
    for s in value:
        try:
            assert s["name"]
            parse_hhmm(s["start"])
            parse_hhmm(s["end"])
        except (KeyError, ValueError, AssertionError, TypeError, AttributeError):
            raise HTTPException(422, "Each shift needs name, start (HH:MM) and end (HH:MM)")


@router.get("/admin/audit")
def audit_trail(
    entity: str = "", limit: int = Query(100, le=1000), user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    q = select(AuditLog).order_by(AuditLog.at.desc()).limit(limit)
    if entity:
        q = q.where(AuditLog.entity == entity)
    names = {u.id: u.name for u in db.scalars(select(User))}
    return [
        {
            "id": a.id,
            "at": a.at.isoformat(),
            "user": names.get(a.user_id, "system"),
            "entity": a.entity,
            "entity_id": a.entity_id,
            "action": a.action,
            "before": a.before,
            "after": a.after,
        }
        for a in db.scalars(q)
    ]


@router.get("/admin/ai-usage")
def ai_usage(days: int = 30, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            AICall.purpose,
            AICall.model,
            func.count(AICall.id),
            func.sum(AICall.input_tokens),
            func.sum(AICall.output_tokens),
            func.sum(AICall.cost_usd),
            func.sum(func.cast(AICall.ok, Integer)),
        )
        .where(AICall.created_at >= since)
        .group_by(AICall.purpose, AICall.model)
    ).all()
    sessions = db.scalar(select(func.count(AISession.id)).where(AISession.created_at >= since)) or 0
    total = sum(float(r[5] or 0) for r in rows)
    return {
        "days": days,
        "sessions": sessions,
        "total_cost_usd": round(total, 4),
        "cost_per_100_sessions_usd": round(total / sessions * 100, 2) if sessions else None,
        "by_purpose": [
            {
                "purpose": r[0],
                "model": r[1],
                "calls": r[2],
                "input_tokens": int(r[3] or 0),
                "output_tokens": int(r[4] or 0),
                "cost_usd": round(float(r[5] or 0), 4),
                "ok": int(r[6] or 0),
            }
            for r in rows
        ],
    }


# ---- import / export -----------------------------------------------------------------------------
@router.get("/admin/templates/{kind}.xlsx")
def template(kind: str, user: User = Depends(admin_only)):
    if kind not in ("machines", "logs", "parts"):
        raise HTTPException(404, "Unknown template")
    return Response(
        excel.template(kind),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="thunai-{kind}-template.xlsx"'},
    )


@router.post("/admin/import/machines")
async def import_machines(file: UploadFile = File(...), user: User = Depends(admin_only), db: Session = Depends(get_db)):
    result = excel.import_machines(db, user, await file.read())
    db.commit()
    return result


@router.post("/admin/import/logs")
async def import_logs(
    file: UploadFile = File(...),
    mark_verified: bool = Form(True),
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    result = excel.import_logs(db, user, await file.read(), mark_verified)
    db.commit()
    return result


@router.post("/admin/import/parts")
async def import_parts(file: UploadFile = File(...), user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Spare parts and stock from the stores system, Excel or CSV."""
    result = excel.import_parts(db, user, await file.read())
    db.commit()
    return result


@router.get("/export/logs.xlsx")
def export_logs(
    since: date | None = None,
    until: date | None = None,
    zone: str = "",
    machine_no: str = "",
    user: User = Depends(supervisor_or_admin),
    db: Session = Depends(get_db),
):
    content = excel.export_logs(db, since=since, until=until, zone=zone, machine_no=machine_no)
    name = f"thunai-logs-{since or 'all'}-{until or date.today()}.xlsx"
    return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})
