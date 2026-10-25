from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from .. import audit, excel, serialize, settings_store
from ..config import get_config
from ..db import get_db
from ..models import AISession, AuditLog, CopilotCall, Glossary, User
from ..schemas import GlossaryIn, PinReset, SettingIn, UserIn, UserUpdate
from ..security import admin_only, current_user, hash_pin, supervisor_or_admin, valid_pin
from ..shifts import parse_hhmm

router = APIRouter(prefix="/api", tags=["admin"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---- users ---------------------------------------------------------------------------------------
def _upn(db: Session, value: str | None, user_id: int | None) -> str | None:
    """Normalise a Microsoft account (UPN) and refuse one that another user already has."""
    upn = (value or "").strip().lower() or None
    if upn and ("@" not in upn or " " in upn):
        raise HTTPException(422, "Microsoft account must look like name@company.com")
    if upn and db.scalar(select(User.id).where(func.lower(User.entra_upn) == upn, User.id != (user_id or 0))):
        raise HTTPException(409, "Another user already has this Microsoft account")
    return upn


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
    new = User(
        **body.model_dump(exclude={"pin", "employee_id", "entra_upn"}),
        employee_id=emp,
        pin_hash=hash_pin(body.pin),
        entra_upn=_upn(db, body.entra_upn, None),
    )
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
    changes = body.model_dump(exclude_unset=True)
    if "entra_upn" in changes:
        upn = _upn(db, changes.pop("entra_upn"), target.id)
        if upn != target.entra_upn:
            target.entra_upn = upn
            target.entra_oid = None  # a new account is bound again on its first use
    for key, value in changes.items():
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


@router.get("/admin/copilot-usage")
def copilot_usage(days: int = Query(30, ge=1, le=365), user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """The Copilot connection's set-up state and tool calls per tool (SPEC 13.3)."""
    cfg = get_config()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            CopilotCall.operation,
            func.count(CopilotCall.id),
            func.sum(func.cast(CopilotCall.ok, Integer)),
            func.count(func.distinct(CopilotCall.user_id)),
            func.max(CopilotCall.created_at),
        )
        .where(CopilotCall.created_at >= since)
        .group_by(CopilotCall.operation)
        .order_by(func.count(CopilotCall.id).desc())
    ).all()
    errors = db.scalars(
        select(CopilotCall).where(CopilotCall.created_at >= since, CopilotCall.ok.is_(False)).order_by(CopilotCall.id.desc()).limit(10)
    ).all()
    users = db.scalars(select(User).where(User.active.is_(True))).all()
    sessions = db.execute(
        select(AISession.channel, func.count(AISession.id)).where(AISession.created_at >= since).group_by(AISession.channel)
    ).all()
    return {
        "days": days,
        "enabled": cfg.copilot_enabled,
        "ready": cfg.copilot_ready,
        "tenant_set": bool(cfg.entra_tenant_id),
        "audience_set": bool(cfg.entra_audiences),
        "scope": cfg.entra_scope,
        "teams_url": cfg.copilot_teams_url,
        "users_active": len(users),
        "users_with_account": sum(1 for u in users if u.entra_upn),
        "users_linked": sum(1 for u in users if u.entra_oid),
        "sessions_by_channel": {c or "app": n for c, n in sessions},
        "calls": sum(r[1] for r in rows),
        "by_tool": [
            {"operation": r[0], "calls": r[1], "ok": int(r[2] or 0), "users": r[3], "last_at": r[4].isoformat() if r[4] else None}
            for r in rows
        ],
        "recent_errors": [
            {"at": e.created_at.isoformat(), "operation": e.operation, "status_code": e.status_code, "error": e.error}
            for e in errors
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
