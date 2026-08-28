#!/usr/bin/env python3
"""
generate_qr_codes.py

Generates every QR code the system needs, plus print-ready label sheets.

  qr/machines/MC-001.png ...   one per machine  -> opens the Machine screen
  qr/technicians/TECH-01.png   one per person   -> opens My PM List
  qr/print/machine-labels.html print sheet, 4 labels per A4 page
  qr/print/technician-badges.html  badge sheet, 8 per A4 page
  qr/qr_payload_index.csv      MachineID/TechID -> exact URL encoded in the code

Before the real rollout, set the three IDs below (or pass them as arguments) and
re-run. Everything downstream reads qr_payload_index.csv, so regenerating is the
only step needed if the app is ever republished to a new environment.

Run:  python3 scripts/generate_qr_codes.py [ENV_ID] [APP_ID] [TENANT_ID]
"""

from __future__ import annotations

import base64
import csv
import io
import os
import sys

import qrcode
from qrcode.constants import ERROR_CORRECT_H

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "data", "dummy")
OUT = os.path.join(ROOT, "qr")

ENV_ID = sys.argv[1] if len(sys.argv) > 1 else "<ENV_ID>"
APP_ID = sys.argv[2] if len(sys.argv) > 2 else "<APP_ID>"
TENANT_ID = sys.argv[3] if len(sys.argv) > 3 else "<TENANT_ID>"

BASE = f"https://apps.powerapps.com/play/e/{ENV_ID}/a/{APP_ID}"


def payload(kind: str, ident: str) -> str:
    return f"{BASE}?tenantId={TENANT_ID}&source=qr&type={kind}&id={ident}"


def make_png(data: str, path: str, box: int = 10) -> None:
    q = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H,
                      box_size=box, border=2)
    q.add_data(data)
    q.make(fit=True)
    q.make_image(fill_color="#0F2A3D", back_color="white").save(path)


