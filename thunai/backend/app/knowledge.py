"""Self-building knowledge base: automatic fault cards, review, versions and contradiction flags.

See SPEC.md section 11.1. Runs in the worker after each log is translated and classified
(tasks.enrich_log) and when a log is verified.
"""
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from . import audit, retrieval, safety, settings_store
from .ai import schemas as ai_schemas
from .ai.service import AIOutputError, call_json
from .models import BreakdownLog, FaultCard, Machine, User, utcnow
from .textutil import rank

COUNTED = ("closed", "verified")
HISTORY_DAYS = 3 * 365
LIVE_STATUSES = ("approved", "needs_review")  # cards the AI may use


def group_key(text: str) -> str:
    """Normalised symptom used to group logs and to find a card again ("Cylinder not returning")."""
    words = re.findall(r"[a-z0-9]+|[஀-௿]+", (text or "").lower())
    return " ".join(words[:8])


def log_symptom(log: BreakdownLog) -> str:
    if log.classification and log.classification.symptom_category:
        return log.classification.symptom_category
    return re.split(r"[,.;]", log.text("issue", "en"))[0]


def _log_text(log: BreakdownLog) -> str:
    parts = [log_symptom(log), log.text("issue", "en")]
    return " ".join(p for p in parts if p)


def _cause_text(log: BreakdownLog) -> str:
    parts = [log.text("root_cause", "en")]
    if log.classification and log.classification.failure_mode:
        parts.append(log.classification.failure_mode)
    return " ".join(p for p in parts if p)


@dataclass
class Group:
    key: str
    symptom: str
    logs: list[BreakdownLog]
    machine_id: int | None
    machine_type_id: int | None


def _candidates(db: Session, machine: Machine) -> list[BreakdownLog]:
    since = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    if machine.machine_type_id:
        scope = or_(
            BreakdownLog.machine_id == machine.id,
            BreakdownLog.machine.has(Machine.machine_type_id == machine.machine_type_id),
        )
    else:
        scope = BreakdownLog.machine_id == machine.id
    return list(
        db.scalars(
            select(BreakdownLog)
            .where(scope, BreakdownLog.status.in_(COUNTED), BreakdownLog.reported_at >= since)
            .options(
                selectinload(BreakdownLog.texts),
                selectinload(BreakdownLog.parts),
                selectinload(BreakdownLog.classification),
                selectinload(BreakdownLog.machine),
            )
            .order_by(BreakdownLog.reported_at)
        )
    )


def similar_logs(db: Session, log: BreakdownLog, candidates: list[BreakdownLog]) -> list[BreakdownLog]:
    """Logs describing the same symptom: same symptom category, or keyword similarity ≥ cutoff."""
    cutoff = float(settings_store.get(db, "similarity_cutoff"))
    key = group_key(log_symptom(log))
    variants = retrieval.glossary_variants(retrieval.active_glossary(db))
    scores = rank(_log_text(log), [_log_text(c) for c in candidates], variants)
    return [c for c, score in zip(candidates, scores) if c.id == log.id or group_key(log_symptom(c)) == key or score >= cutoff]


def _cards_for(db: Session, machine: Machine, statuses: tuple[str, ...]) -> list[FaultCard]:
    scope = [FaultCard.machine_id == machine.id]
    if machine.machine_type_id:
        scope.append((FaultCard.machine_type_id == machine.machine_type_id) & FaultCard.machine_id.is_(None))
    return list(db.scalars(select(FaultCard).where(FaultCard.status.in_(statuses), or_(*scope))))


def _matches_card(db: Session, card: FaultCard, log: BreakdownLog) -> bool:
    if card.group_key and card.group_key == group_key(log_symptom(log)):
        return True
    cutoff = float(settings_store.get(db, "similarity_cutoff"))
    return rank(_log_text(log), [f"{card.symptom} {card.group_key}"])[0] >= cutoff


def _cause_known(db: Session, card: FaultCard, log: BreakdownLog) -> bool:
    cause = _cause_text(log)
    if not cause.strip():
        return True  # nothing to contradict
    cutoff = float(settings_store.get(db, "similarity_cutoff"))
    known = [c.get("cause", "") for c in card.causes or []]
    if any(k.lower().strip() == log.text("root_cause", "en").lower().strip() for k in known):
        return True
    return any(score >= cutoff for score in rank(cause, known)) if known else False


