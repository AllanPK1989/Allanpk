"""Job bodies. Each opens its own database session (see jobs.py)."""
import logging

from . import knowledge, logs_service, media
from .db import SessionLocal
from .models import LogMedia
from .schemas import TextIn

log = logging.getLogger("thunai.tasks")


def enrich_log(log_id: int) -> None:
    with SessionLocal() as db:
        logs_service.enrich_log(db, log_id)
        db.commit()
    update_knowledge(log_id)


def update_knowledge(log_id: int) -> None:
    """Flag fault cards the log contradicts and draft a new card when enough similar logs exist."""
    with SessionLocal() as db:
        result = knowledge.update_for_log(db, log_id)
        db.commit()
        if result["flagged"] or result["drafted"]:
            log.info("Knowledge update for log %s: %s", log_id, result)


def process_offline_voice(log_id: int, media_id: int, language: str) -> None:
    """A voice log recorded offline: transcribe after sync, then let the AI fill the form.

    The technician's typed words (if any) are kept; AI text only fills empty fields and stays
    marked until the technician confirms the log ("Needs your check").
    """
    with SessionLocal() as db:
        lg = logs_service.load_log(db, log_id)
        md = db.get(LogMedia, media_id)
        if md is None:
            return
        transcript = md.transcript or media.transcribe(db, md, language)
        if not transcript:
            lg.needs_confirmation = True
            db.commit()
            return
        extraction = logs_service.extract_fields(db, lg.machine, transcript, log_id=lg.id)
        filled = False
        if extraction.get("ok"):
            for field in ("issue", "root_cause", "corrective_action"):
                current = next((t for t in lg.texts if t.field == field), None)
                if current and (current.original or current.english):
                    continue
                v = extraction[field]
                value = TextIn(original=v["original"], en=v["en"], ta=v["ta"], ai_filled=True, unsure=v["unsure"])
                logs_service.apply_text(db, lg, field, value)
                filled = True
        lg.needs_confirmation = lg.needs_confirmation or filled or lg.status == "draft"
        db.commit()


def purge_expired_media() -> int:
    with SessionLocal() as db:
        count = media.purge_expired(db)
        db.commit()
        log.info("Purged %d expired media files", count)
        return count

