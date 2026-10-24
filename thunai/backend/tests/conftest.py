"""Test set-up: a throw-away SQLite database, mock AI and speech, jobs run right after commit.

Set TEST_DATABASE_URL to run the same tests against PostgreSQL.
"""
import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="thunai-test-"))
os.environ.update(
    DATABASE_URL=os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp / 'test.db'}"),
    JOBS_MODE="sync",
    AI_PROVIDER="mock",
    STT_PROVIDER="mock",
    MEDIA_DIR=str(_tmp / "media"),
    SEED_SAMPLE_DATA="false",
    SECRET_KEY="test-secret-key-that-is-long-enough-123",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed  # noqa: E402
from app.ai import service as ai_service  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed.seed(db)
        db.commit()
    with SessionLocal() as db:
        yield db
    ai_service.get_provider.cache_clear()


@pytest.fixture
def client(db_session):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, employee_id: str, pin: str = "1234") -> dict:
    r = client.post("/api/auth/login", json={"employee_id": employee_id, "pin": pin})
    assert r.status_code == 200, r.text
    return {"authorization": f"Bearer {r.json()['token']}"}