def make_datauri(data: str, box: int = 6) -> str:
    q = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H,
                      box_size=box, border=2)
    q.add_data(data)
    q.make(fit=True)
    buf = io.BytesIO()
    q.make_image(fill_color="#0F2A3D", back_color="white").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def read_csv(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


machines = read_csv("Machine_Master.csv")
techs = read_csv("Technician_Master.csv")
cells = {c["CellID"]: c for c in read_csv("Cell_Master.csv")}

os.makedirs(os.path.join(OUT, "machines"), exist_ok=True)
os.makedirs(os.path.join(OUT, "technicians"), exist_ok=True)
os.makedirs(os.path.join(OUT, "print"), exist_ok=True)

index = []

print("\nMachine QR codes ...")
for m in machines:
    p = payload("machine", m["MachineID"])
    make_png(p, os.path.join(OUT, "machines", f"{m['MachineID']}.png"))
    index.append(["Machine", m["MachineID"], m["MachineName"], m["CellID"], p])
print(f"  {len(machines)} written to qr/machines/")

print("\nTechnician QR codes ...")
for t in techs:
    p = payload("tech", t["TechID"])
    make_png(p, os.path.join(OUT, "technicians", f"{t['TechID']}.png"))
    index.append(["Technician", t["TechID"], t["TechName"], t["PrimaryArea"], p])
print(f"  {len(techs)} written to qr/technicians/")

with open(os.path.join(OUT, "qr_payload_index.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["QRType", "ID", "Name", "Group", "PayloadURL"])
    w.writerows(index)
print("\n  qr/qr_payload_index.csv written")

# ---------------------------------------------------------------------------
# Print sheets
# ---------------------------------------------------------------------------

CSS = """
:root { --ink:#0F2A3D; --accent:#1B6E8C; --line:#C9D6DE; --muted:#5A7183; }
* { box-sizing:border-box; }
body { margin:0; font-family:"Segoe UI",system-ui,sans-serif; color:var(--ink);
       background:#F2F5F7; }
@page { size:A4; margin:10mm; }
.sheet { width:190mm; margin:0 auto; }
.grid { display:grid; gap:6mm; }
.g2 { grid-template-columns:repeat(2,1fr); }
.g3 { grid-template-columns:repeat(3,1fr); }
.card { background:#fff; border:1.5px solid var(--ink); border-radius:3mm;
        padding:5mm; page-break-inside:avoid; break-inside:avoid; }
.hdr { display:flex; justify-content:space-between; align-items:flex-start;
       border-bottom:1.5px solid var(--ink); padding-bottom:2.5mm; margin-bottom:3mm; }
.name { font-size:14pt; font-weight:700; line-height:1.15; }
.id { font-size:20pt; font-weight:800; letter-spacing:.5px; color:var(--accent); }
.meta { font-size:8pt; color:var(--muted); line-height:1.5; }
.body { display:flex; gap:4mm; align-items:center; }
.qr { width:34mm; height:34mm; flex:0 0 34mm; }
.qr img { width:100%; height:100%; display:block; }
.actions { font-size:8.5pt; line-height:1.65; }
.actions b { display:block; font-size:8pt; text-transform:uppercase;
             letter-spacing:.8px; color:var(--accent); margin-bottom:1.5mm; }
.actions li { margin-left:-4mm; }
.foot { margin-top:3mm; padding-top:2mm; border-top:1px dashed var(--line);
        font-size:7pt; color:var(--muted); display:flex; justify-content:space-between; }
.badge { text-align:center; }
.badge .qr { width:42mm; height:42mm; margin:0 auto 3mm; }
.badge .name { font-size:13pt; }
.pill { display:inline-block; padding:.8mm 2.5mm; border-radius:10mm; font-size:7.5pt;
        font-weight:700; background:#E4EDF2; color:var(--accent); }
.crit-A { background:#FBE3E0; color:#B4451F; }
.crit-B { background:#FDF0DC; color:#8A5A16; }
.crit-C { background:#E4EDF2; color:#1B6E8C; }
h1 { font-size:13pt; margin:0 0 1mm; }
.subtitle { font-size:8.5pt; color:var(--muted); margin:0 0 6mm; }
@media print { body { background:#fff; } .noprint { display:none; } }
.noprint { background:#FFF4E5; border:1px solid #E8C99B; padding:4mm;
           border-radius:2mm; font-size:9pt; margin-bottom:6mm; }
"""

MACHINE_ACTIONS = [
    "View last PM done date &amp; full history",
    "Start / continue the PM checklist",
    "Report a breakdown",
    "Request a spare part",
    "Record a spare part replaced",
    "Log an abnormality",
]

cards = []
for m in machines:
    cell = cells.get(m["CellID"], {})
    uri = make_datauri(payload("machine", m["MachineID"]), box=5)
    crit = m["Criticality"]
    cards.append(f"""
    <div class="card">
      <div class="hdr">
        <div>
          <div class="name">{m['MachineName']}</div>
          <div class="meta">{cell.get('CellName', m['CellID'])} &middot; {m['Location']}</div>
        </div>
        <div style="text-align:right">
          <div class="id">{m['MachineID']}</div>
          <span class="pill crit-{crit}">Criticality {crit}</span>
        </div>
      </div>
      <div class="body">
        <div class="qr"><img src="{uri}" alt="QR {m['MachineID']}"></div>
        <div class="actions">
          <b>Scan with your phone camera</b>
          <ul style="margin:0;padding-left:4mm">
            {''.join(f'<li>{a}</li>' for a in MACHINE_ACTIONS)}
          </ul>
        </div>
      </div>
      <div class="foot">
        <span>{m['Make']} {m['Model']} &middot; SN {m['SerialNo']}</span>
        <span>Checklist {m['ChecklistID']} &middot; PM {m['PMStdMinutes']} min</span>
      </div>
    </div>""")

html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Machine QR Labels</title><style>{CSS}</style></head><body>
<div class="sheet">
<div class="noprint">
  <b>Print instructions</b><br>
  Print A4, 100% scale, colour or mono. Laminate or use polyester label stock &mdash;
  these live on machines. Fix at eye height near the operator panel, away from coolant spray.
  Re-print any label after the Power App is republished to a new environment.
</div>
<h1>Machine QR Labels</h1>
<p class="subtitle">{len(machines)} machines &middot; PM Planning, Scheduling &amp; Tracking System</p>
<div class="grid g2">{''.join(cards)}</div>
</div></body></html>"""

with open(os.path.join(OUT, "print", "machine-labels.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("  qr/print/machine-labels.html written")

badges = []
for t in techs:
    uri = make_datauri(payload("tech", t["TechID"]), box=5)
    badges.append(f"""
    <div class="card badge">
      <div class="qr"><img src="{uri}" alt="QR {t['TechID']}"></div>
      <div class="name">{t['TechName']}</div>
      <div class="meta">{t['TechID']} &middot; {t['Shift']}</div>
      <div style="margin-top:2mm"><span class="pill">{t['SkillGroup']}</span></div>
      <div class="foot" style="justify-content:center">Scan to open MY PM LIST</div>
    </div>""")

html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Technician QR Badges</title><style>{CSS}</style></head><body>
<div class="sheet">
<div class="noprint">
  <b>Print instructions</b><br>
  Print A4, 100% scale. Cut and insert into the standard ID card holder, QR facing out.
  Each person's code opens only their own PM list &mdash; the list refreshes itself
  as machine QR scans are completed.
</div>
<h1>Technician QR Badges</h1>
<p class="subtitle">{len(techs)} technicians &middot; scan opens the personal PM work list</p>
<div class="grid g3">{''.join(badges)}</div>
</div></body></html>"""

with open(os.path.join(OUT, "print", "technician-badges.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("  qr/print/technician-badges.html written")

print(f"\nPayload base: {BASE}")
if "<ENV_ID>" in BASE:
    print("NOTE: placeholder IDs in use. Re-run with the real environment, app and "
          "tenant IDs before printing labels for the shop floor.\n")
