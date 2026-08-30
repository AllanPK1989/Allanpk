// ===========================================================================
// Fact_ScanLog  <- Scan_Log
// ---------------------------------------------------------------------------
// Raw QR events.
//
// Worth keeping even though PM_Machine_Task already carries timestamps, because
// this table records the scans that did NOT lead to a completion: the
// technician who started and walked away, the machine scanned with no open work
// order. That gap is where adoption problems show up first, months before they
// show up in compliance percentages.
// ===========================================================================
let
    Source = fnGetTable("Scan_Log", "03_PM_Transactions_Dummy.xlsx", "Scan_Log"),

    Keys = fnCleanKeys(Source, {"Scan_ID", "Machine_ID", "Cell_ID", "Tech_ID", "WO_No"}),

    Typed = Table.TransformColumnTypes(Keys, {
        {"Scan_ID",       type text},
        {"Scan_DateTime", type datetime},
        {"Machine_ID",    type text},
        {"Cell_ID",       type text},
        {"Tech_ID",       type text},
        {"Scan_Action",   type text},
        {"Device",        type text},
        {"WO_No",         type text},
        {"Comments",      type text}
    }),

    WithDate = Table.AddColumn(
        Typed, "Scan_Date",
        each if [Scan_DateTime] = null then null else DateTime.Date([Scan_DateTime]),
        type nullable date),

    // Hour of day, for the shift-pattern view. A cluster of scans in the last
    // ten minutes of a shift is a different behaviour from an even spread.
    WithHour = Table.AddColumn(
        WithDate, "Scan_Hour",
        each if [Scan_DateTime] = null then null else Time.Hour(DateTime.Time([Scan_DateTime])),
        Int64.Type),

    // A scan with no work order in force. Not an error - a technician may look
    // a machine up out of curiosity - but a rising count means people are
    // scanning stickers that have no work behind them.
    WithOrphan = Table.AddColumn(
        WithHour, "Is_Orphan_Scan",
        each [WO_No] = null,
        type logical),

    Final = Table.SelectRows(WithOrphan, each [Scan_ID] <> null)
in
    Final
