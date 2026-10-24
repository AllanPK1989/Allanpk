"""PM plan: a read-only mirror of the PM system's tasks per machine (SPEC 12.3).

Thunai does not schedule preventive maintenance. It shows what is overdue or due soon, and gives
overdue tasks to the AI as evidence for a breakdown on that machine.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit, settings_store
from .config import get_config
from .models import Machine, PMTask, User


def today() -> date:
    return datetime.now(ZoneInfo(get_config().plant_tz)).date()


def due_on(task: PMTask) -> date | None:
    if task.next_due_on:
        return task.next_due_on
    if task.last_done_on and task.frequency_days:
        return task.last_done_on + timedelta(days=task.frequency_days)
    return None


def state(task: PMTask, on: date, soon_days: int) -> str:
    """overdue | due_soon | ok | unknown"""
    due = due_on(task)
    if due is None:
        return "unknown"
    if due < on:
        return "overdue"
    if due <= on + timedelta(days=soon_days):
        return "due_soon"
    return "ok"


def serialize(task: PMTask, on: date, soon_days: int) -> dict:
    due = due_on(task)
    return {
        "id": task.id,
        "task_code": task.task_code,
        "title": task.title,
        "frequency_days": task.frequency_days,
        "last_done_on": task.last_done_on.isoformat() if task.last_done_on else None,
        "next_due_on": due.isoformat() if due else None,
        "state": state(task, on, soon_days),
        "days_overdue": (on - due).days if due and due < on else 0,
        "active": task.active,
    }


def for_machine(db: Session, machine: Machine) -> list[PMTask]:
    tasks = list(db.scalars(select(PMTask).where(PMTask.machine_id == machine.id, PMTask.active.is_(True))))
    tasks.sort(key=lambda t: (due_on(t) or date.max, t.task_code))
    return tasks


def overdue(db: Session, machine: Machine, on: date | None = None) -> list[PMTask]:
    on = on or today()
    return [t for t in for_machine(db, machine) if state(t, on, 0) == "overdue"]


def machine_summary(db: Session, machine: Machine) -> list[dict]:
    on = today()
    soon = int(settings_store.get(db, "pm_due_soon_days"))
    return [serialize(t, on, soon) for t in for_machine(db, machine)]


def _date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unreadable date: {text}")


def upsert(db: Session, user: User | None, rows: list[tuple[int, dict]], source: str) -> dict:
    """Create or update PM tasks by machine and task code.

    values: machine_no, task_code, title, frequency_days, last_done_on, next_due_on. When the next due
    date is missing it is worked out from the last done date and the frequency.
    """
    machines = {m.machine_no.upper(): m for m in db.scalars(select(Machine))}
    created = updated = 0
    errors: list[dict] = []
    for row_no, v in rows:
        if str(v.get("title", "")).startswith("[SAMPLE] Delete"):
            continue
        machine = machines.get(str(v.get("machine_no") or "").strip().upper())
        if machine is None:
            errors.append({"row": row_no, "error": f"Unknown machine {v.get('machine_no')}"})
            continue
        code = str(v.get("task_code") or "").strip() or str(v.get("title") or "").strip()[:80]
        if not code:
            errors.append({"row": row_no, "error": "Missing task code"})
            continue
        try:
            last = _date(v.get("last_done_on"))
            nxt = _date(v.get("next_due_on"))
            freq = v.get("frequency_days")
            freq = int(float(freq)) if freq not in (None, "") else None
        except ValueError as e:
            errors.append({"row": row_no, "error": str(e)})
            continue
        task = db.scalar(select(PMTask).where(PMTask.machine_id == machine.id, PMTask.task_code == code[:80]))
        before = audit.snapshot(task) if task else None
        if task is None:
            task = PMTask(machine_id=machine.id, task_code=code[:80], active=True)
            db.add(task)
            created += 1
        else:
            updated += 1
        if v.get("title"):
            task.title = str(v["title"])[:300]
        if freq is not None:
            task.frequency_days = freq
        if last is not None:
            task.last_done_on = last
        if nxt is not None:
            task.next_due_on = nxt
        elif last is not None and task.frequency_days:
            task.next_due_on = last + timedelta(days=task.frequency_days)
        task.source = source[:40]
        task.active = True
        db.flush()
        if before is not None:
            audit.record(db, user, "pm_task", task.id, "update", before, audit.snapshot(task))
    audit.record(db, user, "import", "pm_tasks", "import", None, {"created": created, "updated": updated, "errors": len(errors), "source": source})
    return {"created": created, "updated": updated, "errors": errors}
