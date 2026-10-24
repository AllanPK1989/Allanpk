"""Shift from time of day, using the shift calendar in settings."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def parse_hhmm(text: str) -> time:
    hours, minutes = text.strip().split(":")
    return time(int(hours), int(minutes))


def shift_for(moment: datetime, shifts: list[dict], tz: str) -> tuple[str, date]:
    """Return (shift name, shift date) for a moment.

    An overnight shift (start later than end, e.g. 22:00-06:00) that is entered after
    midnight belongs to the previous day's shift.
    """
    local = moment.astimezone(ZoneInfo(tz))
    now = local.time()
    for shift in shifts:
        start, end = parse_hhmm(shift["start"]), parse_hhmm(shift["end"])
        if start < end:
            if start <= now < end:
                return shift["name"], local.date()
        elif now >= start:
            return shift["name"], local.date()
        elif now < end:
            return shift["name"], local.date() - timedelta(days=1)
    return "", local.date()


def downtime_minutes(start: datetime | None, end: datetime | None) -> int | None:
    if not start or not end:
        return None
    minutes = round((end - start).total_seconds() / 60)
    return minutes if minutes >= 0 else None
