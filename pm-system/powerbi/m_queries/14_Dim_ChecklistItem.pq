// ===========================================================================
// Dim_ChecklistItem  <- Checklist_Master
// ---------------------------------------------------------------------------
// The 51 check points across 9 checklist sets.
//
// Grain note: a checklist response is identified by Checklist_ID AND Item_No,
// not by Item_No alone. Item 1 of CL-PRESS and item 1 of CL-OVEN are different
// checks. The composite key below is what makes the relationship to
// Fact_ChecklistResponse one-to-many instead of many-to-many.
// ===========================================================================
let
    Source = fnGetTable("Checklist_Master", "01_PM_Master_Data.xlsx", "Checklist_Master"),

    Keys = fnCleanKeys(Source, {"Checklist_ID"}),
    Bools = fnYesNo(Keys, {"Safety_Critical", "Active"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Checklist_ID",        type text},
        {"Checklist_Name",      type text},
        {"Item_No",             Int64.Type},
        {"Check_Point",         type text},
        {"Check_Type",          type text},
        {"Acceptance_Standard", type text},
        {"Tool_Required",       type text},
        {"Frequency",           type text},
        {"Safety_Critical",     type logical},
        {"Expected_Time_Min",   Int64.Type},
        {"Active",              type logical}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Check_Point", each if _ = null then null else Text.Trim(_), type nullable text},
        {"Check_Type",  each if _ = null then null else Text.Trim(_), type nullable text}
    }),

    // Composite key. Built here so the relationship is a single column join -
    // Power BI has no composite relationships, and the alternative is a
    // bidirectional many-to-many that will quietly wreck the filter direction.
    WithKey = Table.AddColumn(
        Trimmed, "Checklist_Item_Key",
        each Text.From([Checklist_ID]) & "|" & Text.From([Item_No]),
        type text),

    // Used on the findings Pareto, where the full check point text is too long
    // for an axis label but the item number alone is meaningless.
    WithShort = Table.AddColumn(
        WithKey, "Check_Point_Short",
        each if [Check_Point] = null then null
             else if Text.Length([Check_Point]) <= 42 then [Check_Point]
             else Text.Start([Check_Point], 39) & "...",
        type nullable text),

    Final = Table.SelectRows(WithShort, each [Checklist_ID] <> null and [Item_No] <> null)
in
    Final
