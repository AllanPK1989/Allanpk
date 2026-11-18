"""JSON shapes returned by the API."""
from datetime import datetime

from . import recurrence
from .lanes import Clock, age_days, is_overdue, lane, waiting_days
from .models import Basket, Task
from .timeutil import iso_utc, utcnow


def basket_dict(b: Basket | None) -> dict | None:
    if b is None:
        return None
    return {"id": b.id, "name": b.name, "color": b.color, "icon": b.icon, "position": b.position,
            "archived": b.archived}


def task_dict(t: Task, c: Clock, now: datetime | None = None) -> dict:
    now = now or utcnow()
    return {
        "id": t.id,
        "title": t.title,
        "notes": t.notes,
        "basket": basket_dict(t.basket),
        "basket_id": t.basket_id,
        "status": t.status,
        "priority": t.priority,
        "lane": lane(t, c),
        "overdue": is_overdue(t, c),
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "due_time": t.due_time.strftime("%H:%M") if t.due_time else None,
        "remind_at": iso_utc(t.remind_at),
        "person": t.person,
        "waiting_since": iso_utc(t.waiting_since),
        "waiting_days": waiting_days(t, now) if t.status == "waiting" else None,
        "nudge_every_days": t.nudge_every_days,
        "next_nudge_at": iso_utc(t.next_nudge_at),
        "nudge_count": t.nudge_count,
        "repeat_rule": t.repeat_rule,
        "repeat_label": recurrence.label(t.repeat_rule),
        "focus": t.focus_date == c.today,
        "source": t.source,
        "transcript": t.transcript,
        "ai_fields": list(t.ai_fields or []),
        "inbox": t.inbox,
        "follows_task_id": t.follows_task_id,
        "checklist": [{"id": i.id, "text": i.text, "done": i.done} for i in t.checklist],
        "checklist_done": sum(1 for i in t.checklist if i.done),
        "closed_at": iso_utc(t.closed_at),
        "closing_note": t.closing_note,
        "created_at": iso_utc(t.created_at),
        "updated_at": iso_utc(t.updated_at),
        "last_activity_at": iso_utc(t.last_activity_at),
        "age_days": age_days(t, now),
    }


def short_task(t: Task, c: Clock, now: datetime | None = None) -> dict:
    d = task_dict(t, c, now)
    keep = ("id", "title", "basket", "status", "priority", "lane", "overdue", "due_date", "due_time",
            "person", "waiting_days", "focus", "repeat_label", "age_days", "checklist_done",
            "closed_at", "ai_fields", "inbox", "next_nudge_at", "nudge_count")
    d["checklist_total"] = len(t.checklist)
    return {k: d[k] for k in keep + ("checklist_total",)}
