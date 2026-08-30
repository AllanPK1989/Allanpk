// ===========================================================================
// Fact_StdHours  <- StdHours_Monthly  (or a folder of monthly workbooks)
// ---------------------------------------------------------------------------
// The number that drives everything. One row per cell per month, added to that
// cell's running counter by Flow 1.
//
// THIS QUERY APPENDS A FOLDER, IT DOES NOT READ ONE FILE. That is deliberate.
// The monthly process is "drop one workbook per month into a library". If the
// query read a single file, every month would need a query edit; as a folder
// query it just picks the new file up. Point pStdHoursArchiveFolder at the
// SharePoint StdHours_Archive library and the same code works unchanged.
//
// Three source shapes are supported, chosen in this order:
//   1. pSourceMode = "SharePoint"          -> the StdHours_Monthly list
//   2. pStdHoursArchiveFolder is set       -> append every workbook in it
//   3. otherwise                           -> the single template workbook
//
// The Instructions sheet is excluded by name in the transform function, so a
// monthly file that still carries it imports cleanly.
// ===========================================================================
let
    // --- shape 3: the single template workbook (dummy data) ----------------
    FromTemplate = fnGetTable("StdHours_Monthly",
                              "02_StdHours_Monthly_Upload_Template.xlsx",
                              "StdHours_Upload"),

    // --- shape 2: append every workbook in the archive folder ---------------
    // The sample-file transform function. Applied to each file's binary, it
    // returns that file's StdHours_Upload sheet with headers promoted. Anything
    // that is not a data sheet - Instructions, a stray pivot - is filtered out
    // rather than erroring, because one malformed file must not stop the year.
    TransformFile = (WorkbookContents as binary) as table =>
        let
            Book   = Excel.Workbook(WorkbookContents, null, true),
            Sheets = Table.SelectRows(Book, each [Kind] = "Sheet"
                                              and [Item] <> "Instructions"),
            Pick   = if Table.RowCount(Table.SelectRows(Sheets, each [Item] = "StdHours_Upload")) > 0
                     then Table.SelectRows(Sheets, each [Item] = "StdHours_Upload")
                     else Sheets,
            Data   = if Table.RowCount(Pick) = 0 then #table({}, {}) else Pick{0}[Data],
            Header = if Table.RowCount(Pick) = 0 then Data
                     else Table.PromoteHeaders(Data, [PromoteAllScalars = true])
        in
            Header,

    FromFolder =
        let
            Files    = Folder.Files(pStdHoursArchiveFolder),
            OnlyXlsx = Table.SelectRows(
                           Files,
                           each Text.Lower([Extension]) = ".xlsx"
                                // Skip Excel's lock files, which appear the moment
                                // someone opens a workbook in the library and would
                                // otherwise fail the whole refresh.
                                and not Text.StartsWith([Name], "~$")),
            Parsed   = Table.AddColumn(OnlyXlsx, "Data", each TransformFile([Content])),
            Kept     = Table.SelectRows(Parsed,
                           each Table.HasColumns([Data], {"Upload_Month", "Cell_ID", "Actual_Std_Hours"})),
            Expanded = Table.ExpandTableColumn(
                           Table.SelectColumns(Kept, {"Data"}), "Data",
                           {"Upload_Month", "Cell_ID", "Cell_Name", "Actual_Std_Hours",
                            "Production_Qty", "Uploaded_By", "Upload_Date", "Remarks"})
        in
            Expanded,

    Source =
        if pSourceMode = "SharePoint" then
            fnGetTable("StdHours_Monthly", "02_StdHours_Monthly_Upload_Template.xlsx", "StdHours_Upload")
        else if Text.Trim(pStdHoursArchiveFolder) <> "" then
            FromFolder
        else
            FromTemplate,

    Keys = fnCleanKeys(Source, {"Cell_ID"}),

    // Upload_Month is text YYYY-MM and must stay text. Let it become a date and
    // "2025-09" silently becomes 1 September, which then sorts correctly by
    // accident and breaks the moment a locale reads it day-first.
    Typed = Table.TransformColumnTypes(Keys, {
        {"Upload_Month",     type text},
        {"Cell_ID",          type text},
        {"Cell_Name",        type text},
        {"Actual_Std_Hours", type number},
        {"Production_Qty",   Int64.Type},
        {"Uploaded_By",      type text},
        {"Upload_Date",      type date},
        {"Remarks",          type text}
    }),

    // A real date for the month, so Dim_Date can join to it. Always the first of
    // the month: the hours belong to the month, not to a day within it.
    WithMonthDate = Table.AddColumn(
        Typed, "Month_Start_Date",
        each if [Upload_Month] = null or Text.Length([Upload_Month]) < 7 then null
             else #date(Number.FromText(Text.Start([Upload_Month], 4)),
                        Number.FromText(Text.Middle([Upload_Month], 5, 2)), 1),
        type nullable date),

    // Guard against the duplicate-upload case surviving into the model. Flow 1
    // rejects a month that already exists, but a hand-loaded file can bypass it,
    // and a double-counted month inflates the counter with no visible error.
    Deduped = Table.Distinct(WithMonthDate, {"Upload_Month", "Cell_ID"}),

    Final = Table.SelectRows(Deduped, each [Cell_ID] <> null and [Actual_Std_Hours] <> null)
in
    Final
