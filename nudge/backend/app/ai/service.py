"""Understanding notes: Claude when configured, the built-in rules otherwise (or when Claude fails)."""
import re
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .. import recurrence, rules
from ..config import BACKEND_DIR, get_config
from ..dashboard import known_people
from ..lanes import is_overdue
from ..models import AICall, Basket, Task
from ..serialize import basket_dict, short_task
from ..settings_store import Prefs
from ..tasks_service import clock
from ..timeutil import local_now, utcnow
from .claude import AIResult, ClaudeClient

PROMPTS = BACKEND_DIR / "prompts"
MAX_OPEN_TASKS_IN_CONTEXT = 150

_STR = {"type": "string"}
INTERPRET_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["create", "complete", "reschedule", "query", "unclear"]},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": _STR,
                    "notes": _STR,
                    "basket": _STR,
                    "due_date": _STR,
                    "due_time": _STR,
                    "priority": {"type": "string", "enum": ["high", "normal", "low"]},
                    "person": _STR,
                    "waiting_on_person": {"type": "boolean"},
                    "repeat_rule": _STR,
                    "checklist": {"type": "array", "items": _STR},
                    "guessed": {"type": "array", "items": {
                        "type": "string", "enum": ["basket", "due_date", "due_time", "priority", "person"]}},
                },
                "required": ["title", "notes", "basket", "due_date", "due_time", "priority", "person",
                             "waiting_on_person", "repeat_rule", "checklist", "guessed"],
                "additionalProperties": False,
            },
        },
        "targets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"task_id": {"type": "integer"}, "new_due_date": _STR, "new_due_time": _STR},
                "required": ["task_id", "new_due_date", "new_due_time"],
                "additionalProperties": False,
            },
        },
        "answer": _STR,
        "match_ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["intent", "tasks", "targets", "answer", "match_ids"],
    "additionalProperties": False,
}
NUDGE_SCHEMA = {
    "type": "object",
    "properties": {"message": _STR},
    "required": ["message"],
    "additionalProperties": False,
}

_client: ClaudeClient | None = None


def claude() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient(get_config())
    return _client


def set_client(client: ClaudeClient | None) -> None:
    """Tests swap in a fake client."""
    global _client
    _client = client


def ai_enabled() -> bool:
    return get_config().ai_provider == "anthropic"


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.v1.md").read_text()


def _log_call(db: Session, purpose: str, result: AIResult) -> None:
    cfg = get_config()
    pin, pout = cfg.price(result.model)
    if (pin, pout) == (0.0, 0.0):
        pin, pout = cfg.price(cfg.ai_model)
    cost = (result.input_tokens * pin + result.output_tokens * pout) / 1_000_000
    db.add(AICall(purpose=purpose, provider="anthropic", model=result.model, input_tokens=result.input_tokens,
                  output_tokens=result.output_tokens, cost_usd=round(cost, 6), ok=not result.error,
                  error=result.error[:500], latency_ms=result.latency_ms))
    db.flush()


# ---- context -----------------------------------------------------------------------------------

def _context(db: Session, prefs: Prefs, now: datetime) -> dict:
    c = clock(prefs, now)
    baskets = db.query(Basket).filter(Basket.archived.is_(False)).order_by(Basket.position, Basket.id).all()
    open_rows = (
        db.query(Task).filter(Task.status.in_(("open", "waiting")))
        .order_by(Task.last_activity_at.desc()).limit(MAX_OPEN_TASKS_IN_CONTEXT).all()
    )
    open_tasks = [{
        "id": t.id, "title": t.title, "person": t.person, "status": t.status, "basket_id": t.basket_id,
        "basket": t.basket.name if t.basket else "", "overdue": is_overdue(t, c),
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "due_time": t.due_time.strftime("%H:%M") if t.due_time else None,
    } for t in open_rows]
    return {"clock": c, "baskets": baskets, "people": known_people(db), "open_tasks": open_tasks,
            "rows": {t.id: t for t in open_rows}}


def _user_message(text: str, ctx: dict, prefs: Prefs, now: datetime) -> str:
    local = local_now(prefs.zone, now)
    today = local.date()
    days = "\n".join(
        f"- {(today + timedelta(days=i)).strftime('%a %d %b %Y')} = {(today + timedelta(days=i)).isoformat()}"
        + (" (today)" if i == 0 else " (tomorrow)" if i == 1 else "")
        for i in range(0, 15)
    )
    baskets = "; ".join(b.name for b in ctx["baskets"]) or "(none)"
    people = ", ".join(ctx["people"]) or "(none yet)"
    tasks = "\n".join(
        f"#{t['id']} | {t['title']} | {t['person'] or '-'} | due {t['due_date'] or '-'}"
        f"{' ' + t['due_time'] if t['due_time'] else ''} | {t['status']}{' (overdue)' if t['overdue'] else ''}"
        for t in ctx["open_tasks"]
    ) or "(no open tasks)"
    return (
        f"Now: {local.strftime('%A %d %B %Y, %H:%M')} ({prefs.zone.key})\n\n"
        f"Calendar for the next two weeks:\n{days}\n\n"
        f"Baskets: {baskets}\n"
        f"People mentioned before: {people}\n\n"
        f"Open tasks (id | title | person | due | status):\n{tasks}\n\n"
        f"Note to interpret:\n\"\"\"\n{text.strip()}\n\"\"\""
    )


# ---- converting Claude's answer into drafts -------------------------------------------------------

def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def _parse_time(s: str) -> time | None:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s or "")
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return None
    return time(int(m[1]), int(m[2]))


