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

    Keys = fnCleanKeys(Source, {"Task_ID", "WO_No", "Machine_ID", "Cell_ID",
                                "Assigned_Tech_ID", "Completed_By", "Checklist_Response_ID"}),
    Bools = fnYesNo(Keys, {"Abnormality_Raised", "Spare_Used_Flag"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Task_ID",               type text},
        {"WO_No",                 type text},
        {"Machine_ID",            type text},
        {"Cell_ID",               type text},
        {"Assigned_Tech_ID",      type text},
        {"Task_Status",           type text},
        {"Scan_Start_Time",       type datetime},
        {"Scan_End_Time",         type datetime},
        {"Duration_Min",          Int64.Type},
        {"Checklist_Response_ID", type text},
        {"NOT_OK_Count",          Int64.Type},
        {"Abnormality_Raised",    type logical},
        {"Spare_Used_Flag",       type logical},
        {"Completed_By",          type text},
        {"Completion_Date",       type date},
        {"Skip_Reason",           type text}
    }),

    WithComplete = Table.AddColumn(
        Typed, "Is_Completed",
        each [Task_Status] = "Completed",
        type logical),

    WithOpen = Table.AddColumn(
        WithComplete, "Is_Open",
        each [Task_Status] = "Pending" or [Task_Status] = "In Progress",
        type logical),

    // A completed task with no findings at all. Rolled up to the work order this
    // becomes First-Pass PM %.
    WithClean = Table.AddColumn(
        WithOpen, "Is_Clean_Pass",
        each [Task_Status] = "Completed"
             and ([NOT_OK_Count] = null or [NOT_OK_Count] = 0),
        type logical),

    // Sort key so a status axis reads in workflow order rather than alphabetically
    // (which would put Completed before In Progress before Pending - backwards).
    WithSort = Table.AddColumn(
        WithClean, "Status_Sort",
        each if [Task_Status] = "Pending" then 1
             else if [Task_Status] = "In Progress" then 2
             else if [Task_Status] = "Completed" then 3
             else 4,
        Int64.Type),

    Final = Table.SelectRows(WithSort, each [Task_ID] <> null)
in
    Final
