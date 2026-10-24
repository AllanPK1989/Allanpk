"""Breakdown logs: create, edit, submit, verify, AI field extraction and enrichment."""
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import audit, jobs, retrieval, settings_store
from .ai import schemas as ai_schemas
from .ai.service import call_json
from .config import get_config
from .models import (
    TEXT_FIELDS,
    BreakdownLog,
    LogClassification,
    LogMedia,
    LogPart,
    LogText,
    Machine,
    TranslationCache,
    User,
    utcnow,
)
from .schemas import LogIn, LogUpdate, PartIn, TextIn
from .shifts import downtime_minutes, shift_for
from .textutil import detect_lang, overlap_ratio

MANDATORY = ("issue", "corrective_action")
# The AI's "original" must come from the technician's words; below this overlap it is flagged.
ORIGINAL_MIN_OVERLAP = 0.7


def load_log(db: Session, log_id: int) -> BreakdownLog:
    log = db.scalar(
        select(BreakdownLog)
        .where(BreakdownLog.id == log_id)
        .options(
            selectinload(BreakdownLog.texts),
            selectinload(BreakdownLog.parts),
            selectinload(BreakdownLog.media),
            selectinload(BreakdownLog.classification),
            selectinload(BreakdownLog.machine),
        )
    )
    if log is None:
        raise HTTPException(404, "Log not found")
    return log


def snapshot(log: BreakdownLog) -> dict:
    data = audit.snapshot(log)
    data["texts"] = {t.field: {"original": t.original, "en": t.english, "ta": t.tamil} for t in log.texts}
    data["parts"] = [{"part_no": p.part_no, "description": p.description, "qty": p.qty} for p in log.parts]
    return data


def set_text(
    db: Session,
    log: BreakdownLog,
    field: str,
    original: str,
    *,
    en: str | None = None,
    ta: str | None = None,
    ai_filled: bool = False,
    unsure: bool = False,
) -> None:
    """Store a text field. A changed original clears old translations so they are redone."""
    row = next((t for t in log.texts if t.field == field), None)
    if row is None:
        row = LogText(field=field)
        log.texts.append(row)
    original = (original or "").strip()
    if original != row.original:
        lang = detect_lang(original) if original else ""
        row.original = original
        row.original_lang = lang
        row.english = original if lang == "en" else ""
        row.tamil = original if lang == "ta" else ""
        row.translated_at = None
    if en is not None and en.strip():
        row.english = en.strip()
    if ta is not None and ta.strip():
        row.tamil = ta.strip()
    row.ai_filled = ai_filled
    row.ai_unsure = unsure


def apply_text(db: Session, log: BreakdownLog, field: str, value: TextIn | None) -> None:
    if value is None:
        return
    original = value.original
    if not original and value.ai_filled:
        # Drafts from a session have no technician words yet; keep the AI text as en/ta only.
        set_text(db, log, field, "", en=value.en, ta=value.ta, ai_filled=True, unsure=value.unsure)
        return
    set_text(db, log, field, original, en=value.en, ta=value.ta, ai_filled=value.ai_filled, unsure=value.unsure)


def _set_parts(log: BreakdownLog, parts: list[PartIn]) -> None:
    # Parts are part of the log's form; the before/after lists are kept in the audit trail.
    log.parts.clear()
    for p in parts:
        if p.description.strip() or p.part_no.strip():
            log.parts.append(LogPart(part_no=p.part_no.strip(), description=p.description.strip(), qty=p.qty))


def _apply_times(db: Session, log: BreakdownLog, start, end, manual_downtime) -> None:
    if start is not None:
        log.start_at = start
    if end is not None:
        log.end_at = end
    computed = downtime_minutes(log.start_at, log.end_at)
    if computed is not None:
        log.downtime_min = computed
    elif manual_downtime is not None:
        log.downtime_min = max(manual_downtime, 0)
    moment = log.start_at or log.reported_at
    log.shift, log.shift_date = shift_for(moment, settings_store.get(db, "shifts"), get_config().plant_tz)


def _attach_media(db: Session, log: BreakdownLog, media_ids: list[int], user: User) -> None:
    for media_id in media_ids:
        media = db.get(LogMedia, media_id)
        if media and media.created_by == user.id and media.log_id in (None, log.id):
            media.log_id = log.id


def _check_mandatory(log: BreakdownLog) -> list[str]:
    missing = []
    for field in MANDATORY:
        row = next((t for t in log.texts if t.field == field), None)
        if row is None or not (row.original or row.english or row.tamil):
            missing.append(field)
    return missing


def _finish_submit(db: Session, log: BreakdownLog, still_down: bool) -> None:
    missing = _check_mandatory(log)
    if missing:
        raise HTTPException(422, {"missing": missing, "message": "Fill the required fields"})
    log.status = "open" if still_down else "closed"
    log.escalated = log.escalated or still_down
    log.needs_confirmation = False
    for t in log.texts:  # submitting is the technician's confirmation
        t.ai_filled = False
        t.ai_unsure = False
    log.machine.status = "down" if still_down else "running"


