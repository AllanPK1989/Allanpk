"""Keeps optional embeddings up to date (no-op unless an embeddings provider is configured)."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import embeddings
from .models import BreakdownLog, DocumentChunk, ExpertTip, FaultCard


def _log_text(log: BreakdownLog) -> str:
    parts = [log.text(f, "en") for f in ("issue", "root_cause", "corrective_action")]
    if log.classification:
        parts += [log.classification.symptom_category, log.classification.failure_mode]
    return " ".join(p for p in parts if p)


def _card_text(card: FaultCard) -> str:
    return f"{card.symptom} {' '.join(c.get('cause', '') for c in card.causes or [])}"


def index_item(db: Session, kind: str, item_id: int) -> int:
    if not embeddings.enabled():
        return 0
    if kind == "log":
        log = db.scalar(
            select(BreakdownLog).where(BreakdownLog.id == item_id)
            .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.classification))
        )
        return embeddings.store(db, [("log", log.id, _log_text(log))]) if log else 0
    if kind == "card":
        card = db.get(FaultCard, item_id)
        return embeddings.store(db, [("card", card.id, _card_text(card))]) if card else 0
    if kind == "tip":
        tip = db.get(ExpertTip, item_id)
        return embeddings.store(db, [("tip", tip.id, f"{tip.text('en')} {tip.original}")]) if tip else 0
    if kind == "document":
        chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == item_id)).all()
        return embeddings.store(db, [("chunk", c.id, c.text) for c in chunks])
    raise ValueError(kind)


def reindex_all(db: Session) -> dict:
    """Embed every record (CLI `reindex`); records whose text did not change are skipped."""
    counts = {}
    logs = db.scalars(
        select(BreakdownLog).where(BreakdownLog.status.in_(("closed", "verified")))
        .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.classification))
    ).all()
    counts["logs"] = embeddings.store(db, [("log", l.id, _log_text(l)) for l in logs])
    cards = db.scalars(select(FaultCard).where(FaultCard.status.in_(("approved", "needs_review")))).all()
    counts["cards"] = embeddings.store(db, [("card", c.id, _card_text(c)) for c in cards])
    tips = db.scalars(select(ExpertTip).where(ExpertTip.status == "approved")).all()
    counts["tips"] = embeddings.store(db, [("tip", t.id, f"{t.text('en')} {t.original}") for t in tips])
    chunks = db.scalars(select(DocumentChunk)).all()
    counts["chunks"] = embeddings.store(db, [("chunk", c.id, c.text) for c in chunks])
    return counts
