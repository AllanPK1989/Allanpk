"""Web push notifications (VAPID). Works on Android, desktop browsers, and iPhone once the app
is added to the Home Screen (iOS 16.4+)."""
import json
import logging

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02, b64urlencode
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from . import settings_store
from .config import get_config
from .models import NotificationLog, PushSubscription
from .security import action_token
from .timeutil import utcnow

log = logging.getLogger("nudge.push")
MAX_FAILURES = 10

TASK_ACTIONS = [{"action": "done", "title": "Done"}, {"action": "snooze_1h", "title": "Snooze 1h"},
                {"action": "tomorrow", "title": "Tomorrow"}]
NUDGE_ACTIONS = [{"action": "nudged", "title": "I've nudged"}, {"action": "tomorrow", "title": "Tomorrow"}]

_vapid_cache: tuple[Vapid02, str] | None = None


def _sender(subscription: dict, data: str, vapid: Vapid02) -> None:
    """Separate so tests can replace it."""
    webpush(subscription_info=subscription, data=data, vapid_private_key=vapid,
            vapid_claims={"sub": get_config().vapid_subject}, ttl=12 * 3600, timeout=10)


def vapid(db: Session) -> tuple[Vapid02, str]:
    global _vapid_cache
    if _vapid_cache:
        return _vapid_cache
    pem = get_config().vapid_private_key or settings_store.get(db, "vapid_private_pem")
    if not pem:
        v = Vapid02()
        v.generate_keys()
        pem = v.private_pem().decode()
        settings_store.put(db, "vapid_private_pem", pem)
        db.commit()
    v = Vapid02.from_pem(pem.encode() if isinstance(pem, str) else pem)
    raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    _vapid_cache = (v, b64urlencode(raw))
    return _vapid_cache


def public_key(db: Session) -> str:
    return vapid(db)[1]


def subscribe(db: Session, sub: dict, user_agent: str) -> PushSubscription:
    endpoint = sub.get("endpoint", "")
    keys = sub.get("keys") or {}
    if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        raise ValueError("Not a valid push subscription")
    row = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if row is None:
        row = PushSubscription(endpoint=endpoint, p256dh=keys["p256dh"], auth=keys["auth"], user_agent=user_agent[:300])
        db.add(row)
    else:
        row.p256dh, row.auth, row.failures = keys["p256dh"], keys["auth"], 0
    db.flush()
    return row


def unsubscribe(db: Session, endpoint: str) -> None:
    db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).delete()
    db.flush()


def device_count(db: Session) -> int:
    return db.query(PushSubscription).count()


def send(
    db: Session, kind: str, title: str, body: str, *, url: str = "/", tag: str = "", task_id: int | None = None,
    actions: list[dict] | None = None,
) -> int:
    """Send to every subscribed device. Returns how many devices accepted it."""
    subs = db.query(PushSubscription).all()
    entry = NotificationLog(kind=kind, channel="push", task_id=task_id, title=title[:200], body=body, at=utcnow())
    db.add(entry)
    if not subs:
        entry.error = "no devices"
        db.flush()
        return 0
    payload = {"title": title, "body": body, "url": url, "tag": tag or kind, "kind": kind}
    if task_id is not None:
        payload["task_id"] = task_id
        payload["token"] = action_token(task_id)
        payload["actions"] = actions if actions is not None else TASK_ACTIONS
    data = json.dumps(payload)
    v, _ = vapid(db)
    delivered, errors = 0, []
    for s in subs:
        try:
            _sender({"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}, data, v)
            s.last_ok_at, s.failures = utcnow(), 0
            delivered += 1
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):  # the browser dropped this subscription
                db.delete(s)
            else:
                s.failures += 1
                if s.failures >= MAX_FAILURES:
                    db.delete(s)
            errors.append(f"{status or ''} {e}".strip()[:200])
        except Exception as e:  # network trouble: try again next time
            s.failures += 1
            errors.append(str(e)[:200])
    entry.delivered = delivered
    entry.error = "; ".join(errors)[:1000]
    db.flush()
    return delivered