def find_open_log(db: Session, machine: Machine) -> BreakdownLog | None:
    return db.scalar(
        select(BreakdownLog)
        .where(BreakdownLog.machine_id == machine.id, BreakdownLog.status == "open")
        .order_by(BreakdownLog.reported_at.desc())
    )


def create_log(db: Session, user: User, machine: Machine, data: LogIn, source: str | None = None) -> BreakdownLog:
    if data.client_uuid:
        existing = db.scalar(select(BreakdownLog).where(BreakdownLog.client_uuid == data.client_uuid))
        if existing:  # offline sync retried; return the log already stored
            return existing
    log = BreakdownLog(
        machine=machine,
        technician_id=user.id,
        technician_name=user.name,
        zone=machine.zone,
        reported_at=utcnow(),
        alarm_code=data.alarm_code.strip(),
        source=source or data.source,
        ai_session_id=data.ai_session_id,
        client_uuid=data.client_uuid,
        status="draft",
    )
    db.add(log)
    for field in TEXT_FIELDS:
        apply_text(db, log, field, getattr(data, field))
    _set_parts(log, data.parts)
    _apply_times(db, log, data.start_at, data.end_at, data.downtime_min)
    log.original_language = detect_lang(" ".join(t.original for t in log.texts))
    db.flush()
    log.log_no = f"BL-{log.reported_at.astimezone(ZoneInfo(get_config().plant_tz)).year}-{log.id:06d}"
    _attach_media(db, log, data.media_ids, user)
    if data.submit:
        _finish_submit(db, log, data.still_down)
    else:
        log.status = "open" if data.still_down else "draft"
        log.needs_confirmation = any(t.ai_filled for t in log.texts)
    audit.record(db, user, "breakdown_log", log.id, "create", None, snapshot(log))
    db.flush()
    if data.submit:
        jobs.enqueue(db, "enrich_log", log_id=log.id)
    return log


def update_log(db: Session, user: User, log: BreakdownLog, data: LogUpdate) -> BreakdownLog:
    if log.status in ("verified", "rejected") and user.role == "technician":
        raise HTTPException(403, "Verified or rejected logs can only be changed by a supervisor")
    if user.role == "technician" and log.technician_id not in (None, user.id) and log.status != "open":
        raise HTTPException(403, "You can only edit your own logs")
    before = snapshot(log)
    for field in TEXT_FIELDS:
        apply_text(db, log, field, getattr(data, field))
    if data.append_note.strip():
        # Adding to an existing open log: keep earlier words, append the new ones.
        row = next((t for t in log.texts if t.field == "corrective_action"), None)
        joined = ((row.original + "\n") if row and row.original else "") + data.append_note.strip()
        set_text(db, log, "corrective_action", joined)
    if data.parts is not None:
        _set_parts(log, data.parts)
    if data.alarm_code is not None:
        log.alarm_code = data.alarm_code.strip()
    _apply_times(db, log, data.start_at, data.end_at, data.downtime_min)
    _attach_media(db, log, data.media_ids, user)
    if data.submit:
        _finish_submit(db, log, data.still_down)
    after = snapshot(log)
    audit.record(db, user, "breakdown_log", log.id, "update", before, after)
    db.flush()
    if data.submit or before["texts"] != after["texts"]:
        jobs.enqueue(db, "enrich_log", log_id=log.id)
    return log


def verify_log(db: Session, user: User, log: BreakdownLog) -> BreakdownLog:
    if log.status not in ("closed", "open"):
        raise HTTPException(409, f"A {log.status} log cannot be verified")
    before = snapshot(log)
    log.status = "verified"
    log.verified_by = user.id
    log.verified_at = utcnow()
    audit.record(db, user, "breakdown_log", log.id, "verify", before, snapshot(log))
    jobs.enqueue(db, "update_knowledge", log_id=log.id)
    return log


def reject_log(db: Session, user: User, log: BreakdownLog, reason: str) -> BreakdownLog:
    before = snapshot(log)
    log.status = "rejected"
    log.reject_reason = reason
    log.verified_by = user.id
    log.verified_at = utcnow()
    audit.record(db, user, "breakdown_log", log.id, "reject", before, snapshot(log))
    return log


# ---- AI: extraction ------------------------------------------------------------------------------
def _check_originals(transcript: str):
    def validate(out: ai_schemas.ExtractOut) -> ai_schemas.ExtractOut:
        for name in TEXT_FIELDS:
            value: ai_schemas.FieldValue = getattr(out, name)
            if value.original and overlap_ratio(value.original, transcript) < ORIGINAL_MIN_OVERLAP:
                # Not the technician's words: keep the AI text but never as "original".
                value.unsure = True
                if not value.en:
                    value.en = value.original
                value.original = ""
        return out

    return validate


