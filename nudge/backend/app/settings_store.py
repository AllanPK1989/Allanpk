"""Settings you change in the app. Stored as JSON values in the `settings` table."""
from datetime import time

from sqlalchemy.orm import Session

from .config import get_config
from .models import Setting
from .timeutil import parse_hhmm, tz

DEFAULTS: dict[str, object] = {
    "display_name": "",
    "timezone": None,  # None → config.default_timezone
    "briefing_time": "07:30",
    "wrapup_time": "18:30",
    "overdue_nag_time": "12:30",
    "nudge_time": "10:00",  # time of day follow-up nudges arrive
    "quiet_start": "21:30",
    "quiet_end": "07:00",
    "stale_days": 14,
    "default_nudge_days": 3,
    "digest_email": "",
    "email_briefing": True,
    "email_wrapup": False,
    "push_reminders": True,
    "push_nudges": True,
    "push_briefing": True,
    "push_wrapup": True,
    "push_overdue": True,
}

# Keys the Settings screen may change through PATCH /api/settings.
EDITABLE = set(DEFAULTS)

# Internal keys (never returned to the client): PIN hash, lockout state, scheduler markers.
INTERNAL_PREFIXES = ("pin_", "auth_", "mark_", "vapid_", "secret_")


def get(db: Session, key: str, default: object = None) -> object:
    row = db.get(Setting, key)
    if row is not None:
        return row.value
    if key in DEFAULTS:
        return DEFAULTS[key]
    return default


def put(db: Session, key: str, value: object) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value
    db.flush()


def all_public(db: Session) -> dict[str, object]:
    out = dict(DEFAULTS)
    for row in db.query(Setting).all():
        if row.key in DEFAULTS:
            out[row.key] = row.value
    out["timezone"] = out["timezone"] or get_config().default_timezone
    return out


class Prefs:
    """Typed view over settings for the scheduler and services."""

    def __init__(self, db: Session):
        s = all_public(db)
        self.raw = s
        self.zone = tz(str(s["timezone"]))
        self.display_name = str(s["display_name"] or "")
        self.briefing_time = parse_hhmm(str(s["briefing_time"]), time(7, 30))
        self.wrapup_time = parse_hhmm(str(s["wrapup_time"]), time(18, 30))
        self.overdue_nag_time = parse_hhmm(str(s["overdue_nag_time"]), time(12, 30))
        self.nudge_time = parse_hhmm(str(s["nudge_time"]), time(10, 0))
        self.quiet_start = parse_hhmm(str(s["quiet_start"]), time(21, 30))
        self.quiet_end = parse_hhmm(str(s["quiet_end"]), time(7, 0))
        self.stale_days = max(3, int(s["stale_days"] or 14))
        self.default_nudge_days = max(1, int(s["default_nudge_days"] or 3))
        self.digest_email = str(s["digest_email"] or get_config().digest_to or "")

    def flag(self, key: str) -> bool:
        return bool(self.raw.get(key))
