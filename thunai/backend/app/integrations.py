"""Integration keys for machine-to-machine access (SPEC 12.1).

One key per connected system (SCADA or PLC gateway, stores system), with scopes.
The token is shown once; only its SHA-256 hash is stored. A random 32-byte token does not need a
slow hash: there is nothing to guess.
"""
import hashlib
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .db import get_db
from .models import INTEGRATION_SCOPES, IntegrationKey, User, utcnow

PREFIX = "thn_"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def serialize(k: IntegrationKey) -> dict:
    return {
        "id": k.id,
        "name": k.name,
        "key_prefix": k.key_prefix,
        "scopes": k.scopes,
        "active": k.active,
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        "created_at": k.created_at.isoformat(),
    }


def create_key(db: Session, user: User, name: str, scopes: list[str]) -> tuple[IntegrationKey, str]:
    bad = [s for s in scopes if s not in INTEGRATION_SCOPES]
    if bad or not scopes:
        raise HTTPException(422, f"Scopes must be some of {', '.join(INTEGRATION_SCOPES)}")
    token = PREFIX + secrets.token_urlsafe(32)
    key = IntegrationKey(name=name.strip()[:120], key_hash=_hash(token), key_prefix=token[:10], scopes=sorted(set(scopes)), created_by=user.id)
    db.add(key)
    db.flush()
    audit.record(db, user, "integration_key", key.id, "create", None, serialize(key))
    return key, token


def set_active(db: Session, user: User, key: IntegrationKey, active: bool) -> IntegrationKey:
    before = serialize(key)
    key.active = active
    audit.record(db, user, "integration_key", key.id, "update", before, serialize(key))
    return key


def require_scope(scope: str):
    """FastAPI dependency: a valid, active key with this scope in the X-Thunai-Key header."""

    def check(x_thunai_key: str = Header(default=""), db: Session = Depends(get_db)) -> IntegrationKey:
        if not x_thunai_key.startswith(PREFIX):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Send an integration key in the X-Thunai-Key header")
        key = db.scalar(select(IntegrationKey).where(IntegrationKey.key_hash == _hash(x_thunai_key)))
        if key is None or not key.active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or inactive integration key")
        if scope not in (key.scopes or []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"This key does not have the '{scope}' scope")
        key.last_used_at = utcnow()
        return key

    return check
