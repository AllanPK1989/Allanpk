"""Understanding notes and writing follow-up messages, entirely on your own server.

No paid service and no outside AI: notes are read by the built-in rules (app/rules.py), and
follow-up messages come from templates. Nothing you say or type is sent anywhere.
"""
import re
from datetime import datetime

from sqlalchemy.orm import Session

from . import recurrence, rules
from .dashboard import known_people
from .lanes import is_overdue
from .models import Basket, Task
from .serialize import basket_dict, short_task
from .settings_store import Prefs
from .tasks_service import clock
from .timeutil import utcnow

MAX_OPEN_TASKS = 300  # for "mark the vendor call done" and "what's pending with Ravi?"


def _context(db: Session, prefs: Prefs, now: datetime) -> dict:
    c = clock(prefs, now)
    baskets = db.query(Basket).filter(Basket.archived.is_(False)).order_by(Basket.position, Basket.id).all()
    open_rows = (
        db.query(Task).filter(Task.status.in_(("open", "waiting")))
        .order_by(Task.last_activity_at.desc()).limit(MAX_OPEN_TASKS).all()
    )
    open_tasks = [{
        "id": t.id, "title": t.title, "person": t.person, "status": t.status, "basket_id": t.basket_id,
        "overdue": is_overdue(t, c),
        "due_date": t.due_date.isoformat() if t.due_date else None,
    } for t in open_rows]
    return {"clock": c, "baskets": baskets, "people": known_people(db), "open_tasks": open_tasks,
            "rows": {t.id: t for t in open_rows}}


def draft_dict(d: rules.Draft, baskets: list[Basket]) -> dict:
    basket = next((b for b in baskets if b.id == d.basket_id), None)
    return {
        "title": d.title, "notes": d.notes, "basket_id": d.basket_id, "basket": basket_dict(basket),
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "due_time": d.due_time.strftime("%H:%M") if d.due_time else None,
        "priority": d.priority, "person": d.person, "waiting": d.waiting, "repeat_rule": d.repeat_rule,
        "repeat_label": recurrence.label(d.repeat_rule), "checklist": d.checklist, "guessed": d.guessed,
    }


def interpret(db: Session, prefs: Prefs, text: str, now: datetime | None = None) -> dict:
    now = now or utcnow()
    ctx = _context(db, prefs, now)
    c = ctx["clock"]
    result = rules.interpret(
        text, today=c.today, now_time=c.now_time,
        baskets=[(b.id, b.name) for b in ctx["baskets"]], people=ctx["people"], open_tasks=ctx["open_tasks"],
    )
    targets = []
    for tg in result.targets:
        row = ctx["rows"].get(tg["task_id"])
        if row is None:
            continue
        targets.append({
            "task_id": row.id, "title": row.title,
            "due_date": tg.get("due_date").isoformat() if tg.get("due_date") else None,
            "due_time": tg.get("due_time").strftime("%H:%M") if tg.get("due_time") else None,
        })
    answer = result.answer
    if result.intent == "create" and not answer:
        n = len(result.drafts)
        answer = "1 task ready to save." if n == 1 else f"{n} tasks ready to save."
    return {
        "transcript": text,
        "intent": result.intent,
        "drafts": [draft_dict(d, ctx["baskets"]) for d in result.drafts],
        "targets": targets,
        "answer": answer,
        "matches": [short_task(ctx["rows"][i], c, now) for i in result.match_ids if i in ctx["rows"]],
    }


# ---- follow-up messages ---------------------------------------------------------------------------

_LEAD = re.compile(
    r"^(?:follow(?:\s|-)?up|chase(?:\s+up)?|remind|waiting\s+(?:for|on)|get|collect|ask)\s+"
    r"(?:with\s+|from\s+)?(?:{person}\s*)?(?:on|about|for|to|regarding|re)?\s*",
    re.I,
)


def _what(task: Task) -> str:
    """'Follow up with Ravi on the spares quotation' -> 'the spares quotation'."""
    title = task.title.strip()
    if task.person:
        lead = re.compile(_LEAD.pattern.replace("{person}", re.escape(task.person)), re.I)
        title = lead.sub("", title, count=1).strip()
        title = re.sub(r"\s+from\s+" + re.escape(task.person) + r"\b", "", title, flags=re.I).strip()
    title = title.strip(" .:,-") or task.title
    if title[:2].isupper():  # keep acronyms such as "PM report"
        return title
    return title[0].lower() + title[1:]


def draft_nudge(db: Session, prefs: Prefs, task: Task, now: datetime | None = None) -> dict:
    """A polite, ready-to-send follow-up. Gets a little firmer the longer you've waited."""
    now = now or utcnow()
    days = max(0, (now - (task.waiting_since or task.created_at)).days)
    asked = task.nudge_count or 0
    name = task.person.title() if task.person else "there"
    what = _what(task)
    if asked == 0 and days < 7:
        body = (f"Hi {name}, hope you're doing well. Just a gentle reminder about {what}. "
                "Could you please share an update when you get a chance?")
    elif asked <= 1 and days < 14:
        body = (f"Hi {name}, following up on {what}. Could you let me know where this stands, "
                "and when I can expect it?")
    else:
        body = (f"Hi {name}, I'm following up again on {what}, as it's been pending for a while now. "
                "Could you please share it, or a firm date, by tomorrow? Let me know if anything is "
                "holding it up.")
    body += " Thanks!"
    if prefs.display_name:
        body += f"\n{prefs.display_name}"
    return {"message": body}
