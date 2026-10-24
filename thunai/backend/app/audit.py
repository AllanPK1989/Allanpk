"""Audit trail. Call record() for every create, update, status change or deactivation."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .models import AuditLog, User

_SKIP = {"pin_hash", "created_at", "updated_at"}


def _plain(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def snapshot(obj) -> dict:
    """Column values of a model instance as JSON-safe data (secrets left out)."""
    mapper = inspect(obj).mapper
    return {
        col.key: _plain(getattr(obj, col.key))
        for col in mapper.column_attrs
        if col.key not in _SKIP
    }


def changed(before: dict | None, after: dict | None) -> bool:
    return (before or {}) != (after or {})


def record(
    db: Session,
    user: User | None,
    entity: str,
    entity_id,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    if action == "update" and not changed(before, after):
        return
    if before and after:  # keep only the fields that changed, to keep the trail readable
        keys = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        before = {k: before.get(k) for k in keys}
        after = {k: after.get(k) for k in keys}
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            before=before,
            after=after,
        )
    )
