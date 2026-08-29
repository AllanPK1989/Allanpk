# 12 · Model Build Guide

Building the semantic model by hand in Power BI Desktop. Nothing here depends on a file format matching your Desktop version.

> Generated from the same table, relationship and measure definitions that produce the project files.

**What you are building:** 16 tables + a measures table, 28 relationships, 94 measures.

**Time:** about half a day. The measures are the long part; paste them in folder order and it goes quickly.

---

## Step 1 · New file and preview features

1. Power BI Desktop ▸ **Blank report**.
2. **File ▸ Options and settings ▸ Options ▸ Preview features**. Nothing here is required if you save as `.pbix`; tick **Store semantic model using TMDL format** and **Enhanced report format (PBIR)** only if you intend to save as a `.pbip` project.
3. **File ▸ Options ▸ Current file ▸ Regional settings**: set the locale you report in. The queries below parse dates as `en-US` explicitly, so this does not change how data loads.

---

## Step 2 · Parameters and functions

**Home ▸ Transform data** to open Power Query. Then **Home ▸ Manage parameters ▸ New parameter** for each parameter below, and **Home ▸ New source ▸ Blank query** for each function (then **Home ▸ Advanced editor** and paste the body).

Name each one exactly as shown — every table query calls `fnSource` by name.

### `SourceMode` — parameter

Local reads the sample CSVs. SharePoint reads the real lists and workbooks. This is the only switch you change at go-live.

Type **Text**. Current value: `"Local"  (allowed: Local, SharePoint)`

### `LocalDataFolder` — parameter

Folder holding the CSVs. Only used when SourceMode = Local.

Type **Text**. Current value: `"C:\PM_Dashboard\data"`

### `SharePointSiteUrl` — parameter

Root URL of the SharePoint site. Only used when SourceMode = SharePoint.

Type **Text**. Current value: `"https://contoso.sharepoint.com/sites/PMSystem"`

### `fnLocalCsv` — function

Reads one sample CSV and promotes headers.

```m
(logicalName as text) as table =>
let
    Sep = if Text.EndsWith(LocalDataFolder, "\") then "" else "\",
    Path = LocalDataFolder & Sep & logicalName & ".csv",
    Raw = Csv.Document(File.Contents(Path), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Raw, [PromoteAllScalars = true]),
    NullBlanks = Table.TransformColumns(Promoted, {}, each if _ = "" then null else _)
in
    NullBlanks
```

### `fnSpList` — function

Reads one SharePoint list by its display name.

```m
(listName as text) as table =>
let
    // ApiVersion 15 is required for non-English SharePoint sites and is safe everywhere.
    // Implementation 2.0 is the current connector; if a list has more than 12 Person or
    // Lookup columns it hits a hard join limit, in which case drop Implementation and
    // ViewMode to fall back to the 1.0 connector.
    Nav = SharePoint.Tables(
        SharePointSiteUrl,
        [ApiVersion = 15, Implementation = "2.0", ViewMode = "All"]
    ),
    // The navigation column is called Title on some tenants and Name on others.
    Cols = Table.ColumnNames(Nav),
    NameCol =
        if List.Contains(Cols, "Title") then "Title"
        else if List.Contains(Cols, "Name") then "Name"
        else error "SharePoint.Tables returned no Title or Name column to navigate by.",
    Matches = Table.SelectRows(Nav, each Record.Field(_, NameCol) = listName),
    Items =
        if Table.RowCount(Matches) = 0
        then error "SharePoint list not found: " & listName
        else Matches{0}[Items]
in
    Items
```

### `fnSpExcel` — function

Reads one named Excel table out of a workbook in the document library.

```m
(relativePath as text, tableName as text) as table =>
let
    Files = SharePoint.Files(SharePointSiteUrl, [ApiVersion = 15]),
    Wanted = Table.SelectRows(Files, each Text.EndsWith([Folder Path] & [Name], relativePath)),
    Content = if Table.RowCount(Wanted) = 0
              then error "File not found in SharePoint: " & relativePath
              else Wanted{0}[Content],
    Book = Excel.Workbook(Content, true, true),
    Data = Book{[Item = tableName, Kind = "Table"]}[Data]
in
    Data
```

### `fnStdHoursFolder` — function

