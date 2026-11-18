"""Background jobs, checked every 30 seconds:

- reminders at a task's due time (pushed, with Done / Snooze / Tomorrow buttons)
- follow-up nudges for "waiting on" tasks, repeating every few days until closed
- morning briefing (push + e-mail), midday overdue nag, evening wrap-up (Sunday: weekly review)
- nightly database backup

Reminders and nudges hold during quiet hours and go out when they end. Daily jobs run once per
day inside a 3-hour window after their time, so a restart never sends yesterday's briefing.
"""
import asyncio
import logging
from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from . import backup, digest, mailer, push, settings_store
from .dashboard import briefing, wrapup
from .db import SessionLocal
from .lanes import is_overdue, waiting_days
from .models import Task
from .settings_store import Prefs
from .tasks_service import clock
from .timeutil import in_quiet_hours, local_now, local_to_utc, utcnow

log = logging.getLogger("nudge.scheduler")
DAILY_WINDOW = timedelta(hours=3)
MISSED_REMINDER_AGE = timedelta(hours=12)
GROUP_OVER = 3


def _due_window(now_local: datetime, at: time) -> bool:
    start = now_local.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
    return start <= now_local < start + DAILY_WINDOW


def _once_today(db: Session, name: str, today_iso: str) -> bool:
    """True the first time it's called today for `name` (and records that it ran)."""
    key = f"mark_{name}"
    if settings_store.get(db, key) == today_iso:
        return False
    settings_store.put(db, key, today_iso)
    return True


def _describe(t: Task) -> str:
    bits = []
    if t.due_time:
        bits.append(f"Due {t.due_time.strftime('%H:%M')}")
    if t.person:
        bits.append(t.person.title())
    if t.basket:
        bits.append(t.basket.name)
    return " · ".join(bits) or "Due now"


def run_reminders(db: Session, prefs: Prefs, now: datetime, quiet: bool) -> int:
    due = (
        db.query(Task)
        .filter(Task.status.in_(("open", "waiting")), Task.remind_at.isnot(None), Task.remind_at <= now)
        .all()
    )
    due = [t for t in due if t.reminded_at is None or t.reminded_at < t.remind_at]
    fresh = []
    for t in due:
        if t.remind_at < now - MISSED_REMINDER_AGE:
            t.reminded_at = now  # too old to be useful; it shows in the briefing instead
        else:
            fresh.append(t)
    if not fresh or quiet:
        return 0
    for t in fresh:
        t.reminded_at = now
    if not prefs.flag("push_reminders"):
        return 0
    if len(fresh) > GROUP_OVER:
        names = ", ".join(t.title for t in fresh[:3])
        push.send(db, "reminder", f"{len(fresh)} reminders", f"{names} and more", url="/tasks?lane=today",
                  tag="reminders")
    else:
        for t in fresh:
            push.send(db, "reminder", t.title, _describe(t), url=f"/task/{t.id}", tag=f"task-{t.id}", task_id=t.id)
    return len(fresh)


def run_nudges(db: Session, prefs: Prefs, now: datetime, quiet: bool) -> int:
    if quiet:
        return 0
    due = (
        db.query(Task)
        .filter(Task.status == "waiting", Task.next_nudge_at.isnot(None), Task.next_nudge_at <= now)
        .all()
    )
    if not due:
        return 0
    today = local_now(prefs.zone, now).date()
    for t in due:
        every = t.nudge_every_days or prefs.default_nudge_days
        t.next_nudge_at = local_to_utc(today + timedelta(days=every), prefs.nudge_time, prefs.zone)
    if not prefs.flag("push_nudges"):
        return len(due)
    if len(due) > GROUP_OVER:
        people = sorted({t.person.title() for t in due})
        push.send(db, "nudge", f"Time to follow up with {len(people)} people", ", ".join(people[:6]),
                  url="/people", tag="nudges")
    else:
        for t in due:
            push.send(db, "nudge", f"Follow up with {t.person.title()}",
                      f"{t.title} · waiting {waiting_days(t, now)} days", url=f"/task/{t.id}?nudge=1",
                      tag=f"nudge-{t.id}", task_id=t.id, actions=push.NUDGE_ACTIONS)
    return len(due)


