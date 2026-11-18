"""Task lifecycle: create, edit, close (with follow-up and repeat), undo, snooze, nudge, focus."""
import re
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from . import recurrence
from .lanes import Clock
from .models import PRIORITIES, Basket, ChecklistItem, Task, TaskEvent
from .settings_store import Prefs
from .timeutil import local_now, local_to_utc, utcnow

MAX_FOCUS = 3
FOLLOW_UP_TITLE = re.compile(r"^(follow(?:\s|-)?up|chase|remind|waiting\s+(?:for|on)|get\b.+\bfrom\b)", re.I)
EDITABLE_FIELDS = {
    "title", "notes", "basket_id", "priority", "due_date", "due_time", "person", "status",
    "repeat_rule", "nudge_every_days",
}


class TaskError(ValueError):
    """A request that can't be applied (shown to the user as-is)."""


def clock(prefs: Prefs, now_utc: datetime | None = None) -> Clock:
    n = local_now(prefs.zone, now_utc)
    return Clock(today=n.date(), now_time=n.time().replace(tzinfo=None))


def log(db: Session, task: Task | None, kind: str, **detail) -> None:
    db.add(TaskEvent(task_id=task.id if task else None, kind=kind, detail=detail, at=utcnow()))


def touch(task: Task) -> None:
    task.last_activity_at = utcnow()


def _remind_at(task: Task, prefs: Prefs) -> datetime | None:
    if task.due_date and task.due_time and task.status in ("open", "waiting"):
        return local_to_utc(task.due_date, task.due_time, prefs.zone)
    return None


def _refresh_reminder(task: Task, prefs: Prefs) -> None:
    task.remind_at = _remind_at(task, prefs)
    task.reminded_at = None


def _schedule_first_nudge(task: Task, prefs: Prefs, now_utc: datetime) -> None:
    every = task.nudge_every_days or prefs.default_nudge_days
    task.nudge_every_days = every
    if task.due_date:
        # "Follow up with Ravi next Tuesday": the first nudge is that day.
        task.next_nudge_at = local_to_utc(task.due_date, task.due_time or prefs.nudge_time, prefs.zone)
    else:
        start = local_now(prefs.zone, now_utc).date() + timedelta(days=every)
        task.next_nudge_at = local_to_utc(start, prefs.nudge_time, prefs.zone)


def _check_basket(db: Session, basket_id) -> int | None:
    if basket_id in (None, "", 0):
        return None
    basket = db.get(Basket, int(basket_id))
    if not basket or basket.archived:
        raise TaskError("That basket doesn't exist")
    return basket.id


def _clean(data: dict) -> dict:
    out = dict(data)
    if "title" in out:
        out["title"] = (out["title"] or "").strip()[:300]
        if not out["title"]:
            raise TaskError("A task needs a title")
    if "priority" in out and out["priority"] not in PRIORITIES:
        out["priority"] = "normal"
    if "status" in out and out["status"] not in ("open", "waiting"):
        raise TaskError("Use close, drop or reopen to change a task's status")
    if "person" in out:
        out["person"] = (out["person"] or "").strip()[:80]
    if "repeat_rule" in out:
        out["repeat_rule"] = recurrence.normalize(out["repeat_rule"] or "")
    if "nudge_every_days" in out and out["nudge_every_days"] is not None:
        out["nudge_every_days"] = max(1, min(60, int(out["nudge_every_days"])))
    if out.get("due_time") and not out.get("due_date", True):
        out["due_time"] = None
    return out


def create_task(db: Session, prefs: Prefs, data: dict, *, source: str = "manual", now: datetime | None = None) -> Task:
    now = now or utcnow()
    data = _clean({"title": data.get("title", ""), **data})
    status = data.get("status") or "open"
    if status == "waiting" and not data.get("person"):
        status = "open"  # waiting needs someone to wait on
    rule = data.get("repeat_rule") or ""
    due_date = data.get("due_date")
    if rule and not due_date:
        due_date = recurrence.first_date(rule, clock(prefs, now).today)
    task = Task(
        title=data["title"],
        notes=(data.get("notes") or "").strip(),
        basket_id=_check_basket(db, data.get("basket_id")),
        priority=data.get("priority") or "normal",
        due_date=due_date,
        due_time=data.get("due_time") if due_date else None,
        person=data.get("person") or "",
        status=status,
        repeat_rule=rule,
        source=source,
        transcript=(data.get("transcript") or "")[:4000],
        ai_fields=list(data.get("ai_fields") or []),
        inbox=bool(data.get("inbox", False)),
        follows_task_id=data.get("follows_task_id"),
        nudge_every_days=data.get("nudge_every_days"),
        created_at=now,
        updated_at=now,
        last_activity_at=now,
    )
    if task.status == "waiting":
        task.waiting_since = now
        _schedule_first_nudge(task, prefs, now)
    task.remind_at = _remind_at(task, prefs)
    db.add(task)
    db.flush()
    for i, text in enumerate(data.get("checklist") or []):
        text = (text or "").strip()
        if text:
            db.add(ChecklistItem(task_id=task.id, text=text[:300], position=i))
    if data.get("focus"):
        set_focus(db, prefs, task, True, now=now)
    log(db, task, "created", source=source)
    db.flush()
    db.refresh(task)
    return task


