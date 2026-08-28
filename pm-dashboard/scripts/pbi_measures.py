"""
pbi_measures.py - the full DAX measure library, in one place.

Each entry: (name, folder, formatString, dax, description)
build_pbip.py writes these into the _Measures table in TMDL, and
docs/08-dax-measure-library.md is generated from the same list.
"""

OK, WARN, BAD, NEUTRAL = "#2F9E7E", "#D08B2C", "#C4553B", "#7B93A3"

PCT = "0.0%"
PCT0 = "0%"
N0 = "#,0"
N1 = "#,0.0"
INR = '"₹"#,0;("₹"#,0);"₹"#,0'
TXT = None

MEASURES = [

# ===========================================================================
# 00 Config & context
# ===========================================================================
("Data As Of", "00 Context", "yyyy-mm-dd", """
CALCULATE ( MAX ( Dim_Date[Date] ), Dim_Date[RelativeToToday] IN { "Past", "Today" }, ALL ( Dim_Date ) )
""", "Latest calendar date in the model. Use it on every page footer."),

("Latest Std Hours Month", "00 Context", TXT, """
VAR LastM =
    CALCULATE ( MAX ( Fact_StdHours[MonthStartDate] ), ALL ( Dim_Date ), ALL ( Dim_Cell ) )
RETURN
    IF ( ISBLANK ( LastM ), "No upload yet", FORMAT ( LastM, "MMM yyyy" ) )
""", "The most recent month for which Production has uploaded standard hours."),

("Cfg PM Interval Std Hrs", "00 Context", N0, """
VAR Raw = LOOKUPVALUE ( Config[ConfigValue], Config[ConfigKey], "DefaultPMIntervalStdHrs" )
RETURN
    IF ( ISBLANK ( Raw ), 4000, VALUE ( Raw ) )
""", "Default hour threshold read from PM_Config, so the rule can be retuned without editing the model."),

("Cfg Due Soon Pct", "00 Context", PCT0, """
VAR Raw = LOOKUPVALUE ( Config[ConfigValue], Config[ConfigKey], "PMDueSoonThresholdPct" )
RETURN
    DIVIDE ( IF ( ISBLANK ( Raw ), 85, VALUE ( Raw ) ), 100 )
""", "Counter percentage at which a cell starts showing as Due Soon."),

# ===========================================================================
# 01 Standard hours & the PM counter
# ===========================================================================
("Std Hours", "01 Standard Hours", N0, """
SUM ( Fact_StdHours[StdHours] )
""", "Production standard hours earned, from the monthly upload."),

("Std Hours PM", "01 Standard Hours", N0, """
CALCULATE ( [Std Hours], DATEADD ( Dim_Date[Date], -1, MONTH ) )
""", "Standard hours in the previous month."),

("Std Hours MoM %", "01 Standard Hours", PCT, """
DIVIDE ( [Std Hours] - [Std Hours PM], [Std Hours PM] )
""", "Month-on-month movement in standard hours."),

("Std Hours 12M", "01 Standard Hours", N0, """
CALCULATE ( [Std Hours], DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -12, MONTH ) )
""", "Rolling twelve-month standard hours."),

("Latest Ledger Month", "01 Standard Hours", "yyyy-mm-dd", """
CALCULATE (
    MAX ( Fact_HourLedger[MonthStartDate] ),
    Fact_HourLedger[Scenario] = "Actual",
    ALL ( Dim_Date )
)
""", "Last month for which the hour ledger holds actual (not forecast) data."),

("Current Counter Std Hrs", "01 Standard Hours", N0, """
VAR LastM = [Latest Ledger Month]
RETURN
    CALCULATE (
        SUM ( Fact_HourLedger[ClosingStdHrs] ),
        Fact_HourLedger[MonthStartDate] = LastM,
        Fact_HourLedger[Scenario] = "Actual",
        ALL ( Dim_Date )
    )
""", "Where the cell's hour counter stands right now, after the latest upload."),

("PM Threshold Std Hrs", "01 Standard Hours", N0, """
SUMX ( VALUES ( Dim_Cell[CellID] ), CALCULATE ( MAX ( Dim_Cell[PMIntervalStdHrs] ) ) )
""", "The hour threshold for the cells in context. Sums correctly across a multi-cell selection."),

("Hours to Next PM", "01 Standard Hours", N0, """
MAX ( 0, [PM Threshold Std Hrs] - [Current Counter Std Hrs] )
""", "Standard hours still to be earned before the next PM falls due."),

("% to PM Threshold", "01 Standard Hours", PCT, """
DIVIDE ( [Current Counter Std Hrs], [PM Threshold Std Hrs] )
""", "Counter as a percentage of the threshold. The headline gauge on the planning page."),

("% to PM Threshold Color", "01 Standard Hours", TXT, f"""
VAR P = [% to PM Threshold]
RETURN
    SWITCH (
        TRUE (),
        P >= 1, "{BAD}",
        P >= [Cfg Due Soon Pct], "{WARN}",
        "{OK}"
    )
""", "Conditional colour for the counter gauge: over threshold, due soon, or comfortable."),

("Run Rate 3M Std Hrs", "01 Standard Hours", N0, """
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
""", "Trailing three-month average standard hours. The run rate used for every projection."),

("Months to PM Projected", "01 Standard Hours", N0, """
VAR Rate = [Run Rate 3M Std Hrs]
RETURN
    IF ( Rate <= 0, BLANK (), ROUNDUP ( DIVIDE ( [Hours to Next PM], Rate ), 0 ) )
""", "How many months at the current run rate before the hour threshold is reached."),

("Last PM Date", "01 Standard Hours", "yyyy-mm-dd", """
CALCULATE (
    MAX ( Fact_WorkOrders[ActualEndDate] ),
    Fact_WorkOrders[Status] = "Completed",
    ALL ( Dim_Date )
)
""", "Most recent completed PM in the current context - cell, machine or technician."),

("Months Since Last PM", "01 Standard Hours", N0, """
VAR L = [Last PM Date]
RETURN
    IF ( ISBLANK ( L ), BLANK (), DATEDIFF ( L, TODAY (), MONTH ) )
""", "Elapsed months since the last completed PM. Drives the calendar backstop."),

("Backstop Months Remaining", "01 Standard Hours", N0, """
VAR Limit = MAX ( Dim_Cell[CalendarBackstopMonths] )
VAR Elapsed = [Months Since Last PM]
RETURN
    IF ( ISBLANK ( Elapsed ), BLANK (), MAX ( 0, Limit - Elapsed ) )
""", "Months left before the calendar backstop forces a PM regardless of hours."),

("Projected Next PM Date", "01 Standard Hours", "yyyy-mm-dd", """
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
""", "The earlier of the hour projection and the calendar backstop. This is the date the plan works to."),

("Projected Trigger Reason", "01 Standard Hours", TXT, """
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
""", "Why the next PM will fire - useful when a low-utilisation cell is riding the backstop."),

("Cells Due In Period", "01 Standard Hours", N0, """
CALCULATE (
    DISTINCTCOUNT ( Fact_HourLedger[CellID] ),
    Fact_HourLedger[PMTriggered] = "Yes"
)
""", "Cells whose counter tripped inside the selected period."),

("Cells Due Next 3 Months", "01 Standard Hours", N0, """
VAR LastM = [Latest Ledger Month]
RETURN
    CALCULATE (
        DISTINCTCOUNT ( Fact_HourLedger[CellID] ),
        ALL ( Dim_Date ),
        Fact_HourLedger[PMTriggered] = "Yes",
        Fact_HourLedger[MonthStartDate] > LastM,
        Fact_HourLedger[MonthStartDate] <= EDATE ( LastM, 3 )
    )
""", "Forward look: how many cells fall due in the next quarter. The manpower planning number."),

# ===========================================================================
# 02 PM execution
# ===========================================================================
("PM Work Orders", "02 PM Execution", N0, """
COUNTROWS ( Fact_WorkOrders )
""", "Total PM work orders in context."),

("PM Completed", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Completed" )
""", "Work orders finished."),

("PM Scheduled", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Scheduled" )
""", "Work orders raised but not yet started."),

("PM In Progress", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "In Progress" )
""", "Work orders a technician has started but not closed."),

("PM Overdue", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Overdue" )
""", "Past due date and still not complete."),

