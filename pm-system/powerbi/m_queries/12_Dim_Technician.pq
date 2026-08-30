// ===========================================================================
// Dim_Technician  <- Technician_Master
// ---------------------------------------------------------------------------
// Technicians share one M365 login, so the name captured on each form is the
// only attribution the system has. That makes this dimension the entire audit
// trail, and it makes an inactive technician's rows worth keeping: a leaver's
// completed work still has to be attributable.
// ===========================================================================
let
    Source = fnGetTable("Technician_Master", "01_PM_Master_Data.xlsx", "Technician_Master"),

    Keys = fnCleanKeys(Source, {"Tech_ID"}),
    Bools = fnYesNo(Keys, {"Active"}),

    Typed = Table.TransformColumnTypes(Bools, {
        {"Tech_ID",       type text},
        {"Tech_Name",     type text},
        {"Skill_Level",   type text},
        {"Trade",         type text},
        {"Default_Shift", type text},
        {"Contact_No",    type text},
        {"Role_Scope",    type text},
        {"Active",        type logical}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Tech_Name",   each if _ = null then null else Text.Trim(_), type nullable text},
        {"Skill_Level", each if _ = null then null else Text.Trim(_), type nullable text},
        {"Trade",       each if _ = null then null else Text.Trim(_), type nullable text}
    }),

    // Senior / Junior / Trainee is a rank, not an alphabet.
    WithSort = Table.AddColumn(
        Trimmed, "Skill_Sort",
        each if [Skill_Level] = "Senior" then 1
             else if [Skill_Level] = "Junior" then 2 else 3,
        Int64.Type),

    // The label used on every visual: the ID alone means nothing to a manager,
    // the name alone is ambiguous when two people share a first name.
    WithLabel = Table.AddColumn(
        WithSort, "Tech_Label",
        each Text.From([Tech_Name]) & " (" & Text.From([Tech_ID]) & ")",
        type text),

    Final = Table.SelectRows(WithLabel, each [Tech_ID] <> null)
in
    Final
