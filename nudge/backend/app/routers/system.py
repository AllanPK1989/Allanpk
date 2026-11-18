"""Settings, push subscriptions, notification buttons, e-mail tests, export and backups."""
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.orm import Session

from .. import backup, digest, mailer, push, scheduler, settings_store, stt
from .. import tasks_service as ts
from ..ai import service as ai
from ..config import get_config
from ..db import get_db
from ..deps import prefs
from ..excel import export
from ..models import NotificationLog, Task
from ..schemas import PushActionIn, PushSubIn, PushUnsubIn
from ..security import read_action_token, require_auth
from ..settings_store import Prefs
from ..timeutil import iso_utc, local_now, tz

router = APIRouter(prefix="/api", tags=["system"])
authed = [Depends(require_auth)]
VERSION = "1.0.0"

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TIME_KEYS = {"briefing_time", "wrapup_time", "overdue_nag_time", "nudge_time", "quiet_start", "quiet_end"}
BOOL_KEYS = {"email_briefing", "email_wrapup", "push_reminders", "push_nudges", "push_briefing", "push_wrapup",
             "push_overdue"}


@router.get("/health")
def health():
    return {"ok": True, "version": VERSION}


@router.get("/settings", dependencies=authed)
def get_settings(db: Session = Depends(get_db)):
    cfg = get_config()
    recent = db.query(NotificationLog).order_by(NotificationLog.id.desc()).limit(15).all()
    return {
        "settings": settings_store.all_public(db),
        "status": {
            "version": VERSION,
            "demo": cfg.demo_mode,
            "ai": ai.usage_summary(db),
            "voice": stt.status(),
            "email_configured": mailer.configured(),
            "outbox": mailer.latest_outbox(),
            "push_devices": push.device_count(db),
            "backups": backup.list_backups()[:5],
        },
        "recent_notifications": [{"at": iso_utc(n.at), "kind": n.kind, "channel": n.channel, "title": n.title,
                                  "delivered": n.delivered, "error": n.error} for n in recent],
    }


@router.patch("/settings", dependencies=authed)
def patch_settings(body: dict, db: Session = Depends(get_db)):
    for key, value in body.items():
        if key not in settings_store.EDITABLE:
            raise HTTPException(422, f"Unknown setting: {key}")
        if key in TIME_KEYS and not (isinstance(value, str) and HHMM.match(value)):
            raise HTTPException(422, f"{key} must look like 07:30")
        if key in BOOL_KEYS and not isinstance(value, bool):
            raise HTTPException(422, f"{key} must be true or false")
        if key in ("stale_days", "default_nudge_days"):
            if not isinstance(value, int) or not (1 <= value <= 90):
                raise HTTPException(422, f"{key} must be a number of days between 1 and 90")
        if key == "timezone":
            if tz(str(value)).key != value:
                raise HTTPException(422, "Unknown timezone")
        if key == "digest_email" and value and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
            raise HTTPException(422, "That e-mail address doesn't look right")
        if key == "display_name":
            value = str(value or "").strip()[:40]
        settings_store.put(db, key, value)
    db.commit()
    return settings_store.all_public(db)


# ---- push ----------------------------------------------------------------------------------------

@router.get("/push/key", dependencies=authed)
def push_key(db: Session = Depends(get_db)):
    return {"public_key": push.public_key(db), "devices": push.device_count(db)}


@router.post("/push/subscribe", dependencies=authed)
def push_subscribe(body: PushSubIn, request: Request, db: Session = Depends(get_db)):
    try:
        push.subscribe(db, body.model_dump(), request.headers.get("user-agent", ""))
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"ok": True, "devices": push.device_count(db)}


@router.post("/push/unsubscribe", dependencies=authed)
def push_unsubscribe(body: PushUnsubIn, db: Session = Depends(get_db)):
    push.unsubscribe(db, body.endpoint)
    db.commit()
    return {"ok": True}


@router.post("/push/test", dependencies=authed)
def push_test(db: Session = Depends(get_db)):
    n = push.send(db, "test", "Nudge is set up", "Reminders will arrive like this one.", url="/settings", tag="test")
    db.commit()
    if n == 0:
        raise HTTPException(409, "No device accepted the test. Turn on notifications on this device first.")
    return {"delivered": n}


@router.post("/push/action")
def push_action(body: PushActionIn, db: Session = Depends(get_db)):
    """Buttons on a notification. The signed token stands in for the login, so Done and Snooze
    work straight from the lock screen."""
    task_id = read_action_token(body.token)
    if task_id is None:
        raise HTTPException(403, "This notification has expired")
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    p = Prefs(db)
    try:
        if body.action == "done":
            ts.close_task(db, p, task)
        elif body.action == "snooze_1h":
            ts.snooze(db, p, task, "1h")
        elif body.action == "tomorrow":
            ts.snooze(db, p, task, "tomorrow")
        elif body.action == "nudged":
            ts.mark_nudged(db, p, task)
        else:
            raise HTTPException(400, "Unknown action")
    except ts.TaskError as e:
        raise HTTPException(409, str(e))
    db.commit()
    return {"ok": True, "status": task.status}


# ---- e-mail digest -------------------------------------------------------------------------------

@router.get("/digest/preview", dependencies=authed, response_class=HTMLResponse)
def digest_preview(kind: str = "briefing", db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    _, html, _ = (digest.wrapup_email if kind == "wrapup" else digest.briefing_email)(db, p)
    return HTMLResponse(html, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})


@router.post("/digest/send-now", dependencies=authed)
def digest_send_now(kind: str = "briefing", db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    if not p.digest_email:
        raise HTTPException(409, "Add your e-mail address in Settings first")
    subject, html, text = (digest.wrapup_email if kind == "wrapup" else digest.briefing_email)(db, p)
    ok = mailer.send(db, kind, p.digest_email, subject, html, text)
    db.commit()
    if not ok and mailer.configured():
        raise HTTPException(502, "The e-mail server refused the message. See Recent notifications for the reason.")
    return {"sent": ok, "saved_to_outbox": not mailer.configured()}


@router.post("/briefing/push-now", dependencies=authed)
def briefing_push_now(db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    out = scheduler.run_briefing(db, p)
    db.commit()
    return out


# ---- export and backups --------------------------------------------------------------------------

@router.get("/export.xlsx", dependencies=authed)
def export_xlsx(db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    data = export(db, p)
    name = f"nudge-tasks-{local_now(p.zone).strftime('%Y-%m-%d')}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/backups", dependencies=authed)
def backups():
    return {"backups": backup.list_backups()}


@router.post("/backups", dependencies=authed)
def backup_now():
    path = backup.run_backup()
    if path is None:
        raise HTTPException(409, "Backups only work with the built-in SQLite database")
    return {"name": path.name}


@router.get("/backups/{name}", dependencies=authed)
def backup_download(name: str):
    path = backup.backup_file(name)
    if path is None:
        raise HTTPException(404, "Backup not found")
    return FileResponse(path, media_type="application/octet-stream", filename=name)
