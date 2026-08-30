"""
prepare_sharepoint_data.py
--------------------------
Converts the three source workbooks in ./input into clean, typed, import-ready
CSV files - one per SharePoint list - and runs the cross-table integrity rules
from the data dictionary before it lets anything through.

Why CSV and not "just upload the Excel file":
  * SharePoint's "Import from Excel" guesses column types. It guesses wrong on
    IDs that look numeric, on Yes/No, and on Indian-format dates. Every guess it
    gets wrong is a column you have to delete and rebuild after the list has
    data in it.
  * These CSVs are written to match provision_lists.ps1 exactly: dates as
    yyyy-MM-dd, timestamps as yyyy-MM-ddTHH:mm:ss, booleans as Yes/No, all IDs
    trimmed and uppercased. Load them with load_data.ps1 into lists whose
    columns already have the right types.

Usage:
    python tools/prepare_sharepoint_data.py
    python tools/prepare_sharepoint_data.py --input ./input --out ./sharepoint/data
    python tools/prepare_sharepoint_data.py --strict     # non-zero exit on any error

Outputs:
    sharepoint/data/<List_Name>.csv          one per list
    sharepoint/data/_VALIDATION_REPORT.md    what passed, what did not
    sharepoint/data/_ROW_COUNTS.csv          row count per list, for reconciliation
"""

import argparse
import csv
import datetime as dt
import os
import sys
from collections import Counter, defaultdict

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required:  pip install -r tools/requirements.txt")