def _basket_id(name: str, baskets: list[Basket]) -> int | None:
    name = (name or "").strip().lower()
    if not name:
        return None
    for b in baskets:
        if b.name.lower() == name:
            return b.id
    for b in baskets:
        if name in b.name.lower() or b.name.lower().split()[0] in name:
            return b.id
    return None


def _from_claude(data: dict, ctx: dict) -> rules.Interpretation:
    intent = data.get("intent") if data.get("intent") in ("create", "complete", "reschedule", "query", "unclear") \
        else "unclear"
    drafts = []
    for t in (data.get("tasks") or [])[:15]:
        title = (t.get("title") or "").strip()[:300]
        if not title:
            continue
        due_date = _parse_date(t.get("due_date", ""))
        rule = recurrence.normalize(t.get("repeat_rule", ""))
        if rule and not due_date:
            due_date = recurrence.first_date(rule, ctx["clock"].today)
        guessed = [g for g in (t.get("guessed") or []) if g in ("basket", "due_date", "due_time", "priority", "person")]
        basket_id = _basket_id(t.get("basket", ""), ctx["baskets"])
        if basket_id is None and "basket" not in guessed:
            guessed.append("basket")
        person = (t.get("person") or "").strip()[:80]
        drafts.append(rules.Draft(
            title=title, notes=(t.get("notes") or "").strip(), basket_id=basket_id, due_date=due_date,
            due_time=_parse_time(t.get("due_time", "")) if due_date else None,
            priority=t.get("priority") if t.get("priority") in ("high", "normal", "low") else "normal",
            person=person, waiting=bool(t.get("waiting_on_person")) and bool(person), repeat_rule=rule,
            checklist=[c.strip() for c in (t.get("checklist") or []) if c and c.strip()][:20], guessed=guessed,
        ))
    open_ids = set(ctx["rows"])
    targets = []
    for tg in data.get("targets") or []:
        if tg.get("task_id") in open_ids:
            targets.append({"task_id": tg["task_id"], "due_date": _parse_date(tg.get("new_due_date", "")),
                            "due_time": _parse_time(tg.get("new_due_time", ""))})
    match_ids = [i for i in (data.get("match_ids") or []) if i in open_ids]
    if intent == "create" and not drafts:
        intent = "unclear"
    if intent in ("complete", "reschedule") and not targets:
        intent = "unclear" if not data.get("answer") else intent
    return rules.Interpretation(intent=intent, drafts=drafts, targets=targets,
                                answer=(data.get("answer") or "").strip()[:500], match_ids=match_ids)


# ---- public ------------------------------------------------------------------------------------

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
    result: rules.Interpretation | None = None
    used, warning = "rules", ""

    if ai_enabled() and text.strip():
        ai = claude().generate_json(system=_prompt("interpret"), user=_user_message(text, ctx, prefs, now),
                                    schema=INTERPRET_SCHEMA)
        _log_call(db, "interpret", ai)
        if ai.data is not None and not ai.error:
            result = _from_claude(ai.data, ctx)
            used = "claude"
        else:
            warning = "Claude couldn't be reached, so simple rules were used. Please check the details."

    if result is None:
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
    matches = [short_task(ctx["rows"][i], c, now) for i in result.match_ids if i in ctx["rows"]]
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
        "matches": matches,
        "understood_by": used,
        "warning": warning,
    }


def draft_nudge(db: Session, prefs: Prefs, task: Task, now: datetime | None = None) -> dict:
    now = now or utcnow()
    days = max(0, (now - (task.waiting_since or task.created_at)).days)
    person = task.person.title() if task.person else "there"
    sender = prefs.display_name
    if ai_enabled():
        user = (
            f"Waiting on: {person}\nWhat is pending: {task.title}\n"
            f"Extra detail: {task.notes or '-'}\nDays waiting so far: {days}\n"
            f"Reminders already sent: {task.nudge_count or 0}\nSender's name: {sender or '(not given)'}"
        )
        ai = claude().generate_json(system=_prompt("nudge"), user=user, schema=NUDGE_SCHEMA, max_tokens=2000)
        _log_call(db, "nudge", ai)
        if ai.data and ai.data.get("message") and not ai.error:
            return {"message": ai.data["message"].strip(), "written_by": "claude"}

    what = re.sub(r"^(follow(?:\s|-)?up|chase|remind|waiting\s+for|waiting\s+on)\s+(?:with\s+)?"
                  + re.escape(task.person) + r"\s*(?:on|about|for|to|regarding)?\s*", "", task.title, flags=re.I).strip()
    what = what or task.title
    what = what[0].lower() + what[1:] if what and not what[:2].isupper() else what
    gentle = "Just a gentle reminder" if not task.nudge_count and days < 7 else "Following up again"
    message = (f"Hi {person}, {gentle.lower()} about {what}. "
               f"Could you please share an update when you get a chance? Thanks!")
    if sender:
        message += f"\n{sender}"
    return {"message": message, "written_by": "template"}


def usage_summary(db: Session) -> dict:
    now = utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(AICall).filter(AICall.at >= start).all()
    return {
        "provider": get_config().ai_provider,
        "model": get_config().ai_model if ai_enabled() else "",
        "calls_this_month": len(rows),
        "failed_this_month": sum(1 for r in rows if not r.ok),
        "cost_usd_this_month": round(sum(r.cost_usd for r in rows), 4),
        "avg_latency_ms": int(sum(r.latency_ms for r in rows) / len(rows)) if rows else 0,
    }
