#!/usr/bin/env python3
"""
generate_dummy_data.py

Generates the full set of dummy CSVs that stand in for the SharePoint lists and
the monthly standard-hours upload, so the Power BI model can be built and
validated before any real data exists.

Run:  python3 scripts/generate_dummy_data.py
Out:  data/dummy/*.csv
"""

from __future__ import annotations

import csv
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from masters import (  # noqa: E402
    ABNORMALITY_CATEGORIES, AREA_TECHS, CELLS, CHECKLISTS, FAILURE_MODES,
    MACHINES, ROOT_CAUSES, SPARES, TECHNICIANS,
)
from pm_core import (  # noqa: E402
    SEED, add_months, forecast_run_rate, month_end, month_key, month_range,
    month_start, months_between, run_pm_engine, working_days,
)

random.seed(SEED)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "dummy")
os.makedirs(OUT, exist_ok=True)

TODAY = date(2026, 8, 28)
HIST_START = date(2024, 9, 1)
HIST_END = month_start(TODAY.year, TODAY.month)          # 2026-09-01 exclusive
FORECAST_END = add_months(HIST_END, 12)                  # 12 months forward

HIST_MONTHS = month_range(HIST_START, TODAY)
FORECAST_MONTHS = month_range(add_months(HIST_END, 1), FORECAST_END)

HOLIDAYS = {
    date(2025, 1, 14), date(2025, 1, 26), date(2025, 4, 14), date(2025, 8, 15),
    date(2025, 10, 20), date(2025, 10, 21), date(2025, 12, 25),
    date(2026, 1, 14), date(2026, 1, 26), date(2026, 4, 14), date(2026, 8, 15),
    date(2026, 11, 8), date(2026, 12, 25),
    date(2027, 1, 14), date(2027, 1, 26), date(2027, 4, 14),
}

MACH_BY_CELL: dict[str, list] = {}
for m in MACHINES:
    MACH_BY_CELL.setdefault(m.cell_id, []).append(m)

CELL_BY_ID = {c.cell_id: c for c in CELLS}
MACH_BY_ID = {m.machine_id: m for m in MACHINES}
TECH_BY_ID = {t.tech_id: t for t in TECHNICIANS}
SPARE_BY_TYPE: dict[str, list] = {}
for s in SPARES:
    SPARE_BY_TYPE.setdefault(s[9], []).append(s)


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:<38} {len(rows):>5} rows")


def iso(d) -> str:
    return d.isoformat() if d else ""


def dt(d, hh: int, mm: int) -> str:
    return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00" if d else ""


# ===========================================================================
# 1. Monthly standard hours per cell (this is the file Production uploads)
# ===========================================================================
print("\nGenerating standard hours ...")

std_hours: dict[str, dict[str, float]] = {c.cell_id: {} for c in CELLS}
sh_rows = []

for c in CELLS:
    # each cell has a slow drift plus month-to-month noise, plus a seasonal dip
    drift = random.uniform(-0.004, 0.010)
    for i, m in enumerate(HIST_MONTHS):
        seasonal = 0.82 if m.month in (4, 10) else (1.08 if m.month in (3, 9) else 1.0)
        noise = random.uniform(0.86, 1.14)
        val = c.baseline_monthly_std_hrs * (1 + drift) ** i * seasonal * noise
        if m == HIST_MONTHS[-1]:      # current month is only part-way through
            val *= TODAY.day / 31.0
        val = round(val, 1)
        std_hours[c.cell_id][month_key(m)] = val
        sh_rows.append([
            month_key(m), m.year, m.month, c.cell_id, c.cell_name, c.area,
            val, "Production Planning", iso(min(month_end(m.year, m.month), TODAY)),
            f"Cell_Standard_Hours_{month_key(m).replace('-', '_')}.xlsx",
        ])

    # forecast months use the trailing 3-month run rate with light noise
    rate = forecast_run_rate(std_hours[c.cell_id], HIST_MONTHS[-2])
    for m in FORECAST_MONTHS:
        seasonal = 0.82 if m.month in (4, 10) else (1.08 if m.month in (3, 9) else 1.0)
        std_hours[c.cell_id][month_key(m)] = round(rate * seasonal, 1)