def extract_fields(db: Session, machine: Machine, transcript: str, log_id: int | None = None) -> dict:
    ctx_glossary = retrieval.format_glossary(retrieval.active_glossary(db))
    out, error = call_json(
        db,
        purpose="extract_log",
        prompt_name="extract_log",
        tier="extraction",
        variables={
            "machine": retrieval.format_machine(machine),
            "components": retrieval.format_components([c for c in machine.components if c.active]),
            "glossary": ctx_glossary,
            "transcript": transcript,
        },
        out_model=ai_schemas.ExtractOut,
        max_tokens=4000,
        hints={"transcript": transcript},
        log_id=log_id,
        validate=_check_originals(transcript),
    )
    if out is None:
        return {"ok": False, "error": error}
    data = out.model_dump()
    data["ok"] = True
    return data


def extraction_to_log_in(machine: Machine, extraction: dict, transcript: str) -> LogIn:
    """Turn an extraction into a log body. Times like "14:30" are read as plant time today."""
    tz = ZoneInfo(get_config().plant_tz)
    today = datetime.now(tz).date()

    def at(hhmm: str):
        if not hhmm:
            return None
        try:
            h, m = hhmm.split(":")
            return datetime(today.year, today.month, today.day, int(h), int(m), tzinfo=tz).astimezone(timezone.utc)
        except ValueError:
            return None

    def text(name: str) -> TextIn:
        v = extraction[name]
        return TextIn(original=v["original"], en=v["en"], ta=v["ta"], ai_filled=True, unsure=v["unsure"])

    return LogIn(
        machine_no=machine.machine_no,
        issue=text("issue"),
        root_cause=text("root_cause"),
        corrective_action=text("corrective_action"),
        start_at=at(extraction.get("start_time", "")),
        end_at=at(extraction.get("end_time", "")),
        downtime_min=extraction["downtime_min"] if extraction.get("downtime_min", -1) >= 0 else None,
        alarm_code=extraction.get("alarm_code", ""),
        parts=[PartIn(**p) for p in extraction.get("parts_replaced", [])],
        source="voice",
        submit=False,
    )


# ---- AI: enrichment (translate + classify) -------------------------------------------------------
def _cache_key(text: str, target: str, glossary_version: str) -> str:
    return hashlib.sha256(f"{target}|{glossary_version}|{text}".encode()).hexdigest()


def enrich_log(db: Session, log_id: int) -> None:
    """Fill missing English/Tamil versions and classify. Never changes the original words."""
    log = load_log(db, log_id)
    glossary = retrieval.active_glossary(db)
    components = [c for c in log.machine.components if c.active]
    glossary_version = str(max((g.updated_at.timestamp() for g in glossary), default=0))
    fields = {t.field: t.original or t.english or t.tamil for t in log.texts if (t.original or t.english or t.tamil)}
    if not fields:
        return

    # Use cached translations first.
    for t in log.texts:
        source = t.original
        if not source:
            continue
        for lang, attr in (("en", "english"), ("ta", "tamil")):
            if not getattr(t, attr):
                hit = db.scalar(
                    select(TranslationCache).where(TranslationCache.key == _cache_key(source, lang, glossary_version))
                )
                if hit:
                    setattr(t, attr, hit.translated)

    out, error = call_json(
        db,
        purpose="enrich_log",
        prompt_name="enrich_log",
        tier="extraction",
        variables={
            "machine": retrieval.format_machine(log.machine),
            "components": retrieval.format_components(components),
            "glossary": retrieval.format_glossary(glossary),
            "fields": "\n".join(f"- {k}: {v}" for k, v in fields.items()),
        },
        out_model=ai_schemas.EnrichOut,
        max_tokens=3000,
        hints={"fields": fields, "components": [{"name": c.name} for c in components]},
        log_id=log.id,
    )
    if out is None:
        return
    by_field = {f.field: f for f in out.fields}
    for t in log.texts:
        tr = by_field.get(t.field)
        if not tr:
            continue
        for lang, attr, value in (("en", "english", tr.en), ("ta", "tamil", tr.ta)):
            if value and not getattr(t, attr):
                setattr(t, attr, value)
                if t.original:
                    key = _cache_key(t.original, lang, glossary_version)
                    if not db.scalar(select(TranslationCache).where(TranslationCache.key == key)):
                        db.add(TranslationCache(key=key, target_lang=lang, source_text=t.original, translated=value))
        t.translated_at = utcnow()

    component_id = next((c.id for c in components if c.name.lower() == out.component_name.lower()), None)
    cls = log.classification
    if cls is None:
        cls = LogClassification(log_id=log.id)
        db.add(cls)
    if cls.edited_by is None:  # never overwrite a supervisor's correction
        cls.symptom_category = out.symptom_category[:120]
        cls.component_name = out.component_name[:200]
        cls.component_id = component_id
        cls.failure_mode = out.failure_mode[:200]
        cls.confidence = min(max(out.confidence, 0.0), 1.0)
    log.enriched_at = utcnow()
