// ===========================================================================
// Fact_Breakdown  <- Breakdown_Log
// ---------------------------------------------------------------------------
// Unplanned stoppages.
//
// Production_Loss_Min and MTTR_Min are deliberately separate and must stay that
// way. MTTR is wrench time; production loss includes waiting for a technician,
// waiting for a spare, and restarting the line. Production loss is almost always
// the larger number, and using MTTR for availability makes availability look
// flattering and wrong.
//
// Linked_PM_WO has been removed. The "Breakdowns After PM (7d)" measure always
// derived the relationship from dates rather than trusting that column, so nothing
// depended on it - it was a stored answer to a question the model already asks.
// ===========================================================================
let
    Source = fnGetTable("Breakdown_Log", "03_PM_Transactions_Dummy.xlsx", "Breakdown_Log"),

    Keys = fnCleanKeys(Source, {"BD_ID", "Machine_ID", "Cell_ID", "Reported_By_Tech_ID"}),
    Bools = fnYesNo(Keys, {"Recurrence_Flag"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"BD_ID",               type text},
        {"Reported_DateTime",   type datetime},
        {"Machine_ID",          type text},
        {"Cell_ID",             type text},
        {"Reported_By_Tech_ID", type text},
        {"Shift",               type text},
        {"Breakdown_Type",      type text},
        {"Symptom",             type text},
        {"Root_Cause",          type text},
        {"Action_Taken",        type text},
        {"Response_DateTime",   type datetime},
        {"Repair_Start",        type datetime},
        {"Repair_End",          type datetime},
        {"Production_Loss_Min", Int64.Type},
        {"Status",              type text},
        {"Recurrence_Flag",     type logical}
    }),

    WithDate = Table.AddColumn(
        Typed, "Reported_Date",
        each if [Reported_DateTime] = null then null else DateTime.Date([Reported_DateTime]),
        type nullable date),

    // Computed from the timestamps, not stored. Flow 6 used to calculate and write
    // both; the timestamps are the evidence, so the model derives the numbers from
    // them and there is nothing to fall out of step.
    WithCalc = Table.AddColumn(
        WithDate, "MTTR_Min",
        each if [Repair_Start] = null or [Repair_End] = null then null
             else Duration.TotalMinutes([Repair_End] - [Repair_Start]),
        type nullable number),

    WithResp = Table.AddColumn(
        WithCalc, "Response_Time_Min",
        each if [Reported_DateTime] = null or [Response_DateTime] = null then null
             else Duration.TotalMinutes([Response_DateTime] - [Reported_DateTime]),
        type nullable number),

    WithLoss = Table.AddColumn(
        WithResp, "Production_Loss_Hrs",
        each if [Production_Loss_Min] = null then null else [Production_Loss_Min] / 60,
        type nullable number),

    WithOpen = Table.AddColumn(
        WithLoss, "Is_Open",
        each [Status] <> "Closed",
        type logical),

    Final = Table.SelectRows(WithOpen, each [BD_ID] <> null)
in
    Final
