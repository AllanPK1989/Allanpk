"""Alarm events from PLCs, SCADA or an alarm historian (SPEC 12.4).

Events arrive through POST /api/integrations/alarms. The newest active alarm pre-fills Ask Thunai and
New log on that machine, and the last 24 hours of alarms are evidence about the current breakdown.
No alarm opens a log by itself.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import settings_store
from .models import BreakdownLog, Machine, MachineAlarm, utcnow

FEED_HOURS = 24


def serialize(a: MachineAlarm) -> dict:
    return {
        "id": a.id,
        "machine_no": a.machine.machine_no,
        "code": a.code,
        "message": a.message,
        "raised_at": a.raised_at.isoformat(),
        "cleared_at": a.cleared_at.isoformat() if a.cleared_at else None,
        "source": a.source,
        "log_id": a.log_id,
    }


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def ingest(db: Session, events: list[dict], source: str) -> dict:
    """Store alarm events. Repeats (same event id, or same machine, code and raised time) are skipped,
    but a repeat may add the cleared time."""
    machines = {m.machine_no.upper(): m for m in db.scalars(select(Machine))}
    accepted = duplicates = 0
    errors: list[dict] = []
    for i, e in enumerate(events):
        machine = machines.get(str(e.get("machine_no") or "").strip().upper())
        code = str(e.get("code") or "").strip()[:60]
        if machine is None:
            errors.append({"row": i, "error": f"Unknown machine {e.get('machine_no')}"})
            continue
        if not code:
            errors.append({"row": i, "error": "Missing alarm code"})
            continue
        raised = _aware(e["raised_at"])
        cleared = _aware(e["cleared_at"]) if e.get("cleared_at") else None
        if raised > utcnow() + timedelta(minutes=5):
            errors.append({"row": i, "error": "raised_at is in the future (check the sender's clock)"})
            continue
        event_id = (str(e.get("event_id") or "").strip() or None)
        existing = None
        if event_id:
            existing = db.scalar(select(MachineAlarm).where(MachineAlarm.event_id == event_id))
        if existing is None:
            existing = db.scalar(
                select(MachineAlarm).where(
                    MachineAlarm.machine_id == machine.id, MachineAlarm.code == code, MachineAlarm.raised_at == raised
                )
            )
        if existing is not None:
            if cleared and not existing.cleared_at:
                existing.cleared_at = cleared
            duplicates += 1
            continue
        db.add(
            MachineAlarm(
                machine_id=machine.id,
                code=code,
                message=str(e.get("message") or "")[:1000],
                raised_at=raised,
                cleared_at=cleared,
                source=source[:80],
                event_id=event_id[:120] if event_id else None,
            )
        )
        db.flush()
        accepted += 1
    return {"accepted": accepted, "duplicates": duplicates, "errors": errors}


def active(db: Session, machine: Machine) -> MachineAlarm | None:
    """The newest alarm on the machine that is not cleared, raised within alarm_prefill_hours."""
    hours = float(settings_store.get(db, "alarm_prefill_hours"))
    return db.scalar(
        select(MachineAlarm)
        .where(
            MachineAlarm.machine_id == machine.id,
            MachineAlarm.cleared_at.is_(None),
            MachineAlarm.raised_at >= utcnow() - timedelta(hours=hours),
        )
        .order_by(MachineAlarm.raised_at.desc())
        .limit(1)
    )


def recent(db: Session, machine: Machine, hours: int = FEED_HOURS) -> list[MachineAlarm]:
    return list(
        db.scalars(
            select(MachineAlarm)
            .where(MachineAlarm.machine_id == machine.id, MachineAlarm.raised_at >= utcnow() - timedelta(hours=hours))
            .order_by(MachineAlarm.raised_at.desc())
            .limit(200)
        )
    )


def counts(alarms: list[MachineAlarm]) -> list[dict]:
    """Per code: how often raised, first and last time, latest message. Most frequent first."""
    by_code: dict[str, dict] = {}
    for a in sorted(alarms, key=lambda x: x.raised_at):
        row = by_code.setdefault(a.code, {"code": a.code, "count": 0, "first": a.raised_at, "last": a.raised_at, "message": ""})
        row["count"] += 1
        row["last"] = a.raised_at
        row["message"] = a.message or row["message"]
        row["active"] = a.cleared_at is None
    return sorted(by_code.values(), key=lambda r: (-r["count"], -r["last"].timestamp()))


def link(db: Session, alarm_id: int | None, log: BreakdownLog) -> None:
    """Remember which alarm event a log came from (only an unlinked event on the same machine)."""
    if not alarm_id:
        return
    alarm = db.get(MachineAlarm, alarm_id)
    if alarm is not None and alarm.machine_id == log.machine_id and alarm.log_id is None:
        alarm.log_id = log.id


def match(db: Session, machine: Machine, code: str, before: datetime) -> MachineAlarm | None:
    """The unlinked event a session's alarm code most likely came from."""
    if not code:
        return None
    hours = float(settings_store.get(db, "alarm_prefill_hours"))
    return db.scalar(
        select(MachineAlarm)
        .where(
            MachineAlarm.machine_id == machine.id,
            func.upper(MachineAlarm.code) == code.strip().upper(),
            MachineAlarm.log_id.is_(None),
            MachineAlarm.raised_at <= before,
            MachineAlarm.raised_at >= before - timedelta(hours=hours),
        )
        .order_by(MachineAlarm.raised_at.desc())
        .limit(1)
    )