Combines every monthly standard-hours upload in the 02 Standard Hours folder. Add a file, refresh, and the new month appears - no query editing.

```m
() as table =>
let
    Files = SharePoint.Files(SharePointSiteUrl, [ApiVersion = 15]),
    Monthly = Table.SelectRows(
        Files,
        each Text.Contains([Folder Path], "/02 Standard Hours/")
            and not Text.Contains([Folder Path], "/_History/")
            and Text.StartsWith([Name], "Cell_Standard_Hours_")
            and Text.EndsWith(Text.Lower([Name]), ".xlsx")
            and not Text.Contains(Text.Upper([Name]), "TEMPLATE")
    ),
    WithData = Table.AddColumn(Monthly, "Data", each
        Excel.Workbook([Content], true, true){[Item = "tblStdHours", Kind = "Table"]}[Data]),
    Cols = {"MonthKey", "Year", "MonthNo", "CellID", "CellName", "Area",
            "StdHours", "UploadedBy", "UploadDate"},
    Expanded = Table.ExpandTableColumn(Table.SelectColumns(WithData, {"Name", "Data"}), "Data", Cols),
    Renamed = Table.RenameColumns(Expanded, {{"Name", "SourceFile"}}),
    NoBlank = Table.SelectRows(Renamed, each [MonthKey] <> null and [CellID] <> null)
in
    NoBlank
```

### `fnSource` — function

Single entry point for every table. Routes to CSV, SharePoint list or SharePoint workbook depending on SourceMode.

```m
(logicalName as text) as table =>
let
    SPLists = {"Abnormality_Log", "Breakdown_Reports", "PM_ChecklistResults", "PM_Hour_Ledger", "PM_WorkOrders", "QR_Scan_Log", "SparePart_Replacements", "SparePart_Requests"},
    ExcelMap = [
            Cell_Master = {"01 Master Data/Cell_Master.xlsx", "tblCellMaster"},
            Machine_Master = {"01 Master Data/Machine_Master.xlsx", "tblMachineMaster"},
            Technician_Master = {"01 Master Data/Technician_Master.xlsx", "tblTechnicianMaster"},
            PM_Checklist_Master = {"01 Master Data/PM_Checklist_Master.xlsx", "tblChecklistMaster"},
            SparePart_Master = {"01 Master Data/SparePart_Master.xlsx", "tblSparePartMaster"},
            PM_Config = {"01 Master Data/PM_Config.xlsx", "tblPMConfig"}
        ],
    Result =
        if SourceMode <> "SharePoint" then
            fnLocalCsv(logicalName)
        else if logicalName = "Cell_Standard_Hours" then
            fnStdHoursFolder()
        else if List.Contains(SPLists, logicalName) then
            fnSpList(logicalName)
        else if Record.HasFields(ExcelMap, logicalName) then
            fnSpExcel(Record.Field(ExcelMap, logicalName){0}, Record.Field(ExcelMap, logicalName){1})
        else
            error "fnSource: no binding defined for " & logicalName
in
    Result
```

> Put the three parameters in a query group called **Parameters** and the five functions in one called **Functions** (right-click ▸ Move to group). It keeps the query list readable once there are 25 entries.

---

## Step 3 · The 17 table queries

For each one: **Home ▸ New source ▸ Blank query**, then **Advanced editor**, paste, and rename the query to the heading exactly. The name matters — every measure and every visual references it.

Set **Home ▸ Close & apply** only after all 17 are in.

### `Dim_Date`

Marked date table. One row per day, 2024-01-01 to 2028-12-31.

