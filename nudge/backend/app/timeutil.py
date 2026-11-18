"""Time helpers. Storage is naive UTC; the user thinks in their own timezone (default IST)."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:  # unknown name: fall back to IST rather than crash
        return ZoneInfo("Asia/Kolkata")


def to_local(dt_utc: datetime, zone: ZoneInfo) -> datetime:
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(zone)


def local_now(zone: ZoneInfo, now_utc: datetime | None = None) -> datetime:
    return to_local(now_utc or utcnow(), zone)


def local_to_utc(d: date, t: time, zone: ZoneInfo) -> datetime:
    return datetime.combine(d, t, tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)


def iso_utc(dt: datetime | None) -> str | None:
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if dt else None


def parse_hhmm(value: str, default: time) -> time:
    try:
        h, m = value.split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        return default


def week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def in_quiet_hours(now_local: datetime, start: time, end: time) -> bool:
    t = now_local.time()
    if start == end:
        return False
    if start < end:
        return start <= t < end
    return t >= start or t < end  # wraps past midnight, e.g. 21:30 → 07:00
