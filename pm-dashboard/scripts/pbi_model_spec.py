"""
pbi_model_spec.py - declarative definition of the Power BI semantic model.

Everything the model needs lives here: which CSV/list feeds which table, the
data type of every column, the relationships, and the full measure library.
build_pbip.py turns this into TMDL.
"""

# ---------------------------------------------------------------------------
# Column typing rules
# ---------------------------------------------------------------------------

DATE_COLS = {
    "Date", "InstallDate", "PlannedDate", "DueDate", "ActualStartDate",
    "ActualEndDate", "RecordedDate", "UploadDate", "RequestDate", "ApprovedDate",
    "IssuedDate", "ReplacedDate", "ReportedDate", "ClosedDate", "MonthStartDate",
    "ScanDate",
}
DATETIME_COLS = {"ReportedDateTime", "RestoredDateTime", "ScanDateTime"}
INT_COLS = {
    "Year", "MonthNo", "Quarter", "Day", "DayOfWeek", "FiscalMonthNo",
    "PMIntervalStdHrs", "CalendarBackstopMonths", "BaselineMonthlyStdHrs",
    "PMStdMinutes", "DailyCapacityMin", "TaskNo", "EstMinutes", "MinStock",
    "CurrentStock", "LeadTimeDays", "DurationMin", "ChecklistTotalTasks",
    "ChecklistDoneTasks", "ChecklistFailTasks", "StdMinutes", "DowntimeMinutes",
    "ResponseMinutes", "QtyRequested", "QtyReplaced", "MonthsSinceLastPM",
}
DEC_COLS = {
    "StdHours", "TriggerStdHrs", "ChecklistCompletionPct", "MeasuredValue",
    "UnitCostINR", "TotalCostINR", "OpeningStdHrs", "StdHoursAdded",
    "ClosingStdHrs", "CarryOverAfterPM", "DowntimeHours", "PctOfThreshold",
}

CURRENCY_FMT = '"₹"#,0.00;("₹"#,0.00);"₹"#,0.00'
PCT_FMT = "0.0%"
NUM0 = "#,0"
NUM1 = "#,0.0"
DATE_FMT = "yyyy-mm-dd"
DATETIME_FMT = "yyyy-mm-dd hh:nn"


def col_type(name: str) -> str:
    if name in DATETIME_COLS:
        return "dateTime"
    if name in DATE_COLS:
        return "dateTime"
    if name in INT_COLS:
        return "int64"
    if name in DEC_COLS:
        return "double"
    return "string"


def col_format(name: str) -> str | None:
    if name in DATETIME_COLS:
        return DATETIME_FMT
    if name in DATE_COLS:
        return DATE_FMT
    if name in INT_COLS:
        return NUM0
    if name in DEC_COLS:
        return CURRENCY_FMT if "Cost" in name else NUM1
    return None


# ---------------------------------------------------------------------------
# Tables:  model name -> spec
#   csv         logical source name (CSV file stem / SharePoint entity)
#   kind        "dim" | "fact" | "calc"
#   hidden      hide from the field list
#   extra_m     additional M steps appended after type conversion
#   extra_cols  columns created by extra_m, so they get typed correctly
# ---------------------------------------------------------------------------