("PM Deferred", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[Status] = "Deferred" )
""", "Formally pushed to a later window with approval."),

("PM Open", "02 PM Execution", N0, """
CALCULATE (
    [PM Work Orders],
    Fact_WorkOrders[Status] IN { "Scheduled", "In Progress", "Overdue" }
)
""", "Everything still to be done."),

("PM Completion %", "02 PM Execution", PCT, """
DIVIDE ( [PM Completed], [PM Work Orders] )
""", "Share of raised work orders that are complete."),

("PM Due To Date", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[DueDate] <= TODAY () )
""", "Work orders whose due date has already passed - the fair denominator for compliance."),

("PM On Time", "02 PM Execution", N0, """
CALCULATE ( [PM Work Orders], Fact_WorkOrders[OnTimeFlag] = "Yes" )
""", "Completed on or before the due date."),

("PM Compliance %", "02 PM Execution", PCT, """
DIVIDE ( [PM On Time], [PM Due To Date] )
""", "The headline KPI: of everything that fell due, how much was done on time."),

("PM Compliance % Color", "02 PM Execution", TXT, f"""
VAR P = [PM Compliance %]
RETURN
    SWITCH ( TRUE (), ISBLANK ( P ), "{NEUTRAL}", P >= 0.95, "{OK}", P >= 0.85, "{WARN}", "{BAD}" )
""", "Green at or above 95%, amber to 85%, red below."),

