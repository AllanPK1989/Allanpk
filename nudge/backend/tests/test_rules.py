"""The built-in rules: what demo mode (and a Claude outage) understands."""
from datetime import date, time

import pytest

from app import recurrence, rules

TODAY = date(2026, 11, 18)  # a Wednesday
BASKETS = [(1, "Work"), (2, "Projects"), (3, "Meetings & action points"), (4, "Personal"), (5, "Home & family"),
           (6, "Finance & bills"), (7, "Learning")]
OPEN = [
    {"id": 10, "title": "Call the vendor about bearing quote", "person": "Vendor", "status": "open",
     "due_date": "2026-11-18", "overdue": False, "basket_id": 1},
    {"id": 11, "title": "Send PM report", "person": "", "status": "open", "due_date": "2026-11-20",
     "overdue": False, "basket_id": 1},
    {"id": 12, "title": "Follow up with Ravi on spares", "person": "Ravi", "status": "waiting",
     "due_date": None, "overdue": True, "basket_id": 1},
]


def run(text, people=("Ravi",)):
    return rules.interpret(text, today=TODAY, now_time=time(14, 5), baskets=BASKETS, people=list(people),
                           open_tasks=OPEN)


def test_brain_dump_splits_into_three_tasks():
    r = run("Call the vendor about the bearing quote, send the PM report by Friday, "
            "and follow up with Ravi on spares next Tuesday")
    assert r.intent == "create"
    assert [d.title for d in r.drafts] == ["Call the vendor about the bearing quote", "Send the PM report",
                                           "Follow up with Ravi on spares"]
    assert r.drafts[1].due_date == date(2026, 11, 20)
    ravi = r.drafts[2]
    assert (ravi.person, ravi.waiting, ravi.due_date) == ("Ravi", True, date(2026, 11, 24))


def test_one_action_with_two_people_stays_one_task():
    r = run("Call Ravi and Kumar about the shutdown plan")
    assert len(r.drafts) == 1


@pytest.mark.parametrize("text,due,at", [
    ("Pay the electricity bill tomorrow at 5pm", date(2026, 11, 19), time(17, 0)),
    ("Email Priya the shutdown plan by 10:30 am tomorrow", date(2026, 11, 19), time(10, 30)),
    ("Renew car insurance on 25/11", date(2026, 11, 25), None),
    ("Submit the report by end of the week", date(2026, 11, 20), None),
    ("Pay rent by the end of the month", date(2026, 11, 30), None),
    ("Book flights in 3 days", date(2026, 11, 21), None),
    ("Call amma tonight", date(2026, 11, 18), time(20, 0)),
    ("Call the plant head at 4", date(2026, 11, 18), time(16, 0)),
    ("Order spares on the 2nd", date(2026, 12, 2), None),
    ("Pay the gas bill on 3rd December", date(2026, 12, 3), None),
])
def test_dates_and_times(text, due, at):
    d = run(text).drafts[0]
    assert (d.due_date, d.due_time) == (due, at)


def test_vague_dates_are_flagged_as_guesses():
    d = run("Book a dentist appointment next week").drafts[0]
    assert d.due_date == date(2026, 11, 23)
    assert "due_date" in d.guessed


@pytest.mark.parametrize("text,rule,first", [
    ("Study CMRP chapter 4 every Monday at 7am", "FREQ=WEEKLY;BYDAY=MO", date(2026, 11, 23)),
    ("Pay credit card bill on the 5th of every month", "FREQ=MONTHLY;BYMONTHDAY=5", date(2026, 12, 5)),
    ("Review the KPI dashboard on the first Monday of every month", "FREQ=MONTHLY;BYDAY=1MO", date(2026, 12, 7)),
    ("Check backups every day", "FREQ=DAILY", date(2026, 11, 18)),
    ("Send the weekly report every weekday", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", date(2026, 11, 18)),
])
def test_repeats(text, rule, first):
    d = run(text).drafts[0]
    assert d.repeat_rule == rule
    assert d.due_date == first


def test_priority_person_and_basket():
    d = run("Urgent: submit the capex proposal to Suresh by end of the week").drafts[0]
    assert d.priority == "high"
    assert d.person == "Suresh"
    assert d.basket_id == 2  # projects keyword
    assert run("Pay the school fees").drafts[0].basket_id == 6
    assert run("Revise CMRP pillar 2 notes").drafts[0].basket_id == 7


def test_named_basket_is_not_a_guess():
    d = run("Add buy a new kettle to the home basket").drafts[0]
    assert d.basket_id == 5 and "basket" not in d.guessed


def test_waiting_detection():
    assert run("Waiting for Anita to send the drawings").drafts[0].waiting
    assert run("Remind Kumar about the calibration certificates").drafts[0].waiting
    assert not run("Call Ravi about the pump").drafts[0].waiting


@pytest.mark.parametrize("text,task_id", [
    ("mark the vendor call done", 10),
    ("I finished the PM report", 11),
    ("The PM report is done", 11),
])
def test_complete_commands(text, task_id):
    r = run(text)
    assert r.intent == "complete" and r.targets == [{"task_id": task_id}]


def test_reschedule_command():
    r = run("move PM report to Monday 10am")
    assert r.intent == "reschedule"
    assert r.targets[0] == {"task_id": 11, "due_date": date(2026, 11, 23), "due_time": time(10, 0)}


def test_queries():
    r = run("what's pending with Ravi?")
    assert r.intent == "query" and r.match_ids == [12]
    r = run("what is overdue")
    assert r.match_ids == [12]


def test_recurrence_helpers():
    assert recurrence.normalize("RRULE:freq=weekly;byday=mo;count=3") == "FREQ=WEEKLY;BYDAY=MO"
    assert recurrence.normalize("FREQ=HOURLY") == ""
    assert recurrence.next_date("FREQ=WEEKLY;BYDAY=MO", date(2026, 11, 23)) == date(2026, 11, 30)
    assert recurrence.next_date("FREQ=MONTHLY;BYMONTHDAY=31", date(2026, 11, 1)) == date(2026, 12, 31)
    assert recurrence.label("FREQ=MONTHLY;BYDAY=1MO") == "Every month on the 1st Monday"
    assert recurrence.label("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR") == "Every weekday"
    assert recurrence.label("FREQ=MONTHLY;BYMONTHDAY=5") == "Every month on the 5th"
