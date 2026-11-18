"""Task lifecycle: lanes, close with follow-up, repeats, undo, snooze, focus, stale."""
from datetime import date, datetime, time, timedelta

import pytest

from app import dashboard
from app import tasks_service as ts
from app.lanes import lane
from app.models import Task

# 10:00 IST on Wednesday 18 Nov 2026
NOW = datetime(2026, 11, 18, 4, 30)
TODAY = date(2026, 11, 18)


def make(db, prefs, **kw):
    t = ts.create_task(db, prefs, {"title": kw.pop("title", "Task"), **kw}, now=kw.pop("now", NOW))
    db.commit()
    return t


def test_lanes(db, prefs):
    c = ts.clock(prefs, NOW)
    assert lane(make(db, prefs), c) == "inbox"
    assert lane(make(db, prefs, due_date=TODAY), c) == "today"
    assert lane(make(db, prefs, due_date=TODAY, due_time=time(9, 0)), c) == "overdue"  # 9:00 passed
    assert lane(make(db, prefs, due_date=TODAY - timedelta(days=1)), c) == "overdue"
    assert lane(make(db, prefs, due_date=TODAY + timedelta(days=3)), c) == "upcoming"
    assert lane(make(db, prefs, person="Ravi", status="waiting"), c) == "waiting"


def test_due_time_sets_reminder_in_utc(db, prefs):
    t = make(db, prefs, due_date=TODAY, due_time=time(17, 0))
    assert t.remind_at == datetime(2026, 11, 18, 11, 30)  # 17:00 IST


def test_waiting_schedules_first_nudge(db, prefs):
    t = make(db, prefs, person="Ravi", status="waiting")
    assert t.waiting_since == NOW
    assert t.nudge_every_days == 3
    assert t.next_nudge_at == datetime(2026, 11, 21, 4, 30)  # 3 days later at 10:00 IST
    dated = make(db, prefs, person="Ravi", status="waiting", due_date=date(2026, 11, 24))
    assert dated.next_nudge_at == datetime(2026, 11, 24, 4, 30)


def test_waiting_without_a_person_is_just_open(db, prefs):
    assert make(db, prefs, status="waiting").status == "open"


def test_close_with_follow_up(db, prefs):
    t = make(db, prefs, title="Send the quote request", person="Ravi")
    t, spawned = ts.close_task(db, prefs, t, note="Sent by mail", follow_up={"in_days": 3}, now=NOW)
    db.commit()
    assert t.status == "done" and t.closing_note == "Sent by mail"
    fu = spawned[0]
    assert fu.title == "Follow up with Ravi: Send the quote request"
    assert (fu.status, fu.person, fu.due_date, fu.follows_task_id) == ("waiting", "Ravi", date(2026, 11, 21), t.id)


def test_follow_up_of_a_follow_up_keeps_its_title(db, prefs):
    t = make(db, prefs, title="Follow up with Ravi on spares", person="Ravi", status="waiting")
    _, spawned = ts.close_task(db, prefs, t, follow_up={"in_days": 2}, now=NOW)
    assert spawned[0].title == "Follow up with Ravi on spares"


def test_repeating_task_rolls_forward_and_undo_restores(db, prefs):
    t = make(db, prefs, title="Weekly report", repeat_rule="FREQ=WEEKLY;BYDAY=MO", due_time=time(9, 0))
    assert t.due_date == date(2026, 11, 23)
    _, spawned = ts.close_task(db, prefs, t, now=NOW)
    db.commit()
    nxt = spawned[0]
    assert nxt.due_date == date(2026, 11, 30) and nxt.repeat_rule == "FREQ=WEEKLY;BYDAY=MO"
    assert nxt.due_time == time(9, 0)
    assert t.repeat_rule == ""
    ts.undo_close(db, prefs, t)
    db.commit()
    assert t.status == "open" and t.repeat_rule == "FREQ=WEEKLY;BYDAY=MO"
    assert db.get(Task, nxt.id) is None


