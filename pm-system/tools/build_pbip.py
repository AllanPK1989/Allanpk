"""
build_pbip.py
-------------
Generates the complete Power BI project under powerbi/:

    PM_Dashboard.pbip
    PM_Dashboard.SemanticModel/   TMDL - tables, columns, relationships, measures
    PM_Dashboard.Report/          PBIR - pages, visuals, theme

The Power Query for each table is read from powerbi/m_queries/*.pq and embedded
into that table's partition, so those files stay the readable, reviewable source
of truth and the model never drifts from them. Re-run this script after editing
any .pq file or dax/measures.dax.

    python tools/build_pbip.py

Power BI Desktop must be CLOSED when this runs - it holds the project files open.
"""

import json
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PBI = os.path.join(ROOT, "powerbi")
MQ = os.path.join(PBI, "m_queries")
NAME = "PM_Dashboard"

sys.path.insert(0, HERE)
from prepare_sharepoint_data import TYPES  # noqa: E402

# Deterministic GUIDs. A lineageTag that changes on every build makes every
# rebuild look like a full model rewrite in source control, which buries the one
# line that actually changed.
NS = uuid.UUID("6f1c8f2e-4b3a-4d8e-9c21-7a5e3b9d0011")


def tag(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))


TYPE_MAP = {"id": "string", "text": "string", "month": "string", "url": "string",
            "int": "int64", "dec": "double", "date": "dateTime",
            "dttm": "dateTime", "bool": "boolean"}

FORMAT = {"int64": "#,##0", "double": "#,##0.00", "dateTime": "yyyy-mm-dd",
          "boolean": '"TRUE";;"FALSE"', "string": None}

# Extra columns each query derives on top of its source columns.
DERIVED = {
    "Dim_Cell": [("Calendar_Due_Date", "dateTime"), ("Amber_Threshold_Hours", "double"),
                 ("Criticality_Sort", "int64")],
    "Dim_Machine": [("Machine_Age_Years", "int64"), ("Machine_Label", "string"),
                    ("Criticality_Sort", "int64")],
    "Dim_Technician": [("Skill_Sort", "int64"), ("Tech_Label", "string")],
    "Dim_Spare": [("ABC_FMR_Class", "string"), ("Below_Min_Stock", "boolean"),
                  ("Stockout_Risk_Score", "double")],
    "Dim_ChecklistItem": [("Checklist_Item_Key", "string"), ("Check_Point_Short", "string")],
    "Fact_StdHours": [("Month_Start_Date", "dateTime")],
    "Fact_WorkOrder": [("Delay_Days", "int64"), ("Is_On_Time", "boolean"),
                       ("Trigger_Overshoot_Hours", "double"), ("Completion_Ratio", "double")],
    "Fact_MachineTask": [("Is_Completed", "boolean"), ("Is_Open", "boolean"),
                         ("Is_Clean_Pass", "boolean"), ("Status_Sort", "int64")],
    "Fact_ChecklistResponse": [("Checklist_Item_Key", "string"), ("Submitted_Date", "dateTime"),
                               ("Is_Not_OK", "boolean"), ("Is_Checked", "boolean")],
    "Fact_ScanLog": [("Scan_Date", "dateTime"), ("Scan_Hour", "int64"),
                     ("Is_Orphan_Scan", "boolean")],
    "Fact_Breakdown": [("Reported_Date", "dateTime"), ("MTTR_Min_Calc", "double"),
                       ("Response_Time_Min_Calc", "double"), ("Production_Loss_Hrs", "double"),
                       ("Is_Open", "boolean")],
    "Fact_SpareRequest": [("Request_Date", "dateTime"), ("Approval_Lead_Days", "int64"),
                          ("Issue_Lead_Days", "int64"), ("Is_Pending_Approval", "boolean"),
                          ("Is_Approved_Not_Issued", "boolean")],
    "Fact_SpareReplaced": [("Replaced_Date", "dateTime"), ("Cost_Integrity_OK", "boolean"),
                           ("Is_Planned_Spend", "boolean")],
    "Fact_Abnormality": [("Logged_Date", "dateTime"), ("Age_Days", "int64"),
                         ("Is_Open", "boolean"), ("Is_Overdue", "boolean"),
                         ("Severity_Sort", "int64")],
    "Fact_PlanCalendar": [("Plan_Month_Date", "dateTime"), ("Is_Committed_Plan", "boolean"),
                          ("Is_On_Time", "boolean")],
}