("PM Schedule Slip Days", "02 PM Execution", N1, """
AVERAGEX (
    FILTER ( Fact_WorkOrders, NOT ISBLANK ( Fact_WorkOrders[ActualEndDate] ) ),
    DATEDIFF ( Fact_WorkOrders[DueDate], Fact_WorkOrders[ActualEndDate], DAY )
)
""", "Average days between due date and actual completion. Negative is early."),

("Open WO Ageing Days", "02 PM Execution", N1, """
AVERAGEX (
    FILTER (
        Fact_WorkOrders,
        Fact_WorkOrders[Status] IN { "Scheduled", "In Progress", "Overdue" }
            && Fact_WorkOrders[DueDate] < TODAY ()
    ),
    DATEDIFF ( Fact_WorkOrders[DueDate], TODAY (), DAY )
)
""", "How long overdue work has been sitting, on average."),

("PM Wrench Hours", "02 PM Execution", N1, """
DIVIDE ( SUM ( Fact_WorkOrders[DurationMin] ), 60 )
""", "Actual hands-on maintenance hours recorded against PM work orders."),

("PM Planned Hours", "02 PM Execution", N1, """
DIVIDE ( SUM ( Fact_WorkOrders[StdMinutes] ), 60 )
""", "Planned hours from the machine master. The capacity planning figure."),

("PM Duration vs Std %", "02 PM Execution", PCT, """
DIVIDE ( SUM ( Fact_WorkOrders[DurationMin] ), SUM ( Fact_WorkOrders[StdMinutes] ) )
""", "Actual against standard time. Persistently over 130% means the standard is wrong or the job has grown."),

("Avg PM Duration Min", "02 PM Execution", N0, """
AVERAGE ( Fact_WorkOrders[DurationMin] )
""", "Average minutes per completed PM."),

# ===========================================================================
# 03 Checklist quality
# ===========================================================================
("Checklist Tasks", "03 Checklist Quality", N0, """
COUNTROWS ( Fact_ChecklistResults )
""", "Checklist lines recorded."),

("Checklist Tasks Not OK", "03 Checklist Quality", N0, """
CALCULATE ( [Checklist Tasks], Fact_ChecklistResults[Result] = "Not OK" )
""", "Lines that failed their acceptance standard."),

("Checklist Fail Rate %", "03 Checklist Quality", PCT, """
DIVIDE ( [Checklist Tasks Not OK], [Checklist Tasks] )
""", "Share of checklist lines failing. A rising rate is a real reliability signal, not noise."),

