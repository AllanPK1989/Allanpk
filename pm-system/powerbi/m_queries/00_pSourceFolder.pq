// ===========================================================================
// Parameter: pSourceFolder
// ---------------------------------------------------------------------------
// Local folder holding the three source workbooks. Used only when
// pSourceMode = "Excel".
//
// Trailing separator is not required - fnGetTable normalises it.
// ===========================================================================
"C:\EPQPL_PM\input" meta [
    IsParameterQuery = true,
    Type = type text,
    IsParameterQueryRequired = true,
    DefaultValue = "C:\EPQPL_PM\input"
]
