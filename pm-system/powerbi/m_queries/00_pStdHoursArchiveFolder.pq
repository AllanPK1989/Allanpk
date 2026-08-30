// ===========================================================================
// Parameter: pStdHoursArchiveFolder
// ---------------------------------------------------------------------------
// Folder holding every monthly standard-hours workbook, one file per month.
// Fact_StdHours appends all of them rather than reading a single file, so a new
// month appears in the model on the next refresh with no query change at all.
//
//   Development : a local folder of monthly files
//   Production  : the SharePoint StdHours_Archive library, reachable over the
//                 OneDrive/SharePoint sync path or via SharePoint.Contents
//
// If you leave this empty the std-hours query falls back to the single
// 02_StdHours_Monthly_Upload_Template.xlsx in pSourceFolder, which is what the
// dummy data uses.
// ===========================================================================
"" meta [
    IsParameterQuery = true,
    Type = type text,
    IsParameterQueryRequired = false,
    DefaultValue = ""
]