write_csv(
    "Cell_Standard_Hours.csv",
    ["MonthKey", "Year", "MonthNo", "CellID", "CellName", "Area", "StdHours",
     "UploadedBy", "UploadDate", "SourceFile"],
    sh_rows,
)

# ===========================================================================
# 2. Run the PM engine -> cycles -> work orders
# ===========================================================================
print("\nRunning PM scheduling engine ...")

ledger_rows = []
cycles = []          # (cell, cycle_no, plan_month, trigger_type, counter, carry, is_forecast)

for c in CELLS:
    # stagger the starting counters so cells do not all fall due together
    opening = random.uniform(200, 3400)
    counter = opening
    last_pm_month = HIST_MONTHS[0]
    cycle_no = 0
    all_months = HIST_MONTHS + FORECAST_MONTHS

    for m in all_months:
        mk = month_key(m)
        added = std_hours[c.cell_id].get(mk, 0.0)
        opening_bal = counter
        counter += added
        hours_due = counter >= c.pm_interval_std_hrs
        cal_due = months_between(last_pm_month, m) >= c.calendar_backstop_months
        triggered = hours_due or cal_due
        carry = max(0.0, counter - c.pm_interval_std_hrs) if triggered else counter

        ledger_rows.append([
            mk, c.cell_id, c.cell_name, round(opening_bal, 1), added,
            round(counter, 1), c.pm_interval_std_hrs,
            "Yes" if triggered else "No",
            ("Std Hours" if hours_due else "Calendar Backstop") if triggered else "",
            round(carry, 1),
            months_between(last_pm_month, m),
            "Actual" if m <= HIST_MONTHS[-1] else "Forecast",
        ])

        if triggered:
            cycle_no += 1
            cycles.append((c, cycle_no, m,
                           "Std Hours" if hours_due else "Calendar Backstop",
                           round(counter, 1), round(carry, 1),
                           m > HIST_MONTHS[-1]))
            counter = carry
            last_pm_month = m

write_csv(
    "PM_Hour_Ledger.csv",
    ["MonthKey", "CellID", "CellName", "OpeningStdHrs", "StdHoursAdded",
     "ClosingStdHrs", "PMIntervalStdHrs", "PMTriggered", "TriggerType",
     "CarryOverAfterPM", "MonthsSinceLastPM", "Scenario"],
    ledger_rows,
)

# --- work orders -----------------------------------------------------------
wo_rows, chk_rows, scan_rows = [], [], []
wo_index = {}          # wo_id -> dict for later linking
wo_seq = 0

