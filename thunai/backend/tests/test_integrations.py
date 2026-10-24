import hashlib
import json
from datetime import datetime, timedelta, timezone

from app.models import MachineAlarm

from .conftest import login

NOW = datetime.now(timezone.utc)


def make_key(client, scopes: list[str], name: str = "SCADA gateway") -> dict:
    r = client.post("/api/admin/integration-keys", headers=login(client, "D-ADMIN"), json={"name": name, "scopes": scopes})
    assert r.status_code == 200, r.text
    return {"X-Thunai-Key": r.json()["token"]}


def test_keys_are_scoped_hashed_and_revocable(client, db_session):
    admin = login(client, "D-ADMIN")
    r = client.post("/api/admin/integration-keys", headers=admin, json={"name": "Stores", "scopes": ["parts"]}).json()
    token = r["token"]
    assert token.startswith("thn_") and r["key_prefix"] == token[:10]
    listed = client.get("/api/admin/integration-keys", headers=admin).json()
    assert "token" not in listed[0] and hashlib.sha256(token.encode()).hexdigest() not in json.dumps(listed)
    body = {"parts": [{"part_no": "DEMO-P-1002", "stock_qty": 7}]}
    assert client.put("/api/integrations/parts", json=body).status_code == 401
    assert client.put("/api/integrations/parts", headers={"X-Thunai-Key": "thn_guess"}, json=body).status_code == 401
    assert client.post("/api/integrations/alarms", headers={"X-Thunai-Key": token}, json={"events": []}).status_code == 403
    assert client.put("/api/integrations/parts", headers={"X-Thunai-Key": token}, json=body).json()["updated"] == 1
    assert client.get("/api/admin/integration-keys", headers=admin).json()[0]["last_used_at"]
    client.patch(f"/api/admin/integration-keys/{r['id']}", headers=admin, json={"active": False})
    assert client.put("/api/integrations/parts", headers={"X-Thunai-Key": token}, json=body).status_code == 401
    assert client.post("/api/admin/integration-keys", headers=admin, json={"name": "x", "scopes": ["root"]}).status_code == 422
    assert client.post("/api/admin/integration-keys", headers=admin, json={"name": "x", "scopes": ["pm"]}).status_code == 422
    assert client.get("/api/integrations/logs?since=2026-01-01", headers={"X-Thunai-Key": token}).status_code == 404
    assert client.get("/api/admin/integration-keys", headers=login(client, "D-SUP1")).status_code == 403


def alarm(code="A101", minutes_ago=10, **extra) -> dict:
    return {"machine_no": "DEMO-SF-01", "code": code, "message": "Cylinder not at home",
            "raised_at": (NOW - timedelta(minutes=minutes_ago)).isoformat(), **extra}


def test_alarm_feed_dedupes_and_prefills(client, db_session):
    key = make_key(client, ["alarms"])
    events = [alarm(minutes_ago=40, event_id="e1"), alarm(minutes_ago=10, event_id="e2"),
              alarm(minutes_ago=10, event_id="e2"),  # repeat
              alarm(minutes_ago=-60),  # an hour in the future
              {**alarm(), "machine_no": "NOPE"}]
    r = client.post("/api/integrations/alarms", headers=key, json={"events": events}).json()
    assert (r["accepted"], r["duplicates"]) == (2, 1) and len(r["errors"]) == 2
    tech = login(client, "D-TECH1")
    active = client.get("/api/machines/DEMO-SF-01/active-alarm", headers=tech).json()["alarm"]
    assert active["code"] == "A101" and active["meaning"]["code"] == "A101"  # with the alarm-list text
    # The feed is evidence about this breakdown (tier 0).
    s = client.post("/api/ai/sessions", headers=tech, json={"machine_no": "DEMO-SF-01", "problem_text": "Cylinder stuck", "alarm_code": "A101", "language": "en"}).json()
    feed = [x for x in s["sources"] if x["kind"] == "scada"]
    assert feed[0]["ref"] == "SCADA-A101" and feed[0]["tier"] == 0 and feed[0]["data"]["count"] == 2
    # Clearing it (a repeat with cleared_at) removes the pre-fill.
    client.post("/api/integrations/alarms", headers=key, json={"events": [alarm(minutes_ago=10, event_id="e2", cleared_at=NOW.isoformat())]})
    assert client.get("/api/machines/DEMO-SF-01/active-alarm", headers=tech).json()["alarm"]["id"] == active["id"] - 1
    client.post("/api/integrations/alarms", headers=key, json={"events": [alarm(minutes_ago=40, event_id="e1", cleared_at=NOW.isoformat())]})
    assert client.get("/api/machines/DEMO-SF-01/active-alarm", headers=tech).json()["alarm"] is None


def test_old_alarms_do_not_prefill(client):
    key = make_key(client, ["alarms"])
    client.post("/api/integrations/alarms", headers=key, json={"events": [alarm(minutes_ago=9 * 60)]})  # setting: 8 h
    assert client.get("/api/machines/DEMO-SF-01/active-alarm", headers=login(client, "D-TECH1")).json()["alarm"] is None


def test_log_and_session_link_their_alarm_event(client, db_session):
    key = make_key(client, ["alarms"])
    client.post("/api/integrations/alarms", headers=key, json={"events": [alarm(minutes_ago=15, event_id="e9")]})
    event = db_session.query(MachineAlarm).filter_by(event_id="e9").one()
    tech = login(client, "D-TECH1")
    body = {"machine_no": "DEMO-SF-01", "issue": {"original": "Cylinder stuck"}, "corrective_action": {"original": "Cleaned valve"},
            "alarm_code": "A101", "alarm_event_id": event.id, "start_at": event.raised_at.isoformat()}
    log = client.post("/api/logs", headers=tech, json=body).json()
    db_session.expire_all()
    assert db_session.get(MachineAlarm, event.id).log_id == log["id"]
    assert log["downtime_min"] is None or log["downtime_min"] >= 0
    # Another alarm, used through Ask Thunai: closing the session links it to the new log.
    client.post("/api/integrations/alarms", headers=key, json={"events": [alarm(code="A205", minutes_ago=5, event_id="e10")]})
    s = client.post("/api/ai/sessions", headers=tech, json={"machine_no": "DEMO-SF-01", "problem_text": "Vibrator stopped", "alarm_code": "A205", "language": "en"}).json()
    closed = client.post(f"/api/ai/sessions/{s['id']}/close", headers=tech, json={"running": False}).json()
    db_session.expire_all()
    assert db_session.query(MachineAlarm).filter_by(event_id="e10").one().log_id == closed["log_id"]