# --------------------------------------------------------------------------
# Column type map. This is the single source of truth shared with
# sharepoint/provision_lists.ps1 - if you change a type here, change it there.
#   text  = plain text, trimmed
#   id    = text, trimmed AND uppercased (all primary/foreign keys)
#   int   = whole number
#   dec   = decimal
#   date  = yyyy-MM-dd
#   dttm  = yyyy-MM-ddTHH:mm:ss
#   bool  = Yes / No
#   url   = hyperlink, left exactly as given
#   month = YYYY-MM text, never let Excel turn it into a date
# --------------------------------------------------------------------------
TYPES = {
    "Cell_Master": {
        "Cell_ID": "id", "Cell_Name": "text", "Plant": "text", "Process_Area": "text",
        "Machine_Count": "int", "PM_Trigger_Hours": "int", "Calendar_Backstop_Months": "int",
        "Cum_Std_Hours_Since_PM": "dec", "Last_PM_Date": "date", "Last_PM_WO_No": "id",
        "Next_PM_Due_Date_Calendar": "date", "Avg_Monthly_Std_Hours_L3M": "dec",
        "Owner_Supervisor": "text", "Criticality": "text", "Active": "bool",
    },
    "Machine_Master": {
        "Machine_ID": "id", "Machine_Name": "text", "Cell_ID": "id", "Cell_Name": "text",
        "Machine_Family": "text", "Make": "text", "Model": "text", "Serial_No": "text",
        "Year_Installed": "int", "Location_Tag": "text", "Checklist_ID": "id",
        "Checklist_Form_URL": "url", "Breakdown_Form_URL": "url",
        "Spare_Request_Form_URL": "url", "Abnormality_Form_URL": "url",
        "QR_Payload_URL": "url", "Criticality": "text", "Active": "bool",
    },
    "Checklist_Master": {
        "Checklist_ID": "id", "Checklist_Name": "text", "Item_No": "int",
        "Check_Point": "text", "Check_Type": "text", "Acceptance_Standard": "text",
        "Tool_Required": "text", "Frequency": "text", "Safety_Critical": "bool",
        "Expected_Time_Min": "int", "Active": "bool",
    },
    "Technician_Master": {
        "Tech_ID": "id", "Tech_Name": "text", "Skill_Level": "text", "Trade": "text",
        "Default_Shift": "text", "Contact_No": "text", "Role_Scope": "text", "Active": "bool",
    },
    "Spare_Master": {
        "Spare_Code": "id", "Spare_Description": "text", "Category": "text", "UOM": "text",
        "ABC_Class": "text", "FMR_Class": "text", "Unit_Cost_INR": "dec", "Min_Stock": "int",
        "Current_Stock": "int", "Lead_Time_Days": "int", "Bin_Location": "text",
        "Preferred_Vendor": "text", "Active": "bool",
    },
    "StdHours_Monthly": {
        "Upload_Month": "month", "Cell_ID": "id", "Cell_Name": "text",
        "Actual_Std_Hours": "dec", "Production_Qty": "int", "Uploaded_By": "text",
        "Upload_Date": "date", "Remarks": "text",
    },
    "PM_WorkOrder": {
        "WO_No": "id", "Cell_ID": "id", "Cell_Name": "text", "Trigger_Type": "text",
        "Trigger_Hours_At_Creation": "dec", "WO_Created_Date": "date",
        "Planned_Month": "month", "Planned_Start_Date": "date", "Planned_End_Date": "date",
        "Lead_Tech_ID": "id", "Priority": "text", "Machines_In_Scope": "int",
        "Machines_Completed": "int", "WO_Status": "text", "Actual_Start_Date": "date",
        "Actual_End_Date": "date", "PM_Duration_Min": "int", "Reset_Applied": "bool",
        "Reset_Date": "date", "Remarks": "text",
    },
    "PM_Machine_Task": {
        "Task_ID": "id", "WO_No": "id", "Machine_ID": "id", "Cell_ID": "id",
        "Assigned_Tech_ID": "id", "Task_Status": "text", "Scan_Start_Time": "dttm",
        "Scan_End_Time": "dttm", "Duration_Min": "int", "Checklist_Response_ID": "id",
        "NOT_OK_Count": "int", "Abnormality_Raised": "bool", "Spare_Used_Flag": "bool",
        "Completed_By": "id", "Completion_Date": "date", "Skip_Reason": "text",
    },
    "Checklist_Response": {
        "Response_ID": "id", "Submitted_DateTime": "dttm", "WO_No": "id",
        "Machine_ID": "id", "Cell_ID": "id", "Checklist_ID": "id", "Item_No": "int",
        "Check_Point": "text", "Result": "text", "Measured_Value": "dec",
        "Observation": "text", "Photo_Link": "url", "Action_Taken": "text",
        "Tech_ID": "id", "Follow_Up_Required": "bool", "Follow_Up_WO": "id",
    },
    "Scan_Log": {
        "Scan_ID": "id", "Scan_DateTime": "dttm", "Machine_ID": "id", "Cell_ID": "id",
        "Tech_ID": "id", "Scan_Action": "text", "Device": "text", "WO_No": "id",
        "Comments": "text",
    },
    "Breakdown_Log": {
        "BD_ID": "id", "Reported_DateTime": "dttm", "Machine_ID": "id", "Cell_ID": "id",
        "Reported_By_Tech_ID": "id", "Shift": "text", "Breakdown_Type": "text",
        "Symptom": "text", "Root_Cause": "text", "Action_Taken": "text",
        "Response_DateTime": "dttm", "Repair_Start": "dttm", "Repair_End": "dttm",
        "Response_Time_Min": "int", "MTTR_Min": "int", "Production_Loss_Min": "int",
        "Spare_Used": "bool", "Status": "text", "Recurrence_Flag": "bool",
        "Linked_PM_WO": "id", "Remarks": "text",
    },
    "Spare_Request": {
        "Req_ID": "id", "Request_DateTime": "dttm", "WO_No": "id", "Machine_ID": "id",
        "Cell_ID": "id", "Spare_Code": "id", "Spare_Description": "text",
        "Qty_Requested": "int", "Requested_By": "id", "Urgency": "text", "Reason": "text",
        "Approval_Status": "text", "Approved_By": "text", "Approved_Date": "date",
        "Issue_Status": "text", "Issued_Qty": "int", "Issue_Date": "date",
        "Stock_At_Request": "int", "Remarks": "text",
    },
    "Spare_Replaced": {
        "Repl_ID": "id", "Replaced_DateTime": "dttm", "Source_Type": "text",
        "Source_Ref": "id", "Machine_ID": "id", "Cell_ID": "id", "Spare_Code": "id",
        "Spare_Description": "text", "Qty_Used": "int", "Unit_Cost_INR": "dec",
        "Total_Cost_INR": "dec", "Old_Part_Condition": "text", "Failure_Mode": "text",
        "Replaced_By": "id", "Expected_Life_Hours": "int", "Warranty_Claim": "bool",
        "Remarks": "text",
    },
    "Abnormality_Log": {
        "Abn_ID": "id", "Logged_DateTime": "dttm", "Machine_ID": "id", "Cell_ID": "id",
        "Logged_By": "id", "Category": "text", "Description": "text", "Severity": "text",
        "Photo_Link": "url", "Immediate_Action": "text", "Responsibility": "text",
        "Target_Date": "date", "Status": "text", "Closed_Date": "date",
        "Closure_Remarks": "text", "Converted_To_WO": "bool",
    },
    "Plant_Calendar": {
        "Calendar_Date": "date", "Day_Type": "text", "Is_Working_Day": "bool",
        "Shift_Count": "int", "Remarks": "text",
    },
    "PM_Plan_Calendar": {
        "Plan_ID": "id", "Plan_Month": "month", "Cell_ID": "id", "Cell_Name": "text",
        "Planned_Date": "date", "Planned_Shift": "text", "Planned_Tech_ID": "id",
        "Estimated_Duration_Hrs": "dec", "Plan_Version": "text", "Frozen_Date": "date",
        "WO_No": "id", "Adherence_Status": "text",
    },
}