# model table -> (source list in TYPES, .pq file)
TABLES = {
    "Dim_Cell":               ("Cell_Master", "10_Dim_Cell.pq"),
    "Dim_Machine":            ("Machine_Master", "11_Dim_Machine.pq"),
    "Dim_Technician":         ("Technician_Master", "12_Dim_Technician.pq"),
    "Dim_Spare":              ("Spare_Master", "13_Dim_Spare.pq"),
    "Dim_ChecklistItem":      ("Checklist_Master", "14_Dim_ChecklistItem.pq"),
    "Fact_StdHours":          ("StdHours_Monthly", "20_Fact_StdHours.pq"),
    "Fact_WorkOrder":         ("PM_WorkOrder", "21_Fact_WorkOrder.pq"),
    "Fact_MachineTask":       ("PM_Machine_Task", "22_Fact_MachineTask.pq"),
    "Fact_ChecklistResponse": ("Checklist_Response", "23_Fact_ChecklistResponse.pq"),
    "Fact_ScanLog":           ("Scan_Log", "24_Fact_ScanLog.pq"),
    "Fact_Breakdown":         ("Breakdown_Log", "25_Fact_Breakdown.pq"),
    "Fact_SpareRequest":      ("Spare_Request", "26_Fact_SpareRequest.pq"),
    "Fact_SpareReplaced":     ("Spare_Replaced", "27_Fact_SpareReplaced.pq"),
    "Fact_Abnormality":       ("Abnormality_Log", "28_Fact_Abnormality.pq"),
    "Fact_PlanCalendar":      ("PM_Plan_Calendar", "29_Fact_PlanCalendar.pq"),
}

HIDE = {  # columns the model keeps but the field list should not show
    "Dim_Cell": {"Criticality_Sort", "Amber_Threshold_Hours"},
    "Dim_Machine": {"Criticality_Sort"},
    "Dim_Technician": {"Skill_Sort"},
    "Dim_ChecklistItem": {"Checklist_Item_Key"},
    "Dim_Spare": set(),
    "Fact_ChecklistResponse": {"Checklist_Item_Key"},
    "Fact_MachineTask": {"Status_Sort"},
    "Fact_Abnormality": {"Severity_Sort"},
}

SORT_BY = {
    ("Dim_Cell", "Criticality"): "Criticality_Sort",
    ("Dim_Machine", "Criticality"): "Criticality_Sort",
    ("Dim_Technician", "Skill_Level"): "Skill_Sort",
    ("Fact_MachineTask", "Task_Status"): "Status_Sort",
    ("Fact_Abnormality", "Severity"): "Severity_Sort",
}