def check_contradictions(db: Session, log: BreakdownLog) -> list[FaultCard]:
    """Flag live cards whose symptom matches the log but whose causes do not include its root cause."""
    flagged = []
    for card in _cards_for(db, log.machine, LIVE_STATUSES):
        if log.id in (card.source_log_ids or []) or log.id in (card.flagged_log_ids or []):
            continue
        if not _matches_card(db, card, log) or _cause_known(db, card, log):
            continue
        before = {"status": card.status, "flagged_log_ids": list(card.flagged_log_ids or [])}
        card.status = "needs_review"
        card.flagged_log_ids = [*(card.flagged_log_ids or []), log.id]
        note = f"{log.log_no}: root cause \"{log.text('root_cause', 'en')}\" is not among this card's causes."
        card.review_note = f"{card.review_note}\n{note}".strip()
        audit.record(db, None, "fault_card", card.id, "flagged", before,
                     {"status": card.status, "flagged_log_ids": card.flagged_log_ids})
        flagged.append(card)
    return flagged


def find_group(db: Session, log: BreakdownLog) -> Group | None:
    """The group this log belongs to, at machine scope if big enough, else machine-type scope."""
    threshold = int(settings_store.get(db, "similar_logs_threshold"))
    machine = log.machine
    group = similar_logs(db, log, _candidates(db, machine))
    on_machine = [g for g in group if g.machine_id == machine.id]
    symptoms = Counter(log_symptom(g) for g in group)
    symptom = symptoms.most_common(1)[0][0] if symptoms else log_symptom(log)
    key = group_key(symptom)
    if len(on_machine) >= threshold:
        return Group(key, symptom, on_machine, machine.id, None)
    if machine.machine_type_id and len(group) >= threshold:
        return Group(key, symptom, group, None, machine.machine_type_id)
    return None


def _existing_card(db: Session, group: Group) -> FaultCard | None:
    q = select(FaultCard).where(FaultCard.group_key == group.key)
    q = q.where(FaultCard.machine_id == group.machine_id) if group.machine_id else q.where(
        FaultCard.machine_type_id == group.machine_type_id, FaultCard.machine_id.is_(None)
    )
    cards = list(db.scalars(q.order_by(FaultCard.id.desc())))
    return next((c for c in cards if c.status != "retired"), None)


def _validator(log_refs: set[str]):
    def validate(out: ai_schemas.DraftCardOut) -> ai_schemas.DraftCardOut:
        if not out.steps:
            raise AIOutputError("The card needs at least one fix step.")
        for step in out.steps:
            phrase = safety.unsafe_instruction(f"{step.en}. {step.ta}")
            if phrase:
                raise AIOutputError(f"Unsafe step '{phrase}'. Never suggest bypassing safety devices.")
        for c in out.causes:
            c.log_refs = [r for r in c.log_refs if r in log_refs]
        return out

    return validate


def _log_line(log: BreakdownLog) -> str:
    parts = ", ".join(f"{p.description} x{p.qty:g}" for p in log.parts) or "none"
    return (
        f"[{retrieval.log_ref(log)}] ({log.status}; machine {log.machine.machine_no}; "
        f"{(log.shift_date or log.reported_at.date()).isoformat()}; downtime {log.downtime_min if log.downtime_min is not None else '?'} min) "
        f"Issue: {log.text('issue', 'en')}. Root cause: {log.text('root_cause', 'en') or 'not recorded'}. "
        f"Fix: {log.text('corrective_action', 'en') or 'not recorded'}. Parts: {parts}."
    )


