// ===========================================================================
// Dim_Cell  <- Cell_Master
// ---------------------------------------------------------------------------
// The heart of the model. One row per production cell, carrying the running
// 4,000-hour counter that triggers PM.
//
// Cum_Std_Hours_Since_PM is a SNAPSHOT, not a history. It is whatever the
// counter reads at refresh time. That matters for how it is aggregated: summing
// it across cells is meaningful (total hours currently banked), but summing it
// across time is not, because there is no time in it. The measures treat it
// accordingly - see "Cum Std Hours" in dax/measures.dax.
// ===========================================================================
let
    Source = fnGetTable("Cell_Master", "01_PM_Master_Data.xlsx", "Cell_Master"),

    Keys = fnCleanKeys(Source, {"Cell_ID", "Last_PM_WO_No"}),
    Bools = fnYesNo(Keys, {"Active"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Cell_ID",                   type text},
        {"Cell_Name",                 type text},
        {"Plant",                     type text},
        {"Process_Area",              type text},
        {"Machine_Count",             Int64.Type},
        {"PM_Trigger_Hours",          Int64.Type},
        {"Calendar_Backstop_Months",  Int64.Type},
        {"Cum_Std_Hours_Since_PM",    type number},
        {"Last_PM_Date",              type date},
        {"Last_PM_WO_No",             type text},
        {"Next_PM_Due_Date_Calendar", type date},
        {"Avg_Monthly_Std_Hours_L3M", type number},
        {"Owner_Supervisor",          type text},
        {"Criticality",               type text},
        {"Active",                    type logical}
    }),

    // Trim text that is displayed rather than joined on. A trailing space in a
    // cell name is harmless until it appears twice in a slicer.
    Trimmed = Table.TransformColumns(Typed, {
        {"Cell_Name",        each if _ = null then null else Text.Trim(_), type nullable text},
        {"Process_Area",     each if _ = null then null else Text.Trim(_), type nullable text},
        {"Owner_Supervisor", each if _ = null then null else Text.Trim(_), type nullable text},
        {"Criticality",      each if _ = null then null else Text.Upper(Text.Trim(_)), type nullable text}
    }),

    // Derived here rather than in DAX because it is a property of the cell, not
    // of a filter context: the calendar clock does not care what is on screen.
    WithBackstop = Table.AddColumn(
        Trimmed, "Calendar_Due_Date",
        each if [Last_PM_Date] = null or [Calendar_Backstop_Months] = null then null
             else Date.AddMonths([Last_PM_Date], [Calendar_Backstop_Months]),
        type nullable date),

    // The amber line. Held per cell so a retuned PM_Trigger_Hours moves its own
    // warning threshold with it, rather than leaving a stale 3,600 behind.
    WithAmber = Table.AddColumn(
        WithBackstop, "Amber_Threshold_Hours",
        each if [PM_Trigger_Hours] = null then null else [PM_Trigger_Hours] * 0.9,
        type nullable number),

    // A sort key so slicers and axes read A, B, C rather than alphabetically by
    // whatever label the choice happens to carry.
    WithSort = Table.AddColumn(
        WithAmber, "Criticality_Sort",
        each if [Criticality] = "A" then 1 else if [Criticality] = "B" then 2 else 3,
        Int64.Type),

    Final = Table.SelectRows(WithSort, each [Cell_ID] <> null)
in
    Final
