"""The Copilot tool API (SPEC 13): Entra ID token checks, account linking and every tool.

Tokens are signed here with a test RSA key. Only the HTTP fetch of the key set is replaced; the
key-id lookup, caching and every token check run as they do against login.microsoftonline.com.
"""
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import entra, safety
from app.config import get_config
from app.models import AISession, BreakdownLog, CopilotCall, User

from .conftest import login

TENANT = "11111111-2222-3333-4444-555555555555"
AUDIENCE = "api://thunai-test"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ACCOUNTS = {"D-TECH1": "tech1@eaton.test", "D-TECH3": "tech3@eaton.test", "D-TECH2": "tech2@eaton.test",
            "D-SUP1": "sup1@eaton.test", "D-SUP2": "sup2@eaton.test", "D-ADMIN": "admin@eaton.test"}
SAFETY_PROMPTS = json.load(open(__file__.rsplit("/tests/", 1)[0] + "/eval/safety_prompts.json"))["prompts"]


def token(emp: str = "D-TECH1", key=KEY, kid: str = "k1", **claims) -> str:
    now = int(time.time())
    body = {"iss": f"https://login.microsoftonline.com/{TENANT}/v2.0", "tid": TENANT, "aud": AUDIENCE, "scp": "Thunai.Use",
            "oid": f"oid-{emp}", "preferred_username": ACCOUNTS.get(emp, f"{emp}@eaton.test"), "iat": now, "nbf": now, "exp": now + 3600}
    body.update(claims)
    body = {k: v for k, v in body.items() if v is not None}
    return jwt.encode(body, key, algorithm="RS256", headers={"kid": kid})


def auth(emp: str = "D-TECH1", **claims) -> dict:
    return {"authorization": f"Bearer {token(emp, **claims)}"}


@pytest.fixture
def copilot(client, db_session, monkeypatch):
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
    jwks = {"keys": [{**jwk, "kid": "k1", "use": "sig", "alg": "RS256"}]}
    fetched = []
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: fetched.append(self.uri) or jwks)
    cfg = get_config()
    for name, value in (("copilot_enabled", True), ("entra_tenant_id", TENANT), ("entra_audience", f"{AUDIENCE}, 0000-client-id")):
        monkeypatch.setattr(cfg, name, value)
    entra._jwks_client.cache_clear()
    admin = login(client, "D-ADMIN")
    users = {u["employee_id"]: u for u in client.get("/api/admin/users", headers=admin).json()}
    for emp, upn in ACCOUNTS.items():
        r = client.patch(f"/api/admin/users/{users[emp]['id']}", headers=admin, json={"entra_upn": upn.upper()})
        assert r.status_code == 200 and r.json()["entra_upn"] == upn  # stored in lower case
    return client


# ---- sign-in -------------------------------------------------------------------------------------
def test_off_until_configured(client):
    assert client.get("/api/copilot/me", headers=auth()).status_code == 503


@pytest.mark.parametrize("bad", [
    {},  # no header at all
    {"authorization": "Bearer not-a-token"},
    auth(aud="api://someone-else"),
    auth(iss="https://login.microsoftonline.com/99999999-0000-0000-0000-000000000000/v2.0"),
    auth(tid="99999999-0000-0000-0000-000000000000"),
    auth(exp=int(time.time()) - 600),  # expired beyond the 60 s leeway
    auth(scp="User.Read"),  # wrong delegated scope
    auth(scp=None, roles=["Thunai.Use"]),  # application-only token: no person
    {"authorization": f"Bearer {token(key=OTHER_KEY)}"},  # right key id, wrong key
    {"authorization": f"Bearer {token(kid='unknown')}"},
    {"authorization": "Bearer " + jwt.encode({"aud": AUDIENCE, "scp": "Thunai.Use", "oid": "x", "tid": TENANT}, "a-shared-secret-of-at-least-32-bytes!", algorithm="HS256")},
])
def test_tokens_are_checked(copilot, bad):
    r = copilot.get("/api/copilot/me", headers=bad)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_keys_come_from_the_tenant(copilot, monkeypatch):
    seen = []
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: seen.append(self.uri) or {"keys": []})
    entra._jwks_client.cache_clear()
    assert copilot.get("/api/copilot/me", headers=auth()).status_code == 401
    assert seen[0] == f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys"