```m
let
    StartDate = #date(2024, 1, 1),
    EndDate = #date(2028, 12, 31),
    Holidays = {
        #date(2025,1,14), #date(2025,1,26), #date(2025,4,14), #date(2025,8,15),
        #date(2025,10,20), #date(2025,10,21), #date(2025,12,25),
        #date(2026,1,14), #date(2026,1,26), #date(2026,4,14), #date(2026,8,15),
        #date(2026,11,8), #date(2026,12,25),
        #date(2027,1,14), #date(2027,1,26), #date(2027,4,14)
    },
    Days = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1,0,0,0)),
    Base = Table.FromList(Days, Splitter.SplitByNothing(), {"Date"}),
    T0 = Table.TransformColumnTypes(Base, {{"Date", type date}}),
    T1 = Table.AddColumn(T0, "Year", each Date.Year([Date]), Int64.Type),
    T2 = Table.AddColumn(T1, "MonthNo", each Date.Month([Date]), Int64.Type),
    T3 = Table.AddColumn(T2, "MonthShort", each Date.ToText([Date], "MMM"), type text),
    T4 = Table.AddColumn(T3, "MonthKey", each Date.ToText([Date], "yyyy-MM"), type text),
    T5 = Table.AddColumn(T4, "Quarter", each Date.QuarterOfYear([Date]), Int64.Type),
    T6 = Table.AddColumn(T5, "Day", each Date.Day([Date]), Int64.Type),
    T7 = Table.AddColumn(T6, "DayShort", each Date.ToText([Date], "ddd"), type text),
    T8 = Table.AddColumn(T7, "DayOfWeek", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),
    T9 = Table.AddColumn(T8, "IsWeekend", each if Date.DayOfWeek([Date], Day.Monday) >= 5 then "Yes" else "No", type text),
    TA = Table.AddColumn(T9, "IsHoliday", each if List.Contains(Holidays, [Date]) then "Yes" else "No", type text),
    TB = Table.AddColumn(TA, "FinancialYear", each
            let y = if Date.Month([Date]) >= 4 then Date.Year([Date]) else Date.Year([Date]) - 1
            in "FY" & Text.End(Text.From(y), 2) & "-" & Text.End(Text.From(y + 1), 2), type text),
    TC = Table.AddColumn(TB, "FiscalMonthNo", each Number.Mod(Date.Month([Date]) - 4, 12) + 1, Int64.Type),
    TD = Table.AddColumn(TC, "MonthSort", each Date.Year([Date]) * 100 + Date.Month([Date]), Int64.Type),
    TE = Table.AddColumn(TD, "RelativeToToday", each
            if [Date] < Date.From(DateTime.LocalNow()) then "Past"
            else if [Date] = Date.From(DateTime.LocalNow()) then "Today"
            else "Future", type text)
in
    TE
```

15 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

**Mark as a date table.** After loading: right-click `Dim_Date` in the Data pane ▸ **Mark as date table** ▸ choose the `Date` column. Time intelligence will not work without this.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`Year`, `MonthNo`, `Quarter`, `Day`, `DayOfWeek`, `FiscalMonthNo`

---

### `Dim_Cell`

Production cells. Carries the PM threshold and calendar backstop.

```m
let
    Source = fnSource("Cell_Master"),
    Typed = Table.TransformColumnTypes(Source, {{"CellID", type text}, {"CellName", type text}, {"Area", type text}, {"Plant", type text}, {"Criticality", type text}, {"PMIntervalStdHrs", Int64.Type}, {"CalendarBackstopMonths", Int64.Type}, {"BaselineMonthlyStdHrs", Int64.Type}, {"CostCenter", type text}, {"Active", type text}}, "en-US")
in
    Typed
```

10 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`PMIntervalStdHrs`, `CalendarBackstopMonths`, `BaselineMonthlyStdHrs`

---

### `Dim_Machine`

Machines. Every QR code resolves to a row here.

```m
let
    Source = fnSource("Machine_Master"),
    Typed = Table.TransformColumnTypes(Source, {{"MachineID", type text}, {"MachineName", type text}, {"CellID", type text}, {"MachineType", type text}, {"Make", type text}, {"Model", type text}, {"SerialNo", type text}, {"InstallDate", type date}, {"Criticality", type text}, {"Location", type text}, {"ChecklistID", type text}, {"PMStdMinutes", Int64.Type}, {"QRPayload", type text}, {"Active", type text}}, "en-US")
in
    Typed
```

14 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`PMStdMinutes`

---

### `Dim_Technician`

Maintenance technicians. Each has a personal QR code.

```m
let
    Source = fnSource("Technician_Master"),
    Typed = Table.TransformColumnTypes(Source, {{"TechID", type text}, {"TechName", type text}, {"Email", type text}, {"Shift", type text}, {"SkillGroup", type text}, {"PrimaryArea", type text}, {"DailyCapacityMin", Int64.Type}, {"QRPayload", type text}, {"Active", type text}}, "en-US")
in
    Typed
```

9 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`DailyCapacityMin`

---

### `Dim_SparePart`