def run_briefing(db: Session, prefs: Prefs) -> dict:
    b = briefing(db, prefs)
    sent = {"push": 0, "email": False}
    if prefs.flag("push_briefing"):
        n_due, n_over = len(b["due_today"]), len(b["overdue"])
        title = f"{b['greeting']}: {n_due} due today" + (f", {n_over} overdue" if n_over else "")
        sent["push"] = push.send(db, "briefing", title, b["text"][:220], url="/briefing", tag="briefing")
    if prefs.flag("email_briefing") and prefs.digest_email:
        subject, html, text = digest.briefing_email(db, prefs)
        sent["email"] = mailer.send(db, "briefing", prefs.digest_email, subject, html, text)
    return sent


def run_overdue_nag(db: Session, prefs: Prefs, now: datetime) -> int:
    c = clock(prefs, now)
    overdue = [t for t in db.query(Task).filter(Task.status.in_(("open", "waiting"))).all() if is_overdue(t, c)]
    if not overdue or not prefs.flag("push_overdue"):
        return 0
    titles = ", ".join(t.title for t in overdue[:3]) + (" and more" if len(overdue) > 3 else "")
    noun = "task is" if len(overdue) == 1 else "tasks are"
    push.send(db, "overdue", f"{len(overdue)} {noun} overdue", f"{titles}. Tap to reschedule or close.",
              url="/tasks?lane=overdue", tag="overdue")
    return len(overdue)


def run_wrapup(db: Session, prefs: Prefs) -> dict:
    w = wrapup(db, prefs)
    sent = {"push": 0, "email": False}
    if prefs.flag("push_wrapup"):
        title = f"Wrap-up: {len(w['closed_today'])} closed, {len(w['carried'])} carried over"
        url = "/review" if w["weekly_review_ready"] else "/wrapup"
        sent["push"] = push.send(db, "wrapup", title, w["text"][:220], url=url, tag="wrapup")
    if prefs.flag("email_wrapup") and prefs.digest_email:
        subject, html, text = digest.wrapup_email(db, prefs)
        sent["email"] = mailer.send(db, "wrapup", prefs.digest_email, subject, html, text)
    return sent


def tick(db: Session, now: datetime | None = None) -> dict:
    now = now or utcnow()
    prefs = Prefs(db)
    local = local_now(prefs.zone, now)
    today = local.date().isoformat()
    quiet = in_quiet_hours(local, prefs.quiet_start, prefs.quiet_end)
    done: dict = {"reminders": run_reminders(db, prefs, now, quiet), "nudges": run_nudges(db, prefs, now, quiet)}

    if _due_window(local, prefs.briefing_time) and _once_today(db, "briefing", today):
        done["briefing"] = run_briefing(db, prefs)
    if _due_window(local, prefs.overdue_nag_time) and not quiet and _once_today(db, "overdue", today):
        done["overdue"] = run_overdue_nag(db, prefs, now)
    if _due_window(local, prefs.wrapup_time) and _once_today(db, "wrapup", today):
        done["wrapup"] = run_wrapup(db, prefs)
    if _due_window(local, time(2, 0)) and _once_today(db, "backup", today):
        path = backup.run_backup()
        done["backup"] = path.name if path else None
    db.flush()
    return done


def tick_once() -> None:
    db = SessionLocal()
    try:
        result = tick(db)
        db.commit()
        if any(v for v in result.values()):
            log.info("scheduler: %s", result)
    except Exception:
        db.rollback()
        log.exception("Scheduler tick failed")
    finally:
        db.close()


async def run_forever(interval_s: int) -> None:
    while True:
        await asyncio.to_thread(tick_once)
        await asyncio.sleep(interval_s)