for cell, cycle_no, m, trig, counter, carry, is_fc in cycles:
    cycle_id = f"{cell.cell_id}-C{cycle_no:02d}"
    wdays = working_days(m.year, m.month, HOLIDAYS)
    pool = AREA_TECHS.get(cell.area, [t.tech_id for t in TECHNICIANS])
    machines = MACH_BY_CELL[cell.cell_id]
    due = month_end(m.year, m.month)

    for j, mc in enumerate(machines):
        wo_seq += 1
        wo_id = f"WO-{wo_seq:05d}"
        planned = wdays[min(int(len(wdays) * (j + 1) / (len(machines) + 1)), len(wdays) - 1)]
        tech = pool[(wo_seq + j) % len(pool)]
        tasks = CHECKLISTS[mc.checklist_id]

        # ---- decide status -------------------------------------------------
        if is_fc or m > HIST_MONTHS[-1]:
            status = "Scheduled"
        elif m == HIST_MONTHS[-1]:
            status = random.choices(
                ["Completed", "In Progress", "Scheduled", "Overdue"],
                weights=[45, 20, 30, 5])[0]
        else:
            status = random.choices(
                ["Completed", "Completed (Late)", "Deferred", "Overdue"],
                weights=[80, 13, 4, 3])[0]

        start = endd = None
        dur = None
        done = fail = 0
        result = ""
        scanned = "No"
        remarks = ""

        if status.startswith("Completed"):
            if status == "Completed (Late)":
                actual = due + timedelta(days=random.randint(1, 9))
                status = "Completed"
                late = True
            else:
                actual = planned + timedelta(days=random.randint(-2, 2))
                actual = min(max(actual, wdays[0]), due)
                late = actual > due
            start = endd = actual
            dur = int(mc.pm_std_minutes * random.uniform(0.75, 1.45))
            done = len(tasks)
            fail = random.choices([0, 0, 0, 1, 1, 2, 3], weights=[45, 15, 10, 12, 8, 6, 4])[0]
            result = "Pass" if fail == 0 else ("Pass with observation" if fail <= 2 else "Fail - follow-up raised")
            scanned = "Yes"
            remarks = "Completed late - manpower shortage" if late else ""
        elif status == "In Progress":
            start = min(TODAY, planned)
            done = random.randint(2, len(tasks) - 1)
            fail = random.choices([0, 0, 1], weights=[60, 25, 15])[0]
            scanned = "Yes"
            dur = None
            result = ""
        elif status == "Overdue":
            remarks = "Not started - awaiting production window"
        elif status == "Deferred":
            remarks = "Deferred with HOD approval - shutdown planned next month"

        wo_rows.append([
            wo_id, cycle_id, cell.cell_id, cell.cell_name, cell.area,
            mc.machine_id, mc.machine_name, mc.machine_type, mc.criticality,
            "PM-4000", trig, counter, month_key(m), iso(planned), iso(due),
            tech, TECH_BY_ID[tech].tech_name, TECH_BY_ID[tech].shift,
            status, iso(start), iso(endd), dur if dur else "",
            len(tasks), done, fail,
            round(100.0 * done / len(tasks), 1),
            scanned, result,
            "Yes" if (status == "Completed" and endd and endd <= due) else
            ("No" if status in ("Completed", "Overdue", "Deferred") else ""),
            mc.pm_std_minutes, remarks,
        ])

        wo_index[wo_id] = dict(cell=cell, machine=mc, tech=tech, month=m,
                               status=status, end=endd, tasks=tasks, fail=fail,
                               planned=planned)

        # ---- checklist result rows ----------------------------------------
        if done:
            fail_slots = random.sample(range(done), min(fail, done))
            for k in range(done):
                t_no, t_desc, t_type, t_std, t_mand, t_safe = tasks[k]
                is_fail = k in fail_slots
                chk_rows.append([
                    f"{wo_id}-T{t_no:02d}", wo_id, mc.machine_id, mc.machine_name,
                    mc.checklist_id, t_no, t_desc, t_type, t_std, t_mand, t_safe,
                    "Not OK" if is_fail else "OK",
                    "" if t_type != "Measurement" else round(random.uniform(0.5, 60), 2),
                    "Deviation observed - abnormality raised" if is_fail else "",
                    tech, iso(start or planned),
                    "Yes" if is_fail else "No",
                ])

        if scanned == "Yes":
            scan_rows.append([
                f"SC-{len(scan_rows) + 1:06d}", "Machine QR", mc.machine_id,
                mc.machine_name, tech, TECH_BY_ID[tech].tech_name,
                dt(start or planned, random.randint(7, 18), random.randint(0, 59)),
                wo_id, "Start PM Checklist", cell.cell_id,
            ])

print(f"  cycles generated: {len(cycles)}")
write_csv(
    "PM_WorkOrders.csv",
    ["WOID", "CycleID", "CellID", "CellName", "Area", "MachineID", "MachineName",
     "MachineType", "Criticality", "PMType", "TriggerType", "TriggerStdHrs",
     "PlanMonth", "PlannedDate", "DueDate", "AssignedTechID", "AssignedTechName",
     "Shift", "Status", "ActualStartDate", "ActualEndDate", "DurationMin",
     "ChecklistTotalTasks", "ChecklistDoneTasks", "ChecklistFailTasks",
     "ChecklistCompletionPct", "MachineQRScanned", "PMResult", "OnTimeFlag",
     "StdMinutes", "Remarks"],
    wo_rows,
)
write_csv(
    "PM_ChecklistResults.csv",
    ["ResultID", "WOID", "MachineID", "MachineName", "ChecklistID", "TaskNo",
     "TaskDescription", "TaskType", "AcceptanceStandard", "Mandatory",
     "SafetyCritical", "Result", "MeasuredValue", "Observation", "TechID",
     "RecordedDate", "AbnormalityRaised"],
    chk_rows,
)

# ===========================================================================
# 3. Breakdowns
# ===========================================================================
print("\nGenerating breakdowns ...")

