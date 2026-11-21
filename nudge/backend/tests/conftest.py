"""Test set-up: a throw-away data folder, mock speech, no scheduler."""
import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="nudge-test-"))
os.environ.update(
    DATA_DIR=str(_tmp),
    STT_PROVIDER="mock",
    SEED_SAMPLE_DATA="false",
    SCHEDULER_ENABLED="false",
    SECRET_KEY="test-secret-key-that-is-long-enough-123",
    DEFAULT_TIMEZONE="Asia/Kolkata",
    INITIAL_PIN="",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import push, security, seed  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.settings_store import Prefs  # noqa: E402

H = {"X-Nudge": "1"}


@pytest.fixture
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        seed.ensure_baskets(s)
        s.commit()
    with SessionLocal() as s:
        yield s
    push._vapid_cache = None


@pytest.fixture
def prefs(db):
    return Prefs(db)


@pytest.fixture
def basket(db):
    from app.models import Basket

    return {b.name.split()[0].lower(): b.id for b in db.query(Basket).all()}


@pytest.fixture
def client(db):
    security.set_pin(db, "2468")
    db.commit()
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"pin": "2468"}, headers=H)
        assert r.status_code == 200
        yield c


@pytest.fixture
def sent_push(monkeypatch):
    """Capture push messages instead of sending them, with one fake device subscribed."""
    sent = []
    monkeypatch.setattr(push, "_sender", lambda sub, data, vapid: sent.append(data))
    return sent


@pytest.fixture
def device(db):
    push.subscribe(db, {"endpoint": "https://push.example.test/abc", "keys": {"p256dh": "k", "auth": "a"}}, "test")
    db.commit()