# ---------------------------------------------------------------------------
# Relationships. Single direction, one-to-many, dimension -> fact, exactly as
# a star schema should be. Nothing is bidirectional: a bidirectional filter here
# would create ambiguous paths between Dim_Cell and Dim_Machine through any fact
# carrying both keys, and Power BI would resolve them in a way nobody predicts.
#
# Each fact gets ONE active date relationship, on its primary business date.
# A second date that genuinely matters (planned vs actual) gets an inactive
# relationship, activated in a measure with USERELATIONSHIP.
# ---------------------------------------------------------------------------
RELS = [
    # Dim_Cell -> facts
    ("Dim_Cell", "Cell_ID", "Fact_StdHours", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_WorkOrder", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_MachineTask", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_ChecklistResponse", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_ScanLog", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_Breakdown", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_SpareRequest", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_SpareReplaced", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_Abnormality", "Cell_ID", True),
    ("Dim_Cell", "Cell_ID", "Fact_PlanCalendar", "Cell_ID", True),
    # Dim_Machine -> machine-level facts
    ("Dim_Machine", "Machine_ID", "Fact_MachineTask", "Machine_ID", True),
    ("Dim_Machine", "Machine_ID", "Fact_ChecklistResponse", "Machine_ID", True),
    ("Dim_Machine", "Machine_ID", "Fact_ScanLog", "Machine_ID", True),
    ("Dim_Machine", "Machine_ID", "Fact_Breakdown", "Machine_ID", True),
    ("Dim_Machine", "Machine_ID", "Fact_SpareRequest", "Machine_ID", True),
    ("Dim_Machine", "Machine_ID", "Fact_SpareReplaced", "Machine_ID", True),
    ("Dim_Machine", "Machine_ID", "Fact_Abnormality", "Machine_ID", True),
    # Dim_Technician -> the person who did the work
    ("Dim_Technician", "Tech_ID", "Fact_MachineTask", "Completed_By", True),
    ("Dim_Technician", "Tech_ID", "Fact_ChecklistResponse", "Tech_ID", True),
    ("Dim_Technician", "Tech_ID", "Fact_ScanLog", "Tech_ID", True),
    ("Dim_Technician", "Tech_ID", "Fact_Breakdown", "Reported_By_Tech_ID", True),
    ("Dim_Technician", "Tech_ID", "Fact_SpareRequest", "Requested_By", True),
    ("Dim_Technician", "Tech_ID", "Fact_SpareReplaced", "Replaced_By", True),
    ("Dim_Technician", "Tech_ID", "Fact_Abnormality", "Logged_By", True),
    ("Dim_Technician", "Tech_ID", "Fact_WorkOrder", "Lead_Tech_ID", False),
    # Dim_Spare -> spares facts
    ("Dim_Spare", "Spare_Code", "Fact_SpareRequest", "Spare_Code", True),
    ("Dim_Spare", "Spare_Code", "Fact_SpareReplaced", "Spare_Code", True),
    # Dim_ChecklistItem -> responses, on the composite key
    ("Dim_ChecklistItem", "Checklist_Item_Key", "Fact_ChecklistResponse", "Checklist_Item_Key", True),
    # Dim_Date -> the primary business date of each fact (active)
    ("Dim_Date", "Date", "Fact_StdHours", "Month_Start_Date", True),
    ("Dim_Date", "Date", "Fact_WorkOrder", "WO_Created_Date", True),
    ("Dim_Date", "Date", "Fact_MachineTask", "Completion_Date", True),
    ("Dim_Date", "Date", "Fact_ChecklistResponse", "Submitted_Date", True),
    ("Dim_Date", "Date", "Fact_ScanLog", "Scan_Date", True),
    ("Dim_Date", "Date", "Fact_Breakdown", "Reported_Date", True),
    ("Dim_Date", "Date", "Fact_SpareRequest", "Request_Date", True),
    ("Dim_Date", "Date", "Fact_SpareReplaced", "Replaced_Date", True),
    ("Dim_Date", "Date", "Fact_Abnormality", "Logged_Date", True),
    ("Dim_Date", "Date", "Fact_PlanCalendar", "Planned_Date", True),
    # Inactive second dates - reached with USERELATIONSHIP where the question
    # is genuinely about a different clock.
    ("Dim_Date", "Date", "Fact_WorkOrder", "Planned_End_Date", False),
    ("Dim_Date", "Date", "Fact_WorkOrder", "Actual_End_Date", False),
    ("Dim_Date", "Date", "Fact_Abnormality", "Target_Date", False),
    ("Dim_Date", "Date", "Fact_SpareRequest", "Approved_Date", False),
]


