"""Expert tips (SPEC.md 11.3): short know-how from experienced technicians, reviewed like logs."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import audit, jobs, retrieval
from .ai import schemas as ai_schemas
from .ai.service import call_json
from .models import ExpertTip, LogMedia, Machine, User, utcnow
from .textutil import detect_lang


def create(db: Session, user: User, machine: Machine, text: str, media_id: int | None) -> ExpertTip:
    original = text.strip()
    lang = detect_lang(original)
    tip = ExpertTip(
        machine_id=machine.id,
        author_id=user.id,
        original=original,
        original_lang=lang,
        english=original if lang == "en" else "",
        tamil=original if lang == "ta" else "",
        status="pending",
    )
    if media_id:
        media = db.get(LogMedia, media_id)
        if media and media.created_by == user.id:
            tip.media_id = media.id
    db.add(tip)
    db.flush()
    audit.record(db, user, "expert_tip", tip.id, "create", None, audit.snapshot(tip))
    jobs.enqueue(db, "enrich_tip", tip_id=tip.id)
    return tip


def translate(db: Session, tip: ExpertTip) -> None:
    if tip.english and tip.tamil:
        return
    out, _ = call_json(
        db,
        purpose="translate",
        prompt_name="translate",
        tier="extraction",
        variables={"glossary": retrieval.format_glossary(retrieval.active_glossary(db)), "text": tip.original},
        out_model=ai_schemas.TranslateOut,
        max_tokens=2000,
        hints={"text": tip.original},
    )
    if out is None:
        return
    tip.english = tip.english or out.en
    tip.tamil = tip.tamil or out.ta


def review(db: Session, user: User, tip: ExpertTip, approve: bool, reason: str = "") -> ExpertTip:
    if tip.status != "pending":
        raise HTTPException(409, f"This tip is already {tip.status}")
    if not approve and len(reason.strip()) < 2:
        raise HTTPException(422, "Give a reason for rejecting")
    before = audit.snapshot(tip)
    tip.status = "approved" if approve else "rejected"
    tip.reject_reason = "" if approve else reason.strip()
    tip.reviewed_by = user.id
    tip.reviewed_at = utcnow()
    audit.record(db, user, "expert_tip", tip.id, "approve" if approve else "reject", before, audit.snapshot(tip))
    if approve:
        jobs.enqueue(db, "index_item", kind="tip", item_id=tip.id)
    return tip
