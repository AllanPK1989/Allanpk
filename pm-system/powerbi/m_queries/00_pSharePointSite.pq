// ===========================================================================
// Parameter: pSharePointSite
// ---------------------------------------------------------------------------
// Site URL, no trailing slash, e.g.
//     https://contoso.sharepoint.com/sites/Maintenance
// Used only when pSourceMode = "SharePoint".
// ===========================================================================
"https://contoso.sharepoint.com/sites/Maintenance" meta [
    IsParameterQuery = true,
    Type = type text,
    IsParameterQueryRequired = true,
    DefaultValue = "https://contoso.sharepoint.com/sites/Maintenance"
]
