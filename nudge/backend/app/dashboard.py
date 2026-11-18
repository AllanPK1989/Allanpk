"""Numbers for the dashboard, the morning briefing, the evening wrap-up and the weekly review."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .lanes import Clock, is_overdue, lane, sort_key, waiting_days
from .models import Basket, Task
from .serialize import basket_dict, short_task
from .settings_store import Prefs
from .tasks_service import clock
from .timeutil import to_local, utcnow, week_start

AGING_BUCKETS = [("0–3 days", 0, 3), ("4–7 days", 4, 7), ("8–14 days", 8, 14), ("15–30 days", 15, 30),
                 ("30+ days", 31, 10**6)]
TREND_WEEKS = 8


def _active(db: Session) -> list[Task]:
    return db.query(Task).filter(Task.status.in_(("open", "waiting"))).all()


def _closed_since(db: Session, since_utc: datetime) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.status == "done", Task.closed_at.isnot(None), Task.closed_at >= since_utc)
        .all()
    )


def _local_date(dt: datetime, prefs: Prefs) -> date:
    return to_local(dt, prefs.zone).date()


def greeting(prefs: Prefs, now: datetime) -> str:
    hour = to_local(now, prefs.zone).hour
    part = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return f"{part}, {prefs.display_name}" if prefs.display_name else part


def is_stale(t: Task, prefs: Prefs, now: datetime, today: date | None = None) -> bool:
    """Open, unscheduled (or long past its date) and untouched for `stale_days`.

    Repeating tasks and "waiting on" items are left out: they have their own rhythm (repeats and
    nudges), and a task with a future date is scheduled, not forgotten.
    """
    limit = now - timedelta(days=prefs.stale_days)
    if t.status != "open" or t.repeat_rule or t.last_activity_at > limit:
        return False
    today = today or to_local(now, prefs.zone).date()
    if t.due_date is not None and t.due_date >= today:
        return False
    return t.stale_prompted_at is None or t.stale_prompted_at < limit


def radar(active: list[Task], c: Clock, now: datetime) -> list[dict]:
    groups: dict[str, list[Task]] = defaultdict(list)
    for t in active:
        if t.status == "waiting" and t.person:
            groups[t.person.strip().title()].append(t)
    out = []
    for person, items in groups.items():
        items.sort(key=lambda t: -waiting_days(t, now))
        out.append({
            "person": person,
            "count": len(items),
            "oldest_days": waiting_days(items[0], now),
            "items": [short_task(t, c, now) for t in items],
        })
    out.sort(key=lambda g: (-g["oldest_days"], g["person"]))
    return out


def dashboard(db: Session, prefs: Prefs, now: datetime | None = None) -> dict:
    now = now or utcnow()
    c = clock(prefs, now)
    active = _active(db)
    wk = week_start(c.today)
    closed_recent = _closed_since(db, now - timedelta(days=7 * TREND_WEEKS + 7))
    closed_week = [t for t in closed_recent if _local_date(t.closed_at, prefs) >= wk]
    closed_today = [t for t in closed_recent if _local_date(t.closed_at, prefs) == c.today]

    lanes = defaultdict(int)
    for t in active:
        lanes[lane(t, c)] += 1
    overdue = [t for t in active if is_overdue(t, c)]
    due_today = [t for t in active if t.due_date == c.today and not is_overdue(t, c)]

    today_list = [t for t in active if lane(t, c) in ("overdue", "today")
                  or (t.status == "waiting" and t.due_date is not None and t.due_date <= c.today)]
    today_list.sort(key=lambda t: sort_key(t, c))
    focus = sorted([t for t in active if t.focus_date == c.today], key=lambda t: sort_key(t, c))

    # Basket tiles
    baskets = db.query(Basket).filter(Basket.archived.is_(False)).order_by(Basket.position, Basket.id).all()
    since30 = now - timedelta(days=30)
    tiles = []
    for b in baskets + [None]:
        bid = b.id if b else None
        items = [t for t in active if t.basket_id == bid]
        cleared = [t for t in closed_recent if t.basket_id == bid and t.closed_at >= since30]
        if b is None and not items and not cleared:
            continue
        oldest = max(((now - t.created_at).days for t in items), default=0)
        total = len(items) + len(cleared)
        tiles.append({
            "basket": basket_dict(b) or {"id": None, "name": "No basket", "color": "slate", "icon": "inbox"},
            "open": len(items),
            "overdue": sum(1 for t in items if is_overdue(t, c)),
            "waiting": sum(1 for t in items if t.status == "waiting"),
            "due_today": sum(1 for t in items if t.due_date == c.today),
            "oldest_days": oldest,
            "cleared_30": len(cleared),
            "cleared_pct": round(100 * len(cleared) / total) if total else 0,
        })

    # Backlog aging (open work by how long it has been around)
    aging = []
    for label, lo, hi in AGING_BUCKETS:
        aging.append({"label": label, "count": sum(1 for t in active if lo <= (now - t.created_at).days <= hi)})

    # Weekly trend: created vs closed, last 8 weeks
    created_recent = db.query(Task.created_at).filter(
        Task.created_at >= now - timedelta(days=7 * TREND_WEEKS + 7),
        Task.source.notin_(("repeat",)),
    ).all()
    trend = []
    for i in range(TREND_WEEKS - 1, -1, -1):
        start = wk - timedelta(days=7 * i)
        end = start + timedelta(days=7)
        trend.append({
            "week_start": start.isoformat(),
            "created": sum(1 for (ca,) in created_recent if start <= _local_date(ca, prefs) < end),
            "closed": sum(1 for t in closed_recent if start <= _local_date(t.closed_at, prefs) < end),
        })

    stale = sorted([t for t in active if is_stale(t, prefs, now)], key=lambda t: t.last_activity_at)

    return {
        "greeting": greeting(prefs, now),
        "today": c.today.isoformat(),
        "kpis": {
            "overdue": len(overdue),
            "due_today": len(due_today),
            "waiting": lanes["waiting"],
            "closed_week": len(closed_week),
        },
        "lanes": {k: lanes.get(k, 0) for k in ("inbox", "today", "upcoming", "waiting", "overdue")},
        "closed_today": len(closed_today),
        "focus": [short_task(t, c, now) for t in focus],
        "today_list": [short_task(t, c, now) for t in today_list[:40]],
        "baskets": tiles,
        "radar": radar(active, c, now),
        "aging": aging,
        "trend": trend,
        "stale": [short_task(t, c, now) for t in stale[:5]],
        "stale_count": len(stale),
        "open_total": len(active),
    }


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def briefing(db: Session, prefs: Prefs, now: datetime | None = None) -> dict:
    now = now or utcnow()
    c = clock(prefs, now)
    active = _active(db)
    overdue = sorted([t for t in active if is_overdue(t, c)], key=lambda t: sort_key(t, c))
    due_today = sorted([t for t in active if t.due_date == c.today and not is_overdue(t, c)],
                       key=lambda t: sort_key(t, c))
    focus = [t for t in active if t.focus_date == c.today]
    end_of_day = now + timedelta(hours=24)
    nudges = sorted(
        [t for t in active if t.status == "waiting" and t.next_nudge_at and t.next_nudge_at <= end_of_day
         and _local_date(t.next_nudge_at, prefs) <= c.today],
        key=lambda t: -waiting_days(t, now),
    )
    waiting = [t for t in active if t.status == "waiting"]
    stale = [t for t in active if is_stale(t, prefs, now)]
    inbox = [t for t in active if lane(t, c) == "inbox"]

    parts = [greeting(prefs, now) + "."]
    if not due_today and not overdue:
        parts.append("Nothing is due today.")
    else:
        bits = []
        if due_today:
            bits.append(f"{_plural(len(due_today), 'task')} due today")
        if overdue:
            bits.append(f"{len(overdue)} overdue")
        parts.append("You have " + " and ".join(bits) + ".")
        first = (overdue + due_today)[0]
        when = f" at {first.due_time.strftime('%H:%M')}" if first.due_time and first in due_today else ""
        parts.append(f"First up: {first.title}{when}.")
    if focus:
        parts.append("Your Top 3: " + _join([t.title for t in focus]) + ".")
    if nudges:
        people = sorted({t.person.title() for t in nudges})
        parts.append(f"Time to follow up with {_join(people)}.")
    elif waiting:
        longest = max(waiting, key=lambda t: waiting_days(t, now))
        parts.append(f"You're waiting on {_plural(len(waiting), 'item')}; the longest is "
                     f"{longest.person.title()} at {_plural(waiting_days(longest, now), 'day')}.")
    if stale:
        parts.append(f"{_plural(len(stale), 'task')} {'has' if len(stale) == 1 else 'have'} gone quiet "
                     "and need a decision.")
    if inbox:
        parts.append(f"{len(inbox)} in your inbox without a date.")

    return {
        "kind": "briefing",
        "greeting": greeting(prefs, now),
        "date": c.today.isoformat(),
        "text": " ".join(parts),
        "overdue": [short_task(t, c, now) for t in overdue],
        "due_today": [short_task(t, c, now) for t in due_today],
        "focus": [short_task(t, c, now) for t in focus],
        "nudges": [short_task(t, c, now) for t in nudges],
        "waiting_count": len(waiting),
        "stale": [short_task(t, c, now) for t in stale[:10]],
        "inbox_count": len(inbox),
    }


def wrapup(db: Session, prefs: Prefs, now: datetime | None = None) -> dict:
    now = now or utcnow()
    c = clock(prefs, now)
    closed_today = [t for t in _closed_since(db, now - timedelta(days=2)) if _local_date(t.closed_at, prefs) == c.today]
    active = _active(db)
    carried = sorted([t for t in active if t.status == "open" and t.due_date is not None and t.due_date <= c.today],
                     key=lambda t: sort_key(t, c))
    tomorrow = c.today + timedelta(days=1)
    due_tomorrow = [t for t in active if t.due_date == tomorrow]

    parts = []
    if closed_today:
        parts.append(f"Nice work: {_plural(len(closed_today), 'task')} closed today.")
    else:
        parts.append("No tasks closed today.")
    if carried:
        parts.append(f"{len(carried)} still open from today or earlier; move them to tomorrow or drop them.")
    parts.append(f"Tomorrow: {_plural(len(due_tomorrow), 'task')} due." if due_tomorrow else "Nothing due tomorrow yet.")
    if c.today.weekday() == 6:
        parts.append("Your weekly review is ready.")
    return {
        "kind": "wrapup",
        "date": c.today.isoformat(),
        "text": " ".join(parts),
        "closed_today": [short_task(t, c, now) for t in closed_today],
        "carried": [short_task(t, c, now) for t in carried],
        "due_tomorrow": [short_task(t, c, now) for t in due_tomorrow],
        "weekly_review_ready": c.today.weekday() == 6,
    }


def weekly_review(db: Session, prefs: Prefs, offset: int = 0, now: datetime | None = None) -> dict:
    now = now or utcnow()
    c = clock(prefs, now)
    ws = week_start(c.today) - timedelta(days=7 * max(0, offset))
    we = ws + timedelta(days=7)
    lookback = now - timedelta(days=7 * (offset + 2) + 2)
    closed = [t for t in _closed_since(db, lookback) if ws <= _local_date(t.closed_at, prefs) < we]
    dropped = db.query(Task).filter(Task.status == "dropped", Task.closed_at >= lookback).all()
    dropped = [t for t in dropped if ws <= _local_date(t.closed_at, prefs) < we]
    created = db.query(Task).filter(Task.created_at >= lookback, Task.source != "repeat").all()
    created = [t for t in created if ws <= _local_date(t.created_at, prefs) < we]
    active = _active(db)

    by_day = []
    for i in range(7):
        d = ws + timedelta(days=i)
        by_day.append({"date": d.isoformat(), "closed": sum(1 for t in closed if _local_date(t.closed_at, prefs) == d)})
    by_basket = defaultdict(int)
    for t in closed:
        by_basket[t.basket.name if t.basket else "No basket"] += 1
    slipped = sorted([t for t in active if t.due_date and ws <= t.due_date < min(we, c.today + timedelta(days=1))
                      and is_overdue(t, c)], key=lambda t: sort_key(t, c))
    oldest = sorted(active, key=lambda t: t.created_at)[:5]
    waiting_longest = sorted([t for t in active if t.status == "waiting"], key=lambda t: -waiting_days(t, now))[:5]
    next_ws, next_we = we, we + timedelta(days=7)
    stale = [t for t in active if is_stale(t, prefs, now)]

    return {
        "week_start": ws.isoformat(),
        "week_end": (we - timedelta(days=1)).isoformat(),
        "offset": offset,
        "closed_count": len(closed),
        "created_count": len(created),
        "dropped_count": len(dropped),
        "closed": [short_task(t, c, now) for t in sorted(closed, key=lambda t: t.closed_at, reverse=True)],
        "by_day": by_day,
        "by_basket": [{"name": k, "count": v} for k, v in sorted(by_basket.items(), key=lambda kv: -kv[1])],
        "slipped": [short_task(t, c, now) for t in slipped],
        "oldest": [short_task(t, c, now) for t in oldest],
        "waiting_longest": [short_task(t, c, now) for t in waiting_longest],
        "stale": [short_task(t, c, now) for t in stale[:10]],
        "next_week_count": sum(1 for t in active if t.due_date and next_ws <= t.due_date < next_we),
        "open_total": len(active),
    }


def people(db: Session, prefs: Prefs, now: datetime | None = None) -> list[dict]:
    now = now or utcnow()
    c = clock(prefs, now)
    since = now - timedelta(days=60)
    rows = db.query(Task).filter(Task.person != "", or_(Task.status.in_(("open", "waiting")),
                                                          Task.closed_at >= since)).all()
    groups: dict[str, list[Task]] = defaultdict(list)
    for t in rows:
        groups[t.person.strip().title()].append(t)
    out = []
    for person, items in groups.items():
        waiting = sorted([t for t in items if t.status == "waiting"], key=lambda t: -waiting_days(t, now))
        open_ = sorted([t for t in items if t.status == "open"], key=lambda t: sort_key(t, c))
        done = sorted([t for t in items if t.status == "done"], key=lambda t: t.closed_at, reverse=True)
        out.append({
            "person": person,
            "waiting": [short_task(t, c, now) for t in waiting],
            "open": [short_task(t, c, now) for t in open_],
            "recent_done": [short_task(t, c, now) for t in done[:5]],
            "oldest_waiting_days": waiting_days(waiting[0], now) if waiting else 0,
        })
    out.sort(key=lambda p: (-len(p["waiting"]), -p["oldest_waiting_days"], p["person"]))
    return out


def known_people(db: Session, limit: int = 60) -> list[str]:
    rows = db.query(Task.person).filter(Task.person != "").order_by(Task.last_activity_at.desc()).limit(500).all()
    seen, out = set(), []
    for (p,) in rows:
        key = p.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(p.strip().title())
        if len(out) >= limit:
            break
    return out
