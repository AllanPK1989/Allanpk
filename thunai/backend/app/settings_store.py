"""Plant settings that admins can change at runtime (stored in the `settings` table).

Values marked SAMPLE are placeholders until the plant confirms them (see SPEC.md, open questions).
"""
from copy import deepcopy

from sqlalchemy.orm import Session

from . import audit
from .models import Setting, User

DEFAULTS: dict = {
    # SAMPLE shift calendar, plant time (Asia/Kolkata). Overnight shifts are allowed.
    "shifts": [
        {"name": "A", "start": "06:00", "end": "14:00"},
        {"name": "B", "start": "14:00", "end": "22:00"},
        {"name": "C", "start": "22:00", "end": "06:00"},
    ],
    "planned_hours_per_day": 24,  # used in MTBF; SAMPLE until the plant confirms
    "kpi_period_days": 90,
    "similar_logs_threshold": 3,  # Phase 2: draft a fault card at this many similar logs
    "similarity_cutoff": 0.35,  # 0..1 keyword similarity for "similar" logs
    "low_confidence_threshold": 0.5,
    "audio_retention_days": 90,
    "idle_logout_minutes": 10,
    "max_clarifying_questions": 3,
    "alarm_prefill_hours": 8,  # Phase 3: a machine alarm this recent pre-fills Ask Thunai and New log
    "skill_min_events": 3,  # Phase 3: skill figures need at least this many events
}


def get(db: Session, key: str):
    row = db.get(Setting, key)
    if row is None:
        return deepcopy(DEFAULTS.get(key))
    return row.value


def all_settings(db: Session) -> dict:
    values = deepcopy(DEFAULTS)
    for row in db.query(Setting).all():
        values[row.key] = row.value
    return values


def put(db: Session, user: User | None, key: str, value) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    row = db.get(Setting, key)
    before = {"value": row.value if row else DEFAULTS[key]}
    if row is None:
        row = Setting(key=key, value=value, updated_by=user.id if user else None)
        db.add(row)
    else:
        row.value = value
        row.updated_by = user.id if user else None
    audit.record(db, user, "setting", key, "update", before, {"value": value})
