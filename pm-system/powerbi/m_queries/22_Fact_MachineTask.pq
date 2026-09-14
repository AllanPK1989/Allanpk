// ===========================================================================
// Fact_MachineTask  <- PM_Machine_Task
// ---------------------------------------------------------------------------
// One row per machine per work order. The grain the whole execution story is
// told at, and the table the technician's allotted list is a view over.
//
// Duration_Min is the pencil-whipping detector. Compared against the summed
// Expected_Time_Min for that machine's checklist, a 45-minute checklist closed
// in 4 minutes is visible immediately. That comparison is the reason this table
// carries an expected-duration column at all.
// ===========================================================================
let
    Source = fnGetTable("PM_Machine_Task", "03_PM_Transactions_Dummy.xlsx", "PM_Machine_Task"),

    Keys = fnCleanKeys(Source, {"Task_ID", "WO_No", "Machine_ID", "Cell_ID", "Completed_By"}),
    Bools = fnYesNo(Keys, {}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Task_ID",               type text},
        {"WO_No",                 type text},
        {"Machine_ID",            type text},
        {"Cell_ID",               type text},
        {"Task_Status",           type text},
        {"Scan_Start_Time",       type datetime},
        {"Scan_End_Time",         type datetime},
        {"Completed_By",          type text},
        {"Skip_Reason",           type text}
    }),

    // Derived here rather than stored on the list. Flow 4 used to compute and write
    // Duration_Min; now the model works it out from the two timestamps on every
    // refresh, so it cannot go stale and there is one less thing a flow can get
    // wrong at two in the morning.
    WithDuration = Table.AddColumn(
        Typed, "Duration_Min",
        each if [Scan_Start_Time] = null or [Scan_End_Time] = null then null
             else Duration.TotalMinutes([Scan_End_Time] - [Scan_Start_Time]),
        type nullable number),

    WithCompletionDate = Table.AddColumn(
        WithDuration, "Completion_Date",
        each if [Scan_End_Time] = null then null else DateTime.Date([Scan_End_Time]),
        type nullable date),

    WithComplete = Table.AddColumn(
        WithCompletionDate, "Is_Completed",
        each [Task_Status] = "Completed",
        type logical),

    WithOpen = Table.AddColumn(
        WithComplete, "Is_Open",
        each [Task_Status] = "Pending" or [Task_Status] = "In Progress",
        type logical),

    // Sort key so a status axis reads in workflow order rather than alphabetically
    // (which would put Completed before In Progress before Pending - backwards).
    WithSort = Table.AddColumn(
        WithOpen, "Status_Sort",
        each if [Task_Status] = "Pending" then 1
             else if [Task_Status] = "In Progress" then 2
             else if [Task_Status] = "Completed" then 3
             else 4,
        Int64.Type),

    Final = Table.SelectRows(WithSort, each [Task_ID] <> null)
in
    Final
