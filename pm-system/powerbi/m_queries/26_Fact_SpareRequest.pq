// ===========================================================================
// Fact_SpareRequest  <- Spare_Request
// ---------------------------------------------------------------------------
// Requests and their approval trail.
//
// The interesting number here is not how many were approved. It is the gap
// between Approved_Date and Issue_Date. Approval is fast because it is one
// click; issue needs someone to walk to the store. That gap is where PMs
// actually stall, and Issue_Lead_Days below is what makes it visible.
// ===========================================================================
let
    Source = fnGetTable("Spare_Request", "03_PM_Transactions_Dummy.xlsx", "Spare_Request"),

    Keys = fnCleanKeys(Source, {"Req_ID", "WO_No", "Machine_ID", "Cell_ID",
                                "Spare_Code", "Requested_By"}),

    Typed = Table.TransformColumnTypes(Keys, {
        {"Req_ID",            type text},
        {"Request_DateTime",  type datetime},
        {"WO_No",             type text},
        {"Machine_ID",        type text},
        {"Cell_ID",           type text},
        {"Spare_Code",        type text},
        {"Spare_Description", type text},
        {"Qty_Requested",     Int64.Type},
        {"Requested_By",      type text},
        {"Urgency",           type text},
        {"Reason",            type text},
        {"Approval_Status",   type text},
        {"Approved_By",       type text},
        {"Approved_Date",     type date},
        {"Issue_Status",      type text},
        {"Issued_Qty",        Int64.Type},
        {"Issue_Date",        type date},
        {"Stock_At_Request",  Int64.Type},
        {"Remarks",           type text}
    }),

    WithDate = Table.AddColumn(
        Typed, "Request_Date",
        each if [Request_DateTime] = null then null else DateTime.Date([Request_DateTime]),
        type nullable date),

    WithApprovalLead = Table.AddColumn(
        WithDate, "Approval_Lead_Days",
        each if [Approved_Date] = null or [Request_Date] = null then null
             else Duration.Days([Approved_Date] - [Request_Date]),
        Int64.Type),

    WithIssueLead = Table.AddColumn(
        WithApprovalLead, "Issue_Lead_Days",
        each if [Issue_Date] = null or [Approved_Date] = null then null
             else Duration.Days([Issue_Date] - [Approved_Date]),
        Int64.Type),

    WithPending = Table.AddColumn(
        WithIssueLead, "Is_Pending_Approval",
        each [Approval_Status] = "Pending",
        type logical),

    // A request that was approved but never issued. This is the silent one:
    // nothing is flagged red, the approver's job is done, and the PM waits.
    WithStuck = Table.AddColumn(
        WithPending, "Is_Approved_Not_Issued",
        each [Approval_Status] = "Approved" and [Issue_Status] <> "Issued",
        type logical),

    Final = Table.SelectRows(WithStuck, each [Req_ID] <> null)
in
    Final
