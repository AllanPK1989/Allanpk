"""Photos after the move to Copilot (SPEC 13.1): the agent reads them in Teams and sends readings;
PWA photos are attachments only. The agent's side of the flow is in test_copilot.py."""
import io

from PIL import Image

from app import photos

from .conftest import login


def test_readings_from_the_agent_are_checked():
    o = photos.clean({
        "shows": "HMI alarm screen of the filling station",
        "readings": [
            {"label": "Air pressure", "value": "3.5", "unit": "bar", "legible": True},
            {"label": "Cycle counter", "value": "1204", "unit": "", "legible": False},  # not sure: value dropped
            {"label": "Temperature", "value": "", "unit": "°C", "legible": True},  # legible without a value: not legible
            {"label": "", "value": "9", "unit": "", "legible": True},  # no label: dropped
        ],
        "screen_text": "A101 CYL NOT HOME",
        "alarm_codes": ["A101", "drop table; --", "A101 X"],  # only real-looking codes survive
    })
    assert o["usable"] and o["source"] == "copilot" and o["shows_en"].startswith("HMI alarm screen")
    assert o["readings"] == [
        {"label": "Air pressure", "value": "3.5", "unit": "bar", "legible": True},
        {"label": "Cycle counter", "value": "", "unit": "", "legible": False},
        {"label": "Temperature", "value": "", "unit": "°C", "legible": False},
    ]
    assert o["alarm_codes"] == ["A101"]


def test_pwa_photos_are_attachments_only(client):
    tech = login(client, "D-TECH1")
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), (30, 60, 90)).save(buf, "PNG")
    media_id = client.post("/api/media/photo", headers=tech, files={"file": ("p.png", buf.getvalue(), "image/png")}).json()["media_id"]
    assert client.post(f"/api/media/{media_id}/read", headers=tech, json={"machine_no": "DEMO-SF-01"}).status_code in (404, 405)
    s = client.post("/api/ai/sessions", headers=tech, json={"machine_no": "DEMO-SF-01", "problem_text": "Cylinder not returning",
                                                            "media_ids": [media_id], "language": "en"}).json()
    assert s["photos"] == [{"media_id": media_id}] and s["observations"] == [] and s["channel"] == "app"
    assert not [x for x in s["sources"] if x["kind"] == "photo"]
    assert client.get(f"/api/media/{media_id}", headers=tech).status_code == 200