TABLES = [
    dict(name="Dim_Date", csv="Dim_Date", kind="dim", date_table=True,
         desc="Marked date table. One row per day, 2024-01-01 to 2028-12-31."),
    dict(name="Dim_Cell", csv="Cell_Master", kind="dim",
         desc="Production cells. Carries the PM threshold and calendar backstop."),
    dict(name="Dim_Machine", csv="Machine_Master", kind="dim",
         desc="Machines. Every QR code resolves to a row here."),
    dict(name="Dim_Technician", csv="Technician_Master", kind="dim",
         desc="Maintenance technicians. Each has a personal QR code."),
    dict(name="Dim_SparePart", csv="SparePart_Master", kind="dim",
         desc="Spare parts catalogue with stock and minimum levels."),
    dict(name="Dim_Checklist", csv="PM_Checklist_Master", kind="dim",
         desc="PM task library, one checklist per machine family.",
         extra_m=[
             '    AddKey = Table.AddColumn(Typed, "TaskKey", each [ChecklistID] & "|" & Text.From([TaskNo]), type text)'],
         extra_cols=[("TaskKey", "string")], last_step="AddKey"),
    dict(name="Config", csv="PM_Config", kind="dim", hidden=True,
         desc="Key/value configuration. Read by measures via LOOKUPVALUE."),

    dict(name="Fact_StdHours", csv="Cell_Standard_Hours", kind="fact",
         desc="Monthly production standard hours per cell - the input that drives scheduling.",
         extra_m=[
             '    AddMonthStart = Table.AddColumn(Typed, "MonthStartDate", each Date.FromText([MonthKey] & "-01"), type date)'],
         extra_cols=[("MonthStartDate", "dateTime")], last_step="AddMonthStart"),
    dict(name="Fact_HourLedger", csv="PM_Hour_Ledger", kind="fact",
         desc="Cell hour counter month by month: opening, added, closing, trigger, carry-over.",
         extra_m=[
             '    AddMonthStart = Table.AddColumn(Typed, "MonthStartDate", each Date.FromText([MonthKey] & "-01"), type date),',
             '    AddPct = Table.AddColumn(AddMonthStart, "PctOfThreshold", each if [PMIntervalStdHrs] = null or [PMIntervalStdHrs] = 0 then null else [ClosingStdHrs] / [PMIntervalStdHrs], type number)'],
         extra_cols=[("MonthStartDate", "dateTime"), ("PctOfThreshold", "double")],
         last_step="AddPct"),
    dict(name="Fact_WorkOrders", csv="PM_WorkOrders", kind="fact",
         desc="One row per machine per PM cycle. The core transactional table."),
    dict(name="Fact_ChecklistResults", csv="PM_ChecklistResults", kind="fact",
         desc="One row per checklist task per work order - the audit evidence.",
         extra_m=[
             '    AddKey = Table.AddColumn(Typed, "TaskKey", each [ChecklistID] & "|" & Text.From([TaskNo]), type text)'],
         extra_cols=[("TaskKey", "string")], last_step="AddKey"),
    dict(name="Fact_Breakdowns", csv="Breakdown_Reports", kind="fact",
         desc="Unplanned stoppages. Feeds MTBF, MTTR and availability.",
         extra_m=[
             '    AddDate = Table.AddColumn(Typed, "ReportedDate", each Date.From([ReportedDateTime]), type date),',
             '    AddHrs = Table.AddColumn(AddDate, "DowntimeHours", each if [DowntimeMinutes] = null then null else [DowntimeMinutes] / 60, type number)'],
         extra_cols=[("ReportedDate", "dateTime"), ("DowntimeHours", "double")],
         last_step="AddHrs"),
    dict(name="Fact_SpareRequests", csv="SparePart_Requests", kind="fact",
         desc="Spare part requests raised from the machine QR."),
    dict(name="Fact_SpareReplacements", csv="SparePart_Replacements", kind="fact",
         desc="What was actually fitted to the machine."),
    dict(name="Fact_Abnormalities", csv="Abnormality_Log", kind="fact",
         desc="Abnormalities - the early warning layer before a breakdown."),
    dict(name="Fact_ScanLog", csv="QR_Scan_Log", kind="fact",
         desc="Every QR scan. Proves attendance at the machine.",
         extra_m=[
             '    AddDate = Table.AddColumn(Typed, "ScanDate", each Date.From([ScanDateTime]), type date)'],
         extra_cols=[("ScanDate", "dateTime")], last_step="AddDate"),
]

