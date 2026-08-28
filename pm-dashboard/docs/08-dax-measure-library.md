# 08 · DAX Measure Library

94 measures, all on the `_Measures` table, organised into 10 display folders.

> Generated from `scripts/pbi_measures.py` by `scripts/build_measure_docs.py`. Edit the Python file, not this one, then re-run both that script and `scripts/build_pbip.py`.

## Contents

- [00 Context](#00-context) — 4 measures
- [01 Standard Hours](#01-standard-hours) — 19 measures
- [02 PM Execution](#02-pm-execution) — 18 measures
- [03 Checklist Quality](#03-checklist-quality) — 8 measures
- [04 Reliability](#04-reliability) — 12 measures
- [05 Spare Parts](#05-spare-parts) — 11 measures
- [06 Abnormalities](#06-abnormalities) — 7 measures
- [07 Technician](#07-technician) — 7 measures
- [08 Data Quality](#08-data-quality) — 5 measures
- [09 Titles](#09-titles) — 3 measures

## 00 Context

| Measure | Format | What it means |
|---------|--------|---------------|
| `Data As Of` | `yyyy-mm-dd` | Latest calendar date in the model. Use it on every page footer. |
| `Latest Std Hours Month` | `text` | The most recent month for which Production has uploaded standard hours. |
| `Cfg PM Interval Std Hrs` | `#,0` | Default hour threshold read from PM_Config, so the rule can be retuned without editing the model. |
| `Cfg Due Soon Pct` | `0%` | Counter percentage at which a cell starts showing as Due Soon. |

### Data As Of

Latest calendar date in the model. Use it on every page footer.

```dax
Data As Of =
CALCULATE ( MAX ( Dim_Date[Date] ), Dim_Date[RelativeToToday] IN { "Past", "Today" }, ALL ( Dim_Date ) )
```

### Latest Std Hours Month

The most recent month for which Production has uploaded standard hours.

```dax
Latest Std Hours Month =
VAR LastM =
    CALCULATE ( MAX ( Fact_StdHours[MonthStartDate] ), ALL ( Dim_Date ), ALL ( Dim_Cell ) )
RETURN
    IF ( ISBLANK ( LastM ), "No upload yet", FORMAT ( LastM, "MMM yyyy" ) )
```

### Cfg PM Interval Std Hrs

Default hour threshold read from PM_Config, so the rule can be retuned without editing the model.

```dax
Cfg PM Interval Std Hrs =
VAR Raw = LOOKUPVALUE ( Config[ConfigValue], Config[ConfigKey], "DefaultPMIntervalStdHrs" )
RETURN
    IF ( ISBLANK ( Raw ), 4000, VALUE ( Raw ) )
```

### Cfg Due Soon Pct

Counter percentage at which a cell starts showing as Due Soon.

```dax
Cfg Due Soon Pct =
VAR Raw = LOOKUPVALUE ( Config[ConfigValue], Config[ConfigKey], "PMDueSoonThresholdPct" )
RETURN
    DIVIDE ( IF ( ISBLANK ( Raw ), 85, VALUE ( Raw ) ), 100 )
```

## 01 Standard Hours

| Measure | Format | What it means |
|---------|--------|---------------|
| `Std Hours` | `#,0` | Production standard hours earned, from the monthly upload. |
| `Std Hours PM` | `#,0` | Standard hours in the previous month. |
| `Std Hours MoM %` | `0.0%` | Month-on-month movement in standard hours. |
| `Std Hours 12M` | `#,0` | Rolling twelve-month standard hours. |
| `Latest Ledger Month` | `yyyy-mm-dd` | Last month for which the hour ledger holds actual (not forecast) data. |
| `Current Counter Std Hrs` | `#,0` | Where the cell's hour counter stands right now, after the latest upload. |
| `PM Threshold Std Hrs` | `#,0` | The hour threshold for the cells in context. Sums correctly across a multi-cell selection. |
| `Hours to Next PM` | `#,0` | Standard hours still to be earned before the next PM falls due. |
| `% to PM Threshold` | `0.0%` | Counter as a percentage of the threshold. The headline gauge on the planning page. |
| `% to PM Threshold Color` | `text` | Conditional colour for the counter gauge: over threshold, due soon, or comfortable. |
| `Run Rate 3M Std Hrs` | `#,0` | Trailing three-month average standard hours. The run rate used for every projection. |
| `Months to PM Projected` | `#,0` | How many months at the current run rate before the hour threshold is reached. |
| `Last PM Date` | `yyyy-mm-dd` | Most recent completed PM in the current context - cell, machine or technician. |
| `Months Since Last PM` | `#,0` | Elapsed months since the last completed PM. Drives the calendar backstop. |
| `Backstop Months Remaining` | `#,0` | Months left before the calendar backstop forces a PM regardless of hours. |
| `Projected Next PM Date` | `yyyy-mm-dd` | The earlier of the hour projection and the calendar backstop. This is the date the plan works to. |
| `Projected Trigger Reason` | `text` | Why the next PM will fire - useful when a low-utilisation cell is riding the backstop. |
| `Cells Due In Period` | `#,0` | Cells whose counter tripped inside the selected period. |
| `Cells Due Next 3 Months` | `#,0` | Forward look: how many cells fall due in the next quarter. The manpower planning number. |

### Std Hours

Production standard hours earned, from the monthly upload.

```dax
Std Hours =
SUM ( Fact_StdHours[StdHours] )
```

### Std Hours PM

Standard hours in the previous month.

```dax
Std Hours PM =
CALCULATE ( [Std Hours], DATEADD ( Dim_Date[Date], -1, MONTH ) )
```

### Std Hours MoM %

Month-on-month movement in standard hours.

```dax
Std Hours MoM % =
DIVIDE ( [Std Hours] - [Std Hours PM], [Std Hours PM] )
```

### Std Hours 12M

Rolling twelve-month standard hours.

```dax
Std Hours 12M =
CALCULATE ( [Std Hours], DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -12, MONTH ) )
```

### Latest Ledger Month

Last month for which the hour ledger holds actual (not forecast) data.

```dax
Latest Ledger Month =
CALCULATE (
    MAX ( Fact_HourLedger[MonthStartDate] ),
    Fact_HourLedger[Scenario] = "Actual",
    ALL ( Dim_Date )
)
```

### Current Counter Std Hrs

Where the cell's hour counter stands right now, after the latest upload.

```dax
Current Counter Std Hrs =
VAR LastM = [Latest Ledger Month]
RETURN
    CALCULATE (
        SUM ( Fact_HourLedger[ClosingStdHrs] ),
        Fact_HourLedger[MonthStartDate] = LastM,
        Fact_HourLedger[Scenario] = "Actual",
        ALL ( Dim_Date )
    )
```

### PM Threshold Std Hrs

The hour threshold for the cells in context. Sums correctly across a multi-cell selection.

```dax
PM Threshold Std Hrs =
SUMX ( VALUES ( Dim_Cell[CellID] ), CALCULATE ( MAX ( Dim_Cell[PMIntervalStdHrs] ) ) )
```

### Hours to Next PM

Standard hours still to be earned before the next PM falls due.

```dax
Hours to Next PM =
MAX ( 0, [PM Threshold Std Hrs] - [Current Counter Std Hrs] )
```

### % to PM Threshold

Counter as a percentage of the threshold. The headline gauge on the planning page.

```dax
% to PM Threshold =
DIVIDE ( [Current Counter Std Hrs], [PM Threshold Std Hrs] )
```

### % to PM Threshold Color

Conditional colour for the counter gauge: over threshold, due soon, or comfortable.

```dax
% to PM Threshold Color =
VAR P = [% to PM Threshold]
RETURN
    SWITCH (
        TRUE (),
        P >= 1, "#C4553B",
        P >= [Cfg Due Soon Pct], "#D08B2C",
        "#2F9E7E"
    )
```

### Run Rate 3M Std Hrs

Trailing three-month average standard hours. The run rate used for every projection.

```dax
Run Rate 3M Std Hrs =
VAR LastM = [Latest Ledger Month]
VAR Total =
    CALCULATE (
        SUM ( Fact_StdHours[StdHours] ),
        ALL ( Dim_Date ),
        Fact_StdHours[MonthStartDate] <= LastM,
        Fact_StdHours[MonthStartDate] > EDATE ( LastM, -3 )
    )
RETURN
    DIVIDE ( Total, 3 )
```

### Months to PM Projected

How many months at the current run rate before the hour threshold is reached.

```dax
Months to PM Projected =
VAR Rate = [Run Rate 3M Std Hrs]
RETURN
    IF ( Rate <= 0, BLANK (), ROUNDUP ( DIVIDE ( [Hours to Next PM], Rate ), 0 ) )
```

### Last PM Date

Most recent completed PM in the current context - cell, machine or technician.

```dax
Last PM Date =
CALCULATE (
    MAX ( Fact_WorkOrders[ActualEndDate] ),
    Fact_WorkOrders[Status] = "Completed",
    ALL ( Dim_Date )
)
```

### Months Since Last PM

Elapsed months since the last completed PM. Drives the calendar backstop.

```dax
Months Since Last PM =
VAR L = [Last PM Date]
RETURN
    IF ( ISBLANK ( L ), BLANK (), DATEDIFF ( L, TODAY (), MONTH ) )
```

### Backstop Months Remaining

Months left before the calendar backstop forces a PM regardless of hours.

```dax
Backstop Months Remaining =
VAR Limit = MAX ( Dim_Cell[CalendarBackstopMonths] )
VAR Elapsed = [Months Since Last PM]
RETURN
    IF ( ISBLANK ( Elapsed ), BLANK (), MAX ( 0, Limit - Elapsed ) )
```

### Projected Next PM Date

The earlier of the hour projection and the calendar backstop. This is the date the plan works to.

```dax
Projected Next PM Date =
VAR MonthsOut = [Months to PM Projected]
VAR LedgerM = [Latest Ledger Month]
VAR HoursDate = IF ( ISBLANK ( MonthsOut ), BLANK (), EOMONTH ( EDATE ( LedgerM, MonthsOut ), 0 ) )
VAR Backstop = MAX ( Dim_Cell[CalendarBackstopMonths] )
VAR LastPM = [Last PM Date]
VAR CalDate = IF ( ISBLANK ( LastPM ), BLANK (), EOMONTH ( EDATE ( LastPM, Backstop ), 0 ) )
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( HoursDate ), CalDate,
        ISBLANK ( CalDate ), HoursDate,
        MIN ( HoursDate, CalDate )
    )
```

### Projected Trigger Reason

Why the next PM will fire - useful when a low-utilisation cell is riding the backstop.

```dax
Projected Trigger Reason =
VAR MonthsOut = [Months to PM Projected]
VAR LedgerM = [Latest Ledger Month]
VAR HoursDate = IF ( ISBLANK ( MonthsOut ), BLANK (), EOMONTH ( EDATE ( LedgerM, MonthsOut ), 0 ) )
VAR Backstop = MAX ( Dim_Cell[CalendarBackstopMonths] )
VAR LastPM = [Last PM Date]
VAR CalDate = IF ( ISBLANK ( LastPM ), BLANK (), EOMONTH ( EDATE ( LastPM, Backstop ), 0 ) )
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( HoursDate ) && ISBLANK ( CalDate ), "No projection",
        ISBLANK ( HoursDate ), "Calendar backstop",
        ISBLANK ( CalDate ), "Std hours",
        HoursDate <= CalDate, "Std hours",
        "Calendar backstop"
    )
```

### Cells Due In Period

Cells whose counter tripped inside the selected period.

```dax
Cells Due In Period =
CALCULATE (
    DISTINCTCOUNT ( Fact_HourLedger[CellID] ),
    Fact_HourLedger[PMTriggered] = "Yes"
)
```

### Cells Due Next 3 Months

Forward look: how many cells fall due in the next quarter. The manpower planning number.

```dax
Cells Due Next 3 Months =
VAR LastM = [Latest Ledger Month]
RETURN
    CALCULATE (
        DISTINCTCOUNT ( Fact_HourLedger[CellID] ),
        ALL ( Dim_Date ),
        Fact_HourLedger[PMTriggered] = "Yes",
        Fact_HourLedger[MonthStartDate] > LastM,
        Fact_HourLedger[MonthStartDate] <= EDATE ( LastM, 3 )
    )
```

## 02 PM Execution

| Measure | Format | What it means |
|---------|--------|---------------|
| `PM Work Orders` | `#,0` | Total PM work orders in context. |
| `PM Completed` | `#,0` | Work orders finished. |
| `PM Scheduled` | `#,0` | Work orders raised but not yet started. |
| `PM In Progress` | `#,0` | Work orders a technician has started but not closed. |
| `PM Overdue` | `#,0` | Past due date and still not complete. |
| `PM Deferred` | `#,0` | Formally pushed to a later window with approval. |
| `PM Open` | `#,0` | Everything still to be done. |
| `PM Completion %` | `0.0%` | Share of raised work orders that are complete. |
| `PM Due To Date` | `#,0` | Work orders whose due date has already passed - the fair denominator for compliance. |
| `PM On Time` | `#,0` | Completed on or before the due date. |
| `PM Compliance %` | `0.0%` | The headline KPI: of everything that fell due, how much was done on time. |
| `PM Compliance % Color` | `text` | Green at or above 95%, amber to 85%, red below. |
| `PM Schedule Slip Days` | `#,0.0` | Average days between due date and actual completion. Negative is early. |
| `Open WO Ageing Days` | `#,0.0` | How long overdue work has been sitting, on average. |
| `PM Wrench Hours` | `#,0.0` | Actual hands-on maintenance hours recorded against PM work orders. |
| `PM Planned Hours` | `#,0.0` | Planned hours from the machine master. The capacity planning figure. |
| `PM Duration vs Std %` | `0.0%` | Actual against standard time. Persistently over 130% means the standard is wrong or the job has grown. |
| `Avg PM Duration Min` | `#,0` | Average minutes per completed PM. |

### PM Work Orders

Total PM work orders in context.

```dax
PM Work Orders =
COUNTROWS ( Fact_WorkOrders )
```

### PM Completed

Work orders finished.

```dax
PM Completed =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Completed" )
```

### PM Scheduled

Work orders raised but not yet started.

```dax
PM Scheduled =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Scheduled" )
```

### PM In Progress

Work orders a technician has started but not closed.

```dax
PM In Progress =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "In Progress" )
```

### PM Overdue

Past due date and still not complete.

```dax
PM Overdue =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Overdue" )
```

### PM Deferred

Formally pushed to a later window with approval.

```dax
PM Deferred =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Deferred" )
```

### PM Open

Everything still to be done.

```dax
PM Open =
CALCULATE (
    [PM Work Orders],
    Fact_WorkOrders[Status] IN { "Scheduled", "In Progress", "Overdue" }
)
```

### PM Completion %

Share of raised work orders that are complete.

```dax
PM Completion % =
DIVIDE ( [PM Completed], [PM Work Orders] )
```

### PM Due To Date

Work orders whose due date has already passed - the fair denominator for compliance.

```dax
PM Due To Date =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[DueDate] <= TODAY () )
```

### PM On Time

Completed on or before the due date.

```dax
PM On Time =
CALCULATE ( [PM Work Orders], Fact_WorkOrders[OnTimeFlag] = "Yes" )
```

### PM Compliance %

The headline KPI: of everything that fell due, how much was done on time.

```dax
PM Compliance % =
DIVIDE ( [PM On Time], [PM Due To Date] )
```

### PM Compliance % Color

Green at or above 95%, amber to 85%, red below.

```dax
PM Compliance % Color =
VAR P = [PM Compliance %]
RETURN
    SWITCH ( TRUE (), ISBLANK ( P ), "#7B93A3", P >= 0.95, "#2F9E7E", P >= 0.85, "#D08B2C", "#C4553B" )
```

### PM Schedule Slip Days

Average days between due date and actual completion. Negative is early.

```dax
PM Schedule Slip Days =
AVERAGEX (
    FILTER ( Fact_WorkOrders, NOT ISBLANK ( Fact_WorkOrders[ActualEndDate] ) ),
    DATEDIFF ( Fact_WorkOrders[DueDate], Fact_WorkOrders[ActualEndDate], DAY )
)
```

### Open WO Ageing Days

How long overdue work has been sitting, on average.

```dax
Open WO Ageing Days =
AVERAGEX (
    FILTER (
        Fact_WorkOrders,
        Fact_WorkOrders[Status] IN { "Scheduled", "In Progress", "Overdue" }
            && Fact_WorkOrders[DueDate] < TODAY ()
    ),
    DATEDIFF ( Fact_WorkOrders[DueDate], TODAY (), DAY )
)
```

### PM Wrench Hours

Actual hands-on maintenance hours recorded against PM work orders.

```dax
PM Wrench Hours =
DIVIDE ( SUM ( Fact_WorkOrders[DurationMin] ), 60 )
```

### PM Planned Hours

Planned hours from the machine master. The capacity planning figure.

```dax
PM Planned Hours =
DIVIDE ( SUM ( Fact_WorkOrders[StdMinutes] ), 60 )
```

### PM Duration vs Std %

Actual against standard time. Persistently over 130% means the standard is wrong or the job has grown.

```dax
PM Duration vs Std % =
DIVIDE ( SUM ( Fact_WorkOrders[DurationMin] ), SUM ( Fact_WorkOrders[StdMinutes] ) )
```

### Avg PM Duration Min

Average minutes per completed PM.

```dax
Avg PM Duration Min =
AVERAGE ( Fact_WorkOrders[DurationMin] )
```

## 03 Checklist Quality

| Measure | Format | What it means |
|---------|--------|---------------|
| `Checklist Tasks` | `#,0` | Checklist lines recorded. |
| `Checklist Tasks Not OK` | `#,0` | Lines that failed their acceptance standard. |
| `Checklist Fail Rate %` | `0.0%` | Share of checklist lines failing. A rising rate is a real reliability signal, not noise. |
| `Safety Critical Fails` | `#,0` | Failed lines on safety-critical tasks. This number should be reviewed every week, without exception. |
| `Checklist Completion %` | `0.0%` | How much of the checklist actually got answered across the work orders in context. |
| `QR Verified Completions` | `#,0` | Completed work orders that have a machine QR scan against them. |
| `QR Verification %` | `0.0%` | Proof of attendance. Should sit at 100%; anything less needs a conversation. |
| `Desk Closed WOs` | `#,0` | Work orders closed without anyone scanning the machine. Investigate every one. |

### Checklist Tasks

Checklist lines recorded.

```dax
Checklist Tasks =
COUNTROWS ( Fact_ChecklistResults )
```

### Checklist Tasks Not OK

Lines that failed their acceptance standard.

```dax
Checklist Tasks Not OK =
CALCULATE ( [Checklist Tasks], Fact_ChecklistResults[Result] = "Not OK" )
```

### Checklist Fail Rate %

Share of checklist lines failing. A rising rate is a real reliability signal, not noise.

```dax
Checklist Fail Rate % =
DIVIDE ( [Checklist Tasks Not OK], [Checklist Tasks] )
```

### Safety Critical Fails

Failed lines on safety-critical tasks. This number should be reviewed every week, without exception.

```dax
Safety Critical Fails =
CALCULATE (
    [Checklist Tasks Not OK],
    Dim_Checklist[SafetyCritical] = "Yes"
)
```

### Checklist Completion %

How much of the checklist actually got answered across the work orders in context.

```dax
Checklist Completion % =
DIVIDE (
    SUM ( Fact_WorkOrders[ChecklistDoneTasks] ),
    SUM ( Fact_WorkOrders[ChecklistTotalTasks] )
)
```

### QR Verified Completions

Completed work orders that have a machine QR scan against them.

```dax
QR Verified Completions =
CALCULATE ( [PM Completed], Fact_WorkOrders[MachineQRScanned] = "Yes" )
```

### QR Verification %

Proof of attendance. Should sit at 100%; anything less needs a conversation.

```dax
QR Verification % =
DIVIDE ( [QR Verified Completions], [PM Completed] )
```

### Desk Closed WOs

Work orders closed without anyone scanning the machine. Investigate every one.

```dax
Desk Closed WOs =
[PM Completed] - [QR Verified Completions]
```

## 04 Reliability

| Measure | Format | What it means |
|---------|--------|---------------|
| `Breakdowns` | `#,0` | Unplanned stoppages reported. |
| `Open Breakdowns` | `#,0` | Still not restored or still waiting on a spare. |
| `Downtime Hours` | `#,0.0` | Total unplanned downtime. |
| `MTTR Hours` | `#,0.0` | Mean time to repair - average hours from stoppage to restoration. |
| `Avg Response Min` | `#,0` | Average minutes from the call to a technician arriving. |
| `Operating Hours Allocated` | `#,0` | Cell standard hours spread evenly across the machines in the cell, so MTBF works at machine level. It is an allocation, not a meter reading - say so on the page. |
| `MTBF Hours` | `#,0` | Mean operating hours between failures. |
| `Availability %` | `0.0%` | Operating hours less unplanned downtime, over operating hours. |
| `Availability % Color` | `text` | Green at or above 97%, amber to 93%, red below. |
| `Repeat Failure Count` | `#,0` | Machine and failure-mode pairs seen more than once. Each one is a root cause that was never closed out. |
| `Breakdowns Within 15d of PM` | `#,0` | Failures within a fortnight of a PM. This is the sharpest available measure of PM quality - a high number means the PM is being signed off, not done. |
| `PM Induced Failure %` | `0.0%` | Share of failures that follow closely on a PM. |

### Breakdowns

Unplanned stoppages reported.

```dax
Breakdowns =
COUNTROWS ( Fact_Breakdowns )
```

### Open Breakdowns

Still not restored or still waiting on a spare.

```dax
Open Breakdowns =
CALCULATE ( [Breakdowns], Fact_Breakdowns[Status] <> "Closed" )
```

### Downtime Hours

Total unplanned downtime.

```dax
Downtime Hours =
DIVIDE ( SUM ( Fact_Breakdowns[DowntimeMinutes] ), 60 )
```

### MTTR Hours

Mean time to repair - average hours from stoppage to restoration.

```dax
MTTR Hours =
DIVIDE (
    SUM ( Fact_Breakdowns[DowntimeMinutes] ),
    CALCULATE ( [Breakdowns], NOT ISBLANK ( Fact_Breakdowns[DowntimeMinutes] ) ) * 60
)
```

### Avg Response Min

Average minutes from the call to a technician arriving.

```dax
Avg Response Min =
AVERAGE ( Fact_Breakdowns[ResponseMinutes] )
```

### Operating Hours Allocated

Cell standard hours spread evenly across the machines in the cell, so MTBF works at machine level. It is an allocation, not a meter reading - say so on the page.

```dax
Operating Hours Allocated =
SUMX (
    VALUES ( Dim_Machine[MachineID] ),
    VAR TheCell = CALCULATE ( SELECTEDVALUE ( Dim_Machine[CellID] ) )
    VAR MachinesInCell =
        CALCULATE ( COUNTROWS ( Dim_Machine ), ALLEXCEPT ( Dim_Machine, Dim_Machine[CellID] ) )
    VAR CellHours =
        CALCULATE (
            SUM ( Fact_StdHours[StdHours] ),
            ALL ( Dim_Machine ),
            Fact_StdHours[CellID] = TheCell
        )
    RETURN
        DIVIDE ( CellHours, MachinesInCell )
)
```

### MTBF Hours

Mean operating hours between failures.

```dax
MTBF Hours =
DIVIDE ( [Operating Hours Allocated], [Breakdowns] )
```

### Availability %

Operating hours less unplanned downtime, over operating hours.

```dax
Availability % =
VAR Op = [Operating Hours Allocated]
RETURN
    IF ( Op = 0, BLANK (), DIVIDE ( Op - [Downtime Hours], Op ) )
```

### Availability % Color

Green at or above 97%, amber to 93%, red below.

```dax
Availability % Color =
VAR A = [Availability %]
RETURN
    SWITCH ( TRUE (), ISBLANK ( A ), "#7B93A3", A >= 0.97, "#2F9E7E", A >= 0.93, "#D08B2C", "#C4553B" )
```

### Repeat Failure Count

Machine and failure-mode pairs seen more than once. Each one is a root cause that was never closed out.

```dax
Repeat Failure Count =
COUNTROWS (
    FILTER (
        ADDCOLUMNS (
            SUMMARIZE (
                Fact_Breakdowns,
                Fact_Breakdowns[MachineID],
                Fact_Breakdowns[FailureMode]
            ),
            "@Cnt", CALCULATE ( COUNTROWS ( Fact_Breakdowns ) )
        ),
        [@Cnt] > 1
    )
)
```

### Breakdowns Within 15d of PM

Failures within a fortnight of a PM. This is the sharpest available measure of PM quality - a high number means the PM is being signed off, not done.

```dax
Breakdowns Within 15d of PM =
COUNTROWS (
    FILTER (
        Fact_Breakdowns,
        VAR M = Fact_Breakdowns[MachineID]
        VAR D = Fact_Breakdowns[ReportedDate]
        VAR LastPM =
            CALCULATE (
                MAX ( Fact_WorkOrders[ActualEndDate] ),
                ALL ( Fact_WorkOrders ),
                Fact_WorkOrders[MachineID] = M,
                Fact_WorkOrders[Status] = "Completed",
                Fact_WorkOrders[ActualEndDate] <= D
            )
        RETURN
            NOT ISBLANK ( LastPM ) && DATEDIFF ( LastPM, D, DAY ) <= 15
    )
)
```

### PM Induced Failure %

Share of failures that follow closely on a PM.

```dax
PM Induced Failure % =
DIVIDE ( [Breakdowns Within 15d of PM], [Breakdowns] )
```

## 05 Spare Parts

| Measure | Format | What it means |
|---------|--------|---------------|
| `Spare Requests` | `#,0` | Requests raised. |
| `Spare Request Value` | `"₹"#,0;("₹"#,0);"₹"#,0` | Value of everything requested. |
| `Spares Issued Value` | `"₹"#,0;("₹"#,0);"₹"#,0` | Value actually issued from stores. |
| `Pending Approvals` | `#,0` | Requests waiting on somebody's decision. |
| `Avg Approval TAT Days` | `#,0.0` | Average days from request to approval. |
| `Emergency Request %` | `0.0%` | Share of requests raised as emergencies. A high figure means planning is losing to firefighting. |
| `Spares Replaced Qty` | `#,0` | Quantity actually fitted. |
| `Spare Consumption Value` | `"₹"#,0;("₹"#,0);"₹"#,0` | Value of parts actually consumed - not the same as requested, and the gap is worth watching. |
| `Spend per Std Hour` | `"₹"#,0;("₹"#,0);"₹"#,0` | Maintenance material cost per production standard hour. The unit-cost trend to hold flat. |
| `Parts Below Min Stock` | `#,0` | Catalogue lines under their reorder level as at the last stock upload. |
| `Stock Value` | `"₹"#,0;("₹"#,0);"₹"#,0` | Value sitting in the store. |

### Spare Requests

Requests raised.

```dax
Spare Requests =
COUNTROWS ( Fact_SpareRequests )
```

### Spare Request Value

Value of everything requested.

```dax
Spare Request Value =
SUM ( Fact_SpareRequests[TotalCostINR] )
```

### Spares Issued Value

Value actually issued from stores.

```dax
Spares Issued Value =
CALCULATE ( [Spare Request Value], Fact_SpareRequests[Status] = "Issued" )
```

### Pending Approvals

Requests waiting on somebody's decision.

```dax
Pending Approvals =
CALCULATE ( [Spare Requests], Fact_SpareRequests[Status] = "Pending Approval" )
```

### Avg Approval TAT Days

Average days from request to approval.

```dax
Avg Approval TAT Days =
AVERAGEX (
    FILTER ( Fact_SpareRequests, NOT ISBLANK ( Fact_SpareRequests[ApprovedDate] ) ),
    DATEDIFF ( Fact_SpareRequests[RequestDate], Fact_SpareRequests[ApprovedDate], DAY )
)
```

### Emergency Request %

Share of requests raised as emergencies. A high figure means planning is losing to firefighting.

```dax
Emergency Request % =
DIVIDE (
    CALCULATE ( [Spare Requests], Fact_SpareRequests[Urgency] = "Emergency" ),
    [Spare Requests]
)
```

### Spares Replaced Qty

Quantity actually fitted.

```dax
Spares Replaced Qty =
SUM ( Fact_SpareReplacements[QtyReplaced] )
```

### Spare Consumption Value

Value of parts actually consumed - not the same as requested, and the gap is worth watching.

```dax
Spare Consumption Value =
SUM ( Fact_SpareReplacements[TotalCostINR] )
```

### Spend per Std Hour

Maintenance material cost per production standard hour. The unit-cost trend to hold flat.

```dax
Spend per Std Hour =
DIVIDE ( [Spare Consumption Value], [Std Hours] )
```

### Parts Below Min Stock

Catalogue lines under their reorder level as at the last stock upload.

```dax
Parts Below Min Stock =
COUNTROWS ( FILTER ( Dim_SparePart, Dim_SparePart[CurrentStock] < Dim_SparePart[MinStock] ) )
```

### Stock Value

Value sitting in the store.

```dax
Stock Value =
SUMX ( Dim_SparePart, Dim_SparePart[CurrentStock] * Dim_SparePart[UnitCostINR] )
```

## 06 Abnormalities

| Measure | Format | What it means |
|---------|--------|---------------|
| `Abnormalities` | `#,0` | Abnormalities logged. |
| `Open Abnormalities` | `#,0` | Still open. |
| `High Severity Open` | `#,0` | Open and rated High. This is the escalation list. |
| `Abnormality Closure %` | `0.0%` | Share closed out. |
| `Avg Abnormality Closure Days` | `#,0.0` | Average days from report to closure. |
| `Abnormalities Open Over 30d` | `#,0` | Open beyond thirty days. These are the ones that turn into breakdowns. |
| `Open Abnormality Color` | `text` | Red if anything High is open, amber if anything has aged past thirty days. |

### Abnormalities

Abnormalities logged.

```dax
Abnormalities =
COUNTROWS ( Fact_Abnormalities )
```

### Open Abnormalities

Still open.

```dax
Open Abnormalities =
CALCULATE ( [Abnormalities], Fact_Abnormalities[Status] <> "Closed" )
```

### High Severity Open

Open and rated High. This is the escalation list.

```dax
High Severity Open =
CALCULATE (
    [Abnormalities],
    Fact_Abnormalities[Status] <> "Closed",
    Fact_Abnormalities[Severity] = "High"
)
```

### Abnormality Closure %

Share closed out.

```dax
Abnormality Closure % =
DIVIDE (
    CALCULATE ( [Abnormalities], Fact_Abnormalities[Status] = "Closed" ),
    [Abnormalities]
)
```

### Avg Abnormality Closure Days

Average days from report to closure.

```dax
Avg Abnormality Closure Days =
AVERAGEX (
    FILTER ( Fact_Abnormalities, NOT ISBLANK ( Fact_Abnormalities[ClosedDate] ) ),
    DATEDIFF ( Fact_Abnormalities[ReportedDate], Fact_Abnormalities[ClosedDate], DAY )
)
```

### Abnormalities Open Over 30d

Open beyond thirty days. These are the ones that turn into breakdowns.

```dax
Abnormalities Open Over 30d =
COUNTROWS (
    FILTER (
        Fact_Abnormalities,
        Fact_Abnormalities[Status] <> "Closed"
            && DATEDIFF ( Fact_Abnormalities[ReportedDate], TODAY (), DAY ) > 30
    )
)
```

### Open Abnormality Color

Red if anything High is open, amber if anything has aged past thirty days.

```dax
Open Abnormality Color =
VAR H = [High Severity Open]
VAR A = [Abnormalities Open Over 30d]
RETURN
    SWITCH ( TRUE (), H > 0, "#C4553B", A > 0, "#D08B2C", "#2F9E7E" )
```

## 07 Technician

| Measure | Format | What it means |
|---------|--------|---------------|
| `Technicians Active` | `#,0` | Headcount available for assignment. |
| `Technician Capacity Hours` | `#,0.0` | Available wrench hours in the selected period, from daily capacity times working days. |
| `Technician Utilisation %` | `0.0%` | PM hours against available hours. Anything above about 70% leaves no room for breakdowns. |
| `WOs per Technician` | `#,0.0` | Average work order load per person - the load balancing view. |
| `QR Scans` | `#,0` | Total QR scans. |
| `Machine Scans` | `#,0` | Scans at a machine. |
| `Machines Touched` | `#,0` | Distinct machines scanned - shop floor coverage. |

### Technicians Active

Headcount available for assignment.

```dax
Technicians Active =
CALCULATE ( DISTINCTCOUNT ( Dim_Technician[TechID] ), Dim_Technician[Active] = "Yes" )
```

### Technician Capacity Hours

Available wrench hours in the selected period, from daily capacity times working days.

```dax
Technician Capacity Hours =
VAR WorkDays =
    CALCULATE (
        COUNTROWS ( Dim_Date ),
        Dim_Date[IsWeekend] = "No",
        Dim_Date[IsHoliday] = "No"
    )
VAR DailyMin =
    SUMX (
        VALUES ( Dim_Technician[TechID] ),
        CALCULATE ( MAX ( Dim_Technician[DailyCapacityMin] ) )
    )
RETURN
    DIVIDE ( DailyMin * WorkDays, 60 )
```

### Technician Utilisation %

PM hours against available hours. Anything above about 70% leaves no room for breakdowns.

```dax
Technician Utilisation % =
DIVIDE ( [PM Wrench Hours], [Technician Capacity Hours] )
```

### WOs per Technician

Average work order load per person - the load balancing view.

```dax
WOs per Technician =
DIVIDE ( [PM Work Orders], DISTINCTCOUNT ( Fact_WorkOrders[AssignedTechID] ) )
```

### QR Scans

Total QR scans.

```dax
QR Scans =
COUNTROWS ( Fact_ScanLog )
```

### Machine Scans

Scans at a machine.

```dax
Machine Scans =
CALCULATE ( [QR Scans], Fact_ScanLog[QRType] = "Machine QR" )
```

### Machines Touched

Distinct machines scanned - shop floor coverage.

```dax
Machines Touched =
CALCULATE ( DISTINCTCOUNT ( Fact_ScanLog[MachineID] ), Fact_ScanLog[QRType] = "Machine QR" )
```

## 08 Data Quality

| Measure | Format | What it means |
|---------|--------|---------------|
| `Expected Std Hours Rows` | `#,0` | How many cell-month rows the upload should contain for the selected period. |
| `Missing Std Hours Rows` | `#,0` | Gaps in the monthly upload. Anything above zero means a cell is not accruing hours and will never be scheduled. |
| `WOs Without Checklist` | `#,0` | Completed work orders with no checklist evidence behind them. |
| `Data Quality Issues` | `#,0` | One number for the health of the inputs. It should be zero. |
| `Data Quality Color` | `text` | Green only at zero. |

### Expected Std Hours Rows

How many cell-month rows the upload should contain for the selected period.

```dax
Expected Std Hours Rows =
VAR ActiveCells =
    CALCULATE ( DISTINCTCOUNT ( Dim_Cell[CellID] ), Dim_Cell[Active] = "Yes", ALL ( Dim_Date ) )
VAR FirstUpload =
    CALCULATE ( MIN ( Fact_StdHours[MonthStartDate] ), ALL ( Dim_Date ), ALL ( Dim_Cell ) )
VAR LastUpload =
    CALCULATE ( MAX ( Fact_StdHours[MonthStartDate] ), ALL ( Dim_Date ), ALL ( Dim_Cell ) )
VAR MonthsInScope =
    IF (
        ISBLANK ( FirstUpload ),
        0,
        CALCULATE (
            DISTINCTCOUNT ( Dim_Date[MonthKey] ),
            Dim_Date[Date] >= FirstUpload,
            Dim_Date[Date] <= EOMONTH ( LastUpload, 0 )
        )
    )
RETURN
    ActiveCells * MonthsInScope
```

### Missing Std Hours Rows

Gaps in the monthly upload. Anything above zero means a cell is not accruing hours and will never be scheduled.

```dax
Missing Std Hours Rows =
MAX ( 0, [Expected Std Hours Rows] - COUNTROWS ( Fact_StdHours ) )
```

### WOs Without Checklist

Completed work orders with no checklist evidence behind them.

```dax
WOs Without Checklist =
COUNTROWS (
    FILTER (
        Fact_WorkOrders,
        Fact_WorkOrders[Status] = "Completed"
            && ISBLANK ( CALCULATE ( COUNTROWS ( Fact_ChecklistResults ) ) )
    )
)
```

### Data Quality Issues

One number for the health of the inputs. It should be zero.

```dax
Data Quality Issues =
[Missing Std Hours Rows] + [Desk Closed WOs] + [WOs Without Checklist]
```

### Data Quality Color

Green only at zero.

```dax
Data Quality Color =
VAR I = [Data Quality Issues]
RETURN
    SWITCH ( TRUE (), I = 0, "#2F9E7E", I <= 5, "#D08B2C", "#C4553B" )
```

## 09 Titles

| Measure | Format | What it means |
|---------|--------|---------------|
| `Title Planning` | `text` | Dynamic subtitle for the planning page. |
| `Title Compliance` | `text` | Dynamic subtitle for the execution page. |
| `Machine Header` | `text` | Header for the Machine 360 page - the same line the QR scan shows on the phone. |

### Title Planning

Dynamic subtitle for the planning page.

```dax
Title Planning =
"PM planning as at " & [Latest Std Hours Month]
    & "  |  " & [Cells Due Next 3 Months] & " cell(s) fall due in the next 3 months"
```

### Title Compliance

Dynamic subtitle for the execution page.

```dax
Title Compliance =
VAR P = [PM Compliance %]
RETURN
    "PM compliance " & FORMAT ( P, "0.0%" )
        & "  |  " & [PM Overdue] & " overdue, " & [PM Open] & " open"
```

### Machine Header

Header for the Machine 360 page - the same line the QR scan shows on the phone.

```dax
Machine Header =
VAR M = SELECTEDVALUE ( Dim_Machine[MachineName] )
VAR ID = SELECTEDVALUE ( Dim_Machine[MachineID] )
VAR L = [Last PM Date]
RETURN
    IF (
        ISBLANK ( M ),
        "Select a machine",
        M & "  (" & ID & ")   |   Last PM: "
            & IF ( ISBLANK ( L ), "never recorded", FORMAT ( L, "dd MMM yyyy" ) )
    )
```

