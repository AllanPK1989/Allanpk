"""HTTP API: login, CSRF header, capture flow, notification buttons, settings, export."""
from fastapi.testclient import TestClient

from app import security
from app.main import app
from app.models import Task

H = {"X-Nudge": "1"}


def test_first_run_setup_then_login_and_lockout(db):
    with TestClient(app) as c:
        assert c.get("/api/auth/status").json()["has_pin"] is False
        assert c.post("/api/auth/setup", json={"pin": "12ab"}, headers=H).status_code == 422
        assert c.post("/api/auth/setup", json={"pin": "4321"}, headers=H).status_code == 200
        assert c.get("/api/dashboard").status_code == 200
        assert c.post("/api/auth/setup", json={"pin": "9999"}, headers=H).status_code == 409
    with TestClient(app) as c:
        for _ in range(4):
            assert c.post("/api/auth/login", json={"pin": "0000"}, headers=H).status_code == 401
        assert c.post("/api/auth/login", json={"pin": "0000"}, headers=H).status_code == 429
        assert c.post("/api/auth/login", json={"pin": "4321"}, headers=H).status_code == 429  # locked


def test_changes_need_the_nudge_header(client):
    assert client.post("/api/tasks", json={"title": "x"}).status_code == 403
    assert client.post("/api/tasks", json={"title": "x"}, headers=H).status_code == 200


def test_voice_capture_review_and_apply(client):
    out = client.post("/api/assistant/voice", files={"audio": ("v.webm", b"0" * 4000, "audio/webm")},
                      headers=H).json()
    assert out["intent"] == "create" and out["understood_by"] == "rules"
    assert len(out["drafts"]) == 3
    saved = client.post("/api/assistant/apply", json={"intent": "create", "transcript": out["transcript"],
                                                       "drafts": out["drafts"]}, headers=H).json()
    assert [t["source"] for t in saved["created"]] == ["voice"] * 3
    assert all(t["ai_fields"] == [] for t in saved["created"])  # reviewed and saved = confirmed
    ravi = saved["created"][2]
    assert ravi["status"] == "waiting" and ravi["person"] == "Ravi"


def test_offline_voice_goes_to_inbox_with_guesses(client):
    out = client.post("/api/assistant/voice?auto=true", files={"audio": ("v.m4a", b"0" * 4000, "audio/mp4")},
                      headers=H).json()
    assert len(out["saved"]) == 3
    assert all(t["inbox"] and "basket" in t["ai_fields"] for t in out["saved"])


def test_rejects_non_audio(client):
    r = client.post("/api/assistant/voice", files={"audio": ("x.txt", b"hello", "text/plain")}, headers=H)
    assert r.status_code == 415


def test_complete_and_reschedule_by_voice_command(client):
    t = client.post("/api/tasks", json={"title": "Send PM report", "due_date": "2026-11-20"}, headers=H).json()
    out = client.post("/api/assistant/interpret", json={"text": "move PM report to 30/11"}, headers=H).json()
    assert out["intent"] == "reschedule" and out["targets"][0]["due_date"] == "2026-11-30"
    client.post("/api/assistant/apply", json={"intent": "reschedule", "targets": out["targets"]}, headers=H)
    assert client.get(f"/api/tasks/{t['id']}").json()["due_date"] == "2026-11-30"
    out = client.post("/api/assistant/interpret", json={"text": "mark the PM report done"}, headers=H).json()
    client.post("/api/assistant/apply", json={"intent": "complete", "targets": out["targets"]}, headers=H)
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "done"


def test_notification_buttons_work_without_login(db, client):
    t = client.post("/api/tasks", json={"title": "Call vendor", "due_date": "2026-11-20"}, headers=H).json()
    token = security.action_token(t["id"])
    anon = TestClient(app)
    assert anon.post("/api/push/action", json={"token": token, "action": "tomorrow"}).status_code == 200
    assert anon.post("/api/push/action", json={"token": token, "action": "done"}).json()["status"] == "done"
    bad = token[:-2] + ("00" if not token.endswith("00") else "11")
    assert anon.post("/api/push/action", json={"token": bad, "action": "done"}).status_code == 403


def test_task_detail_has_history_and_chain(client):
    t = client.post("/api/tasks", json={"title": "Send quote request", "person": "Ravi"}, headers=H).json()
    r = client.post(f"/api/tasks/{t['id']}/close", json={"note": "done", "follow_up": {"in_days": 2}},
                    headers=H).json()
    fu = r["spawned"][0]
    d = client.get(f"/api/tasks/{t['id']}").json()
    assert d["followed_by"][0]["id"] == fu["id"]
    assert [h["kind"] for h in d["history"]] == ["closed", "created"]
    assert client.get(f"/api/tasks/{fu['id']}").json()["follows"]["id"] == t["id"]


def test_lists_and_search(client):
    client.post("/api/tasks", json={"title": "Bearing quote", "person": "Vendor"}, headers=H)
    client.post("/api/tasks", json={"title": "Other", "due_date": "2026-01-01"}, headers=H)
    assert client.get("/api/tasks", params={"lane": "inbox"}).json()["total"] == 1
    assert client.get("/api/tasks", params={"lane": "overdue"}).json()["total"] == 1
    assert client.get("/api/tasks", params={"q": "bearing"}).json()["total"] == 1
    assert client.get("/api/tasks", params={"person": "vendor"}).json()["total"] == 1


def test_baskets_crud(client):
    b = client.post("/api/baskets", json={"name": "Plant 2", "color": "teal", "icon": "factory"}, headers=H).json()
    assert client.post("/api/baskets", json={"name": "plant 2"}, headers=H).status_code == 409
    t = client.post("/api/tasks", json={"title": "x", "basket_id": b["id"]}, headers=H).json()
    work = next(x for x in client.get("/api/baskets").json()["baskets"] if x["name"] == "Work")
    assert client.delete(f"/api/baskets/{b['id']}?move_to={work['id']}", headers=H).status_code == 200
    assert client.get(f"/api/tasks/{t['id']}").json()["basket_id"] == work["id"]


def test_settings_validation(client):
    assert client.patch("/api/settings", json={"briefing_time": "7.30"}, headers=H).status_code == 422
    assert client.patch("/api/settings", json={"timezone": "Mars/Base"}, headers=H).status_code == 422
    assert client.patch("/api/settings", json={"pin_hash": "x"}, headers=H).status_code == 422
    s = client.patch("/api/settings", json={"briefing_time": "08:00", "display_name": "Pravin"}, headers=H).json()
    assert s["briefing_time"] == "08:00"
    assert "pin_hash" not in client.get("/api/settings").json()["settings"]


def test_export_and_digest_preview(client):
    client.post("/api/tasks", json={"title": "x"}, headers=H)
    r = client.get("/api/export.xlsx")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    assert "Open Nudge" in client.get("/api/digest/preview").text


def test_bulk_move_to_tomorrow(client, db):
    ids = [client.post("/api/tasks", json={"title": f"t{i}", "due_date": "2026-01-01"}, headers=H).json()["id"]
           for i in range(3)]
    assert client.post("/api/tasks-bulk", json={"ids": ids, "action": "tomorrow"}, headers=H).json()["changed"] == 3
    db.expire_all()
    assert len({t.due_date for t in db.query(Task).all()}) == 1