Spare parts catalogue with stock and minimum levels.

```m
let
    Source = fnSource("SparePart_Master"),
    Typed = Table.TransformColumnTypes(Source, {{"PartNo", type text}, {"PartName", type text}, {"Category", type text}, {"UOM", type text}, {"UnitCostINR", type number}, {"MinStock", Int64.Type}, {"CurrentStock", Int64.Type}, {"LeadTimeDays", Int64.Type}, {"StoreBin", type text}, {"AppliesToMachineType", type text}}, "en-US")
in
    Typed
```

10 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`UnitCostINR`, `MinStock`, `CurrentStock`, `LeadTimeDays`

---

### `Dim_Checklist`

PM task library, one checklist per machine family.

```m
let
    Source = fnSource("PM_Checklist_Master"),
    Typed = Table.TransformColumnTypes(Source, {{"ChecklistID", type text}, {"TaskNo", Int64.Type}, {"TaskDescription", type text}, {"TaskType", type text}, {"AcceptanceStandard", type text}, {"Mandatory", type text}, {"SafetyCritical", type text}, {"EstMinutes", Int64.Type}}, "en-US"),
    AddKey = Table.AddColumn(Typed, "TaskKey", each [ChecklistID] & "|" & Text.From([TaskNo]), type text)
in
    AddKey
```

9 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`TaskNo`, `EstMinutes`

---

### `Config`

Key/value configuration. Read by measures via LOOKUPVALUE.

```m
let
    Source = fnSource("PM_Config"),
    Typed = Table.TransformColumnTypes(Source, {{"ConfigKey", type text}, {"ConfigValue", type text}, {"DataType", type text}, {"Description", type text}}, "en-US")
in
    Typed
```

4 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

**Hide it.** Right-click `Config` in the Data pane ▸ **Hide**. It is read by measures, not by people.

---

### `Fact_StdHours`

Monthly production standard hours per cell - the input that drives scheduling.

```m
let
    Source = fnSource("Cell_Standard_Hours"),
    Typed = Table.TransformColumnTypes(Source, {{"MonthKey", type text}, {"Year", Int64.Type}, {"MonthNo", Int64.Type}, {"CellID", type text}, {"CellName", type text}, {"Area", type text}, {"StdHours", type number}, {"UploadedBy", type text}, {"UploadDate", type date}, {"SourceFile", type text}}, "en-US"),
    AddMonthStart = Table.AddColumn(Typed, "MonthStartDate", each Date.FromText([MonthKey] & "-01"), type date)
in
    AddMonthStart
```

11 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`Year`, `MonthNo`, `StdHours`

---

### `Fact_HourLedger`

Cell hour counter month by month: opening, added, closing, trigger, carry-over.

```m
let
    Source = fnSource("PM_Hour_Ledger"),
    Typed = Table.TransformColumnTypes(Source, {{"MonthKey", type text}, {"CellID", type text}, {"CellName", type text}, {"OpeningStdHrs", type number}, {"StdHoursAdded", type number}, {"ClosingStdHrs", type number}, {"PMIntervalStdHrs", Int64.Type}, {"PMTriggered", type text}, {"TriggerType", type text}, {"CarryOverAfterPM", type number}, {"MonthsSinceLastPM", Int64.Type}, {"Scenario", type text}}, "en-US"),
    AddMonthStart = Table.AddColumn(Typed, "MonthStartDate", each Date.FromText([MonthKey] & "-01"), type date),
    AddPct = Table.AddColumn(AddMonthStart, "PctOfThreshold", each if [PMIntervalStdHrs] = null or [PMIntervalStdHrs] = 0 then null else [ClosingStdHrs] / [PMIntervalStdHrs], type number)
in
    AddPct
```

14 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`OpeningStdHrs`, `StdHoursAdded`, `ClosingStdHrs`, `PMIntervalStdHrs`, `CarryOverAfterPM`, `MonthsSinceLastPM`, `PctOfThreshold`

---

### `Fact_WorkOrders`

One row per machine per PM cycle. The core transactional table.

