import io

from openpyxl import Workbook
from pypdf import PdfWriter

from .conftest import login


def test_sample_alarm_list_lookup_and_ai_source(client):
    tech = login(client, "D-TECH1")
    hit = client.get("/api/alarms/lookup?machine_no=DEMO-SF-02&code=a101", headers=tech).json()["alarm"]
    assert hit["code"] == "A101" and "home" in hit["message"]  # type-level list covers SF-02 too
    assert client.get("/api/alarms/lookup?machine_no=DEMO-LP-01&code=A101", headers=tech).json()["alarm"] is None
    s = client.post("/api/ai/sessions", headers=tech,
                    json={"machine_no": "DEMO-SF-01", "problem_text": "Machine stopped", "alarm_code": "A101", "language": "en"}).json()
    alarm = [x for x in s["sources"] if x["kind"] == "alarm"]
    assert alarm and alarm[0]["ref"] == "ALM-A101" and alarm[0]["tier"] == 4


def test_upload_text_pdf_alarm_list_and_scanned_image(client):
    admin = login(client, "D-ADMIN")
    text = b"Label sensor: clean the sensor window with a dry cloth.\n\nGap sensor calibration: hold FEED for 3 seconds."
    r = client.post("/api/documents", headers=admin, files={"file": ("sop.txt", text, "text/plain")},
                    data={"title": "Label printer SOP", "kind": "sop", "machine_no": "DEMO-LP-01"})
    assert r.status_code == 200, r.text
    docs = client.get("/api/documents?machine_no=DEMO-LP-01", headers=admin).json()
    sop = next(d for d in docs if d["title"] == "Label printer SOP")
    assert sop["status"] == "indexed" and sop["pages"] == 1
    assert client.get(f"/api/documents/{sop['id']}/file", headers=admin).content == text
    s = client.post("/api/ai/sessions", headers=admin,
                    json={"machine_no": "DEMO-LP-01", "problem_text": "label sensor not detecting gap", "language": "en"}).json()
    assert any(x["kind"] == "doc" and x["ref"].startswith(f"DOC-{sop['id']}-p1") for x in s["sources"])

    # A PDF without a text layer (like a scanned drawing) is stored but marked no_text.
    pdf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(pdf)
    r = client.post("/api/documents", headers=admin, files={"file": ("drawing.pdf", pdf.getvalue(), "application/pdf")},
                    data={"title": "Panel drawing", "kind": "drawing", "machine_type": "Label printer"})
    assert r.status_code == 200
    drawing = next(d for d in client.get("/api/documents", headers=admin).json() if d["title"] == "Panel drawing")
    assert drawing["status"] == "no_text" and drawing["scope"] == "type"

    wb = Workbook()
    ws = wb.active
    ws.append(["Alarm Code", "Description", "Cause", "Remedy"])
    ws.append(["E07", "Ribbon end", "Ribbon finished", "Load a new ribbon"])
    buf = io.BytesIO()
    wb.save(buf)
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    r = client.post("/api/documents", headers=admin, files={"file": ("alarms.xlsx", buf.getvalue(), xlsx)},
                    data={"title": "Printer alarms", "kind": "alarm_list", "machine_no": "DEMO-LP-01"})
    assert r.status_code == 200
    hit = client.get("/api/alarms/lookup?machine_no=DEMO-LP-01&code=E07", headers=admin).json()["alarm"]
    assert hit["remedy"] == "Load a new ribbon"
    # Deactivating the list removes its alarms from lookups (nothing is deleted).
    client.patch(f"/api/documents/{r.json()['id']}", headers=admin, json={"active": False})
    assert client.get("/api/alarms/lookup?machine_no=DEMO-LP-01&code=E07", headers=admin).json()["alarm"] is None


def test_upload_rules(client):
    tech = login(client, "D-TECH1")
    r = client.post("/api/documents", headers=tech, files={"file": ("a.txt", b"x", "text/plain")}, data={"machine_no": "DEMO-LP-01"})
    assert r.status_code == 403
    sup = login(client, "D-SUP1")
    r = client.post("/api/documents", headers=sup, files={"file": ("a.exe", b"x", "application/x-msdownload")}, data={"machine_no": "DEMO-LP-01"})
    assert r.status_code == 415
    r = client.post("/api/documents", headers=sup, files={"file": ("a.txt", b"x", "text/plain")}, data={})
    assert r.status_code == 422


def test_machine_page_lists_documents(client):
    page = client.get("/api/machines/DEMO-SF-02", headers=login(client, "D-TECH1")).json()
    titles = [d["title"] for d in page["documents"]]
    assert "[SAMPLE] Sand filling alarm list" in titles and "[SAMPLE] Sand filling quick checks" in titles
