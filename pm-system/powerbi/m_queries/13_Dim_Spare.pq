// ===========================================================================
// Dim_Spare  <- Spare_Master
// ---------------------------------------------------------------------------
// Current_Stock is a snapshot maintained by Flow 8, not a history, so it is only
// meaningful at the row level.
//
// ABC_Class and FMR_Class were dropped: a stored classification has to be reviewed
// and re-entered as usage changes, and nobody ever does. The spares page ranks by
// actual cost and actual movement instead, which is the same judgement made from
// evidence that updates itself.
// ===========================================================================
let
    Source = fnGetTable("Spare_Master", "01_PM_Master_Data.xlsx", "Spare_Master"),

    Keys = fnCleanKeys(Source, {"Spare_Code"}),
    Bools = fnYesNo(Keys, {"Active"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Spare_Code",        type text},
        {"Spare_Description", type text},
        {"Category",          type text},
        {"UOM",               type text},
        {"Unit_Cost_INR",     type number},
        {"Min_Stock",         Int64.Type},
        {"Current_Stock",     Int64.Type},
        {"Lead_Time_Days",    Int64.Type},
        {"Bin_Location",      type text},
        {"Active",            type logical}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Spare_Description", each if _ = null then null else Text.Trim(_), type nullable text},
        {"Category",          each if _ = null then null else Text.Trim(_), type nullable text}
    }),

    WithBelowMin = Table.AddColumn(
        Trimmed, "Below_Min_Stock",
        each [Current_Stock] <> null and [Min_Stock] <> null and [Current_Stock] <= [Min_Stock],
        type logical),

    // A part one unit below minimum with a 30-day lead time is a different
    // problem from one with a 3-day lead time. This is the column that separates
    // them, and it is what the stock-out risk table sorts on.
    WithRisk = Table.AddColumn(
        WithBelowMin, "Stockout_Risk_Score",
        each if [Current_Stock] = null or [Min_Stock] = null or [Lead_Time_Days] = null then null
             else (if [Min_Stock] = 0 then 0 else (1 - Number.Min([Current_Stock] / [Min_Stock], 1)))
                  * [Lead_Time_Days],
        type nullable number),

    Final = Table.SelectRows(WithRisk, each [Spare_Code] <> null)
in
    Final
