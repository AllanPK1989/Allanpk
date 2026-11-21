"""Web Push to the installed PWA (VAPID). Works on Android/desktop browsers and on iOS 16.4+ once the
app is added to the home screen."""

from __future__ import annotations

import base64
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import PushSubscription

log = logging.getLogger(__name__)


def generate_vapid_keys() -> tuple[str, str]:
    """Returns (public_key, private_key), both base64url without padding."""
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid01

    v = Vapid01()
    v.generate_keys()
    pub = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    priv = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()  # noqa: E731
    return b64(pub), b64(priv)


def send_all(db: Session, *, title: str, body: str, url: str = "/", tag: str = "") -> int:
    s = get_settings()
    if not s.push_enabled:
        log.info("push not configured; skipping '%s'", title)
        return 0
    from pywebpush import WebPushException, webpush

    payload = json.dumps({"title": title[:120], "body": body[:400], "url": url, "tag": tag})
    sent = 0
    for sub in list(db.scalars(select(PushSubscription))):
        info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
        try:
            webpush(info, data=payload, vapid_private_key=s.vapid_private_key,
                    vapid_claims={"sub": s.vapid_subject or f"mailto:{s.gmail_user or 'owner@example.com'}"},
                    ttl=12 * 3600, timeout=15)
            sub.failures = 0
            sent += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):  # subscription expired or unsubscribed
                db.delete(sub)
            else:
                sub.failures = (sub.failures or 0) + 1
                if sub.failures >= 5:
                    db.delete(sub)
                log.warning("push failed (%s): %s", status, e)
        except Exception as e:  # network
            log.warning("push failed: %s", e)
    db.flush()
    return sent
