// ===========================================================================
// Function: fnCleanKeys
// ---------------------------------------------------------------------------
// Trims, cleans and uppercases the named key columns, and converts them to text.
//
// Why this exists as a function rather than a step in each query:
//   A key that differs by a trailing space joins to nothing. The relationship
//   still shows as valid in the model - it just returns blank for those rows,
//   silently, and you find out months later when a cell's PM history looks
//   thin. Doing it identically in every query is the only defence, and the only
//   way to do it identically is to do it in one place.
//
//   Text.Clean strips non-printable characters, which is what you get when a
//   value has been pasted out of a PDF or a terminal report.
// ===========================================================================
let
    fnCleanKeys = (Source as table, KeyColumns as list) as table =>
        let
            Present = List.Intersect({Table.ColumnNames(Source), KeyColumns}),
            Cleaned = Table.TransformColumns(
                Source,
                List.Transform(
                    Present,
                    each {_, (v) => if v = null then null
                                    else Text.Upper(Text.Trim(Text.Clean(Text.From(v)))),
                          type nullable text}
                )
            ),
            // An empty string is not a key. Turning it into null makes the
            // blank-row problem visible in the model instead of creating a
            // phantom member called "".
            Blanked = Table.TransformColumns(
                Cleaned,
                List.Transform(Present, each {_, (v) => if v = "" then null else v, type nullable text})
            )
        in
            Blanked
in
    fnCleanKeys
