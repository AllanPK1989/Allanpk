// ===========================================================================
// Fact_SpareReplaced  <- Spare_Replaced
// ---------------------------------------------------------------------------
// Parts actually fitted.
//
// Unit_Cost_INR is copied from the master at the time of use, not looked up at
// report time, so a price rise does not retrospectively rewrite last year's
// maintenance cost. That is why this fact carries its own cost column rather
// than relying on Dim_Spare.
//
// Failure_Mode is the most valuable column in the table. Repeated
// "Contamination" on the same part is a filtration problem, not a spares
// problem, and no amount of buying more parts will fix it.
// ===========================================================================
let
    Source = fnGetTable("Spare_Replaced", "03_PM_Transactions_Dummy.xlsx", "Spare_Replaced"),

    Keys = fnCleanKeys(Source, {"Repl_ID", "Source_Ref", "Machine_ID",
                                "Cell_ID", "Spare_Code", "Replaced_By"}),
    Bools = fnYesNo(Keys, {"Warranty_Claim"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Repl_ID",             type text},
        {"Replaced_DateTime",   type datetime},
        {"Source_Type",         type text},
        {"Source_Ref",          type text},
        {"Machine_ID",          type text},
        {"Cell_ID",             type text},
        {"Spare_Code",          type text},
        {"Spare_Description",   type text},
        {"Qty_Used",            Int64.Type},
        {"Unit_Cost_INR",       type number},
        {"Total_Cost_INR",      type number},
        {"Old_Part_Condition",  type text},
        {"Failure_Mode",        type text},
        {"Replaced_By",         type text},
        {"Expected_Life_Hours", Int64.Type},
        {"Warranty_Claim",      type logical},
        {"Remarks",             type text}
    }),

    WithDate = Table.AddColumn(
        Typed, "Replaced_Date",
        each if [Replaced_DateTime] = null then null else DateTime.Date([Replaced_DateTime]),
        type nullable date),

    // Integrity rule 5 recomputed in the model. If the source ever disagrees
    // with itself, this column is what surfaces it, rather than the cost total
    // being quietly wrong on a page nobody cross-checks.
    WithCheck = Table.AddColumn(
        WithDate, "Cost_Integrity_OK",
        each if [Qty_Used] = null or [Unit_Cost_INR] = null or [Total_Cost_INR] = null then null
             else Number.Abs([Qty_Used] * [Unit_Cost_INR] - [Total_Cost_INR]) < 0.01,
        type nullable logical),

    WithPlanned = Table.AddColumn(
        WithCheck, "Is_Planned_Spend",
        each [Source_Type] = "PM",
        type logical),

    Final = Table.SelectRows(WithPlanned, each [Repl_ID] <> null)
in
    Final
