// ===========================================================================
// Fact_PlanCalendar  <- PM_Plan_Calendar
// ---------------------------------------------------------------------------
// The frozen monthly plan.
//
// Without this table you can measure "did we do it" but never "did we do it
// when we said we would". Adherence is measured against Planned_Date here, not
// against PM_WorkOrder.Planned_End_Date, because a work order's planned date can
// be edited after the fact and a frozen plan row cannot.
//
// Plan_Version "V1 Forecast" rows are projections beyond the frozen month. They
// are excluded from adherence - scoring yourself against a forecast you have not
// committed to is how adherence percentages become fiction.
// ===========================================================================
let
    Source = fnGetTable("PM_Plan_Calendar", "03_PM_Transactions_Dummy.xlsx", "PM_Plan_Calendar"),

    Keys = fnCleanKeys(Source, {"Plan_ID", "Cell_ID", "Planned_Tech_ID", "WO_No"}),

    Typed = Table.TransformColumnTypes(Keys, {
        {"Plan_ID",                type text},
        {"Plan_Month",             type text},
        {"Cell_ID",                type text},
        {"Cell_Name",              type text},
        {"Planned_Date",           type date},
        {"Planned_Shift",          type text},
        {"Planned_Tech_ID",        type text},
        {"Estimated_Duration_Hrs", type number},
        {"Plan_Version",           type text},
        {"Frozen_Date",            type date},
        {"WO_No",                  type text},
        {"Adherence_Status",       type text}
    }),

    WithMonthDate = Table.AddColumn(
        Typed, "Plan_Month_Date",
        each if [Plan_Month] = null or Text.Length([Plan_Month]) < 7 then null
             else #date(Number.FromText(Text.Start([Plan_Month], 4)),
                        Number.FromText(Text.Middle([Plan_Month], 5, 2)), 1),
        type nullable date),

    // The adherence denominator. A forecast row is a projection, not a promise.
    WithCommitted = Table.AddColumn(
        WithMonthDate, "Is_Committed_Plan",
        each [Plan_Version] <> null
             and not Text.Contains([Plan_Version], "Forecast")
             and [Adherence_Status] <> "Forecast",
        type logical),

    WithOnTime = Table.AddColumn(
        WithCommitted, "Is_On_Time",
        each [Adherence_Status] = "On Time",
        type logical),

    Final = Table.SelectRows(WithOnTime, each [Plan_ID] <> null)
in
    Final
