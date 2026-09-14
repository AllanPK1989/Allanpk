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

    Keys = fnCleanKeys(Source, {"Repl_ID", "Source_Ref", "Machine_ID", "Cell_ID", "Spare_Code", "Replaced_By"}),
    Bools = fnYesNo(Keys, {"Warranty_Claim"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Repl_ID",             type text},
        {"Replaced_DateTime",   type datetime},
        {"Source_Type",         type text},
        {"Source_Ref",          type text},
        {"Machine_ID",          type text},
        {"Cell_ID",             type text},
        {"Spare_Code",          type text},
        {"Qty_Used",            Int64.Type},
        {"Unit_Cost_INR",       type number},
        {"Failure_Mode",        type text},
        {"Replaced_By",         type text},
        {"Warranty_Claim",      type logical}
    }),

    // Qty x unit cost, computed rather than stored. Integrity rule 5 existed only
    // because the total was written to the row and could disagree with its own
    // inputs; computing it removes the rule and the class of defect together.
    WithCost = Table.AddColumn(
        Typed, "Total_Cost_INR",
        each if [Qty_Used] = null or [Unit_Cost_INR] = null then null
             else [Qty_Used] * [Unit_Cost_INR],
        type nullable number),

    WithDate = Table.AddColumn(
        WithCost, "Replaced_Date",
        each if [Replaced_DateTime] = null then null else DateTime.Date([Replaced_DateTime]),
        type nullable date),

    WithPlanned = Table.AddColumn(
        WithDate, "Is_Planned_Spend",
        each [Source_Type] = "PM",
        type logical),

    Final = Table.SelectRows(WithPlanned, each [Repl_ID] <> null)
in
    Final
