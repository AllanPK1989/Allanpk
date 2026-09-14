// ===========================================================================
// Fact_WorkOrder  <- PM_WorkOrder
// ---------------------------------------------------------------------------
// One row per cell PM.
//
// Date relationships: WO_Created_Date is the ACTIVE join to Dim_Date, because
// it is the one date every work order has. Planned_End_Date and Actual_End_Date
// get INACTIVE relationships, exposed through USERELATIONSHIP measures. That is
// what lets a single month slicer answer both "what did we plan for March" and
// "what did we finish in March" without two copies of the fact table.
// ===========================================================================
let
    Source = fnGetTable("PM_WorkOrder", "03_PM_Transactions_Dummy.xlsx", "PM_WorkOrder"),

    Keys = fnCleanKeys(Source, {"WO_No", "Cell_ID"}),
    Bools = fnYesNo(Keys, {"Reset_Applied"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"WO_No",                     type text},
        {"Cell_ID",                   type text},
        {"Trigger_Type",              type text},
        {"Trigger_Hours_At_Creation", type number},
        {"WO_Created_Date",           type date},
        {"Planned_Month",             type text},
        {"Planned_End_Date",          type date},
        {"Priority",                  type text},
        {"Machines_In_Scope",         Int64.Type},
        {"Machines_Completed",        Int64.Type},
        {"WO_Status",                 type text},
        {"Reset_Applied",             type logical},
        {"Remarks",                   type text}
    }),

    // --- actual dates, rolled up from the machine tasks -------------------
    // Flow 5 used to stamp Actual_Start_Date, Actual_End_Date and PM_Duration_Min
    // onto the work order. They are not independent facts: the work order started
    // when its first machine was scanned in and finished when its last was scanned
    // out. Deriving them here means the flow has three fewer fields to set, and the
    // dates cannot contradict the tasks they came from.
    TaskRollup = Table.Group(
        Table.SelectRows(Fact_MachineTask, each [WO_No] <> null),
        {"WO_No"},
        {
            {"Actual_Start_Date", each List.Min([Scan_Start_Time]), type nullable datetime},
            {"Actual_End_Date",   each List.Max([Scan_End_Time]),   type nullable datetime},
            {"PM_Duration_Min",   each List.Sum([Duration_Min]),    type nullable number}
        }),

    Merged = Table.NestedJoin(Typed, {"WO_No"}, TaskRollup, {"WO_No"},
                              "_tasks", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(
        Merged, "_tasks",
        {"Actual_Start_Date", "Actual_End_Date", "PM_Duration_Min"}),

    // The relationship to Dim_Date needs a date, not a datetime - a datetime joins
    // only to the rows that fall exactly at midnight, which is almost none of them.
    Dated = Table.TransformColumns(Expanded, {
        {"Actual_Start_Date", each if _ = null then null else DateTime.Date(_), type nullable date},
        {"Actual_End_Date",   each if _ = null then null else DateTime.Date(_), type nullable date}
    }),

    // Delay in days against the commitment. Negative means early. Computed here
    // rather than in DAX because it is a property of the row: a work order that
    // finished four days late finished four days late regardless of filter.
    WithDelay = Table.AddColumn(
        Dated, "Delay_Days",
        each if [Actual_End_Date] = null or [Planned_End_Date] = null then null
             else Duration.Days([Actual_End_Date] - [Planned_End_Date]),
        Int64.Type),

    WithOnTime = Table.AddColumn(
        WithDelay, "Is_On_Time",
        each if [Actual_End_Date] = null or [Planned_End_Date] = null then null
             else [Actual_End_Date] <= [Planned_End_Date],
        type nullable logical),

    // Overshoot past the trigger. Consistently seeing +300 hours means the
    // monthly upload granularity is too coarse for a 4,000-hour interval - the
    // cell crosses the line mid-month and nothing notices until month end.
    WithOvershoot = Table.AddColumn(
        WithOnTime, "Trigger_Overshoot_Hours",
        each if [Trigger_Hours_At_Creation] = null then null
             else [Trigger_Hours_At_Creation] - 4000,
        type nullable number),

    WithCompletion = Table.AddColumn(
        WithOvershoot, "Completion_Ratio",
        each if [Machines_In_Scope] = null or [Machines_In_Scope] = 0 then null
             else [Machines_Completed] / [Machines_In_Scope],
        type nullable number),

    Final = Table.SelectRows(WithCompletion, each [WO_No] <> null)
in
    Final