bd_rows = []
bd_seq = 0
for mc in MACHINES:
    crit_rate = {"A": 0.34, "B": 0.20, "C": 0.11}[mc.criticality]
    for m in HIST_MONTHS:
        if random.random() > crit_rate:
            continue
        bd_seq += 1
        wdaysm = working_days(m.year, m.month, HOLIDAYS)
        d = random.choice(wdaysm)
        if d > TODAY:
            continue
        fm, fcat = random.choice(FAILURE_MODES)
        h = random.randint(6, 21)
        mins = int(random.choices([25, 60, 120, 240, 480, 960],
                                  weights=[22, 26, 22, 16, 10, 4])[0] * random.uniform(0.7, 1.3))
        resp = random.randint(5, 90)
        tech = random.choice(AREA_TECHS.get(CELL_BY_ID[mc.cell_id].area,
                                            [t.tech_id for t in TECHNICIANS]))
        open_still = (TODAY - d).days < 3 and random.random() < 0.5
        bd_rows.append([
            f"BD-{bd_seq:05d}", mc.machine_id, mc.machine_name, mc.cell_id,
            CELL_BY_ID[mc.cell_id].cell_name, CELL_BY_ID[mc.cell_id].area,
            mc.machine_type, mc.criticality,
            dt(d, h, random.randint(0, 59)),
            "" if open_still else dt(d + timedelta(days=mins // 1440), (h + mins // 60) % 24, 0),
            "" if open_still else mins,
            resp, fm, fcat,
            "" if open_still else random.choice(ROOT_CAUSES),
            "" if open_still else "Component replaced and function verified",
            "Operator" if random.random() < 0.7 else "Technician",
            tech, TECH_BY_ID[tech].tech_name,
            "Open" if open_still else random.choices(["Closed", "Closed", "Closed", "Pending Spare"],
                                                     weights=[70, 15, 10, 5])[0],
            random.choices(["Yes", "No"], weights=[35, 65])[0],
            random.choices(["High", "Medium", "Low"], weights=[20, 45, 35])[0],
        ])

write_csv(
    "Breakdown_Reports.csv",
    ["BreakdownID", "MachineID", "MachineName", "CellID", "CellName", "Area",
     "MachineType", "Criticality", "ReportedDateTime", "RestoredDateTime",
     "DowntimeMinutes", "ResponseMinutes", "FailureMode", "FailureCategory",
     "RootCause", "ActionTaken", "ReportedBy", "AttendedTechID",
     "AttendedTechName", "Status", "SpareUsed", "Severity"],
    bd_rows,
)

# ===========================================================================
# 4. Spare part requests + replacements
# ===========================================================================
print("\nGenerating spare part transactions ...")

req_rows, rep_rows = [], []
req_seq = rep_seq = 0


def pick_spare(machine_type: str):
    pool = SPARE_BY_TYPE.get(machine_type, []) + SPARE_BY_TYPE.get("All", [])
    return random.choice(pool) if pool else random.choice(SPARES)


def add_request(src_type, src_id, mc, when, tech, qty, urgency):
    global req_seq
    req_seq += 1
    sp = pick_spare(mc.machine_type)
    status = random.choices(["Issued", "Approved", "Pending Approval", "Purchase Raised", "Rejected"],
                            weights=[62, 12, 10, 13, 3])[0]
    appr = when + timedelta(days=random.randint(0, 3))
    issued = appr + timedelta(days=random.randint(0, 5))
    req_rows.append([
        f"REQ-{req_seq:05d}", src_type, src_id, mc.machine_id, mc.machine_name,
        mc.cell_id, sp[0], sp[1], sp[2], sp[3], qty, sp[4], round(sp[4] * qty, 2),
        tech, TECH_BY_ID[tech].tech_name, iso(when), urgency, status,
        iso(appr) if status not in ("Pending Approval", "Rejected") else "",
        "Maintenance Head" if status not in ("Pending Approval", "Rejected") else "",
        iso(issued) if status == "Issued" else "",
        sp[7], sp[8],
        "" if status != "Rejected" else "Alternate part available in store",
    ])
    return f"REQ-{req_seq:05d}", sp, status


def add_replacement(src_type, src_id, mc, when, tech, sp, qty, req_id):
    global rep_seq
    rep_seq += 1
    rep_rows.append([
        f"REP-{rep_seq:05d}", src_type, src_id, req_id, mc.machine_id,
        mc.machine_name, mc.cell_id, mc.machine_type, sp[0], sp[1], sp[2],
        sp[3], qty, sp[4], round(sp[4] * qty, 2), tech, TECH_BY_ID[tech].tech_name,
        iso(when), random.choice(["Worn out", "Broken", "Leaking", "Seized",
                                  "End of life", "Preventive replacement"]),
        random.choices(["Yes", "No"], weights=[30, 70])[0],
        f"Old part scrapped - tag {random.randint(10000, 99999)}",
    ])


for wo_id, info in wo_index.items():
    if info["status"] != "Completed":
        continue
    if random.random() < 0.34:
        qty = random.randint(1, 3)
        rid, sp, st = add_request("PM", wo_id, info["machine"], info["end"], info["tech"], qty, "Planned")
        if st == "Issued":
            add_replacement("PM", wo_id, info["machine"], info["end"], info["tech"], sp, qty, rid)

for r in bd_rows:
    if r[20] != "Yes":       # SpareUsed
        continue
    mc = MACH_BY_ID[r[1]]
    when = date.fromisoformat(r[8][:10])
    tech = r[17]
    qty = random.randint(1, 2)
    rid, sp, st = add_request("Breakdown", r[0], mc, when, tech, qty,
                              random.choices(["Emergency", "Urgent"], weights=[45, 55])[0])
    if st == "Issued":
        add_replacement("Breakdown", r[0], mc, when + timedelta(days=random.randint(0, 2)),
                        tech, sp, qty, rid)

write_csv(
    "SparePart_Requests.csv",
    ["RequestID", "SourceType", "SourceID", "MachineID", "MachineName", "CellID",
     "PartNo", "PartName", "Category", "UOM", "QtyRequested", "UnitCostINR",
     "TotalCostINR", "RequestedByTechID", "RequestedByName", "RequestDate",
     "Urgency", "Status", "ApprovedDate", "ApprovedBy", "IssuedDate",
     "LeadTimeDays", "StoreBin", "RejectionReason"],
    req_rows,
)
write_csv(
    "SparePart_Replacements.csv",
    ["ReplacementID", "SourceType", "SourceID", "RequestID", "MachineID",
     "MachineName", "CellID", "MachineType", "PartNo", "PartName", "Category",
     "UOM", "QtyReplaced", "UnitCostINR", "TotalCostINR", "ReplacedByTechID",
     "ReplacedByName", "ReplacedDate", "OldPartCondition", "WarrantyClaim",
     "Remarks"],
    rep_rows,
)

# ===========================================================================
# 5. Abnormality log
# ===========================================================================
print("\nGenerating abnormality log ...")

abn_rows = []
abn_seq = 0

# abnormalities raised from failed checklist tasks
for row in chk_rows:
    if row[16] != "Yes":
        continue
    abn_seq += 1
    mc = MACH_BY_ID[row[2]]
    when = date.fromisoformat(row[15])
    sev = random.choices(["High", "Medium", "Low"], weights=[18, 47, 35])[0]
    age = (TODAY - when).days
    closed = random.random() < (0.92 if age > 45 else 0.55)
    abn_rows.append([
        f"ABN-{abn_seq:05d}", "PM Checklist", row[1], mc.machine_id, mc.machine_name,
        mc.cell_id, CELL_BY_ID[mc.cell_id].cell_name, CELL_BY_ID[mc.cell_id].area,
        random.choice(ABNORMALITY_CATEGORIES), sev,
        f"Task {row[5]}: {row[6]} - outside standard ({row[8]})",
        row[14], TECH_BY_ID[row[14]].tech_name, iso(when),
        "Closed" if closed else random.choices(["Open", "In Progress"], weights=[55, 45])[0],
        iso(when + timedelta(days=random.randint(1, 30))) if closed else "",
        "Corrective action completed and verified" if closed else "",
        random.choice(["Maintenance", "Production", "Safety"]),
        "Yes" if sev == "High" else "No",
        f"/sites/PMSystem/Photos/{mc.machine_id}_{abn_seq}.jpg",
    ])

# ad-hoc abnormalities reported by scanning the machine QR
for _ in range(140):
    abn_seq += 1
    mc = random.choice(MACHINES)
    when = TODAY - timedelta(days=random.randint(1, 700))
    sev = random.choices(["High", "Medium", "Low"], weights=[12, 40, 48])[0]
    closed = random.random() < (0.9 if (TODAY - when).days > 45 else 0.5)
    tech = random.choice(TECHNICIANS).tech_id
    abn_rows.append([
        f"ABN-{abn_seq:05d}", "QR Walk-by", "", mc.machine_id, mc.machine_name,
        mc.cell_id, CELL_BY_ID[mc.cell_id].cell_name, CELL_BY_ID[mc.cell_id].area,
        random.choice(ABNORMALITY_CATEGORIES), sev,
        "Observed during shop floor round - logged via machine QR",
        tech, TECH_BY_ID[tech].tech_name, iso(when),
        "Closed" if closed else random.choices(["Open", "In Progress"], weights=[60, 40])[0],
        iso(when + timedelta(days=random.randint(1, 40))) if closed else "",
        "Rectified during next available window" if closed else "",
        random.choice(["Maintenance", "Production", "Safety"]),
        "Yes" if sev == "High" else "No",
        f"/sites/PMSystem/Photos/{mc.machine_id}_{abn_seq}.jpg",
    ])

abn_rows.sort(key=lambda r: r[13])
write_csv(
    "Abnormality_Log.csv",
    ["AbnormalityID", "Source", "SourceRefID", "MachineID", "MachineName",
     "CellID", "CellName", "Area", "Category", "Severity", "Description",
     "ReportedByTechID", "ReportedByName", "ReportedDate", "Status",
     "ClosedDate", "CorrectiveAction", "OwnerFunction", "EscalationRequired",
     "PhotoURL"],
    abn_rows,
)

# ===========================================================================
# 6. QR scan log (machine + technician scans)
# ===========================================================================
print("\nGenerating QR scan log ...")

for _ in range(600):
    mc = random.choice(MACHINES)
    d = TODAY - timedelta(days=random.randint(0, 700))
    tech = random.choice(TECHNICIANS)
    scan_rows.append([
        f"SC-{len(scan_rows) + 1:06d}", "Machine QR", mc.machine_id, mc.machine_name,
        tech.tech_id, tech.tech_name, dt(d, random.randint(6, 22), random.randint(0, 59)),
        "", random.choices(["View Last PM", "Report Breakdown", "Log Abnormality",
                            "Request Spare", "Record Spare Replaced"],
                           weights=[42, 14, 20, 14, 10])[0],
        mc.cell_id,
    ])
for _ in range(900):
    tech = random.choice(TECHNICIANS)
    d = TODAY - timedelta(days=random.randint(0, 700))
    scan_rows.append([
        f"SC-{len(scan_rows) + 1:06d}", "Technician QR", "", "",
        tech.tech_id, tech.tech_name, dt(d, random.randint(6, 22), random.randint(0, 59)),
        "", "Open My PM List", "",
    ])

scan_rows.sort(key=lambda r: r[6])
for i, r in enumerate(scan_rows, start=1):
    r[0] = f"SC-{i:06d}"

write_csv(
    "QR_Scan_Log.csv",
    ["ScanID", "QRType", "MachineID", "MachineName", "TechID", "TechName",
     "ScanDateTime", "LinkedWOID", "Action", "CellID"],
    scan_rows,
)

# ===========================================================================
# 7. Master data exports
# ===========================================================================
print("\nExporting master data ...")

write_csv(
    "Cell_Master.csv",
    ["CellID", "CellName", "Area", "Plant", "Criticality", "PMIntervalStdHrs",
     "CalendarBackstopMonths", "BaselineMonthlyStdHrs", "CostCenter", "Active"],
    [[c.cell_id, c.cell_name, c.area, c.plant, c.criticality, c.pm_interval_std_hrs,
      c.calendar_backstop_months, c.baseline_monthly_std_hrs, c.cost_center, c.active]
     for c in CELLS],
)

write_csv(
    "Machine_Master.csv",
    ["MachineID", "MachineName", "CellID", "MachineType", "Make", "Model",
     "SerialNo", "InstallDate", "Criticality", "Location", "ChecklistID",
     "PMStdMinutes", "QRPayload", "Active"],
    [[m.machine_id, m.machine_name, m.cell_id, m.machine_type, m.make, m.model,
      m.serial_no, iso(m.install_date), m.criticality, m.location, m.checklist_id,
      m.pm_std_minutes,
      f"https://apps.powerapps.com/play/e/<ENV_ID>/a/<APP_ID>?tenantId=<TENANT_ID>&source=qr&type=machine&id={m.machine_id}",
      m.active] for m in MACHINES],
)

write_csv(
    "Technician_Master.csv",
    ["TechID", "TechName", "Email", "Shift", "SkillGroup", "PrimaryArea",
     "DailyCapacityMin", "QRPayload", "Active"],
    [[t.tech_id, t.tech_name, t.email, t.shift, t.skill_group, t.primary_area,
      t.daily_capacity_min,
      f"https://apps.powerapps.com/play/e/<ENV_ID>/a/<APP_ID>?tenantId=<TENANT_ID>&source=qr&type=tech&id={t.tech_id}",
      t.active] for t in TECHNICIANS],
)

chk_master = []
for cid, tasks in CHECKLISTS.items():
    for t in tasks:
        chk_master.append([cid, t[0], t[1], t[2], t[3], t[4], t[5],
                           round(8 + len(t[1]) * 0.25)])
write_csv(
    "PM_Checklist_Master.csv",
    ["ChecklistID", "TaskNo", "TaskDescription", "TaskType",
     "AcceptanceStandard", "Mandatory", "SafetyCritical", "EstMinutes"],
    chk_master,
)

write_csv(
    "SparePart_Master.csv",
    ["PartNo", "PartName", "Category", "UOM", "UnitCostINR", "MinStock",
     "CurrentStock", "LeadTimeDays", "StoreBin", "AppliesToMachineType"],
    [list(s) for s in SPARES],
)

write_csv(
    "PM_Config.csv",
    ["ConfigKey", "ConfigValue", "DataType", "Description"],
    [
        ["DefaultPMIntervalStdHrs", "4000", "Number",
         "Standard hours a cell must accumulate before a PM is scheduled"],
        ["CalendarBackstopMonths", "12", "Number",
         "Maximum months a cell may go without a PM regardless of hours"],
        ["ForecastRunRateMonths", "3", "Number",
         "Trailing months averaged to project future standard hours"],
        ["PMDueSoonThresholdPct", "85", "Number",
         "Counter percentage at which a cell shows as Due Soon"],
        ["OverdueGraceDays", "0", "Number",
         "Days after DueDate before a work order is flagged Overdue"],
        ["ChecklistPhotoMandatoryOnFail", "Yes", "Yes/No",
         "Force a photo when a checklist task is marked Not OK"],
        ["AbnormalityEscalationSeverity", "High", "Text",
         "Severity that triggers an immediate email to the Maintenance Head"],
        ["SpareApprovalLimitINR", "25000", "Number",
         "Value above which a spare request needs Plant Head approval"],
        ["StdHoursUploadDueDay", "5", "Number",
         "Day of month by which Production must upload standard hours"],
        ["ReportRefreshTimesIST", "06:00,14:00,22:00", "Text",
         "Scheduled semantic model refresh times"],
    ],
)

# ---- date dimension -------------------------------------------------------
d = date(2024, 1, 1)
dim_rows = []
while d <= date(2028, 12, 31):
    fy = d.year if d.month >= 4 else d.year - 1
    dim_rows.append([
        iso(d), d.year, d.month, d.strftime("%b"), month_key(d),
        (d.month - 1) // 3 + 1, d.day, d.strftime("%a"), d.isoweekday(),
        "Yes" if d.weekday() >= 5 else "No",
        "Yes" if d in HOLIDAYS else "No",
        f"FY{fy % 100:02d}-{(fy + 1) % 100:02d}",
        ((d.month - 4) % 12) + 1,
        "Past" if d < TODAY else ("Today" if d == TODAY else "Future"),
    ])
    d += timedelta(days=1)
write_csv(
    "Dim_Date.csv",
    ["Date", "Year", "MonthNo", "MonthShort", "MonthKey", "Quarter", "Day",
     "DayShort", "DayOfWeek", "IsWeekend", "IsHoliday", "FinancialYear",
     "FiscalMonthNo", "RelativeToToday"],
    dim_rows,
)

print("\nDone. Files written to data/dummy/\n")