def update_task(db: Session, prefs: Prefs, task: Task, patch: dict, now: datetime | None = None) -> Task:
    now = now or utcnow()
    confirm_ai = bool(patch.pop("confirm_ai", False))
    inbox = patch.pop("inbox", None)
    patch = _clean({k: v for k, v in patch.items() if k in EDITABLE_FIELDS})
    if task.status in ("done", "dropped") and patch.get("status"):
        raise TaskError("Reopen the task first")
    changed = []
    for key, value in patch.items():
        if key == "basket_id":
            value = _check_basket(db, value)
        if getattr(task, key) != value:
            setattr(task, key, value)
            changed.append(key)
    if task.due_date is None and task.due_time is not None:
        task.due_time = None  # a time without a date means nothing
    if task.status == "waiting" and not task.person:
        task.status = "open"
        changed.append("status")
    if "status" in changed:
        if task.status == "waiting":
            task.waiting_since = now
            _schedule_first_nudge(task, prefs, now)
        else:
            task.waiting_since = None
            task.next_nudge_at = None
    elif task.status == "waiting" and ({"due_date", "due_time", "nudge_every_days"} & set(changed)):
        _schedule_first_nudge(task, prefs, now)
    if {"due_date", "due_time", "status"} & set(changed):
        _refresh_reminder(task, prefs)
    if confirm_ai:
        task.ai_fields = []
    elif changed and task.ai_fields:
        task.ai_fields = [f for f in task.ai_fields if f not in changed and not (f == "basket" and "basket_id" in changed)]
    if inbox is not None:
        task.inbox = bool(inbox)
    elif changed and task.due_date:
        task.inbox = False
    if changed or confirm_ai:
        touch(task)
        log(db, task, "edited", fields=changed)
    db.flush()
    return task


def close_task(
    db: Session, prefs: Prefs, task: Task, *, note: str = "", follow_up: dict | None = None,
    now: datetime | None = None,
) -> tuple[Task, list[Task]]:
    """Mark done. Repeating tasks get their next occurrence; a follow-up can be created in one go."""
    now = now or utcnow()
    if task.status in ("done", "dropped"):
        return task, []
    prev = {"status": task.status, "focus_date": task.focus_date.isoformat() if task.focus_date else None}
    task.status = "done"
    task.closed_at = now
    task.closing_note = (note or "").strip()[:2000]
    task.remind_at = None
    task.next_nudge_at = None
    task.inbox = False
    touch(task)
    spawned: list[Task] = []
    c = clock(prefs, now)

    if task.repeat_rule:
        base = max(task.due_date or c.today, c.today)
        nxt = recurrence.next_date(task.repeat_rule, base, task.due_time)
        if nxt:
            copy = create_task(
                db, prefs,
                {
                    "title": task.title, "notes": task.notes, "basket_id": task.basket_id,
                    "priority": task.priority, "due_date": nxt, "due_time": task.due_time,
                    "person": task.person, "repeat_rule": task.repeat_rule,
                    "status": "open", "follows_task_id": task.id,
                    "checklist": [i.text for i in task.checklist],
                },
                source="repeat", now=now,
            )
            task.repeat_rule = ""  # the rule moves to the new occurrence
            spawned.append(copy)

    if follow_up:
        due = follow_up.get("date")
        if not due and follow_up.get("in_days") is not None:
            due = c.today + timedelta(days=int(follow_up["in_days"]))
        person = (follow_up.get("person") if follow_up.get("person") is not None else task.person) or ""
        title = (follow_up.get("title") or "").strip()
        if not title:
            if FOLLOW_UP_TITLE.match(task.title):
                title = task.title  # already phrased as a follow-up
            else:
                title = f"Follow up with {person}: {task.title}" if person else f"Follow up: {task.title}"
        fu = create_task(
            db, prefs,
            {
                "title": title, "basket_id": task.basket_id, "priority": task.priority,
                "due_date": due, "person": person,
                "status": "waiting" if person else "open",
                "follows_task_id": task.id,
                "notes": f"Closing note: {task.closing_note}" if task.closing_note else "",
            },
            source="followup", now=now,
        )
        spawned.append(fu)

    log(db, task, "closed", prev=prev, spawned=[t.id for t in spawned], note=bool(task.closing_note))
    db.flush()
    return task, spawned


def undo_close(db: Session, prefs: Prefs, task: Task) -> Task:
    """Reverse the last close: restore status and remove what the close created."""
    if task.status != "done":
        raise TaskError("Only a closed task can be undone")
    ev = (
        db.query(TaskEvent)
        .filter(TaskEvent.task_id == task.id, TaskEvent.kind == "closed")
        .order_by(TaskEvent.id.desc())
        .first()
    )
    prev = (ev.detail or {}).get("prev", {}) if ev else {}
    for spawned_id in (ev.detail or {}).get("spawned", []) if ev else []:
        child = db.get(Task, spawned_id)
        if child is None:
            continue
        if child.source == "repeat" and child.repeat_rule:
            task.repeat_rule = child.repeat_rule
        db.delete(child)
    task.status = prev.get("status") or "open"
    task.closed_at = None
    task.closing_note = ""
    fd = prev.get("focus_date")
    task.focus_date = date.fromisoformat(fd) if fd else None
    if task.status == "waiting":
        _schedule_first_nudge(task, prefs, utcnow())
    _refresh_reminder(task, prefs)
    touch(task)
    log(db, task, "undone")
    db.flush()
    return task


