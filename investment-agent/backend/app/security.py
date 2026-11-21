"""Single-owner authentication: password check, signed session cookie, login throttling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import Settings, get_settings

COOKIE_NAME = "ia_session"
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


# ---------- password hashing (stdlib scrypt, no extra dependency) ----------

def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored_hash.split("$", 2)
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
    except ValueError:
        return False
    dk = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return hmac.compare_digest(dk, expected)


def check_owner_password(password: str, settings: Settings) -> bool:
    if settings.owner_password_hash:
        return verify_password(password, settings.owner_password_hash)
    if settings.owner_password:
        return hmac.compare_digest(password.encode(), settings.owner_password.encode())
    return False


# ---------- session cookie ----------

_dev_secret = secrets.token_urlsafe(32)


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    # In development without SECRET_KEY, a per-process secret is used (sessions end on restart).
    return URLSafeTimedSerializer(settings.secret_key or _dev_secret, salt="ia-session")


def make_session_token(settings: Settings) -> str:
    return _serializer(settings).dumps({"sub": "owner", "n": secrets.token_hex(8)})


def read_session_token(token: str, settings: Settings) -> bool:
    try:
        data = _serializer(settings).loads(token, max_age=settings.session_days * 86400)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(data, dict) and data.get("sub") == "owner"


def require_owner(request: Request, settings: Settings = Depends(get_settings)) -> None:
    if settings.environment == "development" and not (settings.owner_password or settings.owner_password_hash):
        return  # local use with no password configured: open, like a desktop app
    token = request.cookies.get(COOKIE_NAME, "")
    if not token or not read_session_token(token, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")


def auth_required(settings: Settings) -> bool:
    return not (settings.environment == "development" and not (settings.owner_password or settings.owner_password_hash))


# ---------- login throttling (per client IP, in memory) ----------

class LoginThrottle:
    def __init__(self, max_attempts: int = 5, window_s: int = 900):
        self.max_attempts, self.window_s = max_attempts, window_s
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        return [t for t in self._fails.get(key, []) if now - t < self.window_s]

    def blocked(self, key: str) -> bool:
        with self._lock:
            now = time.monotonic()
            self._fails[key] = self._recent(key, now)
            return len(self._fails[key]) >= self.max_attempts

    def fail(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._fails[key] = self._recent(key, now) + [now]

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


login_throttle = LoginThrottle()
# Caps failed logins from all addresses together, so rotating IPs doesn't help a brute-force attempt.
global_login_throttle = LoginThrottle(max_attempts=30, window_s=900)


def client_ip(request: Request) -> str:
    # The proxy in front of the app (Render) appends the real client address as the LAST
    # X-Forwarded-For entry; earlier entries come from the client and can be forged.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


# ---------- CSRF: same-origin check for state-changing requests ----------

def same_origin(request: Request, settings: Settings) -> bool:
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if not origin:
        # Non-browser clients (curl, tests) send no Origin; the SameSite=Strict cookie still protects browsers.
        return True
    o = urlparse(origin)
    allowed = {urlparse(settings.base_url).netloc, request.headers.get("host", "")}
    return o.netloc in allowed