("Safety Critical Fails", "03 Checklist Quality", N0, """
CALCULATE (
    [Checklist Tasks Not OK],
    Dim_Checklist[SafetyCritical] = "Yes"
)
""", "Failed lines on safety-critical tasks. This number should be reviewed every week, without exception."),

("Checklist Completion %", "03 Checklist Quality", PCT, """
DIVIDE (
    SUM ( Fact_WorkOrders[ChecklistDoneTasks] ),
    SUM ( Fact_WorkOrders[ChecklistTotalTasks] )
)
""", "How much of the checklist actually got answered across the work orders in context."),

("QR Verified Completions", "03 Checklist Quality", N0, """
CALCULATE ( [PM Completed], Fact_WorkOrders[MachineQRScanned] = "Yes" )
""", "Completed work orders that have a machine QR scan against them."),

("QR Verification %", "03 Checklist Quality", PCT, """
DIVIDE ( [QR Verified Completions], [PM Completed] )
""", "Proof of attendance. Should sit at 100%; anything less needs a conversation."),

("Desk Closed WOs", "03 Checklist Quality", N0, """
[PM Completed] - [QR Verified Completions]
""", "Work orders closed without anyone scanning the machine. Investigate every one."),

# ===========================================================================
# 04 Reliability
# ===========================================================================
("Breakdowns", "04 Reliability", N0, """
COUNTROWS ( Fact_Breakdowns )
""", "Unplanned stoppages reported."),

("Open Breakdowns", "04 Reliability", N0, """
CALCULATE ( [Breakdowns], Fact_Breakdowns[Status] <> "Closed" )
""", "Still not restored or still waiting on a spare."),

("Downtime Hours", "04 Reliability", N1, """
DIVIDE ( SUM ( Fact_Breakdowns[DowntimeMinutes] ), 60 )
""", "Total unplanned downtime."),

("MTTR Hours", "04 Reliability", N1, """
DIVIDE (
    SUM ( Fact_Breakdowns[DowntimeMinutes] ),
    CALCULATE ( [Breakdowns], NOT ISBLANK ( Fact_Breakdowns[DowntimeMinutes] ) ) * 60
)
""", "Mean time to repair - average hours from stoppage to restoration."),

("Avg Response Min", "04 Reliability", N0, """
AVERAGE ( Fact_Breakdowns[ResponseMinutes] )
""", "Average minutes from the call to a technician arriving."),

("Operating Hours Allocated", "04 Reliability", N0, """
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
""", "Cell standard hours spread evenly across the machines in the cell, so MTBF works at machine level. It is an allocation, not a meter reading - say so on the page."),

("MTBF Hours", "04 Reliability", N0, """
DIVIDE ( [Operating Hours Allocated], [Breakdowns] )
""", "Mean operating hours between failures."),

("Availability %", "04 Reliability", PCT, """
VAR Op = [Operating Hours Allocated]
RETURN
    IF ( Op = 0, BLANK (), DIVIDE ( Op - [Downtime Hours], Op ) )
""", "Operating hours less unplanned downtime, over operating hours."),

("Availability % Color", "04 Reliability", TXT, f"""
VAR A = [Availability %]
RETURN
    SWITCH ( TRUE (), ISBLANK ( A ), "{NEUTRAL}", A >= 0.97, "{OK}", A >= 0.93, "{WARN}", "{BAD}" )
""", "Green at or above 97%, amber to 93%, red below."),

("Repeat Failure Count", "04 Reliability", N0, """
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
""", "Machine and failure-mode pairs seen more than once. Each one is a root cause that was never closed out."),

("Breakdowns Within 15d of PM", "04 Reliability", N0, """
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
""", "Failures within a fortnight of a PM. This is the sharpest available measure of PM quality - a high number means the PM is being signed off, not done."),

("PM Induced Failure %", "04 Reliability", PCT, """
DIVIDE ( [Breakdowns Within 15d of PM], [Breakdowns] )
""", "Share of failures that follow closely on a PM."),