```m
let
    Source = fnSource("PM_WorkOrders"),
    Typed = Table.TransformColumnTypes(Source, {{"WOID", type text}, {"CycleID", type text}, {"CellID", type text}, {"CellName", type text}, {"Area", type text}, {"MachineID", type text}, {"MachineName", type text}, {"MachineType", type text}, {"Criticality", type text}, {"PMType", type text}, {"TriggerType", type text}, {"TriggerStdHrs", type number}, {"PlanMonth", type text}, {"PlannedDate", type date}, {"DueDate", type date}, {"AssignedTechID", type text}, {"AssignedTechName", type text}, {"Shift", type text}, {"Status", type text}, {"ActualStartDate", type date}, {"ActualEndDate", type date}, {"DurationMin", Int64.Type}, {"ChecklistTotalTasks", Int64.Type}, {"ChecklistDoneTasks", Int64.Type}, {"ChecklistFailTasks", Int64.Type}, {"ChecklistCompletionPct", type number}, {"MachineQRScanned", type text}, {"PMResult", type text}, {"OnTimeFlag", type text}, {"StdMinutes", Int64.Type}, {"Remarks", type text}}, "en-US")
in
    Typed
```

31 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`TriggerStdHrs`, `DurationMin`, `ChecklistTotalTasks`, `ChecklistDoneTasks`, `ChecklistFailTasks`, `ChecklistCompletionPct`, `StdMinutes`

---

### `Fact_ChecklistResults`

One row per checklist task per work order - the audit evidence.

```m
let
    Source = fnSource("PM_ChecklistResults"),
    Typed = Table.TransformColumnTypes(Source, {{"ResultID", type text}, {"WOID", type text}, {"MachineID", type text}, {"MachineName", type text}, {"ChecklistID", type text}, {"TaskNo", Int64.Type}, {"TaskDescription", type text}, {"TaskType", type text}, {"AcceptanceStandard", type text}, {"Mandatory", type text}, {"SafetyCritical", type text}, {"Result", type text}, {"MeasuredValue", type number}, {"Observation", type text}, {"TechID", type text}, {"RecordedDate", type date}, {"AbnormalityRaised", type text}}, "en-US"),
    AddKey = Table.AddColumn(Typed, "TaskKey", each [ChecklistID] & "|" & Text.From([TaskNo]), type text)
in
    AddKey
```

18 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`TaskNo`, `MeasuredValue`

---

### `Fact_Breakdowns`

Unplanned stoppages. Feeds MTBF, MTTR and availability.

```m
let
    Source = fnSource("Breakdown_Reports"),
    Typed = Table.TransformColumnTypes(Source, {{"BreakdownID", type text}, {"MachineID", type text}, {"MachineName", type text}, {"CellID", type text}, {"CellName", type text}, {"Area", type text}, {"MachineType", type text}, {"Criticality", type text}, {"ReportedDateTime", type datetime}, {"RestoredDateTime", type datetime}, {"DowntimeMinutes", Int64.Type}, {"ResponseMinutes", Int64.Type}, {"FailureMode", type text}, {"FailureCategory", type text}, {"RootCause", type text}, {"ActionTaken", type text}, {"ReportedBy", type text}, {"AttendedTechID", type text}, {"AttendedTechName", type text}, {"Status", type text}, {"SpareUsed", type text}, {"Severity", type text}}, "en-US"),
    AddDate = Table.AddColumn(Typed, "ReportedDate", each Date.From([ReportedDateTime]), type date),
    AddHrs = Table.AddColumn(AddDate, "DowntimeHours", each if [DowntimeMinutes] = null then null else [DowntimeMinutes] / 60, type number)
in
    AddHrs
```

24 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`DowntimeMinutes`, `ResponseMinutes`, `DowntimeHours`

---

### `Fact_SpareRequests`

Spare part requests raised from the machine QR.

```m
let
    Source = fnSource("SparePart_Requests"),
    Typed = Table.TransformColumnTypes(Source, {{"RequestID", type text}, {"SourceType", type text}, {"SourceID", type text}, {"MachineID", type text}, {"MachineName", type text}, {"CellID", type text}, {"PartNo", type text}, {"PartName", type text}, {"Category", type text}, {"UOM", type text}, {"QtyRequested", Int64.Type}, {"UnitCostINR", type number}, {"TotalCostINR", type number}, {"RequestedByTechID", type text}, {"RequestedByName", type text}, {"RequestDate", type date}, {"Urgency", type text}, {"Status", type text}, {"ApprovedDate", type date}, {"ApprovedBy", type text}, {"IssuedDate", type date}, {"LeadTimeDays", Int64.Type}, {"StoreBin", type text}, {"RejectionReason", type text}}, "en-US")
in
    Typed
```

