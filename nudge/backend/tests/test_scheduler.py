"""Reminders, nudges, daily digests, quiet hours."""
import json
from datetime import date, datetime, time, timedelta

from app import mailer, scheduler, settings_store
from app import tasks_service as ts
from app.models import NotificationLog


def of_kind(sent, kind):
    return [json.loads(m) for m in sent if json.loads(m)["kind"] == kind]


def utc(hh, mm, day=18):
    """IST wall clock on Nov `day` 2026, as naive UTC."""
    return datetime(2026, 11, day, hh, mm) - timedelta(hours=5, minutes=30)


def test_reminder_fires_once_at_due_time(db, prefs, sent_push, device):
    t = ts.create_task(db, prefs, {"title": "Call vendor", "due_date": date(2026, 11, 18), "due_time": time(11, 0)},
                       now=utc(9, 0))
    db.commit()
    assert scheduler.tick(db, utc(10, 59))["reminders"] == 0
    assert scheduler.tick(db, utc(11, 0))["reminders"] == 1
    assert scheduler.tick(db, utc(11, 1))["reminders"] == 0
    msg = of_kind(sent_push, "reminder")[0]
    assert msg["title"] == "Call vendor" and msg["task_id"] == t.id and msg["token"]
    assert [a["action"] for a in msg["actions"]] == ["done", "snooze_1h", "tomorrow"]


def test_snoozed_reminder_fires_again(db, prefs, sent_push, device):
    t = ts.create_task(db, prefs, {"title": "Pay", "due_date": date(2026, 11, 18), "due_time": time(11, 0)},
                       now=utc(9, 0))
    db.commit()
    scheduler.tick(db, utc(11, 0))
    ts.snooze(db, prefs, t, "1h", now=utc(11, 2))
    assert scheduler.tick(db, utc(12, 3))["reminders"] == 1
    assert len(of_kind(sent_push, "reminder")) == 2


def test_quiet_hours_hold_reminders(db, prefs, sent_push, device):
    ts.create_task(db, prefs, {"title": "Late call", "due_date": date(2026, 11, 18), "due_time": time(22, 0)},
                   now=utc(9, 0))
    db.commit()
    assert scheduler.tick(db, utc(22, 0))["reminders"] == 0  # 21:30–07:00 is quiet
    assert scheduler.tick(db, utc(7, 0, day=19))["reminders"] == 1


def test_many_reminders_are_grouped(db, prefs, sent_push, device):
    for i in range(5):
        ts.create_task(db, prefs, {"title": f"T{i}", "due_date": date(2026, 11, 18), "due_time": time(10, 0)},
                       now=utc(9, 0))
    db.commit()
    scheduler.tick(db, utc(10, 0))
    reminders = of_kind(sent_push, "reminder")
    assert len(reminders) == 1 and reminders[0]["title"] == "5 reminders"


def test_nudges_repeat_until_closed(db, prefs, sent_push, device):
    t = ts.create_task(db, prefs, {"title": "Follow up with Ravi on spares", "person": "Ravi", "status": "waiting"},
                       now=utc(9, 0))
    db.commit()
    assert t.next_nudge_at == utc(10, 0, day=21)
    assert scheduler.tick(db, utc(10, 0, day=21))["nudges"] == 1
    msg = of_kind(sent_push, "nudge")[-1]
    assert msg["title"] == "Follow up with Ravi" and "waiting 3 days" in msg["body"]
    assert t.next_nudge_at == utc(10, 0, day=24)
    ts.close_task(db, prefs, t, now=utc(11, 0, day=22))
    assert scheduler.tick(db, utc(10, 0, day=24))["nudges"] == 0


def test_briefing_runs_once_in_its_window(db, prefs, sent_push, device):
    settings_store.put(db, "digest_email", "me@example.com")
    db.commit()
    assert "briefing" not in scheduler.tick(db, utc(7, 29))
    first = scheduler.tick(db, utc(7, 30))
    assert first["briefing"]["push"] == 1
    assert "briefing" not in scheduler.tick(db, utc(7, 31))
    # E-mail without SMTP goes to the outbox for preview
    assert any(p.name.endswith("briefing.html") for p in mailer.outbox_dir().iterdir())
    assert db.query(NotificationLog).filter_by(channel="email", kind="briefing").count() == 1


def test_briefing_is_skipped_if_server_starts_late(db, prefs, sent_push, device):
    assert "briefing" not in scheduler.tick(db, utc(11, 0))


def test_overdue_nag_and_wrapup(db, prefs, sent_push, device):
    ts.create_task(db, prefs, {"title": "Old", "due_date": date(2026, 11, 15)}, now=utc(9, 0, day=14))
    db.commit()
    assert scheduler.tick(db, utc(12, 30))["overdue"] == 1
    assert of_kind(sent_push, "overdue")[-1]["title"] == "1 task is overdue"
    w = scheduler.tick(db, utc(18, 30))["wrapup"]
    assert w["push"] == 1


def test_push_preferences_are_respected(db, prefs, sent_push, device):
    settings_store.put(db, "push_reminders", False)
    db.commit()
    ts.create_task(db, Prefs_fresh(db), {"title": "x", "due_date": date(2026, 11, 18), "due_time": time(10, 0)},
                   now=utc(9, 0))
    db.commit()
    scheduler.tick(db, utc(10, 0))
    assert of_kind(sent_push, "reminder") == []


def Prefs_fresh(db):
    from app.settings_store import Prefs

    return Prefs(db)
