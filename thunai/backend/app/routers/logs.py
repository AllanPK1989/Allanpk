import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import audit, jobs, logs_service, machines_service, media, serialize
from ..db import get_db
from ..models import BreakdownLog, LogClassification, Machine, User
from ..schemas import ExtractIn, LogIn, LogUpdate, RejectIn
from ..security import current_user, supervisor_or_admin

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _can_see(user: User, log: BreakdownLog) -> None:
    if user.role == "technician" and log.technician_id != user.id and log.zone != user.zone:
        raise HTTPException(403, "Not your log")


@router.get("")
def list_logs(
    scope: str = "mine",
    status: str = "",
    machine_no: str = "",
    needs_confirmation: bool | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = (
        select(BreakdownLog)
        .options(
            selectinload(BreakdownLog.texts),
            selectinload(BreakdownLog.machine),
            selectinload(BreakdownLog.technician),
            selectinload(BreakdownLog.verifier),
        )
        .order_by(BreakdownLog.reported_at.desc())
    )
    if scope == "mine" or (scope == "all" and user.role == "technician" and not user.zone):
        q = q.where(BreakdownLog.technician_id == user.id)
    elif scope == "zone" or (scope == "all" and user.role == "technician"):
        q = q.where(BreakdownLog.zone == user.zone)
    if status:
        q = q.where(BreakdownLog.status.in_(status.split(",")))
    if machine_no:
        q = q.join(Machine).where(Machine.machine_no == machine_no.upper())
    if needs_confirmation is not None:
        q = q.where(BreakdownLog.needs_confirmation.is_(needs_confirmation))
    return [serialize.log(l, full=False) for l in db.scalars(q.limit(limit).offset(offset))]


@router.get("/{log_id}")
def get_log(log_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    log = logs_service.load_log(db, log_id)
    _can_see(user, log)
    return serialize.log(log)


@router.post("")
def create_log(body: LogIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.get_machine(db, body.machine_no)
    log = logs_service.create_log(db, user, machine, body)
    db.commit()
    return serialize.log(logs_service.load_log(db, log.id))


@router.patch("/{log_id}")
def update_log(log_id: int, body: LogUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    log = logs_service.load_log(db, log_id)
    _can_see(user, log)
    logs_service.update_log(db, user, log, body)
    db.commit()
    return serialize.log(logs_service.load_log(db, log_id))


@router.post("/{log_id}/verify")
def verify(log_id: int, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    log = logs_service.verify_log(db, user, logs_service.load_log(db, log_id))
    db.commit()
    return serialize.log(logs_service.load_log(db, log.id))


@router.post("/{log_id}/reject")
def reject(log_id: int, body: RejectIn, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    log = logs_service.reject_log(db, user, logs_service.load_log(db, log_id), body.reason)
    db.commit()
    return serialize.log(logs_service.load_log(db, log.id))


@router.patch("/{log_id}/classification")
def edit_classification(
    log_id: int, body: dict, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)
):
    log = logs_service.load_log(db, log_id)
    cls = log.classification or LogClassification(log_id=log.id)
    db.add(cls)
    before = audit.snapshot(cls) if cls.id else None
    for key in ("symptom_category", "component_name", "failure_mode"):
        if key in body:
            setattr(cls, key, str(body[key])[:200])
    cls.edited_by = user.id
    db.flush()
    audit.record(db, user, "log_classification", cls.id, "update" if before else "create", before, audit.snapshot(cls))
    db.commit()
    return serialize.log(logs_service.load_log(db, log.id))


@router.post("/extract")
def extract(body: ExtractIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Voice or typed report → form fields (AI-filled, for the technician to check)."""
    machine = machines_service.get_machine(db, body.machine_no)
    result = logs_service.extract_fields(db, machine, body.transcript)
    db.commit()
    return result


@router.post("/offline")
def sync_offline(
    payload: str = Form(...),
    audio: UploadFile | None = File(None),
    language: str = Form("en"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """A log saved on the phone while offline. Transcription and AI filling run after sync."""
    try:
        body = LogIn(**json.loads(payload))
    except (ValueError, ValidationError) as e:
        raise HTTPException(422, f"Bad offline payload: {e}")
    body.client_uuid = body.client_uuid or uuid.uuid4().hex
    machine = machines_service.get_machine(db, body.machine_no)
    existing = db.scalar(select(BreakdownLog).where(BreakdownLog.client_uuid == body.client_uuid))
    if existing:
        return serialize.log(logs_service.load_log(db, existing.id))
    complete = all(getattr(body, f).original.strip() for f in ("issue", "corrective_action"))
    body.submit = body.submit and complete  # otherwise wait for transcription and confirmation
    log = logs_service.create_log(db, user, machine, body, source="voice" if audio else body.source)
    if audio is not None:
        md = media.save_upload(db, user, audio, "audio")
        md.log_id = log.id
        log.needs_confirmation = log.status == "draft"
        jobs.enqueue(db, "process_offline_voice", log_id=log.id, media_id=md.id, language=language)
    db.commit()
    return serialize.log(logs_service.load_log(db, log.id))