def test_v1_tokens_and_client_id_audience_are_accepted(copilot):
    r = copilot.get("/api/copilot/me", headers=auth(iss=f"https://sts.windows.net/{TENANT}/", aud="0000-client-id",
                                                   preferred_username=None, upn="tech1@eaton.test"))
    assert r.status_code == 200 and r.json() == {"employee_id": "D-TECH1", "name": "[Sample] Technician 1", "role": "technician",
                                                 "zone": "Bussmann Zone 1", "language": "ta"}


def test_accounts_are_linked_by_upn_once_then_by_object_id(copilot, db_session):
    assert copilot.get("/api/copilot/me", headers=auth("D-TECH1")).status_code == 200
    db_session.expire_all()
    tech1 = db_session.query(User).filter_by(employee_id="D-TECH1").one()
    assert tech1.entra_oid == "oid-D-TECH1"
    # Renamed account, same object ID: still the same person.
    assert copilot.get("/api/copilot/me", headers=auth("D-TECH1", preferred_username="renamed@eaton.test")).json()["employee_id"] == "D-TECH1"
    # Another Microsoft account presenting the bound UPN is refused.
    assert copilot.get("/api/copilot/me", headers=auth("D-TECH1", oid="oid-intruder")).status_code == 403
    # Unknown account, inactive user.
    assert copilot.get("/api/copilot/me", headers=auth("NOBODY")).status_code == 403
    admin = login(copilot, "D-ADMIN")
    copilot.patch(f"/api/admin/users/{tech1.id}", headers=admin, json={"active": False})
    assert copilot.get("/api/copilot/me", headers=auth("D-TECH1")).status_code == 403
    # Changing the UPN unbinds the old account; the admin sees who is linked.
    copilot.patch(f"/api/admin/users/{tech1.id}", headers=admin, json={"active": True, "entra_upn": "new1@eaton.test"})
    listed = {u["employee_id"]: u for u in copilot.get("/api/admin/users", headers=admin).json()}
    assert listed["D-TECH1"]["entra_upn"] == "new1@eaton.test" and not listed["D-TECH1"]["entra_linked"]
    assert copilot.get("/api/copilot/me", headers=auth("D-TECH1")).status_code == 403
    assert copilot.get("/api/copilot/me", headers=auth("D-TECH1", oid="oid-new", preferred_username="new1@eaton.test")).status_code == 200
    # One account per user.
    r = copilot.patch(f"/api/admin/users/{listed['D-TECH3']['id']}", headers=admin, json={"entra_upn": "new1@eaton.test"})
    assert r.status_code == 409
    assert copilot.patch(f"/api/admin/users/{listed['D-TECH3']['id']}", headers=admin, json={"entra_upn": "no-at-sign"}).status_code == 422
    audit = copilot.get("/api/admin/audit?entity=user", headers=admin).json()
    assert any(a["action"] == "microsoft_account_linked" for a in audit)


