"""Builds the evidence the AI may use, in the brief's priority order.

Tier 1  approved fault cards for this machine
Tier 2  verified logs for this machine
Tier 3  approved fault cards and verified/closed logs for the same machine type
Tier 4  closed logs on this machine that are not yet verified (labelled)
Tier 5  general knowledge (no reference; the UI labels it)

Phase 1 ranks with keyword similarity (see textutil.rank). Results are filtered to the machine
or its type first, so candidate sets stay small.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .models import BreakdownLog, Component, FaultCard, Glossary, Machine
from .textutil import rank

TIER_LABELS = {
    1: "approved fault card, this machine",
    2: "verified log, this machine",
    3: "same machine type",
    4: "not yet verified, this machine",
}
MIN_SCORE = 0.08
HISTORY_DAYS = 3 * 365


@dataclass
class Item:
    ref: str
    kind: str  # fault_card | log
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
        },
    )


def _log_doc(log: BreakdownLog) -> str:
    parts = [log.text(f, "en") for f in ("issue", "root_cause", "corrective_action")]
    if log.classification:
        parts += [log.classification.symptom_category, log.classification.failure_mode]
    return " ".join(p for p in parts if p)


def _ranked(query, docs, variants, alarm_code, alarms):
    scores = rank(query, docs, variants)
    if alarm_code:
        scores = [s + (0.3 if a and a.lower() == alarm_code.lower() else 0) for s, a in zip(scores, alarms)]
    return scores


def active_glossary(db: Session) -> list[Glossary]:
    return list(db.scalars(select(Glossary).where(Glossary.active.is_(True)).order_by(Glossary.term_en).limit(300)))


def build_context(db: Session, machine: Machine, query: str, alarm_code: str = "") -> Context:
    glossary = active_glossary(db)
    variants = glossary_variants(glossary)
    components = [c for c in machine.components if c.active]
    since = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    items: list[Item] = []

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
    cards = list(db.scalars(select(FaultCard).where(FaultCard.status == "approved", or_(*card_filter))))
    if cards:
        docs = [f"{c.symptom} {' '.join(x.get('cause', '') for x in c.causes or [])}" for c in cards]
        scores = rank(query, docs, variants)
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
        scores = _ranked(query, [_log_doc(l) for l in logs], variants, alarm_code, [l.alarm_code for l in logs])
        for log, score in zip(logs, scores):
            if score < MIN_SCORE:
                continue
            if log.machine_id == machine.id:
                tier = 2 if log.status == "verified" else 4
            else:
                tier = 3
            items.append(log_item(log, tier, score))

    # Keep the best few per tier, in tier order.
    limits = {1: 3, 2: 6, 3: 4, 4: 3}
    chosen: list[Item] = []
    for tier in (1, 2, 3, 4):
        tier_items = sorted((i for i in items if i.tier == tier), key=lambda i: i.when, reverse=True)
        tier_items.sort(key=lambda i: -i.score)  # stable: newest first among equal scores
        chosen.extend(tier_items[: limits[tier]])
    return Context(items=chosen, glossary=glossary, components=components)


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