24 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`QtyRequested`, `UnitCostINR`, `TotalCostINR`, `LeadTimeDays`

---

### `Fact_SpareReplacements`

What was actually fitted to the machine.

```m
let
    Source = fnSource("SparePart_Replacements"),
    Typed = Table.TransformColumnTypes(Source, {{"ReplacementID", type text}, {"SourceType", type text}, {"SourceID", type text}, {"RequestID", type text}, {"MachineID", type text}, {"MachineName", type text}, {"CellID", type text}, {"MachineType", type text}, {"PartNo", type text}, {"PartName", type text}, {"Category", type text}, {"UOM", type text}, {"QtyReplaced", Int64.Type}, {"UnitCostINR", type number}, {"TotalCostINR", type number}, {"ReplacedByTechID", type text}, {"ReplacedByName", type text}, {"ReplacedDate", type date}, {"OldPartCondition", type text}, {"WarrantyClaim", type text}, {"Remarks", type text}}, "en-US")
in
    Typed
```

21 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

Set **Summarization: Don't summarize** on these numeric columns so nobody drags a raw sum into a visual by accident — the measures do the aggregating:

`QtyReplaced`, `UnitCostINR`, `TotalCostINR`

---

### `Fact_Abnormalities`

Abnormalities - the early warning layer before a breakdown.

```m
let
    Source = fnSource("Abnormality_Log"),
    Typed = Table.TransformColumnTypes(Source, {{"AbnormalityID", type text}, {"Source", type text}, {"SourceRefID", type text}, {"MachineID", type text}, {"MachineName", type text}, {"CellID", type text}, {"CellName", type text}, {"Area", type text}, {"Category", type text}, {"Severity", type text}, {"Description", type text}, {"ReportedByTechID", type text}, {"ReportedByName", type text}, {"ReportedDate", type date}, {"Status", type text}, {"ClosedDate", type date}, {"CorrectiveAction", type text}, {"OwnerFunction", type text}, {"EscalationRequired", type text}, {"PhotoURL", type text}}, "en-US")
in
    Typed
```

20 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

---

### `Fact_ScanLog`

Every QR scan. Proves attendance at the machine.

```m
let
    Source = fnSource("QR_Scan_Log"),
    Typed = Table.TransformColumnTypes(Source, {{"ScanID", type text}, {"QRType", type text}, {"MachineID", type text}, {"MachineName", type text}, {"TechID", type text}, {"TechName", type text}, {"ScanDateTime", type datetime}, {"LinkedWOID", type text}, {"Action", type text}, {"CellID", type text}}, "en-US"),
    AddDate = Table.AddColumn(Typed, "ScanDate", each Date.From([ScanDateTime]), type date)
in
    AddDate
```

11 columns. Types are set by the query itself, so there is nothing to change in the ribbon.

---

## Step 4 · Relationships

**Model view ▸ Manage relationships ▸ New**. Create all 28 exactly as listed. Cardinality is **Many to one (\*:1)** and cross-filter direction is **Single** on every one of them.

Drag from the *From* column to the *To* column — the direction matters.