# ---- troubleshooting -----------------------------------------------------------------------------
def start(client, emp="D-TECH1", **body):
    body = {"machine_no": "DEMO-SF-01", "problem": "Filling cylinder not returning", "language": "en", **body}
    r = client.post("/api/copilot/sessions", headers=auth(emp), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def answer_all(client, s, emp="D-TECH1"):
    if s["status"] != "questions":
        return s
    answers = [{"question_id": q["id"], "value": q["options"][0]["value"]} for q in s["questions"]]
    return client.post(f"/api/copilot/sessions/{s['session_id']}/answers", headers=auth(emp), json={"answers": answers}).json()


def test_full_session_in_teams(copilot, db_session):
    s = start(copilot)
    assert s["status"] == "questions" and s["questions"][0]["options"][0]["label"]
    assert "answerQuestions" in s["agent_note"]
    s = answer_all(copilot, s)
    step = s["current_step"]
    assert s["status"] == "step" and step["step_no"] == 1 and step["kind"] == "safety"
    assert "LOTO" in step["action"] and step["display"].startswith("**Step 1 of ") and "Reply OK, NOT OK or CAN'T DO." in step["display"]
    assert [l for l in s["likely_causes"] if "coil" in l["cause"].lower()]
    sid = s["session_id"]
    # Only the current step can be answered; another technician cannot touch the session.
    assert copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": 3, "result": "ok"}).status_code == 409
    assert copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth("D-TECH3"), json={"step_no": 1, "result": "ok"}).status_code == 403
    assert copilot.get(f"/api/copilot/sessions/{sid}", headers=auth("D-SUP1")).status_code == 200  # supervisors may look
    seen_evidence = False
    while s["status"] == "step":
        seen_evidence |= any(e["ref"].startswith("FC-") for e in s["current_step"]["evidence"])
        s = copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": s["current_step"]["step_no"], "result": "ok"}).json()
    assert s["status"] == "finished" and seen_evidence and "closeSession" in s["agent_note"]
    # Saving needs the technician's words; then the log is submitted in their words with the English version.
    r = copilot.post(f"/api/copilot/sessions/{sid}/close", headers=auth(), json={"running": True, "confirmed": True})
    assert r.status_code == 422
    r = copilot.post(f"/api/copilot/sessions/{sid}/close", headers=auth(), json={
        "running": True, "confirmed": True, "what_fixed_it": "Coil maathiten, 10 cycle OK", "what_fixed_it_en": "Replaced the coil; 10 cycles OK",
        "root_cause": "Coil burnt", "parts_used": [{"part_no": "DEMO-P-1001", "description": "Solenoid coil 24 V DC", "qty": 1}]}).json()
    assert r["log_status"] == "closed" and r["outcome"] == "resolved" and r["log_no"] in r["message"]
    db_session.expire_all()
    log = db_session.query(BreakdownLog).filter_by(log_no=r["log_no"]).one()
    fix = next(t for t in log.texts if t.field == "corrective_action")
    assert (fix.original, fix.english, fix.ai_filled) == ("Coil maathiten, 10 cycle OK", "Replaced the coil; 10 cycles OK", False)
    assert log.technician_name == "[Sample] Technician 1" and [p.part_no for p in log.parts] == ["DEMO-P-1001"]
    session = db_session.get(AISession, sid)
    assert session.channel == "copilot" and session.outcome == "resolved"
    assert copilot.get(f"/api/copilot/sessions/{sid}", headers=auth()).json()["status"] == "closed"
    assert copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": 1, "result": "ok"}).status_code == 409


def test_unconfirmed_close_saves_a_draft(copilot):
    s = answer_all(copilot, start(copilot))
    r = copilot.post(f"/api/copilot/sessions/{s['session_id']}/close", headers=auth(), json={"running": True}).json()
    assert r["log_status"] == "draft" and "Thunai app" in r["message"]


def test_cant_do_the_safety_step_stops_and_escalates(copilot, db_session):
    s = answer_all(copilot, start(copilot))
    sid = s["session_id"]
    s = copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": 1, "result": "cant_do"}).json()
    assert s["status"] == "stop" and "callSupervisor" in s["agent_note"] and "current_step" not in s
    sup = copilot.post(f"/api/copilot/sessions/{sid}/call-supervisor", headers=auth()).json()
    assert "Thunai: help needed" in sup["summary"] and sup["supervisors"][0]["name"] == "[Sample] Supervisor Zone 1"
    r = copilot.post(f"/api/copilot/sessions/{sid}/close", headers=auth(), json={"running": False, "what_fixed_it": "Could not apply LOTO, isolator broken"}).json()
    assert r["outcome"] == "escalated" and r["log_status"] == "open" and r["summary"]
    db_session.expire_all()
    log = db_session.query(BreakdownLog).filter_by(log_no=r["log_no"]).one()
    assert log.machine.status == "down" and log.escalated
    assert next(t for t in log.texts if t.field == "corrective_action").original == "Could not apply LOTO, isolator broken"


def test_cant_do_an_ordinary_step_skips_it(copilot):
    s = answer_all(copilot, start(copilot))
    sid = s["session_id"]
    s = copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": 1, "result": "ok"}).json()
    while s["status"] == "step" and (s["current_step"]["kind"] == "safety" or s["current_step"]["authorised_only"]):
        s = copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": s["current_step"]["step_no"], "result": "ok"}).json()
    no = s["current_step"]["step_no"]
    s = copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": no, "result": "cant_do"}).json()
    assert s["message"].startswith(f"Step {no} skipped") and s["status"] in ("step", "finished")