# ===========================================================================
# 05 Spare parts
# ===========================================================================
("Spare Requests", "05 Spare Parts", N0, """
COUNTROWS ( Fact_SpareRequests )
""", "Requests raised."),

("Spare Request Value", "05 Spare Parts", INR, """
SUM ( Fact_SpareRequests[TotalCostINR] )
""", "Value of everything requested."),

("Spares Issued Value", "05 Spare Parts", INR, """
CALCULATE ( [Spare Request Value], Fact_SpareRequests[Status] = "Issued" )
""", "Value actually issued from stores."),

("Pending Approvals", "05 Spare Parts", N0, """
CALCULATE ( [Spare Requests], Fact_SpareRequests[Status] = "Pending Approval" )
""", "Requests waiting on somebody's decision."),

("Avg Approval TAT Days", "05 Spare Parts", N1, """
AVERAGEX (
    FILTER ( Fact_SpareRequests, NOT ISBLANK ( Fact_SpareRequests[ApprovedDate] ) ),
    DATEDIFF ( Fact_SpareRequests[RequestDate], Fact_SpareRequests[ApprovedDate], DAY )
)
""", "Average days from request to approval."),

("Emergency Request %", "05 Spare Parts", PCT, """
DIVIDE (
    CALCULATE ( [Spare Requests], Fact_SpareRequests[Urgency] = "Emergency" ),
    [Spare Requests]
)
""", "Share of requests raised as emergencies. A high figure means planning is losing to firefighting."),

("Spares Replaced Qty", "05 Spare Parts", N0, """
SUM ( Fact_SpareReplacements[QtyReplaced] )
""", "Quantity actually fitted."),

("Spare Consumption Value", "05 Spare Parts", INR, """
SUM ( Fact_SpareReplacements[TotalCostINR] )
""", "Value of parts actually consumed - not the same as requested, and the gap is worth watching."),

("Spend per Std Hour", "05 Spare Parts", INR, """
DIVIDE ( [Spare Consumption Value], [Std Hours] )
""", "Maintenance material cost per production standard hour. The unit-cost trend to hold flat."),

("Parts Below Min Stock", "05 Spare Parts", N0, """
COUNTROWS ( FILTER ( Dim_SparePart, Dim_SparePart[CurrentStock] < Dim_SparePart[MinStock] ) )
""", "Catalogue lines under their reorder level as at the last stock upload."),

("Stock Value", "05 Spare Parts", INR, """
SUMX ( Dim_SparePart, Dim_SparePart[CurrentStock] * Dim_SparePart[UnitCostINR] )
""", "Value sitting in the store."),

# ===========================================================================
# 06 Abnormalities
# ===========================================================================
("Abnormalities", "06 Abnormalities", N0, """
COUNTROWS ( Fact_Abnormalities )
""", "Abnormalities logged."),

("Open Abnormalities", "06 Abnormalities", N0, """
CALCULATE ( [Abnormalities], Fact_Abnormalities[Status] <> "Closed" )
""", "Still open."),

("High Severity Open", "06 Abnormalities", N0, """
CALCULATE (
    [Abnormalities],
    Fact_Abnormalities[Status] <> "Closed",
    Fact_Abnormalities[Severity] = "High"
)
""", "Open and rated High. This is the escalation list."),

("Abnormality Closure %", "06 Abnormalities", PCT, """
DIVIDE (
    CALCULATE ( [Abnormalities], Fact_Abnormalities[Status] = "Closed" ),
    [Abnormalities]
)
""", "Share closed out."),

("Avg Abnormality Closure Days", "06 Abnormalities", N1, """
AVERAGEX (
    FILTER ( Fact_Abnormalities, NOT ISBLANK ( Fact_Abnormalities[ClosedDate] ) ),
    DATEDIFF ( Fact_Abnormalities[ReportedDate], Fact_Abnormalities[ClosedDate], DAY )
)
""", "Average days from report to closure."),

("Abnormalities Open Over 30d", "06 Abnormalities", N0, """
COUNTROWS (
    FILTER (
        Fact_Abnormalities,
        Fact_Abnormalities[Status] <> "Closed"
            && DATEDIFF ( Fact_Abnormalities[ReportedDate], TODAY (), DAY ) > 30
    )
)
""", "Open beyond thirty days. These are the ones that turn into breakdowns."),

