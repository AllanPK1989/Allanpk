// ===========================================================================
// Dim_Machine  <- Machine_Master
// ---------------------------------------------------------------------------
// One row per machine. Carries the QR payload the sticker encodes.
//
// The four per-machine form URLs are gone. They were 120 hyperlinks typed into a
// spreadsheet - one per machine per form - and every one of them a chance to point
// a button at the wrong machine. The Machine Hub now builds each link from the
// row it is drawing, so there is nothing per-machine left to maintain or to load.
//
// Cell_Name is gone too: it is reachable through Dim_Cell, and the QR label
// generator prints Cell_ID, so nothing needed the denormalised copy.
// ===========================================================================
let
    Source = fnGetTable("Machine_Master", "01_PM_Master_Data.xlsx", "Machine_Master"),

    Keys = fnCleanKeys(Source, {"Machine_ID", "Cell_ID", "Checklist_ID"}),
    Bools = fnYesNo(Keys, {"Active"}),

    // SharePoint returns a Hyperlink column as a record {Url, Description}.
    // Excel returns plain text. Flatten to text so both look the same downstream.
    UrlColumns = {"QR_Payload_URL"},
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
        {"Machine_Family",         type text},
        {"Serial_No",              type text},
        {"Location_Tag",           type text},
        {"Checklist_ID",           type text},
        {"QR_Payload_URL",         type text},
        {"Criticality",            type text},
        {"Active",                 type logical}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Machine_Name",   each if _ = null then null else Text.Trim(_), type nullable text},
        {"Machine_Family", each if _ = null then null else Text.Trim(_), type nullable text},
        {"Criticality",    each if _ = null then null else Text.Upper(Text.Trim(_)), type nullable text}
    }),

    // A display label that is useful on a crowded axis without a tooltip.
    WithLabel = Table.AddColumn(
        Trimmed, "Machine_Label",
        each Text.From([Machine_ID]) & " - " & Text.From([Machine_Name]),
        type text),

    WithSort = Table.AddColumn(
        WithLabel, "Criticality_Sort",
        each if [Criticality] = "A" then 1 else if [Criticality] = "B" then 2 else 3,
        Int64.Type),

    Final = Table.SelectRows(WithSort, each [Machine_ID] <> null)
in
    Final
