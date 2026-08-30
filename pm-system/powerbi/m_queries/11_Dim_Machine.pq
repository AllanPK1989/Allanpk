// ===========================================================================
// Dim_Machine  <- Machine_Master
// ---------------------------------------------------------------------------
// One row per machine. Carries the QR payload and the four pre-filled form URLs
// that become the Machine Hub buttons.
//
// Cell_Name is kept even though it is available through Dim_Cell. It is
// denormalised in the source for label printing and offline views, and dropping
// it here would mean the QR label generator and the model disagree about what
// the label says.
// ===========================================================================
let
    Source = fnGetTable("Machine_Master", "01_PM_Master_Data.xlsx", "Machine_Master"),

    Keys = fnCleanKeys(Source, {"Machine_ID", "Cell_ID", "Checklist_ID"}),
    Bools = fnYesNo(Keys, {"Active"}),

    // SharePoint returns a Hyperlink column as a record {Url, Description}.
    // Excel returns plain text. Flatten to text so both look the same downstream.
    UrlColumns = {"Checklist_Form_URL", "Breakdown_Form_URL", "Spare_Request_Form_URL",
                  "Abnormality_Form_URL", "QR_Payload_URL"},
    Flattened = Table.TransformColumns(
        Bools,
        List.Transform(
            List.Intersect({Table.ColumnNames(Bools), UrlColumns}),
            each {_, (v) => if v = null then null
                            else if v is record then Record.FieldOrDefault(v, "Url", null)
                            else Text.Trim(Text.From(v)),
                  type nullable text})),

    Typed = Table.TransformColumnTypes(Flattened, {
        {"Machine_ID",             type text},
        {"Machine_Name",           type text},
        {"Cell_ID",                type text},
        {"Cell_Name",              type text},
        {"Machine_Family",         type text},
        {"Make",                   type text},
        {"Model",                  type text},
        {"Serial_No",              type text},
        {"Year_Installed",         Int64.Type},
        {"Location_Tag",           type text},
        {"Checklist_ID",           type text},
        {"Checklist_Form_URL",     type text},
        {"Breakdown_Form_URL",     type text},
        {"Spare_Request_Form_URL", type text},
        {"Abnormality_Form_URL",   type text},
        {"QR_Payload_URL",         type text},
        {"Criticality",            type text},
        {"Active",                 type logical}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Machine_Name",   each if _ = null then null else Text.Trim(_), type nullable text},
        {"Machine_Family", each if _ = null then null else Text.Trim(_), type nullable text},
        {"Criticality",    each if _ = null then null else Text.Upper(Text.Trim(_)), type nullable text}
    }),

    // Age is the evidence base for replacement capex, so it belongs in the
    // model rather than being recalculated in each visual.
    WithAge = Table.AddColumn(
        Trimmed, "Machine_Age_Years",
        each if [Year_Installed] = null then null
             else Date.Year(DateTime.Date(DateTime.LocalNow())) - [Year_Installed],
        Int64.Type),

    // A display label that is useful on a crowded axis without a tooltip.
    WithLabel = Table.AddColumn(
        WithAge, "Machine_Label",
        each Text.From([Machine_ID]) & " - " & Text.From([Machine_Name]),
        type text),

    WithSort = Table.AddColumn(
        WithLabel, "Criticality_Sort",
        each if [Criticality] = "A" then 1 else if [Criticality] = "B" then 2 else 3,
        Int64.Type),

    Final = Table.SelectRows(WithSort, each [Machine_ID] <> null)
in
    Final
