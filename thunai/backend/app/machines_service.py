"""Machine registry, QR codes and the machine page (history, repeat faults, KPIs)."""
import io
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import segno
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import audit, kpi, serialize, settings_store
from .config import get_config
from .models import AISession, BreakdownLog, Component, FaultCard, Machine, MachineType, User
from .schemas import ComponentIn, MachineIn, MachineUpdate


def get_machine(db: Session, machine_no: str) -> Machine:
    machine = db.scalar(
        select(Machine)
        .where(func.upper(Machine.machine_no) == machine_no.strip().upper())
        .options(selectinload(Machine.components), selectinload(Machine.machine_type))
    )
    if machine is None:
        raise HTTPException(404, f"Machine {machine_no} not found")
    return machine


def qr_url(machine_no: str) -> str:
    return f"{get_config().public_base_url.rstrip('/')}/m/{quote(machine_no, safe='')}"


def qr_image(machine_no: str, kind: str) -> bytes:
    qr = segno.make(qr_url(machine_no), error="m")
    buf = io.BytesIO()
    if kind == "svg":
        qr.save(buf, kind="svg", scale=6, border=2, xmldecl=False, omitsize=True)  # viewBox: scales to fit
    else:
        qr.save(buf, kind="png", scale=10, border=2)
    return buf.getvalue()


def type_id(db: Session, name: str) -> int | None:
    name = (name or "").strip()
    if not name:
        return None
    existing = db.scalar(select(MachineType).where(func.lower(MachineType.name) == name.lower()))
    if existing:
        return existing.id
    mt = MachineType(name=name)
    db.add(mt)
    db.flush()
    return mt.id


def create_machine(db: Session, user: User | None, data: MachineIn) -> Machine:
    if db.scalar(select(Machine).where(func.upper(Machine.machine_no) == data.machine_no)):
        raise HTTPException(409, f"Machine {data.machine_no} already exists")
    values = data.model_dump(exclude={"machine_type"})
    machine = Machine(**values, machine_type_id=type_id(db, data.machine_type), qr_code=qr_url(data.machine_no))
    db.add(machine)
    db.flush()
    audit.record(db, user, "machine", machine.machine_no, "create", None, audit.snapshot(machine))
    return machine


def update_machine(db: Session, user: User | None, machine: Machine, data: MachineUpdate) -> Machine:
    before = audit.snapshot(machine)
    values = data.model_dump(exclude_unset=True, exclude={"machine_type"})
    for key, value in values.items():
        setattr(machine, key, value)
    if data.machine_type is not None:
        machine.machine_type_id = type_id(db, data.machine_type)
    db.flush()
    audit.record(db, user, "machine", machine.machine_no, "update", before, audit.snapshot(machine))
    return machine


def add_component(db: Session, user: User, machine: Machine, data: ComponentIn) -> Component:
    comp = Component(machine_id=machine.id, **data.model_dump())
    db.add(comp)
    db.flush()
    audit.record(db, user, "component", comp.id, "create", None, audit.snapshot(comp))
    return comp


def _counted_logs(db: Session, machine_ids: list[int], since: datetime):
    return db.scalars(
        select(BreakdownLog)
        .where(
            BreakdownLog.machine_id.in_(machine_ids),
            BreakdownLog.status.in_(kpi.COUNTED_STATUSES),
            BreakdownLog.reported_at >= since,
        )
        .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.classification))
    ).all()


def kpis(db: Session, machine_ids: list[int], period_days: int | None = None) -> dict[int, kpi.KPI]:
    period_days = period_days or int(settings_store.get(db, "kpi_period_days"))
    hours = float(settings_store.get(db, "planned_hours_per_day"))
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    downtimes: dict[int, list] = defaultdict(list)
    for log in _counted_logs(db, machine_ids, since):
        downtimes[log.machine_id].append(log.downtime_min)
    return {mid: kpi.compute(downtimes.get(mid, []), period_days, hours) for mid in machine_ids}


def _fault_key(log: BreakdownLog) -> tuple[str, str]:
    """(group key, display text) for repeat-fault counting."""
    if log.classification and log.classification.symptom_category:
        label = log.classification.symptom_category.strip()
    else:
        label = " ".join(re.split(r"[,.;]", log.text("issue", "en"))[0].split()[:6])
    return label.lower(), label


def top_faults(logs: list[BreakdownLog], limit: int = 5) -> list[dict]:
    groups: dict[str, dict] = {}
    for log in logs:
        key, label = _fault_key(log)
        if not key:
            continue
        g = groups.setdefault(key, {"symptom": label, "symptom_ta": "", "count": 0, "downtime": [], "last": ""})
        g["count"] += 1
        if not g["symptom_ta"]:
            g["symptom_ta"] = log.text("issue", "ta") if log.text("issue", "ta") != log.text("issue", "en") else ""
        if log.downtime_min is not None:
            g["downtime"].append(log.downtime_min)
        when = (log.shift_date or log.reported_at.date()).isoformat()
        g["last"] = max(g["last"], when)
    rows = sorted(groups.values(), key=lambda g: g["last"], reverse=True)
    rows.sort(key=lambda g: -g["count"])  # stable: most recent first among equal counts
    out = []
    for g in rows[:limit]:
        d = g.pop("downtime")
        g["avg_downtime_min"] = round(sum(d) / len(d)) if d else None
        out.append(g)
    return out


def machine_page(db: Session, machine: Machine) -> dict:
    period = int(settings_store.get(db, "kpi_period_days"))
    since = datetime.now(timezone.utc) - timedelta(days=period)
    timeline = db.scalars(
        select(BreakdownLog)
        .where(BreakdownLog.machine_id == machine.id, BreakdownLog.status != "rejected")
        .options(
            selectinload(BreakdownLog.texts),
            selectinload(BreakdownLog.machine),
            selectinload(BreakdownLog.technician),
            selectinload(BreakdownLog.verifier),
        )
        .order_by(BreakdownLog.reported_at.desc())
        .limit(40)
    ).all()
    counted = list(_counted_logs(db, [machine.id], since))
    cards = db.scalars(
        select(FaultCard)
        .where(
            FaultCard.status.in_(("approved", "needs_review")),
            (FaultCard.machine_id == machine.id)
            | ((FaultCard.machine_type_id == machine.machine_type_id) & FaultCard.machine_id.is_(None)),
        )
        .order_by(FaultCard.id)
    ).all()
    recent_sessions = db.scalar(
        select(func.count(AISession.id)).where(AISession.machine_id == machine.id, AISession.created_at >= since)
    )
    return {
        "machine": serialize.machine(machine, with_components=True),
        "open_logs": [serialize.log(l, full=False) for l in timeline if l.status in ("open", "draft")],
        "timeline": [serialize.log(l, full=False) for l in timeline if l.status not in ("draft",)],
        "top_faults": top_faults(counted),
        "fault_cards": [serialize.fault_card(c) for c in cards],
        "kpi": kpis(db, [machine.id], period)[machine.id].as_dict(),
        "ai_sessions_in_period": recent_sessions or 0,
    }