def draft_card(db: Session, group: Group, replaces: FaultCard | None = None, user: User | None = None) -> FaultCard | None:
    """Ask the AI to write a card from the group's logs. Counts and averages are computed here."""
    logs = group.logs
    refs = {retrieval.log_ref(l): l for l in logs}
    machine = logs[-1].machine
    info: dict = {}
    out, error = call_json(
        db,
        purpose="draft_fault_card",
        prompt_name="draft_fault_card",
        tier="diagnosis",
        variables={
            "machine": retrieval.format_machine(machine)
            + ("" if group.machine_id else " (card for every machine of this type)"),
            "components": retrieval.format_components([c for c in machine.components if c.active]),
            "glossary": retrieval.format_glossary(retrieval.active_glossary(db)),
            "symptom": group.symptom,
            "logs": "\n".join(_log_line(l) for l in logs),
        },
        out_model=ai_schemas.DraftCardOut,
        max_tokens=8000,
        hints={"symptom": group.symptom, "logs": [_mock_hint(l) for l in logs]},
        validate=_validator(set(refs)),
        info=info,
    )
    if out is None:
        return None
    causes, counted = [], set()
    for c in out.causes:
        ids = [refs[r].id for r in c.log_refs if refs[r].id not in counted]
        counted.update(ids)
        causes.append({"cause": c.cause_en, "cause_ta": c.cause_ta, "count": len(ids), "log_ids": ids})
    causes.sort(key=lambda c: -c["count"])  # ranked by how often each cause occurred
    downtimes = [l.downtime_min for l in logs if l.downtime_min is not None]
    card = FaultCard(
        machine_id=group.machine_id,
        machine_type_id=group.machine_type_id,
        group_key=group.key,
        symptom=out.symptom_en,
        symptom_ta=out.symptom_ta,
        causes=causes,
        steps_en=[s.en for s in out.steps],
        steps_ta=[s.ta for s in out.steps],
        parts=out.parts,
        tools=out.tools,
        avg_fix_min=round(sum(downtimes) / len(downtimes)) if downtimes else None,
        source_log_ids=[l.id for l in logs],
        status="draft",
        version=1,
        drafted_at=utcnow(),
        ai_model=info.get("model", ""),
        replaces_id=replaces.id if replaces else None,
    )
    db.add(card)
    db.flush()
    audit.record(db, user, "fault_card", card.id, "draft", None, {"group_key": card.group_key, "logs": card.source_log_ids})
    return card


def _mock_hint(log: BreakdownLog) -> dict:
    return {
        "ref": retrieval.log_ref(log),
        "symptom": log_symptom(log),
        "issue_en": log.text("issue", "en"),
        "issue_ta": log.text("issue", "ta"),
        "cause_en": log.text("root_cause", "en"),
        "cause_ta": log.text("root_cause", "ta"),
        "fix_en": log.text("corrective_action", "en"),
        "fix_ta": log.text("corrective_action", "ta"),
        "parts": [p.description for p in log.parts],
    }


def update_for_log(db: Session, log_id: int) -> dict:
    """After a log is enriched or verified: flag contradicted cards, then draft a card if due."""
    log = db.scalar(
        select(BreakdownLog)
        .where(BreakdownLog.id == log_id)
        .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.classification), selectinload(BreakdownLog.machine))
    )
    if log is None or log.status not in COUNTED:
        return {"flagged": [], "drafted": None}
    flagged = [c.id for c in check_contradictions(db, log)]
    group = find_group(db, log)
    drafted = None
    if group:
        existing = _existing_card(db, group)
        threshold = int(settings_store.get(db, "similar_logs_threshold"))
        rejected_again = (
            existing is not None
            and existing.status == "rejected"
            and len(group.logs) >= len(existing.source_log_ids or []) + threshold
        )
        if existing is None or rejected_again:
            card = draft_card(db, group)
            drafted = card.id if card else None
    return {"flagged": flagged, "drafted": drafted}


# ---- supervisor actions --------------------------------------------------------------------------
def snapshot(card: FaultCard) -> dict:
    return {
        "version": card.version,
        "symptom": card.symptom,
        "symptom_ta": card.symptom_ta,
        "causes": card.causes,
        "steps_en": card.steps_en,
        "steps_ta": card.steps_ta,
        "parts": card.parts,
        "tools": card.tools,
        "approved_by": card.approved_by,
        "approved_at": card.approved_at.isoformat() if card.approved_at else None,
        "archived_at": utcnow().isoformat(),
    }


CONTENT_FIELDS = ("symptom", "symptom_ta", "causes", "steps_en", "steps_ta", "parts", "tools")


