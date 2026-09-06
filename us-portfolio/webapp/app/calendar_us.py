"""US equity market sessions.

Answers two questions the dashboard needs constantly: is the market open right
now, and what was the last session that actually traded. Everything is derived
in US/Eastern and returned as plain data.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# NYSE full-day closures. Advisory: a missing date only costs a wasted fetch,
# it never blocks a refresh the caller asked for.
HOLIDAYS = {
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    # 2027
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
    "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
}
# 1pm ET closes (day after Thanksgiving, Christmas Eve, July 3 when it trades)
HALF_DAYS = {"2026-11-27", "2026-12-24", "2027-11-26"}

OPEN_T = dt.time(9, 30)
CLOSE_T = dt.time(16, 0)
HALF_CLOSE_T = dt.time(13, 0)
PRE_T = dt.time(4, 0)
POST_T = dt.time(20, 0)


def is_session(d: dt.date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS


def last_session(on: dt.date) -> dt.date:
    d = on
    for _ in range(12):
        if is_session(d):
            return d
        d -= dt.timedelta(days=1)
    return d


def next_session(after: dt.date) -> dt.date:
    d = after + dt.timedelta(days=1)
    for _ in range(12):
        if is_session(d):
            return d
        d += dt.timedelta(days=1)
    return d


def close_time(d: dt.date) -> dt.time:
    return HALF_CLOSE_T if d.isoformat() in HALF_DAYS else CLOSE_T


def status(now: dt.datetime | None = None) -> dict:
    """Current market state, as data the UI can render directly.

    phase is one of: open, pre, post, closed
    poll_seconds tells the client how often it is worth asking again.
    """
    now = (now or dt.datetime.now(ET)).astimezone(ET)
    today = now.date()
    trading = is_session(today)
    close_at = close_time(today)

    if trading and OPEN_T <= now.time() < close_at:
        phase, label = "open", "Market open"
        poll = 60
    elif trading and PRE_T <= now.time() < OPEN_T:
        phase, label = "pre", "Pre-market"
        poll = 300
    elif trading and close_at <= now.time() < POST_T:
        phase, label = "post", "After hours"
        poll = 300
    else:
        phase = "closed"
        poll = 900
        if not trading:
            why = "Weekend" if today.weekday() >= 5 else "Market holiday"
            label = f"Closed · {why}"
        else:
            label = "Closed"

    # Before the bell the reference close is still the previous session.
    ref = last_session(today - dt.timedelta(days=1)) if (trading and now.time() < OPEN_T) \
        else last_session(today)

    nxt = next_session(today) if phase == "closed" else None
    return {
        "phase": phase,
        "label": label,
        "is_open": phase == "open",
        "now_et": now.isoformat(timespec="seconds"),
        "last_session": ref.isoformat(),
        "next_session": nxt.isoformat() if nxt else None,
        "poll_seconds": poll,
    }
