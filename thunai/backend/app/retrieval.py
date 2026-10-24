"""Builds the evidence the AI may use, in the brief's priority order.

Tier 0  this breakdown now: photos read by the AI and the machine's PLC/SCADA alarm feed (Phase 3)
Tier 1  approved fault cards for this machine (cards flagged for review are included and labelled)
Tier 2  verified logs and approved expert tips for this machine
Tier 3  fault cards, logs and tips for the same machine type
Tier 4  manuals, drawings, alarm lists and overdue PM tasks for the machine or its type
Tier 5  closed logs on this machine that are not yet verified (labelled)
(no ref) general knowledge; the UI labels such steps "General suggestion"

Ranking is keyword similarity (textutil.rank), mixed with vector similarity when an embeddings
provider is configured (embeddings.py). Results are filtered to the machine or its type first, so
candidate sets stay small.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import alarm_feed, embeddings, parts, pm
from .config import get_config
from .models import (
    AlarmCode,
    BreakdownLog,
    Component,
    Document,
    DocumentChunk,
    ExpertTip,
    FaultCard,
    Glossary,
    LogMedia,
    Machine,
    PMTask,
    SparePart,
)
from .textutil import rank

TIER_LABELS = {
    0: "this breakdown now (photo or machine alarm feed)",
    1: "approved fault card, this machine",
    2: "verified log or expert tip, this machine",
    3: "same machine type",
    4: "manual, drawing, alarm list or PM plan",
    5: "not yet verified, this machine",
}
LIMITS = {0: 5, 1: 3, 2: 6, 3: 4, 4: 5, 5: 3}
MAX_PM_ITEMS = 2
MIN_SCORE = 0.08
HISTORY_DAYS = 3 * 365


@dataclass
class Item:
    ref: str
    kind: str  # fault_card | log | tip | doc | alarm | pm | scada | photo
    tier: int
    score: float
    machine_no: str
    when: str  # ISO date or ""
    text_en: str
    data: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return TIER_LABELS[self.tier]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["label"] = self.label
        return d


@dataclass
class Context:
    items: list[Item]
    glossary: list[Glossary]
    components: list[Component]
    parts: list[SparePart] = field(default_factory=list)

    @property
    def refs(self) -> set[str]:
        return {i.ref for i in self.items}


def glossary_variants(entries: list[Glossary]) -> dict[str, str]:
    out = {}
    for g in entries:
        for spoken in g.spoken_variants or []:
            out[spoken] = g.term_en
        if g.term_ta:
            out[g.term_ta] = g.term_en
    return out


def log_ref(log: BreakdownLog) -> str:
    return f"LOG-{log.log_no}"


def card_ref(card: FaultCard) -> str:
    return f"FC-{card.id}"


def log_item(log: BreakdownLog, tier: int, score: float) -> Item:
    when = log.shift_date or (log.reported_at.date() if log.reported_at else None)
    issue, cause, action = (log.text(f, "en") for f in ("issue", "root_cause", "corrective_action"))
    text = f"Issue: {issue}. Root cause: {cause or 'not recorded'}. Fix: {action or 'not recorded'}."
    if log.downtime_min is not None:
        text += f" Downtime {log.downtime_min} min."
    if log.alarm_code:
        text += f" Alarm {log.alarm_code}."
    return Item(
        ref=log_ref(log),
        kind="log",
        tier=tier,
        score=score,
        machine_no=log.machine.machine_no,
        when=when.isoformat() if when else "",
        text_en=text,
        data={
            "log_id": log.id,
            "status": log.status,
            "issue_en": issue,
            "issue_ta": log.text("issue", "ta"),
            "root_cause_en": cause,
            "root_cause_ta": log.text("root_cause", "ta"),
            "corrective_action_en": action,
            "corrective_action_ta": log.text("corrective_action", "ta"),
            "downtime_min": log.downtime_min,
        },
    )


def card_item(card: FaultCard, tier: int, score: float, machine_no: str) -> Item:
    causes = ", ".join(f"{c.get('cause')} ({c.get('count', 0)}x)" for c in card.causes or [])
    steps = " | ".join(card.steps_en or [])
    text = f"Symptom: {card.symptom}. Causes by frequency: {causes or 'n/a'}. Verified steps: {steps}."
    if card.status == "needs_review":
        text += " (A newer log does not match this card; it is waiting for supervisor review.)"
    if card.avg_fix_min:
        text += f" Average fix {card.avg_fix_min} min."
    return Item(
        ref=card_ref(card),
        kind="fault_card",
        tier=tier,
        score=score,
        machine_no=machine_no,
        when=card.approved_at.date().isoformat() if card.approved_at else "",
        text_en=text,
        data={
            "card_id": card.id,
            "symptom": card.symptom,
            "symptom_ta": card.symptom_ta,
            "causes": card.causes or [],
            "steps_en": card.steps_en or [],
            "steps_ta": card.steps_ta or [],
            "version": card.version,
            "avg_fix_min": card.avg_fix_min,
            "needs_review": card.status == "needs_review",
        },
    )


def tip_ref(tip: ExpertTip) -> str:
    return f"TIP-{tip.id}"


def tip_item(tip: ExpertTip, tier: int, score: float) -> Item:
    return Item(
        ref=tip_ref(tip),
        kind="tip",
        tier=tier,
        score=score,
        machine_no=tip.machine.machine_no,
        when=(tip.reviewed_at or tip.created_at).date().isoformat(),
        text_en=f"Expert tip from {tip.author.name}: {tip.text('en')}",
        data={"tip_id": tip.id, "text_en": tip.text("en"), "text_ta": tip.text("ta")},
    )


def chunk_ref(chunk: DocumentChunk) -> str:
    return f"DOC-{chunk.document_id}-p{chunk.page}"


def chunk_item(chunk: DocumentChunk, doc: Document, score: float, machine_no: str) -> Item:
    return Item(
        ref=chunk_ref(chunk),
        kind="doc",
        tier=4,
        score=score,
        machine_no=machine_no,
        when=doc.indexed_at.date().isoformat() if doc.indexed_at else "",
        text_en=f"{doc.title} ({doc.kind}), page {chunk.page}: {chunk.text[:900]}",
        data={"document_id": doc.id, "title": doc.title, "page": chunk.page, "kind": doc.kind},
    )


def alarm_ref(alarm: AlarmCode) -> str:
    return f"ALM-{alarm.code}"


def alarm_item(alarm: AlarmCode, machine_no: str) -> Item:
    return Item(
        ref=alarm_ref(alarm),
        kind="alarm",
        tier=4,
        score=1.0,
        machine_no=machine_no,
        when="",
        text_en=f"Alarm {alarm.code}: {alarm.message}. Cause: {alarm.cause or 'not listed'}. Remedy: {alarm.remedy or 'not listed'}.",
        data={"code": alarm.code, "message": alarm.message, "cause": alarm.cause, "remedy": alarm.remedy},
    )


def pm_item(task: PMTask, machine_no: str, on, score: float) -> Item:
    due = pm.due_on(task)
    late = (on - due).days if due else 0
    every = f"every {task.frequency_days} days; " if task.frequency_days else ""
    last = task.last_done_on.isoformat() if task.last_done_on else "not recorded"
    code = task.task_code
    return Item(
        ref=code if code.upper().startswith("PM") else f"PM-{code}",
        kind="pm",
        tier=4,
        score=score,
        machine_no=machine_no,
        when=due.isoformat() if due else "",
        text_en=f"PM task {task.task_code} '{task.title}' ({every}last done {last}) is overdue by {late} days.",
        data={"task_code": task.task_code, "title": task.title, "days_overdue": late, "last_done_on": last},
    )


def scada_item(row: dict, machine_no: str) -> Item:
    tz = ZoneInfo(get_config().plant_tz)
    first, last = row["first"].astimezone(tz), row["last"].astimezone(tz)
    state = "still active" if row.get("active") else "cleared"
    return Item(
        ref=f"SCADA-{row['code']}",
        kind="scada",
        tier=0,
        score=1.0 + row["count"] / 100,
        machine_no=machine_no,
        when=last.date().isoformat(),
        text_en=(
            f"Machine alarm feed: {row['code']} {row['message'] or ''} raised {row['count']} time(s) in the last "
            f"{alarm_feed.FEED_HOURS} h (first {first:%d %b %H:%M}, last {last:%d %b %H:%M} plant time); latest {state}."
        ),
        data={"code": row["code"], "message": row["message"], "count": row["count"], "last": last.isoformat(), "active": row.get("active")},
    )


def photo_item(media: LogMedia, machine_no: str) -> Item:
    o = media.observation or {}
    readings = []
    for r in o.get("readings", []):
        if r.get("legible") and r.get("value"):
            readings.append(f"{r['label']} about {r['value']} {r.get('unit', '')}".strip())
        else:
            readings.append(f"{r['label']}: could not be read")
    parts_text = [f"shows {o.get('shows_en', '')}"]
    if readings:
        parts_text.append("readings (approximate): " + "; ".join(readings))
    if o.get("screen_text"):
        parts_text.append(f"screen text: \"{o['screen_text'][:300]}\"")
    if o.get("alarm_codes"):
        parts_text.append("alarm codes on screen: " + ", ".join(o["alarm_codes"]))
    if o.get("damage_en"):
        parts_text.append(f"visible damage: {o['damage_en']}")
    return Item(
        ref=f"PHOTO-{media.id}",
        kind="photo",
        tier=0,
        score=2.0,
        machine_no=machine_no,
        when=media.created_at.date().isoformat(),
        text_en="Photo taken now, read by the AI: " + "; ".join(parts_text) + ".",
        data={"media_id": media.id, **{k: o.get(k) for k in ("shows_en", "shows_ta", "readings", "alarm_codes", "damage_en", "damage_ta", "screen_text")}},
    )


def lookup_alarm(db: Session, machine: Machine, code: str) -> AlarmCode | None:
    """The alarm-list entry for a code: this machine's list first, then its machine type's."""
    code = (code or "").strip()
    if not code:
        return None
    rows = list(
        db.scalars(
            select(AlarmCode).where(
                AlarmCode.active.is_(True),
                func.upper(AlarmCode.code) == code.upper(),  # exact match; no wildcards from user input
                or_(
                    AlarmCode.machine_id == machine.id,
                    (AlarmCode.machine_type_id == machine.machine_type_id) & AlarmCode.machine_id.is_(None)
                    if machine.machine_type_id
                    else False,
                ),
            )
        )
    )
    rows.sort(key=lambda a: 0 if a.machine_id == machine.id else 1)
    return rows[0] if rows else None


def _scores(db: Session, query: str, docs: list[str], keys: list[tuple[str, int]], variants: dict) -> list[float]:
    """Keyword similarity, mixed with vector similarity when embeddings are configured."""
    keyword = rank(query, docs, variants)
    vector = embeddings.similarities(db, query, keys)
    if vector is None:
        return keyword
    return [k if v is None else round(0.5 * k + 0.5 * v, 4) for k, v in zip(keyword, vector)]


def _log_doc(log: BreakdownLog) -> str:
    parts = [log.text(f, "en") for f in ("issue", "root_cause", "corrective_action")]
    if log.classification:
        parts += [log.classification.symptom_category, log.classification.failure_mode]
    return " ".join(p for p in parts if p)


def _ranked(db: Session, query: str, logs: list[BreakdownLog], variants: dict, alarm_code: str) -> list[float]:
    scores = _scores(db, query, [_log_doc(l) for l in logs], [("log", l.id) for l in logs], variants)
    alarms = [l.alarm_code for l in logs]
    if alarm_code:
        scores = [s + (0.3 if a and a.lower() == alarm_code.lower() else 0) for s, a in zip(scores, alarms)]
    return scores


def active_glossary(db: Session) -> list[Glossary]:
    return list(db.scalars(select(Glossary).where(Glossary.active.is_(True)).order_by(Glossary.term_en).limit(300)))


def build_context(
    db: Session, machine: Machine, query: str, alarm_code: str = "", photos: list[LogMedia] | tuple = ()
) -> Context:
    glossary = active_glossary(db)
    variants = glossary_variants(glossary)
    components = [c for c in machine.components if c.active]
    since = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    items: list[Item] = []

    # Tier 0: what is known about this breakdown now (photos read by the AI, the alarm feed).
    for media in photos:
        if (media.observation or {}).get("usable"):
            items.append(photo_item(media, machine.machine_no))
    for row in alarm_feed.counts(alarm_feed.recent(db, machine))[:3]:
        items.append(scada_item(row, machine.machine_no))

    # Machines of the same type (other than this one).
    sibling_ids: dict[int, str] = {}
    if machine.machine_type_id:
        for mid, mno in db.execute(
            select(Machine.id, Machine.machine_no).where(
                Machine.machine_type_id == machine.machine_type_id, Machine.id != machine.id
            )
        ):
            sibling_ids[mid] = mno

    # Fault cards: this machine (tier 1), the type or sibling machines (tier 3).
    card_filter = [FaultCard.machine_id == machine.id]
    if machine.machine_type_id:
        card_filter.append(FaultCard.machine_type_id == machine.machine_type_id)
    if sibling_ids:
        card_filter.append(FaultCard.machine_id.in_(sibling_ids))
    cards = list(
        db.scalars(select(FaultCard).where(FaultCard.status.in_(("approved", "needs_review")), or_(*card_filter)))
    )
    if cards:
        docs = [f"{c.symptom} {' '.join(x.get('cause', '') for x in c.causes or [])}" for c in cards]
        scores = _scores(db, query, docs, [("card", c.id) for c in cards], variants)
        for card, score in zip(cards, scores):
            if score < MIN_SCORE:
                continue
            tier = 1 if card.machine_id == machine.id else 3
            mno = machine.machine_no if card.machine_id in (None, machine.id) else sibling_ids.get(card.machine_id, "")
            items.append(card_item(card, tier, score, mno))

    # Logs for this machine and its siblings.
    machine_ids = [machine.id, *sibling_ids]
    logs = list(
        db.scalars(
            select(BreakdownLog)
            .where(
                BreakdownLog.machine_id.in_(machine_ids),
                BreakdownLog.status.in_(("closed", "verified")),
                BreakdownLog.reported_at >= since,
            )
            .options(
                selectinload(BreakdownLog.texts),
                selectinload(BreakdownLog.classification),
                selectinload(BreakdownLog.machine),
            )
            .order_by(BreakdownLog.reported_at.desc())
            .limit(600)
        )
    )
    if logs:
        scores = _ranked(db, query, logs, variants, alarm_code)
        for log, score in zip(logs, scores):
            if score < MIN_SCORE:
                continue
            if log.machine_id == machine.id:
                tier = 2 if log.status == "verified" else 5
            else:
                tier = 3
            items.append(log_item(log, tier, score))

    # Approved expert tips: this machine (tier 2) and machines of the same type (tier 3).
    tips = list(
        db.scalars(
            select(ExpertTip)
            .where(ExpertTip.status == "approved", ExpertTip.machine_id.in_(machine_ids))
            .options(selectinload(ExpertTip.machine), selectinload(ExpertTip.author))
        )
    )
    if tips:
        scores = _scores(db, query, [f"{t.text('en')} {t.original}" for t in tips], [("tip", t.id) for t in tips], variants)
        for tip, score in zip(tips, scores):
            if score >= MIN_SCORE:
                items.append(tip_item(tip, 2 if tip.machine_id == machine.id else 3, score))

    # Manuals, SOPs, drawings and alarm lists for this machine or its type (tier 4).
    doc_scope = [Document.machine_id == machine.id]
    if machine.machine_type_id:
        doc_scope.append((Document.machine_type_id == machine.machine_type_id) & Document.machine_id.is_(None))
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .join(Document)
            .where(Document.active.is_(True), Document.status == "indexed", or_(*doc_scope))
            .options(selectinload(DocumentChunk.document))
            .limit(3000)
        )
    )
    if chunks:
        scores = _scores(db, f"{query} {alarm_code}", [c.text for c in chunks], [("chunk", c.id) for c in chunks], variants)
        best: dict[str, Item] = {}
        for chunk, score in zip(chunks, scores):
            if score < MIN_SCORE:
                continue
            item = chunk_item(chunk, chunk.document, score, machine.machine_no)
            if item.ref not in best or best[item.ref].score < score:
                best[item.ref] = item
        items.extend(best.values())
    alarm = lookup_alarm(db, machine, alarm_code)
    if alarm:
        items.append(alarm_item(alarm, machine.machine_no))

    # Overdue PM tasks on this machine (tier 4): the most overdue first, keyword match as a tiebreak.
    on = pm.today()
    late = pm.overdue(db, machine, on)
    if late:
        scores = rank(query, [f"{t.title} {t.task_code}" for t in late], variants)
        late_items = [pm_item(t, machine.machine_no, on, 0.5 + sc) for t, sc in zip(late, scores)]
        late_items.sort(key=lambda i: (-i.data["days_overdue"], -i.score))
        items.extend(late_items[:MAX_PM_ITEMS])

    # Keep the best few per tier, in tier order (an exact alarm-code match always stays).
    chosen: list[Item] = []
    for tier in sorted(LIMITS):
        tier_items = sorted((i for i in items if i.tier == tier), key=lambda i: i.when, reverse=True)
        tier_items.sort(key=lambda i: (i.kind != "alarm", -i.score))  # stable: newest first among equals
        chosen.extend(tier_items[: LIMITS[tier]])
    return Context(items=chosen, glossary=glossary, components=components, parts=parts.for_machine(db, machine))


def format_context(ctx: Context) -> str:
    if not ctx.items:
        return "No matching history for this machine or its type."
    lines = []
    for i in ctx.items:
        lines.append(f"[{i.ref}] ({i.label}; machine {i.machine_no}; {i.when or 'no date'}) {i.text_en}")
    return "\n".join(lines)


def format_glossary(entries: list[Glossary], limit: int = 120) -> str:
    rows = []
    for g in entries[:limit]:
        spoken = ", ".join(g.spoken_variants or [])
        rows.append(f"- {g.term_en} = {g.term_ta or '-'}" + (f"; spoken: {spoken}" if spoken else ""))
    return "\n".join(rows) or "(empty)"


def format_components(components: list[Component]) -> str:
    rows = [
        f"- {c.name} ({c.category}" + (f", part {c.part_no}" if c.part_no else "") + (f", {c.location}" if c.location else "") + ")"
        for c in components
    ]
    return "\n".join(rows) or "(none recorded)"


def format_parts(rows: list[SparePart], limit: int = 60) -> str:
    """Spare parts for the prompt. Stock is what the stores system last reported."""
    out = []
    for p in rows[:limit]:
        if p.stock_qty is None:
            stock = "stock not known"
        else:
            stock = f"stock {p.stock_qty:g} {p.unit}".strip() + (f" at {p.location}" if p.location else "")
            if p.stock_at:
                stock += f" (as of {p.stock_at.date().isoformat()})"
            if p.low:
                stock += ", LOW"
        alts = f"; also known as {', '.join(p.alt_part_nos)}" if p.alt_part_nos else ""
        out.append(f"- {p.part_no}: {p.description}{alts}; {stock}")
    return "\n".join(out) or "(no spare parts recorded for this machine)"


def format_machine(m: Machine) -> str:
    return (
        f"{m.machine_no}: {m.name}; type {m.machine_type.name if m.machine_type else 'n/a'}; zone {m.zone}; "
        f"line {m.line or '-'}; make {m.make or '-'} {m.model or ''}; PLC {m.plc_model or '-'}; "
        f"criticality {m.criticality}; key components: {m.key_components or '-'}"
    )


def evidence(sources: list[dict], refs: list[str], machine_no: str) -> dict:
    """What "Why this step?" shows: the cited items plus a short summary."""
    by_ref = {s["ref"]: s for s in sources}
    cited = [by_ref[r] for r in refs if r in by_ref]
    logs_here = [c for c in cited if c["kind"] == "log" and c["machine_no"] == machine_no]
    dates = sorted(c["when"] for c in logs_here if c["when"])
    return {
        "items": cited,
        "logs_this_machine": len(logs_here),
        "last_date": dates[-1] if dates else "",
        "fault_cards": [c["ref"] for c in cited if c["kind"] == "fault_card"],
        "general": not cited,
    }