| # | From (many) | To (one) | Active |
|---|-------------|----------|--------|
| 1 | `Dim_Machine[CellID]` | `Dim_Cell[CellID]` | Yes |
| 2 | `Fact_StdHours[CellID]` | `Dim_Cell[CellID]` | Yes |
| 3 | `Fact_StdHours[MonthStartDate]` | `Dim_Date[Date]` | Yes |
| 4 | `Fact_HourLedger[CellID]` | `Dim_Cell[CellID]` | Yes |
| 5 | `Fact_HourLedger[MonthStartDate]` | `Dim_Date[Date]` | Yes |
| 6 | `Fact_WorkOrders[MachineID]` | `Dim_Machine[MachineID]` | Yes |
| 7 | `Fact_WorkOrders[AssignedTechID]` | `Dim_Technician[TechID]` | Yes |
| 8 | `Fact_WorkOrders[PlannedDate]` | `Dim_Date[Date]` | Yes |
| 9 | `Fact_WorkOrders[ActualEndDate]` | `Dim_Date[Date]` | **No** — untick Active |
| 10 | `Fact_WorkOrders[DueDate]` | `Dim_Date[Date]` | **No** — untick Active |
| 11 | `Fact_ChecklistResults[WOID]` | `Fact_WorkOrders[WOID]` | Yes |
| 12 | `Fact_ChecklistResults[TaskKey]` | `Dim_Checklist[TaskKey]` | Yes |
| 13 | `Fact_Breakdowns[MachineID]` | `Dim_Machine[MachineID]` | Yes |
| 14 | `Fact_Breakdowns[AttendedTechID]` | `Dim_Technician[TechID]` | **No** — untick Active |
| 15 | `Fact_Breakdowns[ReportedDate]` | `Dim_Date[Date]` | Yes |
| 16 | `Fact_SpareRequests[MachineID]` | `Dim_Machine[MachineID]` | Yes |
| 17 | `Fact_SpareRequests[PartNo]` | `Dim_SparePart[PartNo]` | Yes |
| 18 | `Fact_SpareRequests[RequestDate]` | `Dim_Date[Date]` | Yes |
| 19 | `Fact_SpareRequests[RequestedByTechID]` | `Dim_Technician[TechID]` | **No** — untick Active |
| 20 | `Fact_SpareReplacements[MachineID]` | `Dim_Machine[MachineID]` | Yes |
| 21 | `Fact_SpareReplacements[PartNo]` | `Dim_SparePart[PartNo]` | Yes |
| 22 | `Fact_SpareReplacements[ReplacedDate]` | `Dim_Date[Date]` | Yes |
| 23 | `Fact_Abnormalities[MachineID]` | `Dim_Machine[MachineID]` | Yes |
| 24 | `Fact_Abnormalities[ReportedByTechID]` | `Dim_Technician[TechID]` | Yes |
| 25 | `Fact_Abnormalities[ReportedDate]` | `Dim_Date[Date]` | Yes |
| 26 | `Fact_ScanLog[MachineID]` | `Dim_Machine[MachineID]` | Yes |
| 27 | `Fact_ScanLog[TechID]` | `Dim_Technician[TechID]` | Yes |
| 28 | `Fact_ScanLog[ScanDate]` | `Dim_Date[Date]` | Yes |

The three inactive ones are alternate date roles on the work order table. They exist so a measure can use `USERELATIONSHIP` to analyse by completion date or due date without needing a second date table. Power BI will refuse to make them active — that is correct, leave them unticked.

> If a relationship will not create, the usual cause is the *To* column not being unique. Check for blank rows in the dimension — a single blank key will block it.

---

## Step 5 · The measures table

1. **Home ▸ Enter data**. Leave the single column and row as they are, name the table `_Measures`, **Load**.
2. In the Data pane, expand `_Measures`, right-click the `Column1` column ▸ **Hide**.
3. Create every measure from `08-dax-measure-library.md`. For each one: select `_Measures` ▸ **Modeling ▸ New measure** ▸ paste the DAX.
4. Set its **Format** and its **Display folder** from the same document.

There are 94 measures in 10 folders. Work through one folder at a time — later folders reference measures from earlier ones, so in order they will all resolve as you go.

| Folder | Measures |
|--------|---------:|
| 00 Context | 4 |
| 01 Standard Hours | 19 |
| 02 PM Execution | 18 |
| 03 Checklist Quality | 8 |
| 04 Reliability | 12 |
| 05 Spare Parts | 11 |
| 06 Abnormalities | 7 |
| 07 Technician | 7 |
| 08 Data Quality | 5 |
| 09 Titles | 3 |

> Measure names contain spaces and `%` signs. Type them exactly — the report build guide references them by name.

---

## Step 6 · Check the model before building visuals

In **Model view**, confirm:

- 17 tables, `Config` and `_Measures` hidden
- 28 relationships, 4 of them inactive (dashed lines)
- `Dim_Date` marked as a date table
- No relationship between `Fact_ChecklistResults` and `Dim_Machine` or `Dim_Date` directly — it hangs off `Fact_WorkOrders`, and adding those would create ambiguous filter paths that Power BI will reject

Then drop a card on a page with `[PM Compliance %]` and one with `[Std Hours]`. If both show a number, the model works and you can move on to `13-report-build-guide.md`.
