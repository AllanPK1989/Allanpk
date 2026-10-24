import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx

from app import webhooks
from app.models import AuditLog, BreakdownLog, MachineAlarm, WebhookDelivery

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


def test_pm_sync_logs_poll_and_external_ref(client, db_session):
    key = make_key(client, ["pm", "logs"], name="SAP middleware")
    r = client.put("/api/integrations/pm-tasks", headers=key, json={"tasks": [
        {"machine_no": "DEMO-RT-01", "task_code": "PM-RT-01", "title": "[SAMPLE] Calibrate meter", "frequency_days": 90, "last_done_on": "2026-01-10"},
        {"machine_no": "DEMO-ZZ", "task_code": "X"},
    ]}).json()
    assert r["created"] == 1 and len(r["errors"]) == 1
    since = (NOW - timedelta(days=400)).isoformat()
    polled = client.get("/api/integrations/logs", headers=key, params={"since": since, "limit": 3}).json()
    assert len(polled["logs"]) == 3 and polled["logs"][0]["issue"]["en"]
    nxt = client.get("/api/integrations/logs", headers=key, params={"since": polled["next_since"]}).json()
    assert {l["log_no"] for l in nxt["logs"]}.isdisjoint({l["log_no"] for l in polled["logs"]})
    log_no = polled["logs"][0]["log_no"]
    r = client.patch(f"/api/integrations/logs/{log_no}", headers=key, json={"external_ref": "NOTIF-10004567"})
    assert r.json()["external_ref"] == "NOTIF-10004567"
    log_id = db_session.query(BreakdownLog).filter_by(log_no=log_no).one().id
    assert client.get(f"/api/logs/{log_id}", headers=login(client, "D-SUP1")).json()["external_ref"] == "NOTIF-10004567"
    trail = db_session.query(AuditLog).filter_by(entity="breakdown_log", entity_id=str(log_id)).all()
    assert any((a.after or {}).get("by_key") == "SAP middleware" for a in trail)


class Receiver:
    """A fake webhook endpoint that checks the signature the way a receiver should."""

    def __init__(self, secret: str, statuses: list[int]):
        self.secret, self.statuses, self.got = secret, list(statuses), []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        stamp = request.headers["X-Thunai-Timestamp"]
        expected = hmac.new(self.secret.encode(), stamp.encode() + b"." + request.content, hashlib.sha256).hexdigest()
        assert request.headers["X-Thunai-Signature"] == f"sha256={expected}"
        self.got.append(json.loads(request.content))
        return httpx.Response(self.statuses.pop(0) if self.statuses else 200)


def test_webhook_signed_delivery_retries_and_failure(client, db_session, monkeypatch):
    admin = login(client, "D-ADMIN")
    assert client.post("/api/admin/webhooks", headers=admin, json={"url": "ftp://x", "events": ["breakdown.closed"]}).status_code == 422
    hook = client.post("/api/admin/webhooks", headers=admin,
                       json={"name": "SAP PM", "url": "https://middleware.plant.local/thunai", "events": ["breakdown.closed"]}).json()
    receiver = Receiver(hook["secret"], [503])
    real_client = httpx.Client
    monkeypatch.setattr(webhooks.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(receiver)))

    tech = login(client, "D-TECH1")
    log = client.post("/api/logs", headers=tech, json={"machine_no": "DEMO-SF-01", "issue": {"original": "Hopper jam"},
                                                       "corrective_action": {"original": "Cleared the jam"}}).json()
    d = db_session.query(WebhookDelivery).one()
    assert (d.event, d.entity_id, d.status, d.attempts, d.last_status) == ("breakdown.closed", log["log_no"], "pending", 1, 503)
    assert d.next_attempt_at > datetime.now(timezone.utc)  # waits 1 minute before the next try
    body = receiver.got[0]
    assert body["event"] == "breakdown.closed" and body["log"]["log_no"] == log["log_no"]
    assert body["log"]["issue"]["original"] == "Hopper jam" and body["log"]["technician_employee_id"] == "D-TECH1"

    # Admin retry sends exactly the same body again; this time it is accepted.
    client.post(f"/api/admin/webhook-deliveries/{d.id}/retry", headers=admin)
    db_session.expire_all()
    d = db_session.get(WebhookDelivery, d.id)
    assert d.status == "sent" and d.attempts == 2 and receiver.got[1] == body

    # Five failed attempts end in "failed".
    receiver.statuses = [500] * 5
    client.post("/api/logs", headers=tech, json={"machine_no": "DEMO-SF-02", "issue": {"original": "Vibrator weak"},
                                                 "corrective_action": {"original": "Tightened mount"}})
    d2 = db_session.query(WebhookDelivery).order_by(WebhookDelivery.id.desc()).first()
    for _ in range(4):
        webhooks.deliver(db_session, d2)
    db_session.commit()
    assert d2.status == "failed" and d2.attempts == 5
    rows = client.get("/api/admin/webhook-deliveries?status=failed", headers=admin).json()
    assert rows[0]["id"] == d2.id and "HTTP 500" in rows[0]["last_error"]


def test_webhook_events_follow_log_status(client, db_session, monkeypatch):
    admin = login(client, "D-ADMIN")
    client.post("/api/admin/webhooks", headers=admin,
                json={"url": "https://pm.plant.local/hook", "events": ["breakdown.opened", "breakdown.closed", "breakdown.verified"]})
    real_client = httpx.Client
    monkeypatch.setattr(webhooks.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(lambda r: httpx.Response(204))))
    tech = login(client, "D-TECH1")
    body = {"machine_no": "DEMO-SF-01", "issue": {"original": "Machine down"}, "corrective_action": {"original": "Waiting for spare"}}
    log = client.post("/api/logs", headers=tech, json={**body, "still_down": True}).json()
    client.patch(f"/api/logs/{log['id']}", headers=tech, json={"submit": True})
    client.post(f"/api/logs/{log['id']}/verify", headers=login(client, "D-SUP1"))
    events = [d.event for d in db_session.query(WebhookDelivery).order_by(WebhookDelivery.id)]
    assert events == ["breakdown.opened", "breakdown.closed", "breakdown.verified"]
    assert all(d.status == "sent" for d in db_session.query(WebhookDelivery))
    # Draft logs and a deactivated endpoint send nothing.
    hook_id = client.get("/api/admin/webhooks", headers=admin).json()[0]["id"]
    client.patch(f"/api/admin/webhooks/{hook_id}", headers=admin, json={"active": False})
    client.post("/api/logs", headers=tech, json={**body, "submit": True})
    assert db_session.query(WebhookDelivery).count() == 3