def test_tamil_session_uses_thunai_tamil_text_and_flags_gaps(copilot):
    s = answer_all(copilot, start(copilot, language="ta"))
    step = s["current_step"]
    assert step["language"] == "ta" and "LOTO" in step["action"] and step["display"].startswith("**Step 1 / ")
    assert "translate" not in s["agent_note"]
    # A machine with no Tamil history: the generic steps have Tamil; force a step without it via a log in English only.
    sid = s["session_id"]
    langs = set()
    while s["status"] == "step":
        langs.add(s["current_step"]["language"])
        if s["current_step"]["language"] == "en":
            assert "translate display faithfully" in s["agent_note"]
        s = copilot.post(f"/api/copilot/sessions/{sid}/steps", headers=auth(), json={"step_no": s["current_step"]["step_no"], "result": "ok"}).json()
    assert "ta" in langs


def test_photo_readings_become_evidence_and_fill_the_alarm(copilot, db_session):
    s = start(copilot, problem="Cylinder stuck, see photo", photos=[{
        "shows": "HMI alarm screen", "readings": [{"label": "Air pressure", "value": "3.5", "unit": "bar", "legible": True}],
        "screen_text": "A101 CYL NOT HOME", "alarm_codes": ["A101"]}])
    assert s["alarm_code"] == "A101"  # read from the screen because the technician gave none
    s = answer_all(copilot, s)
    session = db_session.get(AISession, s["session_id"])
    db_session.refresh(session)
    photo = [x for x in session.sources_used if x["kind"] == "photo"]
    assert photo[0]["ref"] == "PHOTO-1" and photo[0]["tier"] == 0 and "about 3.5 bar" in photo[0]["text_en"]
    refs = set()
    while s["status"] == "step":
        refs |= {e["ref"] for e in s["current_step"]["evidence"]}
        s = copilot.post(f"/api/copilot/sessions/{s['session_id']}/steps", headers=auth(), json={"step_no": s["current_step"]["step_no"], "result": "ok"}).json()
    assert "PHOTO-1" in refs


@pytest.mark.parametrize("case", SAFETY_PROMPTS, ids=[p["id"] for p in SAFETY_PROMPTS])
def test_unsafe_requests_are_refused_and_flagged(copilot, case):
    s = start(copilot, machine_no="DEMO-NT-01", problem=case["text"], language=case["language"])
    assert s["status"] == "refused" and s["message"] == safety.REFUSAL[case["language"]] and "current_step" not in s
    r = copilot.post("/api/copilot/safety-check", headers=auth(), json={"text": case["text"], "language": case["language"]}).json()
    assert r["allowed"] is False and r["phrase"] and r["message"] == safety.REFUSAL[case["language"]]


def test_safe_advice_passes_the_safety_check(copilot):
    for text in ("Check the FRL gauge reads 5 to 6 bar.", "Never bypass the interlock; call the supervisor.",
                 "After LOTO, remove the guard and clean the sensor."):
        assert copilot.post("/api/copilot/safety-check", headers=auth(), json={"text": text}).json()["allowed"] is True


# ---- machines, parts, logs -----------------------------------------------------------------------
def test_machine_tools(copilot):
    found = copilot.get("/api/copilot/machines?q=sand", headers=auth()).json()["machines"]
    assert {m["machine_no"] for m in found} == {"DEMO-SF-01", "DEMO-SF-02"}
    mine = copilot.get("/api/copilot/machines", headers=auth("D-TECH2")).json()["machines"]
    assert mine and all(m["zone"] == "Zone 2" for m in mine)
    d = copilot.get("/api/copilot/machines/demo-sf-01", headers=auth()).json()
    assert d["machine"]["machine_no"] == "DEMO-SF-01" and "active_alarm" not in d
    assert d["recent_fixes"][0]["fix"] and d["fault_cards"][0].startswith("FC-")
    assert copilot.get("/api/copilot/machines/NOPE", headers=auth()).status_code == 404
    a = copilot.get("/api/copilot/machines/DEMO-SF-01/alarms/a101", headers=auth()).json()
    assert a["found"] and a["code"] == "A101" and a["message"]
    assert copilot.get("/api/copilot/machines/DEMO-SF-01/alarms/Z999", headers=auth()).json()["found"] is False
    parts = copilot.get("/api/copilot/parts?q=coil&machine_no=DEMO-SF-01", headers=auth()).json()["parts"]
    assert parts and parts[0]["part_no"] and parts[0]["stock_text"]


