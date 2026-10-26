"""Phase 2: automatic fault cards, review, versions and contradiction flags (rules engine, sync jobs)."""
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, FaultCard

from .conftest import login


def post_log(client, h, machine_no, issue, cause, fix, minutes=20):
    r = client.post(
        "/api/logs",
        headers=h,
        json={
            "machine_no": machine_no,
            "issue": {"original": issue},
            "root_cause": {"original": cause},
            "corrective_action": {"original": fix},
            "downtime_min": minutes,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def cards(**where):
    with SessionLocal() as db:
        q = select(FaultCard)
        for k, v in where.items():
            q = q.where(getattr(FaultCard, k) == v)
        return list(db.scalars(q.order_by(FaultCard.id)))


def test_third_similar_log_drafts_a_machine_card(client):
    h = login(client, "D-TECH1")
    # DEMO-LP-01 already has one "Label print faded" log in the sample data.
    post_log(client, h, "DEMO-LP-01", "Label print faded", "Print head dirty", "Cleaned print head with IPA", 15)
    assert not cards(status="draft")
    post_log(client, h, "DEMO-LP-01", "Label print faded", "Ribbon wrinkled", "Reloaded ribbon, adjusted tension", 25)
    drafts = cards(status="draft")
    assert len(drafts) == 1
    card = drafts[0]
    assert card.machine_id is not None and card.machine_type_id is None
    assert len(card.source_log_ids) == 3
    assert card.causes[0] == {**card.causes[0], "cause": "Print head dirty", "count": 2}  # counted in code
    assert card.avg_fix_min == 20  # (20 sample + 15 + 25) / 3
    assert card.steps_en and card.status == "draft"

    sup = login(client, "D-SUP1")
    queue = client.get("/api/fault-cards", headers=sup).json()
    assert [c["id"] for c in queue] == [card.id]
    tech_list = client.get("/api/fault-cards", headers=h)
    assert tech_list.status_code == 403
    approved = client.post(f"/api/fault-cards/{card.id}/approve", headers=sup).json()
    assert approved["status"] == "approved" and approved["version"] == 1
    page = client.get("/api/machines/DEMO-LP-01", headers=h).json()
    assert any(c["id"] == card.id for c in page["fault_cards"])
    session = client.post(
        "/api/ai/sessions", headers=h, json={"machine_no": "DEMO-LP-01", "problem_text": "Label print faded", "language": "en"}
    ).json()
    assert any(s["ref"] == f"FC-{card.id}" and s["tier"] == 1 for s in session["sources"])


def test_group_across_machines_of_one_type_drafts_a_type_card(client):
    h = login(client, "D-TECH1")
    post_log(client, h, "DEMO-SF-01", "Hopper jam", "Wet sand lumps", "Cleared hopper, dried sand")
    post_log(client, h, "DEMO-SF-02", "Hopper jam", "Wet sand lumps", "Cleared hopper")
    assert not cards(status="draft")
    post_log(client, h, "DEMO-SF-02", "Hopper jam", "Foreign object", "Removed bolt from hopper")
    drafts = cards(status="draft")
    assert len(drafts) == 1
    assert drafts[0].machine_id is None and drafts[0].machine_type_id is not None


def test_contradicting_log_flags_card_and_matching_log_does_not(client):
    h = login(client, "D-TECH1")
    post_log(client, h, "DEMO-SF-01", "Cylinder not returning", "Solenoid coil burnt", "Replaced coil")
    assert cards(id=1)[0].status == "approved"
    log = post_log(client, h, "DEMO-SF-01", "Cylinder not returning", "Air leak at push-in fitting", "Replaced fitting")
    card = cards(id=1)[0]
    assert card.status == "needs_review"
    assert card.flagged_log_ids == [log["id"]]
    assert log["log_no"] in card.review_note
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.entity == "fault_card", AuditLog.action == "flagged"))
    # A flagged card is still used, with the flag passed on to the AI.
    s = client.post(
        "/api/ai/sessions", headers=h, json={"machine_no": "DEMO-SF-01", "problem_text": "Cylinder not returning", "language": "en"}
    ).json()
    assert any(src["ref"] == "FC-1" and src["data"]["needs_review"] for src in s["sources"])


def test_redraft_then_approve_retires_old_card_and_keeps_history(client):
    h = login(client, "D-TECH1")
    post_log(client, h, "DEMO-SF-01", "Cylinder not returning", "Air leak at push-in fitting", "Replaced fitting")
    sup = login(client, "D-SUP1")
    new = client.post("/api/fault-cards/1/redraft", headers=sup).json()
    assert new["status"] == "draft" and new["replaces_id"] == 1
    assert any("leak" in c["cause"].lower() for c in new["causes"])
    assert cards(id=1)[0].status == "needs_review"  # old card stays in use until approval
    approved = client.post(f"/api/fault-cards/{new['id']}/approve", headers=sup).json()
    assert approved["version"] == 2 and len(approved["history"]) == 1
    assert approved["history"][0]["symptom"] == "Filling cylinder not returning"
    assert cards(id=1)[0].status == "retired"


def test_editing_live_card_versions_it_and_blocks_unsafe_steps(client):
    sup = login(client, "D-SUP1")
    card = client.get("/api/fault-cards/1", headers=sup).json()
    edited = client.patch(
        "/api/fault-cards/1", headers=sup,
        json={"steps_en": card["steps_en"] + ["Check the cylinder cushion screw."], "causes": [{"cause": "Solenoid coil burnt out"}]},
    ).json()
    assert edited["version"] == 2 and len(edited["history"]) == 1
    assert edited["causes"] == [{"cause": "Solenoid coil burnt out", "cause_ta": "", "count": 3, "log_ids": []}]
    r = client.patch("/api/fault-cards/1", headers=sup, json={"steps_en": ["Bypass the door interlock to test."]})
    assert r.status_code == 422


def test_rejected_draft_is_not_drafted_again_right_away(client):
    h = login(client, "D-TECH1")
    for cause in ("Print head dirty", "Ribbon wrinkled"):
        post_log(client, h, "DEMO-LP-01", "Label print faded", cause, "Cleaned head")
    draft = cards(status="draft")[0]
    sup = login(client, "D-SUP1")
    r = client.post(f"/api/fault-cards/{draft.id}/reject", headers=sup, json={"reason": "Too few details"}).json()
    assert r["status"] == "rejected"
    post_log(client, h, "DEMO-LP-01", "Label print faded", "Print head dirty", "Cleaned head")
    assert not cards(status="draft")