def test_closing_a_late_repeat_skips_to_the_next_one(db, prefs):
    t = make(db, prefs, title="Pay rent", repeat_rule="FREQ=MONTHLY;BYMONTHDAY=5", due_date=date(2026, 11, 5))
    _, spawned = ts.close_task(db, prefs, t, now=NOW)
    assert spawned[0].due_date == date(2026, 12, 5)


def test_snooze_presets(db, prefs):
    t = make(db, prefs, due_date=TODAY, due_time=time(11, 0))
    ts.snooze(db, prefs, t, "1h", now=NOW)
    assert t.remind_at == NOW + timedelta(hours=1) and t.due_date == TODAY
    ts.snooze(db, prefs, t, "tomorrow", now=NOW)
    assert t.due_date == date(2026, 11, 19) and t.remind_at == datetime(2026, 11, 19, 5, 30)
    ts.snooze(db, prefs, t, "next_week", now=NOW)
    assert t.due_date == date(2026, 11, 23)
    with pytest.raises(ts.TaskError):
        ts.snooze(db, prefs, t, "date", now=NOW)


def test_top_three_limit(db, prefs):
    tasks = [make(db, prefs, title=f"T{i}") for i in range(4)]
    for t in tasks[:3]:
        ts.set_focus(db, prefs, t, True, now=NOW)
    with pytest.raises(ts.TaskError):
        ts.set_focus(db, prefs, tasks[3], True, now=NOW)


def test_editing_a_field_clears_its_ai_highlight(db, prefs, basket):
    t = make(db, prefs, ai_fields=["basket", "due_date"], inbox=True)
    ts.update_task(db, prefs, t, {"basket_id": basket["home"]})
    assert t.ai_fields == ["due_date"]
    ts.update_task(db, prefs, t, {"due_date": TODAY})
    assert t.inbox is False and t.ai_fields == []


def test_mark_nudged_pushes_next_reminder(db, prefs):
    t = make(db, prefs, person="Ravi", status="waiting", nudge_every_days=2)
    ts.mark_nudged(db, prefs, t, now=NOW)
    assert t.nudge_count == 1 and t.next_nudge_at == datetime(2026, 11, 20, 4, 30)


def test_stale_detection(db, prefs):
    old = NOW - timedelta(days=20)
    quiet = make(db, prefs, title="Forgotten", now=old)
    make(db, prefs, title="Scheduled", due_date=TODAY + timedelta(days=5), now=old)
    make(db, prefs, title="Repeats", repeat_rule="FREQ=DAILY", now=old)
    make(db, prefs, title="Fresh")
    stale = [t for t in db.query(Task).all() if dashboard.is_stale(t, prefs, NOW)]
    assert [t.title for t in stale] == ["Forgotten"]
    ts.keep_stale(db, quiet)
    assert not dashboard.is_stale(quiet, prefs, NOW + timedelta(minutes=1))


def test_dashboard_numbers(db, prefs, basket):
    make(db, prefs, title="Late", due_date=TODAY - timedelta(days=2), basket_id=basket["work"])
    make(db, prefs, title="Today", due_date=TODAY, basket_id=basket["work"])
    make(db, prefs, title="Wait", person="Anita", status="waiting", basket_id=basket["projects"])
    done = make(db, prefs, title="Done", basket_id=basket["work"])
    ts.close_task(db, prefs, done, now=NOW)
    db.commit()
    d = dashboard.dashboard(db, prefs, NOW)
    assert d["kpis"] == {"overdue": 1, "due_today": 1, "waiting": 1, "closed_week": 1}
    work = next(b for b in d["baskets"] if b["basket"]["name"] == "Work")
    assert (work["open"], work["overdue"], work["cleared_30"], work["cleared_pct"]) == (2, 1, 1, 33)
    assert d["radar"][0]["person"] == "Anita"
    assert sum(a["count"] for a in d["aging"]) == 3
    assert d["trend"][-1] == {"week_start": "2026-11-16", "created": 4, "closed": 1}