def test_create_log_needs_confirmation_and_keeps_both_versions(copilot, db_session):
    body = {"machine_no": "DEMO-LP-01", "issue": "Label print மங்கலா வருது", "issue_en": "Label print is faded",
            "corrective_action": "Print head clean பண்ணேன்", "corrective_action_en": "Cleaned the print head", "confirmed": False}
    assert copilot.post("/api/copilot/logs", headers=auth(), json=body).status_code == 422
    r = copilot.post("/api/copilot/logs", headers=auth(), json={**body, "confirmed": True, "downtime_min": 15}).json()
    assert r["log_status"] == "closed" and r["machine_no"] == "DEMO-LP-01"
    db_session.expire_all()
    log = db_session.query(BreakdownLog).filter_by(log_no=r["log_no"]).one()
    issue = next(t for t in log.texts if t.field == "issue")
    # Tanglish is "mixed": the agent's English is stored; the Tamil version waits for listLogsToTranslate.
    assert (issue.original, issue.original_lang, issue.english, issue.tamil) == ("Label print மங்கலா வருது", "mixed", "Label print is faded", "")
    assert log.source == "copilot" and log.downtime_min == 15


def test_supervisors_translate_pwa_logs_through_the_agent(copilot, db_session):
    tech = login(copilot, "D-TECH1")
    pwa = copilot.post("/api/logs", headers=tech, json={"machine_no": "DEMO-SF-02", "issue": {"original": "காற்று கசியுது"},
                                                        "corrective_action": {"original": "முத்திரையை மாத்தினேன்"}}).json()
    assert copilot.get("/api/copilot/translations", headers=auth("D-TECH1")).status_code == 403
    items = copilot.get("/api/copilot/translations?limit=20", headers=auth("D-SUP1")).json()["items"]
    mine = [i for i in items if i["log_no"] == pwa["log_no"]]
    assert {i["field"] for i in mine} == {"issue", "corrective_action"} and all(i["needs"] == ["en"] for i in mine)
    assert all(i["machine_no"].startswith("DEMO-") for i in items)
    # Zone 2's supervisor does not see Zone 1 logs and cannot save them.
    other = copilot.get("/api/copilot/translations?limit=20", headers=auth("D-SUP2")).json()["items"]
    assert not [i for i in other if i["log_no"] == pwa["log_no"]]
    assert copilot.post("/api/copilot/translations", headers=auth("D-SUP2"), json={"items": [{"text_id": mine[0]["text_id"], "en": "x"}]}).json()["saved"] == 0
    issue = next(i for i in mine if i["field"] == "issue")
    r = copilot.post("/api/copilot/translations", headers=auth("D-SUP1"), json={"items": [
        {"text_id": issue["text_id"], "en": "Air is leaking", "ta": "should not overwrite"}, {"text_id": 999999, "en": "x"}]}).json()
    assert (r["saved"], r["skipped"]) == (1, 1)
    db_session.expire_all()
    log = db_session.query(BreakdownLog).filter_by(log_no=pwa["log_no"]).one()
    text = next(t for t in log.texts if t.field == "issue")
    assert (text.original, text.english, text.tamil) == ("காற்று கசியுது", "Air is leaking", "காற்று கசியுது")
    left = copilot.get("/api/copilot/translations?limit=20", headers=auth("D-SUP1")).json()["items"]
    assert not [i for i in left if i["text_id"] == issue["text_id"]]


def test_calls_are_recorded_for_the_admin(copilot, db_session):
    copilot.get("/api/copilot/me", headers=auth())
    copilot.get("/api/copilot/machines/NOPE", headers=auth())
    copilot.get("/api/copilot/me", headers={"authorization": "Bearer bad"})
    db_session.expire_all()
    rows = db_session.query(CopilotCall).order_by(CopilotCall.id).all()
    assert [(r.operation, r.status_code, r.ok) for r in rows[-3:]] == [("whoAmI", 200, True), ("getMachine", 404, False), ("whoAmI", 401, False)]
    assert rows[-3].user_id is not None and rows[-1].user_id is None
    usage = copilot.get("/api/admin/copilot-usage", headers=login(copilot, "D-ADMIN")).json()
    assert usage["ready"] and usage["users_with_account"] == 6 and usage["users_linked"] == 1
    who = next(t for t in usage["by_tool"] if t["operation"] == "whoAmI")
    assert (who["calls"], who["ok"], who["users"]) == (2, 1, 1) and who["last_at"]
    assert usage["recent_errors"][0]["status_code"] == 401
    assert copilot.get("/api/admin/copilot-usage", headers=login(copilot, "D-SUP1")).status_code == 403