def cols_for(table):
    src, _ = TABLES[table]
    out = [(c, TYPE_MAP[t]) for c, t in TYPES[src].items()]
    out += DERIVED.get(table, [])
    return out


def indent_m(code):
    """Indent an M script for a TMDL triple-backtick block (4 tabs)."""
    return "\n".join(("\t\t\t\t" + ln).rstrip() for ln in code.split("\n"))


def read_pq(fname):
    with open(os.path.join(MQ, fname), encoding="utf-8") as fh:
        return fh.read().rstrip()


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def wj(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------------------
def build_table_tmdl(table):
    src, pqfile = TABLES[table]
    lines = [f"table {table}", f"\tlineageTag: {tag('table', table)}", ""]

    hidden = HIDE.get(table, set())
    for col, dt in cols_for(table):
        lines.append(f"\tcolumn {col}")
        lines.append(f"\t\tdataType: {dt}")
        if col in hidden:
            lines.append("\t\tisHidden: true")
        lines.append(f"\t\tlineageTag: {tag('col', table, col)}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: {col}")
        fs = FORMAT.get(dt)
        if fs:
            lines.append(f'\t\tformatString: {fs}')
        if dt == "dateTime":
            lines.append("\t\tannotation UnderlyingDateTimeDataType = Date")
        sb = SORT_BY.get((table, col))
        if sb:
            lines.append(f"\t\tsortByColumn: {sb}")
        lines.append("")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        lines.append("")

    lines.append(f"\tpartition {table} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource = ```")
    lines.append(indent_m(read_pq(pqfile)))
    lines.append("\t\t\t\t```")
    lines.append("")
    lines.append("\tannotation PBI_ResultType = Table")
    lines.append("")
    return "\n".join(lines)


DIM_DATE_DAX = """VAR _Start = DATE ( 2025, 4, 1 )
VAR _End = DATE ( 2027, 3, 31 )
VAR _Base = CALENDAR ( _Start, _End )
RETURN
ADDCOLUMNS (
    _Base,
    "Year", YEAR ( [Date] ),
    "Month No", MONTH ( [Date] ),
    "Month Name", FORMAT ( [Date], "MMM" ),
    "Month Year", FORMAT ( [Date], "MMM yyyy" ),
    "Year Month", FORMAT ( [Date], "yyyy-MM" ),
    "Quarter", "Q" & FORMAT ( [Date], "Q" ),
    "Day", DAY ( [Date] ),
    "Day Name", FORMAT ( [Date], "ddd" ),
    "Week No", WEEKNUM ( [Date], 2 ),
    "Is Weekend", WEEKDAY ( [Date], 2 ) > 5,
    "Fin Year",
        "FY" & FORMAT ( IF ( MONTH ( [Date] ) >= 4, YEAR ( [Date] ), YEAR ( [Date] ) - 1 ), "0000" )
            & "-" & FORMAT ( IF ( MONTH ( [Date] ) >= 4, YEAR ( [Date] ) + 1, YEAR ( [Date] ) ) - 2000, "00" ),
    "Fin Month No", IF ( MONTH ( [Date] ) >= 4, MONTH ( [Date] ) - 3, MONTH ( [Date] ) + 9 ),
    "Fin Quarter", "Q" & ROUNDUP ( DIVIDE ( IF ( MONTH ( [Date] ) >= 4, MONTH ( [Date] ) - 3, MONTH ( [Date] ) + 9 ), 3 ), 0 ),
    "Month Sort", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Is Past", [Date] <= TODAY ()
)"""

DIM_DATE_COLS = [
    ("Date", "dateTime", None), ("Year", "int64", None), ("Month No", "int64", None),
    ("Month Name", "string", "Month Sort"), ("Month Year", "string", "Month Sort"),
    ("Year Month", "string", None), ("Quarter", "string", None), ("Day", "int64", None),
    ("Day Name", "string", None), ("Week No", "int64", None), ("Is Weekend", "boolean", None),
    ("Fin Year", "string", None), ("Fin Month No", "int64", None),
    ("Fin Quarter", "string", None), ("Month Sort", "int64", None), ("Is Past", "boolean", None),
]


def build_dim_date():
    lines = ["table Dim_Date", f"\tlineageTag: {tag('table', 'Dim_Date')}", ""]
    lines.append("\t/// Generated in DAX and marked as the model's date table. The range covers")
    lines.append("\t/// two Indian financial years, 2025-04-01 to 2027-03-31, so a report opened")
    lines.append("\t/// in the current year still has next year's forecast dates to land on.")
    lines.append("\t/// Marking it as a date table is what makes the time intelligence functions")
    lines.append("\t/// work; without it they silently return wrong answers rather than erroring.")
    lines.append("")
    for col, dt, sortby in DIM_DATE_COLS:
        lines.append(f"\tcolumn '{col}'" if " " in col else f"\tcolumn {col}")
        lines.append(f"\t\tdataType: {dt}")
        if col == "Month Sort":
            lines.append("\t\tisHidden: true")
        lines.append(f"\t\tlineageTag: {tag('col', 'Dim_Date', col)}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: [{col}]")
        if dt == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
            lines.append("\t\tisKey")
        if sortby:
            lines.append(f"\t\tsortByColumn: '{sortby}'")
        lines.append("")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        lines.append("")
    lines.append("\tpartition Dim_Date = calculated")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource = ```")
    lines.append("\n".join("\t\t\t\t" + l for l in DIM_DATE_DAX.split("\n")))
    lines.append("\t\t\t\t```")
    lines.append("")
    lines.append("\tannotation PBI_Id = DateTable")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
MEASURE_FORMAT = [
    (r"%$", "0.0%"),
    (r"(Count|Total|Qty)$", "#,##0"),
    (r"Colour$", None),
    (r"^Title", None),
    (r"Date$", "yyyy-mm-dd"),
    (r"\(Days\)$", "#,##0.0"),
    (r"\(Min\)$", "#,##0"),
    (r"\(Hrs\)$", "#,##0.0"),
    (r"\(INR\)$", '#,##0'),
    (r"Cost", '"₹"#,##0'),
    (r"Hours", "#,##0"),
]


def measure_format(name):
    for pat, fs in MEASURE_FORMAT:
        if re.search(pat, name):
            return fs
    return "#,##0.00"


def parse_measures(path):
    """
    Reads dax/measures.dax into (folder, name, expression, comment) tuples.

    Two things this has to get right, both of which bit on the first pass:

      * A measure body can start with a top-level `VAR x =` at column zero, which
        looks exactly like a measure header. Anything beginning VAR or RETURN is
        therefore never treated as the start of a new measure.
      * Comment lines belong to the measure BELOW them, not the one above. They
        are buffered and only attached when a header actually follows; if body
        content comes next instead, they are flushed back into the body so an
        in-line explanation is not silently deleted.
    """
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    HEADER = re.compile(r"^([A-Za-z][A-Za-z0-9 %\-\(\)&/\.']*?) =\s*$")
    RESERVED = ("VAR ", "RETURN", "EVALUATE", "DEFINE")

    def is_header(line):
        m = HEADER.match(line)
        if not m:
            return None
        name = m.group(1).strip()
        if name.upper().startswith(RESERVED) or name.upper() in ("RETURN",):
            return None
        return name

    out = []
    folder = "99 Other"
    pending = []          # buffered comment lines awaiting an owner
    cur = None            # (folder, name, comment)
    body = []

    def flush():
        if cur is None:
            return
        expr = "\n".join(body).strip("\n").rstrip()
        if expr:
            out.append((cur[0], cur[1], expr, cur[2]))

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Folder banner:  // ===== / // 01 PM Compliance / // =====
        # A trailing parenthetical after the folder name is allowed, so
        # "// 08 Utility  (formatting and titles)" still reads as folder "08 Utility".
        m = re.match(r"^// (\d\d [A-Za-z0-9 &]+?)(?:\s*\(.*\))?$", stripped)
        if m and i > 0 and lines[i - 1].strip().startswith("// ====="):
            flush()
            cur, body, pending = None, [], []
            folder = m.group(1).strip()
            continue

        if stripped.startswith("//"):
            txt = stripped.lstrip("/").strip()
            if txt and set(txt) != {"="} and set(txt) != {"-"}:
                pending.append(txt)
            continue

        name = is_header(line)
        if name:
            flush()
            comment = " ".join(pending).strip()
            cur, body, pending = (folder, name, comment), [], []
            continue

        # Ordinary body line. Anything still buffered was an in-body comment, so
        # put it back where it was rather than losing it.
        if cur is not None:
            if pending:
                body.extend("// " + c for c in pending)
                pending = []
            body.append(line)

    flush()
    return out


def build_measures_table(measures):
    lines = ["table _Measures", f"\tlineageTag: {tag('table', '_Measures')}", ""]
    lines.append("\t/// Every measure in the model lives here, grouped into display folders.")
    lines.append("\t/// A dedicated measure table keeps the field list readable: measures are")
    lines.append("\t/// found by what they answer, not by which table happens to hold the column")
    lines.append("\t/// they were first written against.")
    lines.append("")
    for folder, name, expr, comment in measures:
        if comment:
            for c in comment.split(". "):
                c = c.strip()
                if c:
                    lines.append(f"\t/// {c if c.endswith('.') else c + '.'}")
        lines.append(f"\tmeasure '{name}' = ```")
        for ln in expr.split("\n"):
            lines.append(("\t\t\t" + ln).rstrip())
        lines.append("\t\t\t```")
        fs = measure_format(name)
        if fs:
            lines.append(f"\t\tformatString: {fs}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append(f"\t\tlineageTag: {tag('measure', name)}")
        lines.append("")
    # A measure table still needs one hidden column to exist as a table.
    lines.append("\tcolumn _placeholder")
    lines.append("\t\tisHidden: true")
    lines.append("\t\tdataType: int64")
    lines.append(f"\t\tlineageTag: {tag('col', '_Measures', '_placeholder')}")
    lines.append("\t\tsummarizeBy: none")
    lines.append("\t\tsourceColumn: [_placeholder]")
    lines.append("")
    lines.append("\t\tannotation SummarizationSetBy = Automatic")
    lines.append("")
    lines.append("\tpartition _Measures = calculated")
    lines.append("\t\tmode: import")
    lines.append('\t\tsource = ROW("_placeholder", 1)')
    lines.append("")
    return "\n".join(lines)


def build_relationships():
    out = []
    for frm, fcol, to, tcol, active in RELS:
        rid = tag("rel", frm, fcol, to, tcol)
        out.append(f"relationship {rid}")
        if not active:
            out.append("\tisActive: false")
        out.append(f"\tfromColumn: {to}.{tcol}")
        out.append(f"\ttoColumn: {frm}.{fcol}")
        out.append("")
    return "\n".join(out)


def build_expressions():
    params = [
        ("pSourceMode", "00_pSourceMode.pq", "Text"),
        ("pSourceFolder", "00_pSourceFolder.pq", "Text"),
        ("pSharePointSite", "00_pSharePointSite.pq", "Text"),
        ("pStdHoursArchiveFolder", "00_pStdHoursArchiveFolder.pq", "Text"),
    ]
    funcs = [
        ("fnGetTable", "01_fnGetTable.pq"),
        ("fnCleanKeys", "02_fnCleanKeys.pq"),
        ("fnYesNo", "03_fnYesNo.pq"),
    ]
    lines = []
    for nm, f, rt in params:
        body = read_pq(f)
        lines.append(f"expression {nm} = ```")
        for ln in body.split("\n"):
            lines.append(("\t\t" + ln).rstrip())
        lines.append("\t\t```")
        lines.append(f"\tlineageTag: {tag('expr', nm)}")
        lines.append("\tqueryGroup: '00 Parameters'")
        lines.append("")
        lines.append("\tannotation PBI_NavigationStepName = Navigation")
        lines.append(f"\tannotation PBI_ResultType = {rt}")
        lines.append("")
    for nm, f in funcs:
        body = read_pq(f)
        lines.append(f"expression {nm} = ```")
        for ln in body.split("\n"):
            lines.append(("\t\t" + ln).rstrip())
        lines.append("\t\t```")
        lines.append(f"\tlineageTag: {tag('expr', nm)}")
        lines.append("\tqueryGroup: '01 Functions'")
        lines.append("")
        lines.append("\tannotation PBI_ResultType = Function")
        lines.append("")
    return "\n".join(lines)


def build_model_tmdl(all_tables):
    lines = [
        "model Model",
        "\tculture: en-IN",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-IN",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "\tqueryGroup '00 Parameters'",
        f"\t\tannotation PBI_QueryGroupOrder = 0",
        "",
        "\tqueryGroup '01 Functions'",
        f"\t\tannotation PBI_QueryGroupOrder = 1",
        "",
        "\tannotation PBI_QueryOrder = " + json.dumps(
            ["pSourceMode", "pSourceFolder", "pSharePointSite", "pStdHoursArchiveFolder",
             "fnGetTable", "fnCleanKeys", "fnYesNo"] + list(TABLES.keys())),
        "",
        "\tannotation PBIDesktopVersion = 2.140.0.0",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        "",
    ]
    for t in all_tables:
        lines.append(f"\tref table {t}")
    lines.append("")
    lines.append("\tref cultureInfo en-IN")
    lines.append("")
    return "\n".join(lines)


def main():
    sm = os.path.join(PBI, f"{NAME}.SemanticModel")
    rp = os.path.join(PBI, f"{NAME}.Report")
    defs = os.path.join(sm, "definition")

    # ---- .pbip entry point -------------------------------------------------
    wj(os.path.join(PBI, f"{NAME}.pbip"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/pbip/definitionProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })

    # ---- semantic model ----------------------------------------------------
    wj(os.path.join(sm, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": tag("logical", "semanticmodel")},
    })
    wj(os.path.join(sm, "definition.pbism"), {"version": "4.2", "settings": {}})

    w(os.path.join(defs, "database.tmdl"), "database\n\tcompatibilityLevel: 1567\n")

    all_tables = list(TABLES.keys()) + ["Dim_Date", "_Measures"]
    w(os.path.join(defs, "model.tmdl"), build_model_tmdl(all_tables))
    w(os.path.join(defs, "expressions.tmdl"), build_expressions())
    w(os.path.join(defs, "relationships.tmdl"), build_relationships())
    w(os.path.join(defs, "cultures", "en-IN.tmdl"),
      "cultureInfo en-IN\n\n\tlinguisticMetadata =\n\t\t\t{\n"
      '\t\t\t  "Version": "1.0.0",\n\t\t\t  "Language": "en-IN"\n\t\t\t}\n'
      "\t\tcontentType: json\n")

    for t in TABLES:
        w(os.path.join(defs, "tables", f"{t}.tmdl"), build_table_tmdl(t))
    w(os.path.join(defs, "tables", "Dim_Date.tmdl"), build_dim_date())

    measures = parse_measures(os.path.join(PBI, "dax", "measures.dax"))
    w(os.path.join(defs, "tables", "_Measures.tmdl"), build_measures_table(measures))

    # ---- report shell ------------------------------------------------------
    wj(os.path.join(rp, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": tag("logical", "report")},
    })
    wj(os.path.join(rp, "definition.pbir"), {
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })

    print(f"  semantic model : {len(all_tables)} tables, {len(RELS)} relationships, "
          f"{len(measures)} measures")
    return measures


if __name__ == "__main__":
    main()