# Where each list is read from: (workbook file, sheet name)
SOURCES = {
    "Cell_Master":        ("01_PM_Master_Data.xlsx", "Cell_Master"),
    "Machine_Master":     ("01_PM_Master_Data.xlsx", "Machine_Master"),
    "Checklist_Master":   ("01_PM_Master_Data.xlsx", "Checklist_Master"),
    "Technician_Master":  ("01_PM_Master_Data.xlsx", "Technician_Master"),
    "Spare_Master":       ("01_PM_Master_Data.xlsx", "Spare_Master"),
    "StdHours_Monthly":   ("02_StdHours_Monthly_Upload_Template.xlsx", "StdHours_Upload"),
    "PM_WorkOrder":       ("03_PM_Transactions_Dummy.xlsx", "PM_WorkOrder"),
    "PM_Machine_Task":    ("03_PM_Transactions_Dummy.xlsx", "PM_Machine_Task"),
    "Checklist_Response": ("03_PM_Transactions_Dummy.xlsx", "Checklist_Response"),
    "Scan_Log":           ("03_PM_Transactions_Dummy.xlsx", "Scan_Log"),
    "Breakdown_Log":      ("03_PM_Transactions_Dummy.xlsx", "Breakdown_Log"),
    "Spare_Request":      ("03_PM_Transactions_Dummy.xlsx", "Spare_Request"),
    "Spare_Replaced":     ("03_PM_Transactions_Dummy.xlsx", "Spare_Replaced"),
    "Abnormality_Log":    ("03_PM_Transactions_Dummy.xlsx", "Abnormality_Log"),
    "PM_Plan_Calendar":   ("03_PM_Transactions_Dummy.xlsx", "PM_Plan_Calendar"),
}

# Lists built here rather than read from a workbook.
GENERATED = {"Plant_Calendar"}

# Plant_Calendar covers the same span as Dim_Date in the Power BI model, so the
# working-day proration and the report's date table can never disagree about
# which dates exist.
CALENDAR_START = dt.date(2025, 4, 1)
CALENDAR_END = dt.date(2027, 3, 31)


def build_plant_calendar():
    """
    One row per date, marking whether the plant runs that day.

    This exists because Actual_Std_Hours is a CAPACITY figure. Capacity accrues on
    working days, not on calendar days, so a PM reset falling mid-month has to be
    prorated by working days - otherwise a reset landing next to a run of Sundays
    posts hours the plant was never open to earn.

    Seeded with Sunday as the weekly off and everything else working three shifts.
    Festival holidays and shutdowns are plant-specific and are NOT guessed here:
    mark them in the list after loading, or the proration will be wrong by exactly
    the number of days you did not mark.
    """
    rows = []
    d = CALENDAR_START
    while d <= CALENDAR_END:
        sunday = d.weekday() == 6
        rows.append([
            d.isoformat(),
            "Weekly Off" if sunday else "Working",
            "No" if sunday else "Yes",
            "0" if sunday else "3",
            "Seeded: Sunday weekly off. Mark festival holidays and shutdowns here."
            if sunday else "",
        ])
        d += dt.timedelta(days=1)
    return rows