("Open Abnormality Color", "06 Abnormalities", TXT, f"""
VAR H = [High Severity Open]
VAR A = [Abnormalities Open Over 30d]
RETURN
    SWITCH ( TRUE (), H > 0, "{BAD}", A > 0, "{WARN}", "{OK}" )
""", "Red if anything High is open, amber if anything has aged past thirty days."),

# ===========================================================================
# 07 Technician
# ===========================================================================
("Technicians Active", "07 Technician", N0, """
CALCULATE ( DISTINCTCOUNT ( Dim_Technician[TechID] ), Dim_Technician[Active] = "Yes" )
""", "Headcount available for assignment."),

("Technician Capacity Hours", "07 Technician", N1, """
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
""", "Available wrench hours in the selected period, from daily capacity times working days."),

("Technician Utilisation %", "07 Technician", PCT, """
DIVIDE ( [PM Wrench Hours], [Technician Capacity Hours] )
""", "PM hours against available hours. Anything above about 70% leaves no room for breakdowns."),

("WOs per Technician", "07 Technician", N1, """
DIVIDE ( [PM Work Orders], DISTINCTCOUNT ( Fact_WorkOrders[AssignedTechID] ) )
""", "Average work order load per person - the load balancing view."),

("QR Scans", "07 Technician", N0, """
COUNTROWS ( Fact_ScanLog )
""", "Total QR scans."),

("Machine Scans", "07 Technician", N0, """
CALCULATE ( [QR Scans], Fact_ScanLog[QRType] = "Machine QR" )
""", "Scans at a machine."),

("Machines Touched", "07 Technician", N0, """
CALCULATE ( DISTINCTCOUNT ( Fact_ScanLog[MachineID] ), Fact_ScanLog[QRType] = "Machine QR" )
""", "Distinct machines scanned - shop floor coverage."),

# ===========================================================================
# 08 Data quality
# ===========================================================================
("Expected Std Hours Rows", "08 Data Quality", N0, """
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
""", "How many cell-month rows the upload should contain for the selected period."),

("Missing Std Hours Rows", "08 Data Quality", N0, """
MAX ( 0, [Expected Std Hours Rows] - COUNTROWS ( Fact_StdHours ) )
""", "Gaps in the monthly upload. Anything above zero means a cell is not accruing hours and will never be scheduled."),

("WOs Without Checklist", "08 Data Quality", N0, """
COUNTROWS (
    FILTER (
        Fact_WorkOrders,
        Fact_WorkOrders[Status] = "Completed"
            && ISBLANK ( CALCULATE ( COUNTROWS ( Fact_ChecklistResults ) ) )
    )
)
""", "Completed work orders with no checklist evidence behind them."),

("Data Quality Issues", "08 Data Quality", N0, """
[Missing Std Hours Rows] + [Desk Closed WOs] + [WOs Without Checklist]
""", "One number for the health of the inputs. It should be zero."),

("Data Quality Color", "08 Data Quality", TXT, f"""
VAR I = [Data Quality Issues]
RETURN
    SWITCH ( TRUE (), I = 0, "{OK}", I <= 5, "{WARN}", "{BAD}" )
""", "Green only at zero."),

# ===========================================================================
# 09 Dynamic titles
# ===========================================================================
("Title Planning", "09 Titles", TXT, """
"PM planning as at " & [Latest Std Hours Month]
    & "  |  " & [Cells Due Next 3 Months] & " cell(s) fall due in the next 3 months"
""", "Dynamic subtitle for the planning page."),

("Title Compliance", "09 Titles", TXT, """
VAR P = [PM Compliance %]
RETURN
    "PM compliance " & FORMAT ( P, "0.0%" )
        & "  |  " & [PM Overdue] & " overdue, " & [PM Open] & " open"
""", "Dynamic subtitle for the execution page."),

("Machine Header", "09 Titles", TXT, """
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
""", "Header for the Machine 360 page - the same line the QR scan shows on the phone."),
]
