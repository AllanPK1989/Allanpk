import os

os.environ.update({
    "ENVIRONMENT": "test",
    "DATA_MODE": "demo",
    "DATABASE_URL": "sqlite:///:memory:",
    "OWNER_PASSWORD": "correct-horse-battery",
    "SECRET_KEY": "x" * 40,
    "ANTHROPIC_API_KEY": "",
    "GMAIL_USER": "",
    "GMAIL_APP_PASSWORD": "",
    "VAPID_PUBLIC_KEY": "",
    "VAPID_PRIVATE_KEY": "",
    "BASE_URL": "http://testserver",
    "IA_NO_APP": "1",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db as dbmod  # noqa: E402
from app.data import cache  # noqa: E402


TEST_DB = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")  # set to a Postgres URL to test against it


@pytest.fixture()
def app():
    cache.clear()
    engine = dbmod.configure(TEST_DB)
    if not TEST_DB.startswith("sqlite"):
        from app import models  # noqa: F401

        dbmod.Base.metadata.drop_all(engine)
    from app.main import create_app
    from app.security import global_login_throttle, login_throttle

    login_throttle._fails.clear()
    global_login_throttle._fails.clear()
    return create_app()


@pytest.fixture()
def client(app):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"password": "correct-horse-battery"})
    assert r.status_code == 200
    return c


@pytest.fixture()
def db(app):
    s = dbmod.new_session()
    yield s
    s.close()