# Load order matters: masters before the facts that reference them.
LOAD_ORDER = [
    "Cell_Master", "Technician_Master", "Spare_Master", "Checklist_Master",
    "Machine_Master", "Plant_Calendar", "StdHours_Monthly", "PM_WorkOrder", "PM_Machine_Task",
    "Checklist_Response", "Scan_Log", "Breakdown_Log", "Spare_Request",
    "Spare_Replaced", "Abnormality_Log", "PM_Plan_Calendar",
]

TRUE_WORDS = {"yes", "y", "true", "1", "1.0"}
FALSE_WORDS = {"no", "n", "false", "0", "0.0"}


class Issue:
    def __init__(self, level, table, rule, detail):
        self.level, self.table, self.rule, self.detail = level, table, rule, detail


issues = []


def err(table, rule, detail):
    issues.append(Issue("ERROR", table, rule, detail))


def warn(table, rule, detail):
    issues.append(Issue("WARN", table, rule, detail))


# --------------------------------------------------------------------------
# Value coercion
# --------------------------------------------------------------------------
def coerce(value, kind, table, column, rownum):
    """Return the CSV-ready string for one cell, logging anything suspicious."""
    if value is None:
        return ""
    if isinstance(value, str):
        value = value.strip()
        if value == "" or value == "-":
            return "" if value == "" else value

    if kind == "id":
        return str(value).strip().upper()

    if kind == "text":
        # Collapse newlines - a stray newline inside a SharePoint single-line
        # text column silently truncates on some import paths.
        return " ".join(str(value).split())

    if kind == "url":
        return str(value).strip()

    if kind == "month":
        # Guard against Excel having helpfully turned "2025-09" into a date.
        if isinstance(value, (dt.datetime, dt.date)):
            warn(table, "month-as-date",
                 f"row {rownum}: {column} arrived as a date ({value}); wrote YYYY-MM")
            return f"{value.year:04d}-{value.month:02d}"
        s = str(value).strip()
        if len(s) != 7 or s[4] != "-":
            err(table, "bad-month", f"row {rownum}: {column}='{s}' is not YYYY-MM")
        return s

    if kind == "date":
        if isinstance(value, dt.datetime):
            return value.date().isoformat()
        if isinstance(value, dt.date):
            return value.isoformat()
        s = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return dt.datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        err(table, "bad-date", f"row {rownum}: {column}='{s}' not a recognised date")
        return ""

    if kind == "dttm":
        if isinstance(value, dt.datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        if isinstance(value, dt.date):
            return dt.datetime(value.year, value.month, value.day).strftime("%Y-%m-%dT%H:%M:%S")
        s = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
        err(table, "bad-datetime", f"row {rownum}: {column}='{s}' not a recognised timestamp")
        return ""

    if kind == "bool":
        s = str(value).strip().lower()
        if s in TRUE_WORDS:
            return "Yes"
        if s in FALSE_WORDS:
            return "No"
        err(table, "bad-boolean", f"row {rownum}: {column}='{value}' is not Yes/No")
        return ""

    if kind == "int":
        try:
            f = float(value)
        except (TypeError, ValueError):
            err(table, "bad-number", f"row {rownum}: {column}='{value}' is not numeric")
            return ""
        if abs(f - round(f)) > 1e-9:
            warn(table, "int-rounded", f"row {rownum}: {column}={f} rounded to whole number")
        return str(int(round(f)))

    if kind == "dec":
        try:
            f = float(value)
        except (TypeError, ValueError):
            err(table, "bad-number", f"row {rownum}: {column}='{value}' is not numeric")
            return ""
        # Trim trailing zeros so 872.0 does not become 872.00000000001 downstream.
        return f"{f:.4f}".rstrip("0").rstrip(".") or "0"

    return str(value)


def read_sheet(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return [], []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    body = [r for r in rows[1:] if any(c is not None and str(c).strip() != "" for c in r)]
    return header, body


# --------------------------------------------------------------------------
# Cross-table integrity rules (data dictionary, "Cross-table integrity rules")
# --------------------------------------------------------------------------
def run_integrity_checks(data):
    def col(table, name):
        hdr = data[table]["header"]
        return hdr.index(name) if name in hdr else None

    def values(table, name):
        i = col(table, name)
        return [r[i] for r in data[table]["rows"]] if i is not None else []

    def rows_of(table):
        return data[table]["rows"]

    # Rule 0 - primary keys must be unique and present.
    pks = {
        "Cell_Master": "Cell_ID", "Machine_Master": "Machine_ID",
        "Technician_Master": "Tech_ID", "Spare_Master": "Spare_Code",
        "PM_WorkOrder": "WO_No", "PM_Machine_Task": "Task_ID",
        "Checklist_Response": "Response_ID", "Scan_Log": "Scan_ID",
        "Breakdown_Log": "BD_ID", "Spare_Request": "Req_ID",
        "Spare_Replaced": "Repl_ID", "Abnormality_Log": "Abn_ID",
        "PM_Plan_Calendar": "Plan_ID",
    }
    for table, pk in pks.items():
        vals = values(table, pk)
        dupes = [v for v, n in Counter(vals).items() if n > 1]
        if dupes:
            err(table, "R0-duplicate-pk", f"{pk} repeated: {sorted(dupes)[:10]}")
        blanks = sum(1 for v in vals if v == "")
        if blanks:
            err(table, "R0-blank-pk", f"{pk} blank on {blanks} row(s)")

    # Referential integrity - every foreign key must resolve to a master row.
    cells = set(values("Cell_Master", "Cell_ID"))
    machines = set(values("Machine_Master", "Machine_ID"))
    techs = set(values("Technician_Master", "Tech_ID"))
    spares = set(values("Spare_Master", "Spare_Code"))
    wos = set(values("PM_WorkOrder", "WO_No"))
    checklists = set(values("Checklist_Master", "Checklist_ID"))

    fk_map = [
        ("Machine_Master", "Cell_ID", cells, "Cell_Master"),
        ("Machine_Master", "Checklist_ID", checklists, "Checklist_Master"),
        ("StdHours_Monthly", "Cell_ID", cells, "Cell_Master"),
        ("PM_WorkOrder", "Cell_ID", cells, "Cell_Master"),
        ("PM_WorkOrder", "Lead_Tech_ID", techs, "Technician_Master"),
        ("PM_Machine_Task", "WO_No", wos, "PM_WorkOrder"),
        ("PM_Machine_Task", "Machine_ID", machines, "Machine_Master"),
        ("PM_Machine_Task", "Cell_ID", cells, "Cell_Master"),
        ("Checklist_Response", "WO_No", wos, "PM_WorkOrder"),
        ("Checklist_Response", "Machine_ID", machines, "Machine_Master"),
        ("Scan_Log", "Machine_ID", machines, "Machine_Master"),
        ("Breakdown_Log", "Machine_ID", machines, "Machine_Master"),
        ("Spare_Request", "Spare_Code", spares, "Spare_Master"),
        ("Spare_Replaced", "Spare_Code", spares, "Spare_Master"),
        ("Abnormality_Log", "Machine_ID", machines, "Machine_Master"),
        ("PM_Plan_Calendar", "Cell_ID", cells, "Cell_Master"),
    ]
    for table, fkcol, valid, parent in fk_map:
        bad = sorted({v for v in values(table, fkcol) if v and v not in valid})
        if bad:
            err(table, "FK-unmatched",
                f"{fkcol} has {len(bad)} value(s) with no row in {parent}: {bad[:10]}")

    # Rule 1 - PM_Machine_Task row count for a WO must equal Machines_In_Scope.
    scope = {}
    i_wo, i_scope = col("PM_WorkOrder", "WO_No"), col("PM_WorkOrder", "Machines_In_Scope")
    i_st = col("PM_WorkOrder", "WO_Status")
    for r in rows_of("PM_WorkOrder"):
        scope[r[i_wo]] = (int(r[i_scope] or 0), r[i_st])
    task_count = Counter(values("PM_Machine_Task", "WO_No"))
    for wo, (n, status) in scope.items():
        got = task_count.get(wo, 0)
        if status == "Cancelled" and got == 0:
            continue
        if got != n:
            err("PM_Machine_Task", "R1-task-count",
                f"{wo}: Machines_In_Scope={n} but {got} task row(s) exist")

    # Rule 2 - a WO may only be Completed when no task is Pending or In Progress.
    pending_by_wo = defaultdict(int)
    i_twn, i_ts = col("PM_Machine_Task", "WO_No"), col("PM_Machine_Task", "Task_Status")
    for r in rows_of("PM_Machine_Task"):
        if r[i_ts] in ("Pending", "In Progress"):
            pending_by_wo[r[i_twn]] += 1
    for wo, (_, status) in scope.items():
        if status == "Completed" and pending_by_wo.get(wo, 0) > 0:
            err("PM_WorkOrder", "R2-premature-close",
                f"{wo} is Completed but {pending_by_wo[wo]} task(s) are still open")

    # Rule 3 - the reset quartet moves together, or not at all.
    i_res = col("PM_WorkOrder", "Reset_Applied")
    i_rd = col("PM_WorkOrder", "Reset_Date")
    for r in rows_of("PM_WorkOrder"):
        if r[i_res] == "Yes" and not r[i_rd]:
            err("PM_WorkOrder", "R3-reset-incomplete",
                f"{r[i_wo]}: Reset_Applied=Yes but Reset_Date is blank")
        if r[i_st] == "Completed" and r[i_res] != "Yes":
            warn("PM_WorkOrder", "R3-completed-no-reset",
                 f"{r[i_wo]} is Completed with Reset_Applied={r[i_res] or 'blank'} "
                 f"- this belongs on the daily digest")

    # Rule 4 - every Checklist_Response needs a parent PM_Machine_Task.
    task_keys = set()
    i_tm = col("PM_Machine_Task", "Machine_ID")
    for r in rows_of("PM_Machine_Task"):
        task_keys.add((r[i_twn], r[i_tm]))
    i_cw, i_cm = col("Checklist_Response", "WO_No"), col("Checklist_Response", "Machine_ID")
    orphans = {(r[i_cw], r[i_cm]) for r in rows_of("Checklist_Response")
               if (r[i_cw], r[i_cm]) not in task_keys}
    if orphans:
        err("Checklist_Response", "R4-orphan-response",
            f"{len(orphans)} WO/Machine combination(s) with no parent task: "
            f"{sorted(orphans)[:5]}")

    # Rule 5 - Total_Cost_INR must equal Qty_Used x Unit_Cost_INR.
    i_q = col("Spare_Replaced", "Qty_Used")
    i_u = col("Spare_Replaced", "Unit_Cost_INR")
    i_t = col("Spare_Replaced", "Total_Cost_INR")
    i_rid = col("Spare_Replaced", "Repl_ID")
    for r in rows_of("Spare_Replaced"):
        try:
            expected = float(r[i_q] or 0) * float(r[i_u] or 0)
            actual = float(r[i_t] or 0)
        except ValueError:
            continue
        if abs(expected - actual) > 0.01:
            err("Spare_Replaced", "R5-cost-mismatch",
                f"{r[i_rid]}: {r[i_q]} x {r[i_u]} = {expected:.2f} but "
                f"Total_Cost_INR = {actual:.2f}")

    # Rule 6 - never delete a master row; a master with Active blank is a defect.
    for table in ("Cell_Master", "Machine_Master", "Technician_Master",
                  "Spare_Master", "Checklist_Master"):
        blanks = sum(1 for v in values(table, "Active") if v == "")
        if blanks:
            err(table, "R6-active-blank", f"Active is blank on {blanks} row(s)")

    # Duplicate-upload guard: one row per Cell per Upload_Month.
    i_m, i_c = col("StdHours_Monthly", "Upload_Month"), col("StdHours_Monthly", "Cell_ID")
    key_count = Counter((r[i_m], r[i_c]) for r in rows_of("StdHours_Monthly"))
    dupes = [k for k, n in key_count.items() if n > 1]
    if dupes:
        err("StdHours_Monthly", "duplicate-month-cell",
            f"{len(dupes)} Upload_Month/Cell_ID pair(s) appear more than once: {dupes[:5]}")

    # Machine_Count on the cell should equal its active machine rows.
    active_machines = Counter()
    i_mc, i_ma = col("Machine_Master", "Cell_ID"), col("Machine_Master", "Active")
    for r in rows_of("Machine_Master"):
        if r[i_ma] == "Yes":
            active_machines[r[i_mc]] += 1
    i_cc, i_cn = col("Cell_Master", "Cell_ID"), col("Cell_Master", "Machine_Count")
    for r in rows_of("Cell_Master"):
        declared, actual = int(r[i_cn] or 0), active_machines.get(r[i_cc], 0)
        if declared != actual:
            err("Cell_Master", "machine-count-mismatch",
                f"{r[i_cc]}: Machine_Count={declared} but {actual} active machine(s) exist")

    # Every month that reports hours must have working days on the plant calendar.
    # Without them the proration divides by zero and the flow fails at 2 a.m.
    cal_working = defaultdict(int)
    i_cd = col("Plant_Calendar", "Calendar_Date")
    i_wd = col("Plant_Calendar", "Is_Working_Day")
    if i_cd is not None and i_wd is not None:
        for r in rows_of("Plant_Calendar"):
            if r[i_wd] == "Yes":
                cal_working[r[i_cd][:7]] += 1
        for m in sorted({r[col("StdHours_Monthly", "Upload_Month")]
                         for r in rows_of("StdHours_Monthly")}):
            if cal_working.get(m, 0) == 0:
                err("Plant_Calendar", "no-working-days",
                    f"{m} has std-hours rows but no working days on the plant "
                    f"calendar - proration would divide by zero")

    # A counter above its own trigger with no open work order is an unfired trigger.
    open_wo_cells = {r[col("PM_WorkOrder", "Cell_ID")] for r in rows_of("PM_WorkOrder")
                     if r[i_st] in ("Planned", "In Progress", "Overdue")}
    i_cum = col("Cell_Master", "Cum_Std_Hours_Since_PM")
    i_trg = col("Cell_Master", "PM_Trigger_Hours")
    for r in rows_of("Cell_Master"):
        try:
            cum, trg = float(r[i_cum] or 0), float(r[i_trg] or 0)
        except ValueError:
            continue
        if trg and cum >= trg and r[i_cc] not in open_wo_cells:
            warn("Cell_Master", "trigger-not-fired",
                 f"{r[i_cc]} is at {cum:g}h against a {trg:g}h trigger with no open "
                 f"work order - Flow 2 should raise one on its next run")


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="input", help="folder holding the source workbooks")
    ap.add_argument("--out", default="sharepoint/data", help="folder to write CSVs into")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any ERROR is raised")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    data = {}

    for table in LOAD_ORDER:
        if table in GENERATED:
            data[table] = {"header": list(TYPES[table]), "rows": build_plant_calendar()}
            continue

        wbfile, sheet = SOURCES[table]
        path = os.path.join(args.input, wbfile)
        if not os.path.exists(path):
            err(table, "missing-source", f"{path} not found")
            continue

        header, body = read_sheet(path, sheet)
        typemap = TYPES[table]

        missing = [c for c in typemap if c not in header]
        extra = [c for c in header if c and c not in typemap]
        if missing:
            err(table, "missing-column", f"source sheet is missing: {missing}")
        if extra:
            warn(table, "extra-column", f"source sheet has unmapped column(s): {extra}")

        out_cols = [c for c in typemap if c in header]
        idx = {c: header.index(c) for c in out_cols}
        clean = []
        for n, raw in enumerate(body, start=2):
            clean.append([coerce(raw[idx[c]] if idx[c] < len(raw) else None,
                                 typemap[c], table, c, n) for c in out_cols])

        data[table] = {"header": out_cols, "rows": clean}

    run_integrity_checks(data)

    # Write one CSV per list. UTF-8 with BOM so Excel and SharePoint both read
    # Tamil/rupee characters correctly, and CRLF so PnP's CSV reader is happy.
    counts = []
    for table in LOAD_ORDER:
        if table not in data:
            continue
        path = os.path.join(args.out, f"{table}.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            w.writerow(data[table]["header"])
            w.writerows(data[table]["rows"])
        counts.append((table, len(data[table]["rows"]), len(data[table]["header"])))
        print(f"  wrote {path}  ({len(data[table]['rows'])} rows, "
              f"{len(data[table]['header'])} columns)")

    with open(os.path.join(args.out, "_ROW_COUNTS.csv"), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["List_Name", "Row_Count", "Column_Count", "Load_Order"])
        for i, (t, r, c) in enumerate(counts, start=1):
            w.writerow([t, r, c, i])

    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    lines = [
        "# Data Validation Report",
        "",
        f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Source: `{args.input}`  ->  Output: `{args.out}`",
        "",
        f"**{len(errors)} error(s), {len(warns)} warning(s).**",
        "",
        "An ERROR means the row would break a documented integrity rule once it is in",
        "SharePoint. Fix it in the source workbook and re-run - do not load past it.",
        "A WARN is something worth knowing that does not block the load.",
        "",
        "## Row counts",
        "",
        "| # | List | Rows | Columns |",
        "|---|---|---:|---:|",
    ]
    for i, (t, r, c) in enumerate(counts, start=1):
        lines.append(f"| {i} | `{t}` | {r} | {c} |")
    lines += ["", f"**Total rows: {sum(r for _, r, _ in counts):,}**", ""]

    for level, bucket in (("Errors", errors), ("Warnings", warns)):
        lines += [f"## {level}", ""]
        if not bucket:
            lines += [f"None. All {level.lower()[:-1]} checks passed.", ""]
            continue
        lines += ["| List | Rule | Detail |", "|---|---|---|"]
        for i in bucket:
            lines.append(f"| `{i.table}` | `{i.rule}` | {i.detail} |")
        lines.append("")

    lines += [
        "## Rules that were checked",
        "",
        "| Rule | What it protects |",
        "|---|---|",
        "| `R0-duplicate-pk` / `R0-blank-pk` | Primary keys unique and present. A repeated key silently merges two machines' history. |",
        "| `FK-unmatched` | Every foreign key resolves to a master row. An unmatched `Cell_ID` is the single most common monthly-upload failure. |",
        "| `R1-task-count` | Task rows per work order equal `Machines_In_Scope`. A short work order closes early and resets the counter it should not have. |",
        "| `R2-premature-close` | No work order is Completed while a task is Pending or In Progress. |",
        "| `R3-reset-incomplete` / `R3-completed-no-reset` | The reset quartet moves together: counter, date, work order number, flag. |",
        "| `R4-orphan-response` | Every checklist response has a parent machine task. |",
        "| `R5-cost-mismatch` | `Total_Cost_INR` = `Qty_Used` x `Unit_Cost_INR` on every row. |",
        "| `R6-active-blank` | No master row has a blank `Active` - blank is neither in nor out of scope. |",
        "| `duplicate-month-cell` | One std-hours row per cell per month. Two rows double-count into the counter. |",
        "| `machine-count-mismatch` | `Cell_Master.Machine_Count` equals the active machines in that cell. |",
        "| `trigger-not-fired` | A cell over its trigger with no open work order. |",
        "| `bad-date` / `bad-datetime` / `bad-number` / `bad-boolean` | Type coercion succeeded on every cell. |",
        "| `month-as-date` | `YYYY-MM` columns did not get converted to dates by Excel. |",
        "",
    ]

    report = os.path.join(args.out, "_VALIDATION_REPORT.md")
    with open(report, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"\n  wrote {report}")
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s).")
    for i in errors[:20]:
        print(f"  ERROR  [{i.table}/{i.rule}] {i.detail}")
    for i in warns[:20]:
        print(f"  WARN   [{i.table}/{i.rule}] {i.detail}")

    if args.strict and errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