def edit(db: Session, user: User, card: FaultCard, changes: dict) -> FaultCard:
    if card.status in ("retired", "rejected"):
        raise HTTPException(409, f"A {card.status} card cannot be edited")
    for key in ("steps_en", "steps_ta"):
        for step in changes.get(key) or []:
            phrase = safety.unsafe_instruction(step)
            if phrase:
                raise HTTPException(422, f"Unsafe step: '{phrase}'")
    before = audit.snapshot(card)
    if card.status in LIVE_STATUSES and any(k in changes and changes[k] != getattr(card, k) for k in CONTENT_FIELDS):
        # Editing a card in use is an approval of the new content: keep the old one in history.
        card.history = [*(card.history or []), snapshot(card)]
        card.version += 1
        card.approved_by = user.id
        card.approved_at = utcnow()
    for key in CONTENT_FIELDS:
        if key in changes:
            setattr(card, key, changes[key])
    audit.record(db, user, "fault_card", card.id, "update", before, audit.snapshot(card))
    return card


def approve(db: Session, user: User, card: FaultCard) -> FaultCard:
    if card.status not in ("draft", "needs_review"):
        raise HTTPException(409, f"A {card.status} card cannot be approved")
    before = audit.snapshot(card)
    if card.replaces_id:
        old = db.get(FaultCard, card.replaces_id)
        if old is not None and old.status != "retired":
            old_before = audit.snapshot(old)
            card.history = [*(old.history or []), snapshot(old)]
            card.version = old.version + 1
            old.status = "retired"
            old.review_note = f"Replaced by FC-{card.id}"
            audit.record(db, user, "fault_card", old.id, "retire", old_before, audit.snapshot(old))
    card.status = "approved"
    card.approved_by = user.id
    card.approved_at = utcnow()
    card.flagged_log_ids = []
    card.review_note = ""
    audit.record(db, user, "fault_card", card.id, "approve", before, audit.snapshot(card))
    return card


def reject(db: Session, user: User, card: FaultCard, reason: str) -> FaultCard:
    if card.status != "draft":
        raise HTTPException(409, "Only drafts can be rejected; retire an approved card instead")
    before = audit.snapshot(card)
    card.status = "rejected"
    card.review_note = reason
    audit.record(db, user, "fault_card", card.id, "reject", before, audit.snapshot(card))
    return card


def retire(db: Session, user: User, card: FaultCard, reason: str) -> FaultCard:
    if card.status not in LIVE_STATUSES:
        raise HTTPException(409, f"A {card.status} card cannot be retired")
    before = audit.snapshot(card)
    card.status = "retired"
    card.review_note = reason
    audit.record(db, user, "fault_card", card.id, "retire", before, audit.snapshot(card))
    return card


def redraft(db: Session, user: User, card: FaultCard) -> FaultCard:
    """Write a fresh draft from today's logs. An approved card stays in use until the draft is approved."""
    if card.status in ("retired", "rejected"):
        raise HTTPException(409, f"A {card.status} card cannot be re-drafted")
    source = db.scalar(
        select(BreakdownLog)
        .where(BreakdownLog.id.in_(card.source_log_ids or [0]))
        .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.classification), selectinload(BreakdownLog.machine))
        .order_by(BreakdownLog.reported_at.desc())
    )
    if source is None:
        raise HTTPException(409, "The card's source logs are not available")
    machine = source.machine
    group_logs = similar_logs(db, source, _candidates(db, machine))
    flagged = list(card.flagged_log_ids or [])
    extra = list(db.scalars(select(BreakdownLog).where(BreakdownLog.id.in_(flagged)))) if flagged else []
    logs = {l.id: l for l in group_logs + extra}
    if card.machine_id:
        logs = {i: l for i, l in logs.items() if l.machine_id == card.machine_id}
    group = Group(card.group_key, card.symptom, sorted(logs.values(), key=lambda l: l.reported_at),
                  card.machine_id, card.machine_type_id)
    new = draft_card(db, group, replaces=card if card.status in LIVE_STATUSES else None, user=user)
    if new is None:
        raise HTTPException(503, "The AI could not draft the card right now. Try again later.")
    if card.status == "draft":
        before = audit.snapshot(card)
        card.status = "retired"
        card.review_note = f"Replaced by draft FC-{new.id}"
        audit.record(db, user, "fault_card", card.id, "retire", before, audit.snapshot(card))
    return new
