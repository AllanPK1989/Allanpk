// ===========================================================================
// Fact_ChecklistResponse  <- Checklist_Response
// ---------------------------------------------------------------------------
// One row per check point per machine per PM. The largest table in the model
// (about 1,000 rows on dummy data, roughly 25,000 a year in production) and the
// one that turns a checklist into condition monitoring.
//
// Measured_Value is the reason this table matters. A bearing running 48, 52,
// 57 degrees across three PMs is a failure you can see coming - but only if the
// reading is stored as a number, per check point, per machine, over time. That
// is exactly this grain.
// ===========================================================================
let
    Source = fnGetTable("Checklist_Response", "03_PM_Transactions_Dummy.xlsx", "Checklist_Response"),

    Keys = fnCleanKeys(Source, {"Response_ID", "WO_No", "Machine_ID", "Cell_ID",
                                "Checklist_ID", "Tech_ID", "Follow_Up_WO"}),
    Bools = fnYesNo(Keys, {"Follow_Up_Required"}),

    // Photo_Link is a hyperlink in SharePoint and text in Excel - flatten both.
    Flattened = Table.TransformColumns(
        Bools,
        List.Transform(
            List.Intersect({Table.ColumnNames(Bools), {"Photo_Link"}}),
            each {_, (v) => if v = null then null
                            else if v is record then Record.FieldOrDefault(v, "Url", null)
                            else Text.From(v),
                  type nullable text})),

    Typed = Table.TransformColumnTypes(Flattened, {
        {"Response_ID",        type text},
        {"Submitted_DateTime", type datetime},
        {"WO_No",              type text},
        {"Machine_ID",         type text},
        {"Cell_ID",            type text},
        {"Checklist_ID",       type text},
        {"Item_No",            Int64.Type},
        {"Check_Point",        type text},
        {"Result",             type text},
        {"Measured_Value",     type number},
        {"Observation",        type text},
        {"Photo_Link",         type text},
        {"Action_Taken",       type text},
        {"Tech_ID",            type text},
        {"Follow_Up_Required", type logical},
        {"Follow_Up_WO",       type text}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Result", each if _ = null then null else Text.Upper(Text.Trim(_)), type nullable text}
    }),

    // Matches Dim_ChecklistItem[Checklist_Item_Key]. Built the same way in both
    // queries; if you change one, change the other.
    WithKey = Table.AddColumn(
        Trimmed, "Checklist_Item_Key",
        each Text.From([Checklist_ID]) & "|" & Text.From([Item_No]),
        type text),

    // A date column for the Dim_Date join. The relationship has to be on a date,
    // not a datetime: joining a datetime to a date table matches only the rows
    // that happen to fall exactly at midnight, which is almost none of them.
    WithDate = Table.AddColumn(
        WithKey, "Submitted_Date",
        each if [Submitted_DateTime] = null then null else DateTime.Date([Submitted_DateTime]),
        type nullable date),

    WithNotOk = Table.AddColumn(
        WithDate, "Is_Not_OK",
        each [Result] = "NOT OK",
        type logical),

    WithChecked = Table.AddColumn(
        WithNotOk, "Is_Checked",
        each [Result] = "OK" or [Result] = "NOT OK",
        type logical),

    Final = Table.SelectRows(WithChecked, each [Response_ID] <> null)
in
    Final
