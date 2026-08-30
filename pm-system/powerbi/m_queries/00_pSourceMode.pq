// ===========================================================================
// Parameter: pSourceMode
// ---------------------------------------------------------------------------
// "Excel"      - read the dummy workbooks from a local folder (development)
// "SharePoint" - read the live SharePoint lists (production)
//
// THIS IS THE SWITCH. Changing this one parameter from "Excel" to "SharePoint"
// repoints the entire model. No query is edited, nothing is rewritten. Every
// table goes through fnGetTable, and fnGetTable is the only place that knows
// which of the two sources it is talking to.
//
// Set it in Power BI Desktop:  Home > Transform data > Manage parameters
// Set it in the Service:       Semantic model > Settings > Parameters
// ===========================================================================
"Excel" meta [
    IsParameterQuery = true,
    List = {"Excel", "SharePoint"},
    DefaultValue = "Excel",
    Type = type text,
    IsParameterQueryRequired = true
]
