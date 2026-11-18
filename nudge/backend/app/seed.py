"""Default baskets for every new install, and sample tasks for demo mode.

Sample tasks have source="sample"; `python -m app.cli clear-sample` removes them before going live.
"""
from datetime import time, timedelta

from sqlalchemy.orm import Session

from . import recurrence, security
from .config import get_config
from .models import Basket, Task
from .settings_store import Prefs
from .tasks_service import close_task, create_task, set_focus
from .timeutil import local_now, utcnow

DEFAULT_BASKETS = [
    ("Work", "blue", "briefcase"),
    ("Projects", "violet", "layers"),
    ("Meetings & action points", "teal", "users"),
    ("Personal", "pink", "user"),
    ("Home & family", "orange", "home"),
    ("Finance & bills", "green", "wallet"),
    ("Learning", "amber", "book"),
]


def ensure_baskets(db: Session) -> None:
    if db.query(Basket).count():
        return
    for i, (name, color, icon) in enumerate(DEFAULT_BASKETS):
        db.add(Basket(name=name, color=color, icon=icon, position=i))
    db.flush()


def ensure_pin(db: Session) -> None:
    cfg = get_config()
    if security.has_pin(db):
        return
    if cfg.initial_pin and security.valid_pin_format(cfg.initial_pin):
        security.set_pin(db, cfg.initial_pin)
    elif cfg.seed_sample_data:
        security.set_pin(db, "1234")


def seed_sample(db: Session) -> int:
    """Fill an empty database with a realistic fortnight of work. Dates are relative to today."""
    if db.query(Task).count():
        return 0
    prefs = Prefs(db)
    b = {x.name.split()[0].lower(): x.id for x in db.query(Basket).all()}
    now = utcnow()
    today = local_now(prefs.zone, now).date()
    days_to_fri = (4 - today.weekday()) % 7
    next_mon = today + timedelta(days=7 - today.weekday())

    def add(title, basket, *, due=None, at=None, person="", status="open", priority="normal", age=1,
            rule="", notes="", focus=False, quiet_days=None, checklist=None, nudge_days=None, inbox=False):
        created = now - timedelta(days=age, hours=2)
        if rule and due is None:
            due = recurrence.first_date(rule, today)
        t = create_task(db, prefs, {
            "title": title, "basket_id": b.get(basket), "due_date": due, "due_time": at, "person": person,
            "status": status, "priority": priority, "repeat_rule": rule, "notes": notes,
            "checklist": checklist or [], "nudge_every_days": nudge_days, "inbox": inbox,
        }, source="sample", now=created)
        if quiet_days is not None:
            t.last_activity_at = now - timedelta(days=quiet_days)
        if focus:
            set_focus(db, prefs, t, True, now=now)
        return t

    d = timedelta
    # Today and overdue
    add("Call the vendor about the bearing quote", "work", due=today, at=time(11, 0), person="Vendor",
        focus=True, notes="SKF 6205 x 40, ask for delivery in 2 weeks")
    add("Approve the lubrication schedule for line 3", "work", due=today, at=time(15, 0), focus=True)
    add("Share minutes of Monday's review meeting", "meetings", due=today, person="Team", age=2,
        checklist=["Breakdown Pareto", "Open action points", "Next review date"])
    add("Review spare parts min-max levels", "work", due=today - d(2), priority="high", age=6, focus=True)
    add("Submit travel reimbursement claim", "finance", due=today - d(5), age=9)
    add("Call amma", "home", due=today, at=time(20, 0), age=0)

    # Upcoming
    add("Send the PM compliance report to the plant head", "work", due=today + d(days_to_fri or 7),
        person="Suresh", priority="high", age=3)
    add("Draft the predictive maintenance pilot proposal", "projects", due=next_mon + d(2), age=5,
        checklist=["Scope: 3 critical pumps", "Sensor shortlist", "Cost and payback", "Pilot timeline"])
    add("Vibration monitoring: shortlist sensor suppliers", "projects", due=today + d(6), age=4)
    add("Update the breakdown Pareto for the monthly review", "meetings", due=next_mon, age=2)
    add("Renew car insurance", "finance", due=today + d(7), age=12, priority="high")
    add("Pay credit card bill", "finance", rule="FREQ=MONTHLY;BYMONTHDAY=5", age=20)
    add("Study CMRP pillar 3: equipment reliability", "learning", at=time(7, 0), rule="FREQ=WEEKLY;BYDAY=MO", age=15)
    add("Take the CMRP practice test", "learning", due=today + d(10), age=8)
    add("Buy groceries for the weekend", "home", due=today + d((5 - today.weekday()) % 7 or 7), age=1)
    add("Renew driving licence", "personal", due=today + d(12), age=10)

    # Waiting on others (follow-up radar)
    add("Follow up with Ravi on the spares quotation", "work", person="Ravi", status="waiting", age=9,
        nudge_days=3, notes="Quote for gearbox spares, needed before the shutdown")
    add("Waiting for Anita to send the conveyor drawings", "projects", person="Anita", status="waiting", age=4)
    add("Remind Kumar about the calibration certificates", "work", person="Kumar", status="waiting", age=2)
    add("Get the revised AMC quote from Ravi", "work", person="Ravi", status="waiting", age=5)

    # Inbox (no date yet) and gone quiet
    add("Book a dentist appointment", "personal", age=3, inbox=True)
    add("Look into a better tool-crib layout", "projects", age=34, quiet_days=21)
    add("Update the asset register for the new compressors", "work", age=28, quiet_days=17)

    # History so the charts have something to show: closed work over the last 8 weeks
    history = [
        ("Close the PO for conveyor belts", "work", 2, 1), ("Send monthly MTTR numbers", "work", 3, 1),
        ("Pay electricity bill", "finance", 4, 0), ("Prepare toolbox talk on LOTO", "work", 6, 2),
        ("Fix the compressor alarm escalation list", "work", 7, 3), ("Renew gym membership", "personal", 8, 1),
        ("Review the kaizen submissions", "projects", 10, 4), ("Book train tickets for Chennai", "home", 11, 2),
        ("Send shutdown plan to production", "work", 13, 5), ("Study CMRP pillar 2", "learning", 14, 1),
        ("Collect the calibration report", "work", 16, 3), ("Pay school fees", "finance", 18, 2),
        ("Share the oil analysis results", "work", 20, 4), ("Finalise the spares budget", "projects", 23, 6),
        ("Update the PM checklist for pumps", "work", 25, 3), ("Car service", "home", 27, 1),
        ("Send RCA for the boiler trip", "work", 30, 2), ("Plan the quarterly safety audit", "meetings", 33, 5),
        ("Order bearings for line 2", "work", 36, 2), ("Revise CMRP pillar 1 notes", "learning", 38, 3),
        ("Submit the capex request for the new chiller", "projects", 41, 7), ("Pay house rent", "finance", 44, 0),
        ("Organise the 5S audit", "work", 47, 4), ("Get the AMC renewal signed", "work", 50, 6),
    ]
    for title, basket, closed_ago, took in history:
        t = add(title, basket, due=today - d(closed_ago), age=closed_ago + took)
        close_task(db, prefs, t, note="", now=now - d(days=closed_ago, hours=3))
    db.flush()
    return db.query(Task).count()


def clear_sample(db: Session) -> int:
    rows = db.query(Task).filter(Task.source == "sample").all()
    ids = {t.id for t in rows}
    extra = db.query(Task).filter(Task.follows_task_id.in_(ids), Task.source == "repeat").all() if ids else []
    for t in rows + extra:
        db.delete(t)
    db.flush()
    return len(rows) + len(extra)
