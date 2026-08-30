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
// Linked_PM_WO is populated by Flow 6 when a breakdown falls within 7 days of a
// completed PM on that cell. It is EMPTY on the dummy data, so the
// "Breakdowns After PM (7d)" measure does not depend on it - the measure derives
// the relationship from dates instead, and works whether or not the flow has
// backfilled the column. See dax/measures.dax.
// ===========================================================================
let
    Source = fnGetTable("Breakdown_Log", "03_PM_Transactions_Dummy.xlsx", "Breakdown_Log"),

    Keys = fnCleanKeys(Source, {"BD_ID", "Machine_ID", "Cell_ID",
                                "Reported_By_Tech_ID", "Linked_PM_WO"}),
    Bools = fnYesNo(Keys, {"Spare_Used", "Recurrence_Flag"}),

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
        {"Response_Time_Min",   Int64.Type},
        {"MTTR_Min",            Int64.Type},
        {"Production_Loss_Min", Int64.Type},
        {"Spare_Used",          type logical},
        {"Status",              type text},
        {"Recurrence_Flag",     type logical},
        {"Linked_PM_WO",        type text},
        {"Remarks",             type text}
    }),

    WithDate = Table.AddColumn(
        Typed, "Reported_Date",
        each if [Reported_DateTime] = null then null else DateTime.Date([Reported_DateTime]),
        type nullable date),

    // Recomputed from the timestamps rather than trusted from the source column.
    // If the two disagree, the timestamps are the evidence and the number is the
    // claim - and the discrepancy is worth seeing.
    WithCalc = Table.AddColumn(
        WithDate, "MTTR_Min_Calc",
        each if [Repair_Start] = null or [Repair_End] = null then null
             else Duration.TotalMinutes([Repair_End] - [Repair_Start]),
        type nullable number),

    WithResp = Table.AddColumn(
        WithCalc, "Response_Time_Min_Calc",
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