# SharePoint LISTS vs Excel files in a document library
SP_LISTS = {
    "PM_WorkOrders", "PM_ChecklistResults", "Breakdown_Reports",
    "SparePart_Requests", "SparePart_Replacements", "Abnormality_Log",
    "PM_Hour_Ledger", "QR_Scan_Log",
}
SP_EXCEL = {
    "Cell_Master": ("01 Master Data/Cell_Master.xlsx", "tblCellMaster"),
    "Machine_Master": ("01 Master Data/Machine_Master.xlsx", "tblMachineMaster"),
    "Technician_Master": ("01 Master Data/Technician_Master.xlsx", "tblTechnicianMaster"),
    "PM_Checklist_Master": ("01 Master Data/PM_Checklist_Master.xlsx", "tblChecklistMaster"),
    "SparePart_Master": ("01 Master Data/SparePart_Master.xlsx", "tblSparePartMaster"),
    "PM_Config": ("01 Master Data/PM_Config.xlsx", "tblPMConfig"),
}

# ---------------------------------------------------------------------------
# Relationships:  (fromTable, fromCol, toTable, toCol, active)
# Single direction, many-to-one, dimension filters fact.
# ---------------------------------------------------------------------------

RELATIONSHIPS = [
    ("Dim_Machine", "CellID", "Dim_Cell", "CellID", True),

    ("Fact_StdHours", "CellID", "Dim_Cell", "CellID", True),
    ("Fact_StdHours", "MonthStartDate", "Dim_Date", "Date", True),

    ("Fact_HourLedger", "CellID", "Dim_Cell", "CellID", True),
    ("Fact_HourLedger", "MonthStartDate", "Dim_Date", "Date", True),

    ("Fact_WorkOrders", "MachineID", "Dim_Machine", "MachineID", True),
    ("Fact_WorkOrders", "AssignedTechID", "Dim_Technician", "TechID", True),
    ("Fact_WorkOrders", "PlannedDate", "Dim_Date", "Date", True),
    ("Fact_WorkOrders", "ActualEndDate", "Dim_Date", "Date", False),
    ("Fact_WorkOrders", "DueDate", "Dim_Date", "Date", False),

    # Checklist results hang off the work order, not off Dim_Machine and Dim_Date
    # directly. Relating them to all three would create ambiguous filter paths
    # (Date -> WO -> Checklist and Date -> Checklist), and it would also break
    # any measure that counts checklist rows per work order.
    ("Fact_ChecklistResults", "WOID", "Fact_WorkOrders", "WOID", True),
    ("Fact_ChecklistResults", "TaskKey", "Dim_Checklist", "TaskKey", True),

    ("Fact_Breakdowns", "MachineID", "Dim_Machine", "MachineID", True),
    ("Fact_Breakdowns", "AttendedTechID", "Dim_Technician", "TechID", False),
    ("Fact_Breakdowns", "ReportedDate", "Dim_Date", "Date", True),

    ("Fact_SpareRequests", "MachineID", "Dim_Machine", "MachineID", True),
    ("Fact_SpareRequests", "PartNo", "Dim_SparePart", "PartNo", True),
    ("Fact_SpareRequests", "RequestDate", "Dim_Date", "Date", True),
    ("Fact_SpareRequests", "RequestedByTechID", "Dim_Technician", "TechID", False),

    ("Fact_SpareReplacements", "MachineID", "Dim_Machine", "MachineID", True),
    ("Fact_SpareReplacements", "PartNo", "Dim_SparePart", "PartNo", True),
    ("Fact_SpareReplacements", "ReplacedDate", "Dim_Date", "Date", True),

    ("Fact_Abnormalities", "MachineID", "Dim_Machine", "MachineID", True),
    ("Fact_Abnormalities", "ReportedByTechID", "Dim_Technician", "TechID", True),
    ("Fact_Abnormalities", "ReportedDate", "Dim_Date", "Date", True),

    ("Fact_ScanLog", "MachineID", "Dim_Machine", "MachineID", True),
    ("Fact_ScanLog", "TechID", "Dim_Technician", "TechID", True),
    ("Fact_ScanLog", "ScanDate", "Dim_Date", "Date", True),
]
