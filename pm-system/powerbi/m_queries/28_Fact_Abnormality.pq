// ===========================================================================
// Fact_Abnormality  <- Abnormality_Log
// ---------------------------------------------------------------------------
// Conditions found that are not yet failures. The cheapest maintenance data
// there is: an air leak logged today costs nothing to record and shows up in the
// compressed-air bill for years if it is not.
//
// Ageing is computed against the CLOSED date where one exists and against today
// where it does not, so a closed item's age stops moving. Ageing that keeps
// counting after closure makes the average meaningless.
// ===========================================================================
let
    Source = fnGetTable("Abnormality_Log", "03_PM_Transactions_Dummy.xlsx", "Abnormality_Log"),

    Keys = fnCleanKeys(Source, {"Abn_ID", "Machine_ID", "Cell_ID", "Logged_By"}),
    Bools = fnYesNo(Keys, {"Converted_To_WO"}),

    Flattened = Table.TransformColumns(
        Bools,
        List.Transform(
            List.Intersect({Table.ColumnNames(Bools), {"Photo_Link"}}),
            each {_, (v) => if v = null then null
                            else if v is record then Record.FieldOrDefault(v, "Url", null)
                            else Text.From(v),
                  type nullable text})),

    Typed = Table.TransformColumnTypes(Flattened, {
        {"Abn_ID",           type text},
        {"Logged_DateTime",  type datetime},
        {"Machine_ID",       type text},
        {"Cell_ID",          type text},
        {"Logged_By",        type text},
        {"Category",         type text},
        {"Description",      type text},
        {"Severity",         type text},
        {"Photo_Link",       type text},
        {"Immediate_Action", type text},
        {"Responsibility",   type text},
        {"Target_Date",      type date},
        {"Status",           type text},
        {"Closed_Date",      type date},
        {"Closure_Remarks",  type text},
        {"Converted_To_WO",  type logical}
    }),

    WithDate = Table.AddColumn(
        Typed, "Logged_Date",
        each if [Logged_DateTime] = null then null else DateTime.Date([Logged_DateTime]),
        type nullable date),

    WithAge = Table.AddColumn(
        WithDate, "Age_Days",
        each if [Logged_Date] = null then null
             else if [Closed_Date] <> null
                  then Duration.Days([Closed_Date] - [Logged_Date])
                  else Duration.Days(Date.From(DateTime.LocalNow()) - [Logged_Date]),
        Int64.Type),

    WithOpen = Table.AddColumn(
        WithAge, "Is_Open",
        each [Status] <> "Closed",
        type logical),

    WithOverdue = Table.AddColumn(
        WithOpen, "Is_Overdue",
        each [Status] <> "Closed"
             and [Target_Date] <> null
             and [Target_Date] < Date.From(DateTime.LocalNow()),
        type logical),

    WithSort = Table.AddColumn(
        WithOverdue, "Severity_Sort",
        each if [Severity] = "High" then 1 else if [Severity] = "Medium" then 2 else 3,
        Int64.Type),

    Final = Table.SelectRows(WithSort, each [Abn_ID] <> null)
in
    Final
