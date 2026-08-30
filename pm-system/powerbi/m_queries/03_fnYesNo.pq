// ===========================================================================
// Function: fnYesNo
// ---------------------------------------------------------------------------
// Converts the named columns to logical true/false.
//
// Excel gives "Yes"/"No" text. SharePoint gives real booleans. Both arrive here
// and leave as logical, so no measure ever has to test for both shapes - which
// is exactly the kind of thing that works in development and fails on the day
// you repoint to SharePoint.
// ===========================================================================
let
    fnYesNo = (Source as table, BoolColumns as list) as table =>
        let
            Present = List.Intersect({Table.ColumnNames(Source), BoolColumns}),
            Converted = Table.TransformColumns(
                Source,
                List.Transform(
                    Present,
                    each {_, (v) =>
                            if v = null then null
                            else if v is logical then v
                            else if v is number then v <> 0
                            else List.Contains({"YES", "Y", "TRUE", "1"},
                                               Text.Upper(Text.Trim(Text.From(v)))),
                          type nullable logical}
                )
            )
        in
            Converted
in
    fnYesNo
