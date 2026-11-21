"""The free, on-server understanding: extra phrasings, follow-up messages, and no network use."""
import socket
from datetime import date, datetime, time

import pytest

from app import rules
from app import tasks_service as ts
from app import understand
from app.models import Task

TODAY = date(2026, 11, 21)  # a Saturday
NOW = datetime(2026, 11, 21, 8, 35)  # 14:05 IST
BASKETS = [(1, "Work"), (2, "Projects"), (3, "Meetings & action points"), (4, "Personal"), (5, "Home & family"),
           (6, "Finance & bills"), (7, "Learning")]


def one(text):
    r = rules.interpret(text, today=TODAY, now_time=time(14, 5), baskets=BASKETS, people=["Ravi"], open_tasks=[])
    return r.drafts


@pytest.mark.parametrize("text,title,due,at", [
    ("remind me in 2 hours to call the plant head", "Call the plant head", TODAY, time(16, 5)),
    ("call the electrician in 30 minutes", "Call the electrician", TODAY, time(14, 35)),
    ("tonight at 9 pay the phone bill", "Pay the phone bill", TODAY, time(21, 0)),
    ("next week Monday submit the audit report", "Submit the audit report", date(2026, 11, 23), None),
    ("Remind me at 6 to call mom", "Call mom", TODAY, time(18, 0)),
    ("tomorrow morning at 8 meeting with the contractor", "Meeting with the contractor", date(2026, 11, 22), time(8, 0)),
    ("after lunch review the shutdown plan", "Review the shutdown plan", TODAY, time(14, 0)),
])
def test_more_phrasings(text, title, due, at):
    d = one(text)[0]
    assert (d.title, d.due_date, d.due_time) == (title, due, at)


def test_adjectives_are_not_repeats():
    d = one("by Friday evening send the weekly report to Suresh")[0]
    assert d.title == "Send the weekly report to Suresh" and d.repeat_rule == ""
    assert one("backup the laptop weekly")[0].repeat_rule == "FREQ=WEEKLY"


def test_several_weekdays_and_monthly_day():
    assert one("check compressor oil level every Monday and Thursday")[0].repeat_rule == "FREQ=WEEKLY;BYDAY=MO,TH"
    d = one("pay EMI on the 10th every month")[0]
    assert d.repeat_rule == "FREQ=MONTHLY;BYMONTHDAY=10" and d.person == ""  # EMI is not a name


def test_mom_means_mother_but_MoM_means_minutes():
    assert one("call mom tonight")[0].basket_id == 5
    assert one("Share the MoM of the plant review")[0].basket_id == 3


def test_inform_splits_into_its_own_task():
    assert [d.title for d in one("order bearings for line 2 asap and inform stores")] == [
        "Order bearings for line 2", "Inform stores"]


def _waiting(db, prefs, days, nudges=0):
    t = ts.create_task(db, prefs, {"title": "Follow up with Ravi on the spares quotation", "person": "Ravi",
                                   "status": "waiting"}, now=NOW)
    t.waiting_since = datetime(2026, 11, 21 - days, 8, 0) if days < 21 else datetime(2026, 10, 1)
    t.nudge_count = nudges
    db.commit()
    return t


def test_follow_up_message_gets_firmer(db, prefs):
    gentle = understand.draft_nudge(db, prefs, _waiting(db, prefs, 2), now=NOW)["message"]
    assert gentle.startswith("Hi Ravi, hope you're doing well. Just a gentle reminder about the spares quotation.")
    second = understand.draft_nudge(db, prefs, _waiting(db, prefs, 9, nudges=1), now=NOW)["message"]
    assert second.startswith("Hi Ravi, following up on the spares quotation.")
    firm = understand.draft_nudge(db, prefs, _waiting(db, prefs, 30, nudges=3), now=NOW)["message"]
    assert "pending for a while" in firm


def test_follow_up_message_signs_with_your_name(db):
    from app import settings_store
    from app.settings_store import Prefs

    settings_store.put(db, "display_name", "Sam")
    db.commit()
    t = Task(title="Get the drawings from Anita", person="Anita", status="waiting", created_at=NOW,
             last_activity_at=NOW, updated_at=NOW)
    msg = understand.draft_nudge(db, Prefs(db), t, now=NOW)["message"]
    assert "about the drawings." in msg and msg.endswith("\nSam")


def test_nothing_leaves_the_server(db, prefs, monkeypatch):
    """Understanding notes and writing messages must work with the network switched off."""
    def blocked(*a, **kw):
        raise AssertionError("tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    out = understand.interpret(db, prefs, "Pay the electricity bill tomorrow and follow up with Ravi on Monday")
    assert out["intent"] == "create" and len(out["drafts"]) == 2
    t = _waiting(db, prefs, 3)
    assert understand.draft_nudge(db, prefs, t)["message"]
