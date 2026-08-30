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

    Keys = fnCleanKeys(Source, {"WO_No", "Cell_ID", "Lead_Tech_ID"}),
    Bools = fnYesNo(Keys, {"Reset_Applied"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"WO_No",                     type text},
        {"Cell_ID",                   type text},
        {"Cell_Name",                 type text},
        {"Trigger_Type",              type text},
        {"Trigger_Hours_At_Creation", type number},
        {"WO_Created_Date",           type date},
        {"Planned_Month",             type text},
        {"Planned_Start_Date",        type date},
        {"Planned_End_Date",          type date},
        {"Lead_Tech_ID",              type text},
        {"Priority",                  type text},
        {"Machines_In_Scope",         Int64.Type},
        {"Machines_Completed",        Int64.Type},
        {"WO_Status",                 type text},
        {"Actual_Start_Date",         type date},
        {"Actual_End_Date",           type date},
        {"PM_Duration_Min",           Int64.Type},
        {"Reset_Applied",             type logical},
        {"Reset_Date",                type date},
        {"Remarks",                   type text}
    }),

    // Delay in days against the commitment. Negative means early. Computed here
    // rather than in DAX because it is a property of the row: a work order that
    // finished four days late finished four days late regardless of filter.
    WithDelay = Table.AddColumn(
        Typed, "Delay_Days",
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