def reopen_task(db: Session, prefs: Prefs, task: Task) -> Task:
    if task.status not in ("done", "dropped"):
        return task
    task.status = "open"
    task.closed_at = None
    _refresh_reminder(task, prefs)
    touch(task)
    log(db, task, "reopened")
    db.flush()
    return task


def drop_task(db: Session, task: Task, now: datetime | None = None) -> Task:
    if task.status in ("done", "dropped"):
        return task
    prev_status = task.status
    task.status = "dropped"
    task.closed_at = now or utcnow()
    task.remind_at = None
    task.next_nudge_at = None
    task.inbox = False
    touch(task)
    log(db, task, "dropped", prev={"status": prev_status})
    db.flush()
    return task


SNOOZE_PRESETS = ("1h", "3h", "tonight", "tomorrow", "next_week", "date")


def snooze(
    db: Session, prefs: Prefs, task: Task, preset: str, *, on: date | None = None, at: time | None = None,
    now: datetime | None = None,
) -> Task:
    """1h / 3h / tonight push the reminder only; tomorrow / next week / date move the task."""
    now = now or utcnow()
    if task.status not in ("open", "waiting"):
        raise TaskError("This task is closed")
    if preset not in SNOOZE_PRESETS:
        raise TaskError("Unknown snooze option")
    local = local_now(prefs.zone, now)
    today = local.date()
    if preset in ("1h", "3h"):
        task.remind_at = now + timedelta(hours=1 if preset == "1h" else 3)
        task.reminded_at = None
    elif preset == "tonight":
        evening = local_to_utc(today, time(19, 0), prefs.zone)
        task.remind_at = evening if evening > now else now + timedelta(hours=1)
        task.reminded_at = None
    else:
        if preset == "tomorrow":
            new_date = today + timedelta(days=1)
        elif preset == "next_week":
            new_date = today + timedelta(days=7 - today.weekday())  # next Monday
        else:
            if on is None:
                raise TaskError("Pick a date")
            new_date = on
        task.due_date = new_date
        if at is not None:
            task.due_time = at
        task.inbox = False
        _refresh_reminder(task, prefs)
        if task.status == "waiting":
            task.next_nudge_at = local_to_utc(new_date, task.due_time or prefs.nudge_time, prefs.zone)
        if task.focus_date == today and new_date != today:
            task.focus_date = None
    touch(task)
    log(db, task, "snoozed", preset=preset, to=task.due_date.isoformat() if task.due_date else None)
    db.flush()
    return task


def mark_nudged(db: Session, prefs: Prefs, task: Task, now: datetime | None = None) -> Task:
    """You chased them: count it and schedule the next reminder to chase again."""
    now = now or utcnow()
    if task.status != "waiting":
        raise TaskError("Only 'waiting on' tasks can be nudged")
    task.nudge_count += 1
    every = task.nudge_every_days or prefs.default_nudge_days
    nxt = local_now(prefs.zone, now).date() + timedelta(days=every)
    task.next_nudge_at = local_to_utc(nxt, prefs.nudge_time, prefs.zone)
    touch(task)
    log(db, task, "nudged", count=task.nudge_count)
    db.flush()
    return task


def set_focus(db: Session, prefs: Prefs, task: Task, on: bool, now: datetime | None = None) -> Task:
    today = clock(prefs, now).today
    if on:
        if task.status not in ("open", "waiting"):
            raise TaskError("This task is closed")
        count = db.query(Task).filter(Task.focus_date == today, Task.id != task.id,
                                      Task.status.in_(("open", "waiting"))).count()
        if count >= MAX_FOCUS:
            raise TaskError("Your Top 3 is full. Take one off first.")
        task.focus_date = today
    else:
        task.focus_date = None
    touch(task)
    db.flush()
    return task


def keep_stale(db: Session, task: Task) -> Task:
    task.stale_prompted_at = utcnow()
    touch(task)
    log(db, task, "kept")
    db.flush()
    return task


def bulk(db: Session, prefs: Prefs, ids: list[int], action: str, basket_id: int | None = None) -> int:
    tasks = db.query(Task).filter(Task.id.in_(ids)).all()
    n = 0
    for t in tasks:
        try:
            if action == "tomorrow":
                snooze(db, prefs, t, "tomorrow")
            elif action == "done":
                close_task(db, prefs, t)
            elif action == "drop":
                drop_task(db, t)
            elif action == "basket":
                update_task(db, prefs, t, {"basket_id": basket_id})
            else:
                raise TaskError("Unknown action")
            n += 1
        except TaskError:
            continue
    db.flush()
    return n
