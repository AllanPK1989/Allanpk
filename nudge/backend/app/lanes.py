"""Which list a task sits in: Inbox, Today, Upcoming, Waiting, Overdue or Done.

- Done: closed or dropped.
- Waiting: you're waiting on someone (status "waiting"); flagged overdue if its date has passed.
- Overdue: open and the due date (or due time today) has passed.
- Today: open and due today, or picked for today's Top 3.
- Upcoming: open and due later.
- Inbox: open with no date yet (new captures land here until you schedule them).
"""
from dataclasses import dataclass
from datetime import date, datetime, time

from .models import Task

LANES = ("inbox", "today", "upcoming", "waiting", "overdue", "done")


@dataclass
class Clock:
    today: date
    now_time: time  # local wall clock


def is_overdue(t: Task, c: Clock) -> bool:
    if t.status not in ("open", "waiting") or t.due_date is None:
        return False
    if t.due_date < c.today:
        return True
    return t.due_date == c.today and t.due_time is not None and t.due_time < c.now_time


def lane(t: Task, c: Clock) -> str:
    if t.status in ("done", "dropped"):
        return "done"
    if t.status == "waiting":
        return "waiting"
    if is_overdue(t, c):
        return "overdue"
    if t.due_date == c.today or t.focus_date == c.today:
        return "today"
    if t.due_date is None:
        return "inbox"
    return "upcoming"


def age_days(t: Task, now_utc: datetime) -> int:
    return max(0, (now_utc - t.created_at).days)


def waiting_days(t: Task, now_utc: datetime) -> int:
    start = t.waiting_since or t.created_at
    return max(0, (now_utc - start).days)


PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}


def sort_key(t: Task, c: Clock):
    """Overdue first, then by date and time, then priority."""
    return (
        0 if is_overdue(t, c) else 1,
        t.due_date or date.max,
        t.due_time or time.max,
        PRIORITY_ORDER.get(t.priority, 1),
        t.id,
    )
