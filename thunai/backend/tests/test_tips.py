from .conftest import login


def test_tip_review_and_use_as_ai_source(client):
    tech = login(client, "D-TECH1")
    r = client.post("/api/tips", headers=tech, json={"machine_no": "DEMO-SF-01", "text": "Coil burns faster when air pressure is above 6 bar; check the FRL first."})
    tip = r.json()
    assert r.status_code == 200 and tip["status"] == "pending" and tip["en"]
    assert tip not in client.get("/api/machines/DEMO-SF-01", headers=tech).json()["tips"]
    mine = client.get("/api/tips?mine=true", headers=tech).json()
    assert [t["id"] for t in mine] == [tip["id"]]
    sup = login(client, "D-SUP1")
    assert [t["id"] for t in client.get("/api/tips", headers=sup).json()] == [tip["id"]]
    assert client.post(f"/api/tips/{tip['id']}/approve", headers=tech).status_code == 403
    approved = client.post(f"/api/tips/{tip['id']}/approve", headers=sup).json()
    assert approved["status"] == "approved"
    page = client.get("/api/machines/DEMO-SF-01", headers=tech).json()
    assert [t["id"] for t in page["tips"]] == [tip["id"]]
    s = client.post("/api/ai/sessions", headers=tech,
                    json={"machine_no": "DEMO-SF-01", "problem_text": "Solenoid coil burnt again, air pressure high", "language": "en"}).json()
    tip_sources = [x for x in s["sources"] if x["kind"] == "tip"]
    assert tip_sources and tip_sources[0]["tier"] == 2 and tip_sources[0]["ref"] == f"TIP-{tip['id']}"
    assert client.post(f"/api/tips/{tip['id']}/approve", headers=sup).status_code == 409


def test_rejecting_a_tip_needs_a_reason(client):
    tech = login(client, "D-TECH1")
    tip = client.post("/api/tips", headers=tech, json={"machine_no": "DEMO-SF-01", "text": "Hit the valve with a spanner"}).json()
    sup = login(client, "D-SUP1")
    assert client.post(f"/api/tips/{tip['id']}/reject", headers=sup, json={"reason": ""}).status_code == 422
    r = client.post(f"/api/tips/{tip['id']}/reject", headers=sup, json={"reason": "Not a safe practice"}).json()
    assert r["status"] == "rejected"
