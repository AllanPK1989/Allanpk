"""Repeating tasks, stored as RFC 5545 RRULE strings such as FREQ=WEEKLY;BYDAY=MO."""
from datetime import date, datetime, time, timedelta

from dateutil.rrule import rrulestr

DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", -1: "last"}
ALLOWED_KEYS = {"FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYMONTH", "BYSETPOS"}


def normalize(rule: str) -> str:
    """Return a clean RRULE (no 'RRULE:' prefix, no COUNT/UNTIL/DTSTART), or '' if invalid."""
    if not rule:
        return ""
    rule = rule.strip().upper()
    if rule.startswith("RRULE:"):
        rule = rule[6:]
    parts = {}
    for chunk in rule.split(";"):
        if "=" not in chunk:
            continue
        k, v = chunk.split("=", 1)
        if k in ALLOWED_KEYS and v:
            parts[k] = v
    if parts.get("FREQ") not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        return ""
    clean = ";".join(f"{k}={parts[k]}" for k in ["FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYMONTH", "BYSETPOS"] if k in parts)
    try:
        rrulestr(clean, dtstart=datetime(2026, 1, 1, 9, 0))
    except (ValueError, TypeError):
        return ""
    return clean


def next_date(rule: str, after: date, at: time | None = None) -> date | None:
    """First occurrence strictly after `after`."""
    rule = normalize(rule)
    if not rule:
        return None
    start = datetime.combine(after, at or time(9, 0))
    r = rrulestr(rule, dtstart=start - timedelta(days=400))
    nxt = r.after(datetime.combine(after, time(23, 59, 59)))
    return nxt.date() if nxt else None


def first_date(rule: str, on_or_after: date) -> date | None:
    """First occurrence on or after a date (used when a repeating task is created without a date)."""
    return next_date(rule, on_or_after - timedelta(days=1))


def label(rule: str) -> str:
    rule = normalize(rule)
    if not rule:
        return ""
    p = dict(chunk.split("=", 1) for chunk in rule.split(";"))
    freq, interval = p["FREQ"], int(p.get("INTERVAL", "1") or 1)
    byday = [d for d in p.get("BYDAY", "").split(",") if d]

    def day_name(code: str) -> str:
        code = code[-2:]
        return DAY_NAMES[DAY_CODES.index(code)] if code in DAY_CODES else code

    if freq == "DAILY":
        return "Every day" if interval == 1 else f"Every {interval} days"
    if freq == "WEEKLY":
        if sorted(byday) == sorted(["MO", "TU", "WE", "TH", "FR"]):
            return "Every weekday"
        days = ", ".join(day_name(d) for d in byday)
        base = "Every week" if interval == 1 else f"Every {interval} weeks"
        if days:
            return f"Every {days}" if interval == 1 else f"{base} on {days}"
        return base
    if freq == "MONTHLY":
        base = "Every month" if interval == 1 else f"Every {interval} months"
        if byday:
            code = byday[0]
            n = code[:-2]
            try:
                ordinal = ORDINALS.get(int(n), f"{n}th") if n else ""
            except ValueError:
                ordinal = ""
            return f"{base} on the {ordinal} {day_name(code)}".replace("  ", " ")
        if "BYMONTHDAY" in p:
            d = int(p["BYMONTHDAY"].split(",")[0])
            if d == -1:
                return f"{base} on the last day"
            suffix = "th" if 11 <= d % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
            return f"{base} on the {d}{suffix}"
        return base
    if freq == "YEARLY":
        return "Every year" if interval == 1 else f"Every {interval} years"
    return "Repeats"
