#!/usr/bin/env python3
"""
build_power_app.py - builds PM_Field_App.html, a working offline prototype of the
Power Apps canvas app, and POWERFX_REFERENCE.md, the build sheet for Studio.

The prototype is not a Power App. It is the same seven screens with the same
rules, running on the sample data, so the app can be used, demonstrated and
signed off before anyone opens Studio. Every screen carries the exact Power Fx
that implements it, read from powerfx_reference.py, so the demo and the
specification cannot drift apart.

Run:  python3 scripts/build_power_app.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "dummy")
sys.path.insert(0, HERE)
from powerfx_reference import APP, SCREENS  # noqa: E402


def rows(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick(rs, keys):
    return [{k: r[k] for k in keys} for r in rs]


cells = pick(rows("Cell_Master.csv"),
             ["CellID", "CellName", "Area", "Criticality", "PMIntervalStdHrs",
              "CalendarBackstopMonths"])
machines = pick(rows("Machine_Master.csv"),
                ["MachineID", "MachineName", "CellID", "MachineType", "Make", "Model",
                 "SerialNo", "Criticality", "Location", "ChecklistID", "PMStdMinutes"])
techs = pick(rows("Technician_Master.csv"),
             ["TechID", "TechName", "Email", "Shift", "SkillGroup", "PrimaryArea"])
spares = pick(rows("SparePart_Master.csv"),
              ["PartNo", "PartName", "Category", "UOM", "UnitCostINR", "MinStock",
               "CurrentStock", "AppliesToMachineType"])

checklists = defaultdict(list)
for t in rows("PM_Checklist_Master.csv"):
    checklists[t["ChecklistID"]].append({
        "TaskNo": int(t["TaskNo"]), "TaskDescription": t["TaskDescription"],
        "TaskType": t["TaskType"], "AcceptanceStandard": t["AcceptanceStandard"],
        "Mandatory": t["Mandatory"], "SafetyCritical": t["SafetyCritical"]})

wo_all = rows("PM_WorkOrders.csv")
WO_KEYS = ["WOID", "CycleID", "CellID", "CellName", "MachineID", "MachineName",
           "PlanMonth", "PlannedDate", "DueDate", "AssignedTechID", "AssignedTechName",
           "Status", "ActualEndDate", "PMResult", "TriggerType", "StdMinutes",
           "ChecklistTotalTasks", "MachineQRScanned"]
open_wos = pick([w for w in wo_all
                 if w["Status"] in ("Scheduled", "In Progress", "Overdue")
                 and w["PlanMonth"] <= "2026-09"], WO_KEYS)
done_wos = pick([w for w in wo_all if w["Status"] == "Completed"], WO_KEYS)

ledger = [r for r in rows("PM_Hour_Ledger.csv") if r["Scenario"] == "Actual"]
latest_ledger = {}
for r in sorted(ledger, key=lambda x: x["MonthKey"]):
    latest_ledger[r["CellID"]] = {
        "MonthKey": r["MonthKey"], "ClosingStdHrs": float(r["ClosingStdHrs"]),
        "PMIntervalStdHrs": int(r["PMIntervalStdHrs"]),
        "MonthsSinceLastPM": int(r["MonthsSinceLastPM"]),
        "CarryOverAfterPM": float(r["CarryOverAfterPM"])}

std_hours = defaultdict(dict)
for r in rows("Cell_Standard_Hours.csv"):
    std_hours[r["CellID"]][r["MonthKey"]] = float(r["StdHours"])

# The sample upload stops at the current month, so future months have no actual
# figure. Fall back to the trailing three-month run rate, which is exactly what
# the forecast in the semantic model does. The last month is part-complete, so
# take the three full months before it.
run_rate = {}
for cid, months in std_hours.items():
    keys = sorted(months)[-4:-1]
    run_rate[cid] = round(sum(months[k] for k in keys) / len(keys), 1) if keys else 0.0

FAILURE_MODES = ["Bearing failure", "Hydraulic leak", "Sensor / proximity fault",
                 "Drive / VFD trip", "Coolant pump failure", "Spindle overheating",
                 "Belt / chain breakage", "PLC communication loss",
                 "Pneumatic pressure drop", "Thermocouple drift", "Seal / gasket leak",
                 "Limit switch damage", "Tool clamp malfunction",
                 "Motor winding failure", "Software / parameter loss"]
ABN_CATS = ["Abnormal noise", "Abnormal vibration", "Oil / coolant leak", "Overheating",
            "Loose / missing fastener", "Damaged guard or cover", "Wiring / cable damage",
            "Air leak", "Corrosion / rust", "Housekeeping / 5S issue",
            "Safety device bypassed", "Warning lamp / alarm active"]

fx = {"App": [{"c": c, "p": p, "f": f, "w": w} for c, p, f, w in APP]}
for key, (title, sub, items) in SCREENS.items():
    fx[key] = {"title": title, "sub": sub,
               "items": [{"c": c, "p": p, "f": f, "w": w} for c, p, f, w in items]}

DATA_JS = json.dumps({
    "cells": cells, "machines": machines, "techs": techs, "spares": spares,
    "checklists": checklists, "openWOs": open_wos, "doneWOs": done_wos,
    "ledger": latest_ledger, "stdHours": std_hours, "runRate": run_rate,
    "failureModes": FAILURE_MODES, "abnCats": ABN_CATS,
}, ensure_ascii=False, separators=(",", ":"))
FX_JS = json.dumps(fx, ensure_ascii=False)

print(f"  data embedded: {len(machines)} machines, {len(techs)} technicians, "
      f"{sum(len(v) for v in checklists.values())} checklist tasks, "
      f"{len(open_wos)} open work orders")

# ---------------------------------------------------------------------------
# the build reference document
# ---------------------------------------------------------------------------
md = ["# Power Fx Reference",
      "",
      "Every control and formula in the PM Field App, in build order. Create the "
      "screen, add the control with exactly the name given, and paste the formula "
      "into the named property.",
      "",
      "> Generated from `scripts/powerfx_reference.py`. The working prototype shows "
      "these same formulas next to the screen they implement, so what you demo and "
      "what you build cannot drift apart.",
      "",
      "## Before you start",
      "",
      "1. Power Apps ▸ Create ▸ Blank app ▸ Canvas ▸ **Phone** (640 × 1136).",
      "2. Name it `PM Field App`.",
      "3. Add the SharePoint connector and all eight lists, plus the six master "
      "workbooks as data sources.",
      "4. Create the screens in this order: `scrHome`, `scrMachineHub`, `scrMyPMList`, "
      "`scrChecklist`, `scrBreakdown`, `scrSpareRequest`, `scrSpareReplaced`, "
      "`scrAbnormality`, `scrMachineHistory`.",
      "",
      "## App",
      ""]
for c, p, f, w in APP:
    md += [f"### `{c}.{p}`", "", w, "", "```powerfx", f.strip(), "```", ""]
for key, (title, sub, items) in SCREENS.items():
    md += [f"## `{key}` — {title}", "", f"*{sub}*", ""]
    for c, p, f, w in items:
        md += [f"### `{c}.{p}`", "", w, "", "```powerfx", f.strip(), "```", ""]
md += ["## Rules the app enforces, and why", "",
       "| Rule | Reason |",
       "|------|--------|",
       "| A checklist can only start from a machine QR scan in the same session | Stops desk closure |",
       "| Every screen entry writes to `QR_Scan_Log` | Attendance is provable, not asserted |",
       "| Photo mandatory on any Not OK and on every abnormality | An abnormality without a photo does not get fixed |",
       "| Mandatory tasks block submit | Partial PMs stop being signed off as complete |",
       "| `ReportedDateTime` is `Now()`, never editable | MTTR stays honest |",
       "| The technician QR shows the signed-in user's list, not the badge's | A borrowed badge cannot close someone else's work |",
       ""]
out_md = os.path.join(ROOT, "powerapp", "POWERFX_REFERENCE.md")
os.makedirs(os.path.dirname(out_md), exist_ok=True)
open(out_md, "w", encoding="utf-8").write("\n".join(md))
n_fx = len(APP) + sum(len(v[2]) for v in SCREENS.values())
print(f"  powerapp/POWERFX_REFERENCE.md  ({n_fx} formulas across {len(SCREENS)} screens)")

# ---------------------------------------------------------------------------
tpl = open(os.path.join(HERE, "power_app_template.html"), encoding="utf-8").read()
html = tpl.replace("/*__DATA__*/", DATA_JS).replace("/*__FX__*/", FX_JS)
out = os.path.join(ROOT, "powerapp", "PM_Field_App.html")
open(out, "w", encoding="utf-8").write(html)
print(f"  powerapp/PM_Field_App.html     ({len(html)/1024:.0f} KB)")
