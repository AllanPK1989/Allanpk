"""PIN login for a single user, cookie sessions, and signed tokens for notification buttons."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import settings_store
from .config import get_config
from .db import get_db
from .models import AuthSession
from .timeutil import utcnow

COOKIE = "nudge_session"
MAX_FAILS_BEFORE_LOCK = 5


def secret_key() -> bytes:
    cfg = get_config()
    if cfg.secret_key:
        return cfg.secret_key.encode()
    path = cfg.data_dir / "secret_key"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48))
        path.chmod(0o600)
    return path.read_text().strip().encode()


# ---- PIN -------------------------------------------------------------------------------------

def _hash_pin(pin: str, salt: bytes) -> str:
    return hashlib.scrypt(pin.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32).hex()


def valid_pin_format(pin: str) -> bool:
    return pin.isdigit() and 4 <= len(pin) <= 8


def has_pin(db: Session) -> bool:
    return bool(settings_store.get(db, "pin_hash"))


def set_pin(db: Session, pin: str) -> None:
    salt = secrets.token_bytes(16)
    settings_store.put(db, "pin_salt", salt.hex())
    settings_store.put(db, "pin_hash", _hash_pin(pin, salt))
    settings_store.put(db, "pin_fails", 0)
    settings_store.put(db, "pin_locked_until", None)


def lock_remaining_s(db: Session, now: datetime | None = None) -> int:
    until = settings_store.get(db, "pin_locked_until")
    if not until:
        return 0
    remaining = (datetime.fromisoformat(str(until)) - (now or utcnow())).total_seconds()
    return max(0, int(remaining))


def check_pin(db: Session, pin: str) -> bool:
    """Verify the PIN, counting failures. Locks for 5 minutes after 5 misses, 30 after 10."""
    salt_hex = settings_store.get(db, "pin_salt")
    stored = settings_store.get(db, "pin_hash")
    if not salt_hex or not stored:
        return False
    ok = hmac.compare_digest(_hash_pin(pin, bytes.fromhex(str(salt_hex))), str(stored))
    fails = int(settings_store.get(db, "pin_fails", 0) or 0)
    if ok:
        settings_store.put(db, "pin_fails", 0)
        settings_store.put(db, "pin_locked_until", None)
        return True
    fails += 1
    settings_store.put(db, "pin_fails", fails)
    if fails >= MAX_FAILS_BEFORE_LOCK:
        minutes = 30 if fails >= 2 * MAX_FAILS_BEFORE_LOCK else 5
        settings_store.put(db, "pin_locked_until", (utcnow() + timedelta(minutes=minutes)).isoformat())
    return False


# ---- Sessions --------------------------------------------------------------------------------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user_agent: str) -> str:
    token = secrets.token_urlsafe(32)
    now = utcnow()
    db.add(
        AuthSession(
            token_hash=_token_hash(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=get_config().session_days),
            user_agent=user_agent[:300],
        )
    )
    db.flush()
    return token


def end_session(db: Session, token: str | None) -> None:
    if token:
        row = db.get(AuthSession, _token_hash(token))
        if row:
            db.delete(row)
            db.flush()


def end_all_sessions(db: Session) -> None:
    db.query(AuthSession).delete()
    db.flush()


def session_valid(db: Session, token: str | None) -> bool:
    if not token:
        return False
    row = db.get(AuthSession, _token_hash(token))
    now = utcnow()
    if not row or row.expires_at < now:
        return False
    if (now - row.last_seen_at) > timedelta(hours=1):  # sliding expiry, written at most hourly
        row.last_seen_at = now
        row.expires_at = now + timedelta(days=get_config().session_days)
        db.commit()
    return True


def require_auth(request: Request, db: Session = Depends(get_db)) -> None:
    """Every /api route except login, health and push actions depends on this.

    Changing requests must also carry the X-Nudge header, which a cross-site form cannot set
    (a second line of defence next to the SameSite cookie).
    """
    if not session_valid(db, request.cookies.get(COOKIE)):
        raise HTTPException(401, "Please log in")
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-nudge") != "1":
        raise HTTPException(403, "Missing X-Nudge header")


# ---- Signed tokens for notification buttons (Done / Snooze work without opening the app) -----

def action_token(task_id: int, days: int = 7) -> str:
    exp = int((utcnow() + timedelta(days=days)).timestamp())
    payload = f"{task_id}.{exp}"
    sig = hmac.new(secret_key(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def read_action_token(token: str) -> int | None:
    try:
        task_id, exp, sig = token.split(".")
        payload = f"{task_id}.{exp}"
        good = hmac.new(secret_key(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good):
            return None
        if int(exp) < int(utcnow().timestamp()):
            return None
        return int(task_id)
    except (ValueError, AttributeError):
        return None
