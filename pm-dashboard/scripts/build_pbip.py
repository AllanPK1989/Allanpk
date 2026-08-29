#!/usr/bin/env python3
"""
build_pbip.py - generates the whole Power BI project.

  powerbi/PM_Dashboard.pbip
  powerbi/PM_Dashboard.SemanticModel/   TMDL model: tables, relationships, 94 measures
  powerbi/PM_Dashboard.Report/          PBIR report: 10 pages of visuals + theme

Two ways to use it:

  python3 scripts/build_pbip.py
      Writes a complete, self-contained project into powerbi/.

  python3 scripts/build_pbip.py --inject "C:/path/Blank.pbip"
      Writes the model and the pages into a project Power BI Desktop created,
      keeping Desktop's own boilerplate. Use this if the self-contained project
      will not open on your Desktop version.

Power BI Desktop must be CLOSED while this runs.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pbi_measures import MEASURES                                  # noqa: E402
from pbi_model_spec import (RELATIONSHIPS, SP_EXCEL, SP_LISTS,     # noqa: E402
                            TABLES, col_format, col_type)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "dummy")
NAME = "PM_Dashboard"

T = "\t"


def uid() -> str:
    return str(uuid.uuid4())


def w(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def wj(path: str, obj) -> None:
    w(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def headers(csv_stem: str) -> list[str]:
    with open(os.path.join(DATA, csv_stem + ".csv"), encoding="utf-8") as f:
        return next(csv.reader(f))


# ===========================================================================
# PALETTE
# ===========================================================================
INK = "#0F2A3D"
INK_2 = "#173C52"
ACCENT = "#1B6E8C"
ACCENT_2 = "#54A0B8"
PAPER = "#F2F5F7"
CARD = "#FFFFFF"
LINE = "#D5DEE4"
MUTED = "#5A7183"
GOOD = "#2F9E7E"
WARN = "#D08B2C"
BAD = "#C4553B"
SERIES = [ACCENT, "#2F9E7E", "#D08B2C", "#C4553B", "#7B5EA7", "#54A0B8",
          "#8A9A5B", "#B4707E"]


# ===========================================================================
# TMDL helpers
# ===========================================================================

def tmdl_expr(dax: str, indent: int) -> list[str]:
    """Render a DAX/M expression as a TMDL multi-line block."""
    pad = T * indent
    lines = [ln.rstrip() for ln in dax.strip("\n").split("\n")]
    out = ["```"]
    out += [pad + ln for ln in lines]
    out.append(pad + "```")
    return out


def m_types(cols: list[str]) -> str:
    """Table.TransformColumnTypes type list for a set of columns."""
    parts = []
    for c in cols:
        t = col_type(c)
        if t == "int64":
            m = "Int64.Type"
        elif t == "double":
            m = "type number"
        elif t == "dateTime":
            m = "type datetime" if c.endswith("DateTime") else "type date"
        else:
            m = "type text"
        parts.append(f'{{"{c}", {m}}}')
    return ", ".join(parts)


DATE_TABLE_M = """
let
    StartDate = #date(2024, 1, 1),
    EndDate = #date(2028, 12, 31),
    Holidays = {
        #date(2025,1,14), #date(2025,1,26), #date(2025,4,14), #date(2025,8,15),
        #date(2025,10,20), #date(2025,10,21), #date(2025,12,25),
        #date(2026,1,14), #date(2026,1,26), #date(2026,4,14), #date(2026,8,15),
        #date(2026,11,8), #date(2026,12,25),
        #date(2027,1,14), #date(2027,1,26), #date(2027,4,14)
    },
    Days = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1,0,0,0)),
    Base = Table.FromList(Days, Splitter.SplitByNothing(), {"Date"}),
    T0 = Table.TransformColumnTypes(Base, {{"Date", type date}}),
    T1 = Table.AddColumn(T0, "Year", each Date.Year([Date]), Int64.Type),
    T2 = Table.AddColumn(T1, "MonthNo", each Date.Month([Date]), Int64.Type),
    T3 = Table.AddColumn(T2, "MonthShort", each Date.ToText([Date], "MMM"), type text),
    T4 = Table.AddColumn(T3, "MonthKey", each Date.ToText([Date], "yyyy-MM"), type text),
    T5 = Table.AddColumn(T4, "Quarter", each Date.QuarterOfYear([Date]), Int64.Type),
    T6 = Table.AddColumn(T5, "Day", each Date.Day([Date]), Int64.Type),
    T7 = Table.AddColumn(T6, "DayShort", each Date.ToText([Date], "ddd"), type text),
    T8 = Table.AddColumn(T7, "DayOfWeek", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),
    T9 = Table.AddColumn(T8, "IsWeekend", each if Date.DayOfWeek([Date], Day.Monday) >= 5 then "Yes" else "No", type text),
    TA = Table.AddColumn(T9, "IsHoliday", each if List.Contains(Holidays, [Date]) then "Yes" else "No", type text),
    TB = Table.AddColumn(TA, "FinancialYear", each
            let y = if Date.Month([Date]) >= 4 then Date.Year([Date]) else Date.Year([Date]) - 1
            in "FY" & Text.End(Text.From(y), 2) & "-" & Text.End(Text.From(y + 1), 2), type text),
    TC = Table.AddColumn(TB, "FiscalMonthNo", each Number.Mod(Date.Month([Date]) - 4, 12) + 1, Int64.Type),
    TD = Table.AddColumn(TC, "MonthSort", each Date.Year([Date]) * 100 + Date.Month([Date]), Int64.Type),
    TE = Table.AddColumn(TD, "RelativeToToday", each
            if [Date] < Date.From(DateTime.LocalNow()) then "Past"
            else if [Date] = Date.From(DateTime.LocalNow()) then "Today"
            else "Future", type text)
in
    TE
"""

DATE_TABLE_COLS = ["Date", "Year", "MonthNo", "MonthShort", "MonthKey", "Quarter",
                   "Day", "DayShort", "DayOfWeek", "IsWeekend", "IsHoliday",
                   "FinancialYear", "FiscalMonthNo", "MonthSort", "RelativeToToday"]


def build_table_m(spec: dict) -> str:
    if spec["name"] == "Dim_Date":
        return DATE_TABLE_M
    cols = headers(spec["csv"])
    steps = [
        f'    Source = fnSource("{spec["csv"]}"),',
        f'    Typed = Table.TransformColumnTypes(Source, {{{m_types(cols)}}}, "en-US")'
        + ("," if spec.get("extra_m") else ""),
    ]
    if spec.get("extra_m"):
        steps += spec["extra_m"]
    last = spec.get("last_step", "Typed")
    return "let\n" + "\n".join(steps) + f"\nin\n    {last}\n"


def table_columns(spec: dict) -> list[tuple[str, str]]:
    if spec["name"] == "Dim_Date":
        return [(c, col_type(c)) for c in DATE_TABLE_COLS]
    cols = [(c, col_type(c)) for c in headers(spec["csv"])]
    cols += [(c, t) for c, t in spec.get("extra_cols", [])]
    return cols


def emit_table(spec: dict) -> str:
    name = spec["name"]
    L = []
    if spec.get("desc"):
        L.append(f'/// {spec["desc"]}')
    L.append(f"table {name}")
    if spec.get("date_table"):
        L.append(T + "dataCategory: Time")
    L.append(T + f"lineageTag: {uid()}")
    if spec.get("hidden"):
        L.append(T + "isHidden")
    L.append("")

    for col, dtype in table_columns(spec):
        L.append(T + f"column {col}")
        L.append(T * 2 + f"dataType: {dtype}")
        if spec.get("date_table") and col == "Date":
            L.append(T * 2 + "isKey")
        fmt = col_format(col)
        if fmt:
            L.append(T * 2 + f'formatString: {fmt}')
        L.append(T * 2 + f"lineageTag: {uid()}")
        L.append(T * 2 + "summarizeBy: none")
        L.append(T * 2 + f"sourceColumn: {col}")
        if col == "MonthShort":
            L.append(T * 2 + "sortByColumn: MonthNo")
        L.append("")
        L.append(T * 2 + "annotation SummarizationSetBy = Automatic")
        if dtype == "dateTime":
            L.append("")
            L.append(T * 2 + "annotation UnderlyingDateTimeDataType = Date")
        L.append("")

    L.append(T + f"partition {name} = m")
    L.append(T * 2 + "mode: import")
    L.append(T * 2 + "source = " + tmdl_expr(build_table_m(spec), 4)[0])
    L += tmdl_expr(build_table_m(spec), 4)[1:]
    L.append("")
    L.append(T + "annotation PBI_ResultType = Table")
    L.append("")
    return "\n".join(L)


def emit_measures_table() -> str:
    L = ["/// Every measure in the model lives here. The table itself holds no data.",
         "table _Measures",
         T + f"lineageTag: {uid()}",
         ""]
    for name, folder, fmt, dax, desc in MEASURES:
        L.append(T + f"/// {desc}")
        L.append(T + f"measure '{name}' = " + tmdl_expr(dax, 3)[0])
        L += tmdl_expr(dax, 3)[1:]
        if fmt:
            L.append(T * 2 + f"formatString: {fmt}")
        L.append(T * 2 + f"displayFolder: {folder}")
        L.append(T * 2 + f"lineageTag: {uid()}")
        L.append("")
    L.append(T + "column _Placeholder")
    L.append(T * 2 + "dataType: int64")
    L.append(T * 2 + "isHidden")
    L.append(T * 2 + "formatString: 0")
    L.append(T * 2 + "lineageTag: " + uid())
    L.append(T * 2 + "summarizeBy: none")
    L.append(T * 2 + "isNameInferred")
    L.append(T * 2 + "sourceColumn: [_Placeholder]")
    L.append("")
    L.append(T * 2 + "annotation SummarizationSetBy = Automatic")
    L.append("")
    L.append(T + "partition _Measures = calculated")
    L.append(T * 2 + "mode: import")
    L.append(T * 2 + 'source = ROW("_Placeholder", 1)')
    L.append("")
    L.append(T + "annotation PBI_Id = measures_table")
    L.append("")
    return "\n".join(L)


def emit_expressions() -> str:
    sp_lists = ", ".join(f'"{x}"' for x in sorted(SP_LISTS))
    excel_map = ",\n            ".join(
        f'{k} = {{"{v[0]}", "{v[1]}"}}' for k, v in SP_EXCEL.items())

    fn_local = """
(logicalName as text) as table =>
let
    Sep = if Text.EndsWith(LocalDataFolder, "\\") then "" else "\\",
    Path = LocalDataFolder & Sep & logicalName & ".csv",
    Raw = Csv.Document(File.Contents(Path), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Raw, [PromoteAllScalars = true]),
    NullBlanks = Table.TransformColumns(Promoted, {}, each if _ = "" then null else _)
in
    NullBlanks
"""

    fn_splist = """
(listName as text) as table =>
let
    // ApiVersion 15 is required for non-English SharePoint sites and is safe everywhere.
    // Implementation 2.0 is the current connector; if a list has more than 12 Person or
    // Lookup columns it hits a hard join limit, in which case drop Implementation and
    // ViewMode to fall back to the 1.0 connector.
    Nav = SharePoint.Tables(
        SharePointSiteUrl,
        [ApiVersion = 15, Implementation = "2.0", ViewMode = "All"]
    ),
    // The navigation column is called Title on some tenants and Name on others.
    Cols = Table.ColumnNames(Nav),
    NameCol =
        if List.Contains(Cols, "Title") then "Title"
        else if List.Contains(Cols, "Name") then "Name"
        else error "SharePoint.Tables returned no Title or Name column to navigate by.",
    Matches = Table.SelectRows(Nav, each Record.Field(_, NameCol) = listName),
    Items =
        if Table.RowCount(Matches) = 0
        then error "SharePoint list not found: " & listName
        else Matches{0}[Items]
in
    Items
"""

    fn_spexcel = """
(relativePath as text, tableName as text) as table =>
let
    Files = SharePoint.Files(SharePointSiteUrl, [ApiVersion = 15]),
    Wanted = Table.SelectRows(Files, each Text.EndsWith([Folder Path] & [Name], relativePath)),
    Content = if Table.RowCount(Wanted) = 0
              then error "File not found in SharePoint: " & relativePath
              else Wanted{0}[Content],
    Book = Excel.Workbook(Content, true, true),
    Data = Book{[Item = tableName, Kind = "Table"]}[Data]
in
    Data
"""

    fn_stdhours = """
() as table =>
let
    Files = SharePoint.Files(SharePointSiteUrl, [ApiVersion = 15]),
    Monthly = Table.SelectRows(
        Files,
        each Text.Contains([Folder Path], "/02 Standard Hours/")
            and not Text.Contains([Folder Path], "/_History/")
            and Text.StartsWith([Name], "Cell_Standard_Hours_")
            and Text.EndsWith(Text.Lower([Name]), ".xlsx")
            and not Text.Contains(Text.Upper([Name]), "TEMPLATE")
    ),
    WithData = Table.AddColumn(Monthly, "Data", each
        Excel.Workbook([Content], true, true){[Item = "tblStdHours", Kind = "Table"]}[Data]),
    Cols = {"MonthKey", "Year", "MonthNo", "CellID", "CellName", "Area",
            "StdHours", "UploadedBy", "UploadDate"},
    Expanded = Table.ExpandTableColumn(Table.SelectColumns(WithData, {"Name", "Data"}), "Data", Cols),
    Renamed = Table.RenameColumns(Expanded, {{"Name", "SourceFile"}}),
    NoBlank = Table.SelectRows(Renamed, each [MonthKey] <> null and [CellID] <> null)
in
    NoBlank
"""

    fn_source = f"""
(logicalName as text) as table =>
let
    SPLists = {{{sp_lists}}},
    ExcelMap = [
            {excel_map}
        ],
    Result =
        if SourceMode <> "SharePoint" then
            fnLocalCsv(logicalName)
        else if logicalName = "Cell_Standard_Hours" then
            fnStdHoursFolder()
        else if List.Contains(SPLists, logicalName) then
            fnSpList(logicalName)
        else if Record.HasFields(ExcelMap, logicalName) then
            fnSpExcel(Record.Field(ExcelMap, logicalName){{0}}, Record.Field(ExcelMap, logicalName){{1}})
        else
            error "fnSource: no binding defined for " & logicalName
in
    Result
"""

    def param(name, value, ptype, desc, allowed=None):
        meta = f'IsParameterQuery=true, Type="{ptype}", IsParameterQueryRequired=true'
        if allowed:
            meta = f'IsParameterQuery=true, List={{{allowed}}}, DefaultValue="{value}", Type="{ptype}", IsParameterQueryRequired=true'
        return "\n".join([
            f"/// {desc}",
            f'expression {name} = "{value}" meta [{meta}]',
            T + f"lineageTag: {uid()}",
            T + "queryGroup: 0 Parameters",
            "",
            T + "annotation PBI_ResultType = Text",
            "", ""])

    def func(name, body, desc):
        L = [f"/// {desc}", f"expression {name} = " + tmdl_expr(body, 2)[0]]
        L += tmdl_expr(body, 2)[1:]
        L.append(T + f"lineageTag: {uid()}")
        L.append(T + "queryGroup: 1 Functions")
        L.append("")
        L.append(T + "annotation PBI_ResultType = Function")
        L.append("")
        L.append("")
        return "\n".join(L)

    out = []
    out.append(param(
        "SourceMode", "Local", "Text",
        "Local reads the dummy CSVs. SharePoint reads the real lists and workbooks. "
        "This is the only switch you change at go-live.",
        allowed='"Local", "SharePoint"'))
    out.append(param(
        "LocalDataFolder", "C:\\PM_Dashboard\\data", "Text",
        "Folder holding the CSVs. Only used when SourceMode = Local. "
        "Unzip the project to C:\\PM_Dashboard and this default is already correct."))
    out.append(param(
        "SharePointSiteUrl", "https://contoso.sharepoint.com/sites/PMSystem", "Text",
        "Root URL of the SharePoint site. Only used when SourceMode = SharePoint."))
    out.append(func("fnLocalCsv", fn_local, "Reads one dummy CSV and promotes headers."))
    out.append(func("fnSpList", fn_splist, "Reads one SharePoint list by its display name."))
    out.append(func("fnSpExcel", fn_spexcel,
                    "Reads one named Excel table out of a workbook in the document library."))
    out.append(func("fnStdHoursFolder", fn_stdhours,
                    "Combines every monthly standard-hours upload in the 02 Standard Hours folder. "
                    "Add a file, refresh, and the new month appears - no query editing."))
    out.append(func("fnSource", fn_source,
                    "Single entry point for every table. Routes to CSV, SharePoint list or "
                    "SharePoint workbook depending on SourceMode."))
    return "\n".join(out)


def emit_relationships() -> str:
    L = []
    for ft, fc, tt, tc, active in RELATIONSHIPS:
        L.append(f"relationship {uid()}")
        if not active:
            L.append(T + "isActive: false")
        L.append(T + f"fromColumn: {ft}.{fc}")
        L.append(T + f"toColumn: {tt}.{tc}")
        L.append("")
    return "\n".join(L)


def emit_model() -> str:
    order = [t["name"] for t in TABLES] + ["_Measures"]
    L = [
        "model Model",
        T + "culture: en-US",
        T + "defaultPowerBIDataSourceVersion: powerBI_V3",
        T + "sourceQueryCulture: en-US",
        T + "dataAccessOptions",
        T * 2 + "legacyRedirects",
        T * 2 + "returnErrorValuesAsNull",
        "",
        "annotation PBI_QueryOrder = " + json.dumps(
            ["SourceMode", "LocalDataFolder", "SharePointSiteUrl", "fnLocalCsv",
             "fnSpList", "fnSpExcel", "fnStdHoursFolder", "fnSource"] + order),
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        "annotation PBI_ProTooling = [\"TMDL\"]",
        "",
    ]
    for t in TABLES:
        L.append(f"ref table {t['name']}")
    L.append("ref table _Measures")
    L.append("")
    return "\n".join(L)


def build_semantic_model(base: str) -> None:
    sm = os.path.join(base, f"{NAME}.SemanticModel")
    if os.path.isdir(os.path.join(sm, "definition", "tables")):
        shutil.rmtree(os.path.join(sm, "definition", "tables"))

    wj(os.path.join(sm, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": uid()},
    })
    wj(os.path.join(sm, "definition.pbism"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                   "semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {},
    })
    w(os.path.join(sm, "definition", "database.tmdl"),
      "database\n" + T + "compatibilityLevel: 1567\n")
    w(os.path.join(sm, "definition", "model.tmdl"), emit_model())
    w(os.path.join(sm, "definition", "expressions.tmdl"), emit_expressions())
    w(os.path.join(sm, "definition", "relationships.tmdl"), emit_relationships())
    for spec in TABLES:
        w(os.path.join(sm, "definition", "tables", f"{spec['name']}.tmdl"), emit_table(spec))
    w(os.path.join(sm, "definition", "tables", "_Measures.tmdl"), emit_measures_table())
    print(f"  semantic model: {len(TABLES) + 1} tables, {len(MEASURES)} measures, "
          f"{len(RELATIONSHIPS)} relationships")


# ===========================================================================
# PBIR helpers
# ===========================================================================

VIS_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
              "definition/visualContainer/2.4.0/schema.json")
PAGE_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
               "definition/page/2.0.0/schema.json")
PAGES_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                "definition/pagesMetadata/1.0.0/schema.json")
REPORT_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                 "definition/report/3.0.0/schema.json")

W, H = 1600, 900


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def slit(s):
    return lit("'" + s + "'")


def dnum(x):
    return lit(f"{x}D")


def solid(hexcolor):
    return {"solid": {"color": lit("'" + hexcolor + "'")}}


def measure_solid(prop):
    return {"solid": {"color": {"expr": {"Measure": {
        "Expression": {"SourceRef": {"Entity": "_Measures"}},
        "Property": prop}}}}}


def fm(prop, entity="_Measures"):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}},
                                  "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def fc(entity, prop):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}},
                                 "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def container(color=CARD, border=True, radius=8):
    o = {"background": [{"properties": {"show": lit("true"), "color": solid(color),
                                        "transparency": dnum(0)}}]}
    if border:
        o["border"] = [{"properties": {"show": lit("true"), "color": solid(LINE),
                                       "radius": dnum(radius)}}]
    return o


def title_obj(text, size=11, color=INK, align="left"):
    return [{"properties": {
        "show": lit("true"),
        "text": slit(text),
        "fontSize": dnum(size),
        "fontColor": solid(color),
        "background": solid(CARD),
        "alignment": slit(align),
        "titleWrap": lit("true"),
    }}]


class Page:
    def __init__(self, key, display, subtitle=""):
        self.key, self.display, self.subtitle = key, display, subtitle
        self.visuals = []
        self._z = 1000
        self._tab = 0

    def add(self, name, x, y, w, h, visual, z=None):
        self._z += 1
        self._tab += 1
        self.visuals.append({
            "$schema": VIS_SCHEMA,
            "name": name,
            "position": {"x": x, "y": y, "z": z if z is not None else self._z,
                         "width": w, "height": h, "tabOrder": self._tab},
            "visual": visual,
        })

    # -- building blocks ---------------------------------------------------
    def band(self, title, subtitle):
        self.add("v00Header", 0, 0, W, 76, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": title, "textStyle": {
                    "fontSize": "20pt", "fontWeight": "bold",
                    "color": "#FFFFFF", "fontFamily": "Segoe UI Semibold"}}],
                 "horizontalTextAlignment": "left"},
                {"textRuns": [{"value": subtitle, "textStyle": {
                    "fontSize": "10pt", "color": "#A9C2D0",
                    "fontFamily": "Segoe UI"}}],
                 "horizontalTextAlignment": "left"},
            ]}}]},
            "visualContainerObjects": {
                "background": [{"properties": {"show": lit("true"),
                                               "color": solid(INK),
                                               "transparency": dnum(0)}}]},
            "drillFilterOtherVisuals": True,
        }, z=100)

    def note(self, name, x, y, w, h, text, size=9, color=MUTED):
        self.add(name, x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": text, "textStyle": {
                    "fontSize": f"{size}pt", "color": color,
                    "fontFamily": "Segoe UI"}}]}]}}]},
            "visualContainerObjects": container(PAPER, border=False),
            "drillFilterOtherVisuals": True,
        })

    def kpi(self, name, x, y, w, h, measure, label, color_measure=None,
            ref_measure=None, ref_label=None):
        qs = {"Data": {"projections": [fm(measure)]}}
        if ref_measure:
            qs["ReferenceLabels"] = {"projections": [fm(ref_measure)]}
        objs = {
            "calloutValue": [{"properties": {
                "fontSize": dnum(30),
                "fontFamily": slit("Segoe UI Semibold"),
                "color": measure_solid(color_measure) if color_measure else solid(INK),
            }}],
            "cards": [{"properties": {"showLabel": lit("false")}}],
            "title": title_obj(label, size=10, color=MUTED),
        }
        if ref_measure:
            objs["referenceLabel"] = [{"properties": {
                "show": lit("true"),
                "titleText": slit(ref_label or ref_measure)}}]
        self.add(name, x, y, w, h, {
            "visualType": "cardVisual",
            "query": {"queryState": qs},
            "objects": objs,
            "visualContainerObjects": container(),
            "drillFilterOtherVisuals": True,
        })

    def chart(self, name, kind, x, y, w, h, title, category, values,
              series=None, colors=None, legend=False, labels=False,
              line_values=None):
        qs = {}
        if category:
            qs["Category"] = {"projections": [category]}
        if kind == "lineClusteredColumnComboChart":
            qs["ColumnY"] = {"projections": values}
            if line_values:
                qs["LineY"] = {"projections": line_values}
        elif kind in ("donutChart", "pieChart"):
            qs["Y"] = {"projections": values}
        else:
            qs["Y"] = {"projections": values}
        if series:
            qs["Series"] = {"projections": [series]}

        objs = {"title": title_obj(title)}
        if colors and not series:
            objs["dataPoint"] = [{"properties": {"fill": solid(colors[0])}}]
        objs["legend"] = [{"properties": {"show": lit("true" if legend else "false")}}]
        if labels:
            objs["labels"] = [{"properties": {"show": lit("true"),
                                              "fontSize": dnum(9),
                                              "color": solid(MUTED)}}]
        objs["categoryAxis"] = [{"properties": {"show": lit("true"),
                                                "fontSize": dnum(9),
                                                "labelColor": solid(MUTED),
                                                "showAxisTitle": lit("false")}}]
        objs["valueAxis"] = [{"properties": {"show": lit("true"),
                                             "fontSize": dnum(9),
                                             "labelColor": solid(MUTED),
                                             "showAxisTitle": lit("false")}}]
        self.add(name, x, y, w, h, {
            "visualType": kind,
            "query": {"queryState": qs},
            "objects": objs,
            "visualContainerObjects": container(),
            "drillFilterOtherVisuals": True,
        })

    def table(self, name, x, y, w, h, title, cols):
        self.add(name, x, y, w, h, {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": cols}}},
            "objects": {
                "title": title_obj(title),
                "grid": [{"properties": {"gridVertical": lit("true"),
                                         "gridVerticalColor": solid(LINE),
                                         "gridHorizontalColor": solid(LINE),
                                         "rowPadding": dnum(3)}}],
                "columnHeaders": [{"properties": {"fontColor": solid(CARD),
                                                  "backColor": solid(INK_2),
                                                  "fontSize": dnum(9),
                                                  "bold": lit("true")}}],
                "values": [{"properties": {"fontSize": dnum(9),
                                           "fontColor": solid(INK),
                                           "backColorPrimary": solid(CARD),
                                           "backColorSecondary": solid(PAPER)}}],
            },
            "visualContainerObjects": container(),
            "drillFilterOtherVisuals": True,
        })

    def matrix(self, name, x, y, w, h, title, rows, columns, values):
        self.add(name, x, y, w, h, {
            "visualType": "pivotTable",
            "query": {"queryState": {
                "Rows": {"projections": rows},
                "Columns": {"projections": columns},
                "Values": {"projections": values}}},
            "objects": {
                "title": title_obj(title),
                "columnHeaders": [{"properties": {"fontColor": solid(CARD),
                                                  "backColor": solid(INK_2),
                                                  "fontSize": dnum(9)}}],
                "values": [{"properties": {"fontSize": dnum(9),
                                           "fontColor": solid(INK)}}],
            },
            "visualContainerObjects": container(),
            "drillFilterOtherVisuals": True,
        })

    def slicer(self, name, x, y, w, h, field, title, dropdown=True):
        objs = {"title": title_obj(title, size=9, color=MUTED)}
        if dropdown:
            objs["data"] = [{"properties": {"mode": slit("Dropdown")}}]
        self.add(name, x, y, w, h, {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [field]}}},
            "objects": objs,
            "visualContainerObjects": container(),
            "drillFilterOtherVisuals": True,
        })

    def to_json(self):
        return {
            "$schema": PAGE_SCHEMA,
            "name": self.key,
            "displayName": self.display,
            "displayOption": "FitToPage",
            "width": W,
            "height": H,
            "objects": {
                "background": [{"properties": {"color": solid(PAPER),
                                               "transparency": dnum(0)}}],
                "outspace": [{"properties": {"color": solid(PAPER),
                                             "transparency": dnum(0)}}],
            },
        }


# ===========================================================================
# Layout grid (1600 x 900, 76px header band)
# ===========================================================================
M = 24                      # page margin
GAP = 14
FULL_W = W - 2 * M          # 1552
HALF_W = (FULL_W - GAP) // 2            # 769
TWO_THIRDS = 1030
ONE_THIRD = FULL_W - TWO_THIRDS - GAP   # 508
KPI_W, KPI_STEP, KPI_H = 247, 261, 118
R1_Y = 92
R2_Y = 226
R2_H = 310
R3_Y = 550
R3_H = 326
X2_HALF = M + HALF_W + GAP              # 807
X2_THIRD = M + TWO_THIRDS + GAP         # 1068


def kx(i):
    return M + i * KPI_STEP


# ===========================================================================
# Pages
# ===========================================================================

def page_overview():
    p = Page("pg01Overview", "1 Overview")
    p.band("Preventive Maintenance Control Tower",
           "PM compliance, machine availability and the forward plan, in one view")
    kpis = [
        ("v01KpiCompliance", "PM Compliance %", "PM compliance (of work due)", "PM Compliance % Color"),
        ("v02KpiOverdue", "PM Overdue", "Overdue work orders", None),
        ("v03KpiAvailability", "Availability %", "Machine availability", "Availability % Color"),
        ("v04KpiBreakdowns", "Breakdowns", "Breakdowns reported", None),
        ("v05KpiAbnormal", "Open Abnormalities", "Open abnormalities", "Open Abnormality Color"),
        ("v06KpiDueSoon", "Cells Due Next 3 Months", "Cells due in next 3 months", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.chart("v07TrendCompliance", "lineClusteredColumnComboChart",
            M, R2_Y, TWO_THIRDS, R2_H,
            "PM work orders completed and overdue, with compliance trend",
            fc("Dim_Date", "MonthKey"),
            [fm("PM Completed"), fm("PM Overdue")],
            line_values=[fm("PM Compliance %")], legend=True)

    p.chart("v08CounterByCell", "clusteredBarChart",
            X2_THIRD, R2_Y, ONE_THIRD, R2_H,
            "Hour counter against the 4000 h threshold, by cell",
            fc("Dim_Cell", "CellName"), [fm("% to PM Threshold")],
            colors=[ACCENT], labels=True)

    p.table("v09CellPlan", M, R3_Y, TWO_THIRDS, R3_H,
            "Cell plan - where every counter stands and when the next PM lands",
            [fc("Dim_Cell", "CellName"), fm("Last PM Date"), fm("Months Since Last PM"),
             fm("Current Counter Std Hrs"), fm("Hours to Next PM"),
             fm("% to PM Threshold"), fm("Projected Next PM Date"),
             fm("Projected Trigger Reason")])

    p.chart("v10DowntimeByArea", "donutChart",
            X2_THIRD, R3_Y, ONE_THIRD, R3_H,
            "Unplanned downtime hours by area",
            fc("Dim_Cell", "Area"), [fm("Downtime Hours")], legend=True)
    return p


def page_planning():
    p = Page("pg02Planning", "2 PM Planning")
    p.band("PM Planning - the 4000 standard-hour counter",
           "Standard hours accrue per cell from the monthly upload. At 4000 the whole cell is scheduled; "
           "the calendar backstop catches any cell that has gone 12 months without one")
    kpis = [
        ("v01KpiRunRate", "Run Rate 3M Std Hrs", "Run rate (3-month avg std hrs)", None),
        ("v02KpiStd12M", "Std Hours 12M", "Standard hours, rolling 12 months", None),
        ("v03KpiDuePeriod", "Cells Due In Period", "Cells tripped in period", None),
        ("v04KpiDue3M", "Cells Due Next 3 Months", "Cells due next 3 months", None),
        ("v05KpiHoursTo", "Hours to Next PM", "Std hours to next PM", None),
        ("v06KpiPct", "% to PM Threshold", "Counter vs threshold", "% to PM Threshold Color"),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.table("v07Forecast", M, R2_Y, TWO_THIRDS, R2_H,
            "Forward plan by cell - projection is the earlier of the hour run rate and the calendar backstop",
            [fc("Dim_Cell", "CellName"), fc("Dim_Cell", "Area"),
             fm("Current Counter Std Hrs"), fm("Hours to Next PM"),
             fm("Run Rate 3M Std Hrs"), fm("Months to PM Projected"),
             fm("Projected Next PM Date"), fm("Projected Trigger Reason"),
             fm("Backstop Months Remaining")])

    p.slicer("v08SlicerArea", X2_THIRD, R2_Y, ONE_THIRD, 150,
             fc("Dim_Cell", "Area"), "Area", dropdown=False)
    p.slicer("v09SlicerFY", X2_THIRD, R2_Y + 164, ONE_THIRD, R2_H - 164,
             fc("Dim_Date", "FinancialYear"), "Financial year")

    p.chart("v10StdHoursTrend", "clusteredColumnChart",
            M, R3_Y, TWO_THIRDS, R3_H,
            "Standard hours uploaded per month, by cell",
            fc("Dim_Date", "MonthKey"), [fm("Std Hours")],
            series=fc("Dim_Cell", "CellName"), legend=True)

    p.matrix("v11LedgerMatrix", X2_THIRD, R3_Y, ONE_THIRD, R3_H,
             "Closing counter by cell and month",
             [fc("Dim_Cell", "CellName")], [fc("Dim_Date", "MonthKey")],
             [fm("Current Counter Std Hrs")])
    return p


def page_schedule():
    p = Page("pg03Schedule", "3 Monthly Schedule")
    p.band("Monthly PM Schedule",
           "Every work order the engine has raised, by month, cell and technician")
    kpis = [
        ("v01KpiTotal", "PM Work Orders", "Work orders in view", None),
        ("v02KpiScheduled", "PM Scheduled", "Not started", None),
        ("v03KpiProgress", "PM In Progress", "In progress", None),
        ("v04KpiOverdue", "PM Overdue", "Overdue", None),
        ("v05KpiDeferred", "PM Deferred", "Deferred", None),
        ("v06KpiPlannedHrs", "PM Planned Hours", "Planned wrench hours", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.matrix("v07PlanMatrix", M, R2_Y, TWO_THIRDS, R2_H,
             "Work orders by cell and plan month",
             [fc("Dim_Cell", "CellName")], [fc("Fact_WorkOrders", "PlanMonth")],
             [fm("PM Work Orders")])

    p.chart("v08ByStatus", "clusteredColumnChart",
            X2_THIRD, R2_Y, ONE_THIRD, R2_H,
            "Work orders by status and month",
            fc("Fact_WorkOrders", "PlanMonth"), [fm("PM Work Orders")],
            series=fc("Fact_WorkOrders", "Status"), legend=True)

    p.table("v09WoList", M, R3_Y, FULL_W, R3_H,
            "Work order list",
            [fc("Fact_WorkOrders", "WOID"), fc("Dim_Cell", "CellName"),
             fc("Dim_Machine", "MachineName"), fc("Fact_WorkOrders", "TriggerType"),
             fc("Fact_WorkOrders", "PlannedDate"), fc("Fact_WorkOrders", "DueDate"),
             fc("Fact_WorkOrders", "AssignedTechName"), fc("Fact_WorkOrders", "Shift"),
             fc("Fact_WorkOrders", "Status"), fm("Checklist Completion %"),
             fc("Fact_WorkOrders", "MachineQRScanned")])
    return p


def page_execution():
    p = Page("pg04Execution", "4 Execution & Quality")
    p.band("PM Execution and Checklist Quality",
           "Not just whether the PM was closed - whether it was actually done, and done at the machine")
    kpis = [
        ("v01KpiCompliance", "PM Compliance %", "On-time compliance", "PM Compliance % Color"),
        ("v02KpiCompletion", "PM Completion %", "Completion rate", None),
        ("v03KpiChecklist", "Checklist Completion %", "Checklist answered", None),
        ("v04KpiFailRate", "Checklist Fail Rate %", "Checklist fail rate", None),
        ("v05KpiQr", "QR Verification %", "Closed with a machine scan", None),
        ("v06KpiDuration", "PM Duration vs Std %", "Actual vs standard time", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.chart("v07ComplianceTrend", "lineChart",
            M, R2_Y, HALF_W, R2_H,
            "PM compliance and checklist fail rate by month",
            fc("Dim_Date", "MonthKey"),
            [fm("PM Compliance %"), fm("Checklist Fail Rate %")], legend=True)

    p.chart("v08FailByType", "clusteredBarChart",
            X2_HALF, R2_Y, HALF_W, R2_H,
            "Checklist failures by machine type",
            fc("Dim_Machine", "MachineType"),
            [fm("Checklist Tasks Not OK")], colors=[BAD], labels=True)

    p.table("v09Overdue", M, R3_Y, TWO_THIRDS, R3_H,
            "Open and overdue work orders - oldest first",
            [fc("Fact_WorkOrders", "WOID"), fc("Dim_Machine", "MachineName"),
             fc("Fact_WorkOrders", "DueDate"), fc("Fact_WorkOrders", "AssignedTechName"),
             fc("Fact_WorkOrders", "Status"), fm("Open WO Ageing Days"),
             fc("Fact_WorkOrders", "Remarks")])

    p.chart("v10SafetyFails", "clusteredColumnChart",
            X2_THIRD, R3_Y, ONE_THIRD, R3_H,
            "Safety-critical checklist failures by cell",
            fc("Dim_Cell", "CellName"), [fm("Safety Critical Fails")],
            colors=[BAD], labels=True)
    return p


def page_machine360():
    p = Page("pg05Machine360", "5 Machine 360")
    p.band("Machine 360",
           "The page a machine QR code opens - last PM, history, breakdowns, spares and open abnormalities")

    p.slicer("v01SlicerMachine", M, R1_Y, 300, KPI_H,
             fc("Dim_Machine", "MachineName"), "Machine")
    kpis = [
        ("v02KpiLastPm", "Last PM Date", "Last PM done", None),
        ("v03KpiMonths", "Months Since Last PM", "Months since last PM", None),
        ("v04KpiBreak", "Breakdowns", "Breakdowns", None),
        ("v05KpiDown", "Downtime Hours", "Downtime hours", None),
        ("v06KpiMtbf", "MTBF Hours", "MTBF (hours)", None),
    ]
    x = M + 300 + GAP
    step = (FULL_W - 300 - GAP - 4 * GAP) // 5
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, x + i * (step + GAP), R1_Y, step, KPI_H, meas, label, color_measure=colr)

    p.table("v07PmHistory", M, R2_Y, HALF_W, R2_H,
            "PM history",
            [fc("Fact_WorkOrders", "WOID"), fc("Fact_WorkOrders", "PlanMonth"),
             fc("Fact_WorkOrders", "ActualEndDate"), fc("Fact_WorkOrders", "AssignedTechName"),
             fc("Fact_WorkOrders", "Status"), fc("Fact_WorkOrders", "PMResult"),
             fm("Checklist Completion %")])

    p.table("v08BreakHistory", X2_HALF, R2_Y, HALF_W, R2_H,
            "Breakdown history",
            [fc("Fact_Breakdowns", "BreakdownID"), fc("Fact_Breakdowns", "ReportedDate"),
             fc("Fact_Breakdowns", "FailureMode"), fc("Fact_Breakdowns", "RootCause"),
             fc("Fact_Breakdowns", "DowntimeMinutes"), fc("Fact_Breakdowns", "Status")])

    p.table("v09Spares", M, R3_Y, HALF_W, R3_H,
            "Spares replaced on this machine",
            [fc("Fact_SpareReplacements", "ReplacedDate"), fc("Fact_SpareReplacements", "PartNo"),
             fc("Fact_SpareReplacements", "PartName"), fc("Fact_SpareReplacements", "QtyReplaced"),
             fc("Fact_SpareReplacements", "OldPartCondition"),
             fm("Spare Consumption Value")])

    p.table("v10Abnormal", X2_HALF, R3_Y, HALF_W, R3_H,
            "Abnormalities logged against this machine",
            [fc("Fact_Abnormalities", "AbnormalityID"), fc("Fact_Abnormalities", "ReportedDate"),
             fc("Fact_Abnormalities", "Category"), fc("Fact_Abnormalities", "Severity"),
             fc("Fact_Abnormalities", "Status"), fc("Fact_Abnormalities", "Description")])
    return p


def page_reliability():
    p = Page("pg06Reliability", "6 Reliability")
    p.band("Breakdown and Reliability Analysis",
           "Where the losses are, what causes them, and whether the PM programme is actually preventing them")
    kpis = [
        ("v01KpiBreak", "Breakdowns", "Breakdowns", None),
        ("v02KpiDown", "Downtime Hours", "Downtime hours", None),
        ("v03KpiMttr", "MTTR Hours", "MTTR (hours)", None),
        ("v04KpiMtbf", "MTBF Hours", "MTBF (hours)", None),
        ("v05KpiAvail", "Availability %", "Availability", "Availability % Color"),
        ("v06KpiInduced", "PM Induced Failure %", "Failures within 15d of PM", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.chart("v07Pareto", "clusteredBarChart",
            M, R2_Y, TWO_THIRDS, R2_H,
            "Downtime hours by failure mode - work the top of this list",
            fc("Fact_Breakdowns", "FailureMode"), [fm("Downtime Hours")],
            colors=[BAD], labels=True)

    p.chart("v08MttrTrend", "lineClusteredColumnComboChart",
            X2_THIRD, R2_Y, ONE_THIRD, R2_H,
            "Breakdowns and MTTR by month",
            fc("Dim_Date", "MonthKey"), [fm("Breakdowns")],
            line_values=[fm("MTTR Hours")], legend=True)

    p.table("v09BadActors", M, R3_Y, TWO_THIRDS, R3_H,
            "Bad actors - highest loss machines",
            [fc("Dim_Machine", "MachineName"), fc("Dim_Cell", "CellName"),
             fc("Dim_Machine", "Criticality"), fm("Breakdowns"), fm("Downtime Hours"),
             fm("MTTR Hours"), fm("MTBF Hours"), fm("Availability %"),
             fm("Breakdowns Within 15d of PM")])

    p.chart("v10ByCategory", "donutChart",
            X2_THIRD, R3_Y, ONE_THIRD, R3_H,
            "Breakdowns by failure category",
            fc("Fact_Breakdowns", "FailureCategory"), [fm("Breakdowns")], legend=True)
    return p


def page_spares():
    p = Page("pg07Spares", "7 Spare Parts")
    p.band("Spare Parts - requests, consumption and cost",
           "Requested is not the same as consumed. The gap between the two is where the money leaks")
    kpis = [
        ("v01KpiReqVal", "Spare Request Value", "Requested value", None),
        ("v02KpiConsVal", "Spare Consumption Value", "Consumed value", None),
        ("v03KpiPending", "Pending Approvals", "Pending approvals", None),
        ("v04KpiEmergency", "Emergency Request %", "Emergency requests", None),
        ("v05KpiBelowMin", "Parts Below Min Stock", "Parts below minimum", None),
        ("v06KpiSpendHr", "Spend per Std Hour", "Spend per std hour", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.chart("v07ByCategory", "clusteredBarChart",
            M, R2_Y, HALF_W, R2_H,
            "Consumption value by part category",
            fc("Dim_SparePart", "Category"), [fm("Spare Consumption Value")],
            colors=[ACCENT], labels=True)

    p.chart("v08RequestTrend", "clusteredColumnChart",
            X2_HALF, R2_Y, HALF_W, R2_H,
            "Requests by status and month",
            fc("Dim_Date", "MonthKey"), [fm("Spare Requests")],
            series=fc("Fact_SpareRequests", "Status"), legend=True)

    p.table("v09TopParts", M, R3_Y, HALF_W, R3_H,
            "Top consuming parts",
            [fc("Dim_SparePart", "PartNo"), fc("Dim_SparePart", "PartName"),
             fc("Dim_SparePart", "Category"), fm("Spares Replaced Qty"),
             fm("Spare Consumption Value"), fm("Avg Approval TAT Days")])

    p.table("v10BelowMin", X2_HALF, R3_Y, HALF_W, R3_H,
            "Stock below minimum as at the last stock upload",
            [fc("Dim_SparePart", "PartNo"), fc("Dim_SparePart", "PartName"),
             fc("Dim_SparePart", "CurrentStock"), fc("Dim_SparePart", "MinStock"),
             fc("Dim_SparePart", "LeadTimeDays"), fc("Dim_SparePart", "StoreBin")])
    return p


def page_abnormality():
    p = Page("pg08Abnormality", "8 Abnormalities")
    p.band("Abnormality Log",
           "The early warning layer. Every one of these is a breakdown that has not happened yet")
    kpis = [
        ("v01KpiTotal", "Abnormalities", "Logged", None),
        ("v02KpiOpen", "Open Abnormalities", "Open", "Open Abnormality Color"),
        ("v03KpiHigh", "High Severity Open", "High severity open", None),
        ("v04KpiAged", "Abnormalities Open Over 30d", "Open beyond 30 days", None),
        ("v05KpiClosure", "Abnormality Closure %", "Closure rate", None),
        ("v06KpiDays", "Avg Abnormality Closure Days", "Avg days to close", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.chart("v07ByCategory", "clusteredBarChart",
            M, R2_Y, HALF_W, R2_H,
            "Abnormalities by category",
            fc("Fact_Abnormalities", "Category"), [fm("Abnormalities")],
            colors=[WARN], labels=True)

    p.chart("v08BySeverity", "clusteredColumnChart",
            X2_HALF, R2_Y, HALF_W, R2_H,
            "Abnormalities raised by month and severity",
            fc("Dim_Date", "MonthKey"), [fm("Abnormalities")],
            series=fc("Fact_Abnormalities", "Severity"), legend=True)

    p.table("v09OpenList", M, R3_Y, FULL_W, R3_H,
            "Open abnormalities",
            [fc("Fact_Abnormalities", "AbnormalityID"), fc("Fact_Abnormalities", "ReportedDate"),
             fc("Dim_Machine", "MachineName"), fc("Dim_Cell", "CellName"),
             fc("Fact_Abnormalities", "Category"), fc("Fact_Abnormalities", "Severity"),
             fc("Fact_Abnormalities", "Description"), fc("Fact_Abnormalities", "ReportedByName"),
             fc("Fact_Abnormalities", "Status"), fc("Fact_Abnormalities", "OwnerFunction")])
    return p


def page_technician():
    p = Page("pg09Technician", "9 Technician")
    p.band("Technician Workload and Performance",
           "Load balance first, performance second - an overloaded technician is a compliance problem, not an attitude problem")
    kpis = [
        ("v01KpiHeadcount", "Technicians Active", "Technicians active", None),
        ("v02KpiWoPer", "WOs per Technician", "Work orders per person", None),
        ("v03KpiWrench", "PM Wrench Hours", "Wrench hours", None),
        ("v04KpiCapacity", "Technician Capacity Hours", "Capacity hours", None),
        ("v05KpiUtil", "Technician Utilisation %", "Utilisation", None),
        ("v06KpiScans", "Machine Scans", "Machine QR scans", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.chart("v07LoadByTech", "clusteredColumnChart",
            M, R2_Y, HALF_W, R2_H,
            "Wrench hours against capacity, by technician",
            fc("Dim_Technician", "TechName"),
            [fm("PM Wrench Hours"), fm("Technician Capacity Hours")], legend=True)

    p.chart("v08ComplianceByTech", "clusteredBarChart",
            X2_HALF, R2_Y, HALF_W, R2_H,
            "On-time compliance by technician",
            fc("Dim_Technician", "TechName"), [fm("PM Compliance %")],
            colors=[GOOD], labels=True)

    p.table("v09Scorecard", M, R3_Y, FULL_W, R3_H,
            "Technician scorecard",
            [fc("Dim_Technician", "TechName"), fc("Dim_Technician", "Shift"),
             fc("Dim_Technician", "SkillGroup"), fc("Dim_Technician", "PrimaryArea"),
             fm("PM Work Orders"), fm("PM Completed"), fm("PM Compliance %"),
             fm("PM Wrench Hours"), fm("Technician Utilisation %"),
             fm("Checklist Fail Rate %"), fm("Machine Scans")])
    return p


def page_data_quality():
    p = Page("pg10DataQuality", "10 Data Quality")
    p.band("Data Quality and Refresh",
           "The dashboard is only as honest as its inputs. Everything on this page should read zero")
    kpis = [
        ("v01KpiIssues", "Data Quality Issues", "Total issues", "Data Quality Color"),
        ("v02KpiMissing", "Missing Std Hours Rows", "Missing upload rows", None),
        ("v03KpiDesk", "Desk Closed WOs", "Closed without a scan", None),
        ("v04KpiNoChecklist", "WOs Without Checklist", "No checklist evidence", None),
        ("v05KpiLatest", "Latest Std Hours Month", "Latest upload month", None),
        ("v06KpiAsOf", "Data As Of", "Data as of", None),
    ]
    for i, (n, meas, label, colr) in enumerate(kpis):
        p.kpi(n, kx(i), R1_Y, KPI_W, KPI_H, meas, label, color_measure=colr)

    p.matrix("v07UploadMatrix", M, R2_Y, FULL_W, R2_H,
             "Standard hours uploaded, by cell and month - any blank cell is a missing upload",
             [fc("Dim_Cell", "CellName")], [fc("Dim_Date", "MonthKey")],
             [fm("Std Hours")])

    p.table("v08DeskClosed", M, R3_Y, HALF_W, R3_H,
            "Completed work orders with no machine QR scan",
            [fc("Fact_WorkOrders", "WOID"), fc("Dim_Machine", "MachineName"),
             fc("Fact_WorkOrders", "ActualEndDate"), fc("Fact_WorkOrders", "AssignedTechName"),
             fc("Fact_WorkOrders", "MachineQRScanned"), fm("Checklist Completion %")])

    p.note("v09RefreshNote", X2_HALF, R3_Y, HALF_W, R3_H,
           "Refresh and ownership\n\n"
           "The semantic model refreshes three times a day (06:00, 14:00, 22:00 IST). "
           "SharePoint lists and workbooks in Microsoft 365 refresh from the cloud, so no gateway is needed.\n\n"
           "Missing upload rows: chase Production Planning. Until a cell's hours are loaded, its counter "
           "does not move and no PM will ever be scheduled for it.\n\n"
           "Closed without a scan: the technician closed the job without being at the machine, or the "
           "QR label is damaged. Check the label first, then have the conversation.\n\n"
           "No checklist evidence: the work order was closed outside the app. This should be impossible "
           "once item-level permissions are set correctly.", size=10, color=INK)
    return p


PAGES = [page_overview, page_planning, page_schedule, page_execution,
         page_machine360, page_reliability, page_spares, page_abnormality,
         page_technician, page_data_quality]

# ===========================================================================
# Theme
# ===========================================================================

def theme() -> dict:
    return {
        "name": "PM Industrial",
        "dataColors": SERIES,
        "background": PAPER,
        "backgroundLight": CARD,
        "backgroundNeutral": LINE,
        "foreground": INK,
        "foregroundNeutralSecondary": MUTED,
        "foregroundNeutralTertiary": LINE,
        "tableAccent": ACCENT,
        "good": GOOD,
        "neutral": WARN,
        "bad": BAD,
        "maximum": ACCENT,
        "minimum": "#E4EDF2",
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 14, "color": INK},
            "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": MUTED},
            "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 30, "color": INK},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": INK},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": CARD}},
                                    "transparency": 0}],
                    "border": [{"show": True, "color": {"solid": {"color": LINE}},
                                "radius": 8}],
                    "dropShadow": [{"show": False}],
                    "visualHeader": [{"show": False}],
                    "title": [{"show": True, "fontColor": {"solid": {"color": INK}},
                               "fontSize": 11, "fontFamily": "Segoe UI Semibold",
                               "alignment": "left"}],
                    "labels": [{"fontSize": 9, "color": {"solid": {"color": MUTED}}}],
                    "legend": [{"fontSize": 9, "labelColor": {"solid": {"color": MUTED}},
                                "position": "TopCenter", "showTitle": False}],
                    "categoryAxis": [{"fontSize": 9,
                                      "labelColor": {"solid": {"color": MUTED}},
                                      "showAxisTitle": False,
                                      "gridlineShow": False}],
                    "valueAxis": [{"fontSize": 9,
                                   "labelColor": {"solid": {"color": MUTED}},
                                   "showAxisTitle": False,
                                   "gridlineColor": {"solid": {"color": LINE}},
                                   "gridlineStyle": "dotted"}],
                }
            },
            "page": {"*": {"background": [{"color": {"solid": {"color": PAPER}},
                                           "transparency": 0}],
                           "outspace": [{"color": {"solid": {"color": PAPER}},
                                         "transparency": 0}]}},
            "tableEx": {"*": {
                "columnHeaders": [{"fontColor": {"solid": {"color": CARD}},
                                   "backColor": {"solid": {"color": INK_2}},
                                   "fontSize": 9, "bold": True}],
                "values": [{"fontSize": 9, "fontColor": {"solid": {"color": INK}},
                            "backColorPrimary": {"solid": {"color": CARD}},
                            "backColorSecondary": {"solid": {"color": PAPER}}}],
                "grid": [{"gridVerticalColor": {"solid": {"color": LINE}},
                          "gridHorizontalColor": {"solid": {"color": LINE}},
                          "rowPadding": 3}],
            }},
            "pivotTable": {"*": {
                "columnHeaders": [{"fontColor": {"solid": {"color": CARD}},
                                   "backColor": {"solid": {"color": INK_2}},
                                   "fontSize": 9}],
                "values": [{"fontSize": 9, "fontColor": {"solid": {"color": INK}}}],
            }},
            "lineChart": {"*": {"lineStyles": [{"strokeWidth": 2.5,
                                                "showMarker": True,
                                                "markerSize": 4}]}},
        },
    }


# ===========================================================================
# Report
# ===========================================================================

def build_report(base: str, inject: bool = False) -> None:
    rp = os.path.join(base, f"{NAME}.Report")
    defn = os.path.join(rp, "definition")
    pages_dir = os.path.join(defn, "pages")

    if not inject:
        wj(os.path.join(rp, ".platform"), {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": NAME},
            "config": {"version": "2.0", "logicalId": uid()},
        })
        wj(os.path.join(rp, "definition.pbir"), {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                       "report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
        })
        # Deliberately references nothing on disk. Every resourcePackages entry
        # and every custom themeCollection entry names a file that must exist,
        # and getting those wrong is what "required artifact is missing" means.
        # The theme is imported by hand instead; INSTALL.cmd keeps Desktop's own
        # report.json, which already has its resource wiring correct.
        wj(os.path.join(defn, "report.json"), {
            "$schema": REPORT_SCHEMA,
            "settings": {
                "useStylableVisualContainerHeader": True,
                "defaultDropInteraction": "Filter",
                "useNewFilterPaneExperience": True,
                "allowChangeFilterTypes": True,
            },
        })

    # theme is always also shipped standalone, for manual import
    wj(os.path.join(base, "theme", "PM_Theme.json"), theme())

    # wipe only the pages this script owns
    built = [f() for f in PAGES]
    for p in built:
        d = os.path.join(pages_dir, p.key)
        if os.path.isdir(d):
            shutil.rmtree(d)

    n_vis = 0
    for p in built:
        d = os.path.join(pages_dir, p.key)
        wj(os.path.join(d, "page.json"), p.to_json())
        for v in p.visuals:
            wj(os.path.join(d, "visuals", v["name"], "visual.json"), v)
            n_vis += 1

    pages_json_path = os.path.join(pages_dir, "pages.json")
    order = [p.key for p in built]
    if inject and os.path.exists(pages_json_path):
        with open(pages_json_path, encoding="utf-8") as f:
            existing = json.load(f)
        keep = [k for k in existing.get("pageOrder", []) if k not in order]
        existing["pageOrder"] = keep + order
        existing.setdefault("activePageName", order[0])
        wj(pages_json_path, existing)
    else:
        wj(pages_json_path, {"$schema": PAGES_SCHEMA,
                             "pageOrder": order,
                             "activePageName": order[0]})

    print(f"  report: {len(built)} pages, {n_vis} visuals")


def package(base: str) -> None:
    """Rezip the project on every build, so the downloadable archive can never
    drift from what is in powerbi/."""
    out = os.path.join(ROOT, "PM_Dashboard_pbip")
    archive = shutil.make_archive(out, "zip", root_dir=base)
    size = os.path.getsize(archive) / 1024
    print(f"  package: {os.path.basename(archive)} ({size:.0f} KB)")


def copy_local_data(base: str) -> None:
    """Put a copy of the dummy CSVs next to the .pbip so the project is
    self-contained: one folder to point LocalDataFolder at."""
    dest = os.path.join(base, "data")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(DATA, dest)
    n = len([f for f in os.listdir(dest) if f.endswith(".csv")])
    print(f"  local data: {n} CSVs copied to powerbi/data/")

    # keep the open-and-connect instructions next to the file they describe
    src_doc = os.path.join(ROOT, "docs", "11-opening-the-pbip.md")
    if os.path.exists(src_doc):
        shutil.copyfile(src_doc, os.path.join(base, "SETUP.md"))
        print("  setup guide: powerbi/SETUP.md")

    # Windows helpers. Batch files need CRLF or cmd.exe mangles multi-line blocks.
    counts = {
        "__NTMDL__": len([f for f in os.listdir(os.path.join(
            base, f"{NAME}.SemanticModel", "definition", "tables")) if f.endswith(".tmdl")]),
        "__NPAGES__": len([d for d in os.listdir(os.path.join(
            base, f"{NAME}.Report", "definition", "pages")) if d.startswith("pg")]),
        "__NVIS__": sum(1 for _r, _d, fs in os.walk(os.path.join(
            base, f"{NAME}.Report", "definition", "pages")) for f in fs if f == "visual.json"),
        "__NCSV__": len([f for f in os.listdir(dest) if f.endswith(".csv")]),
        "__NTABLES__": len(TABLES) + 1,
        "__NMEAS__": len(MEASURES),
        "__NREL__": len(RELATIONSHIPS),
    }
    for src_name, dst_name in (("win_check.cmd", "CHECK.cmd"),
                               ("win_install.cmd", "INSTALL.cmd")):
        src = os.path.join(HERE, src_name)
        if not os.path.exists(src):
            continue
        text = open(src, encoding="utf-8").read()
        for k, v in counts.items():
            text = text.replace(k, str(v))
        assert "__N" not in text, f"{src_name} has an unsubstituted count placeholder"
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        with open(os.path.join(base, dst_name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    print("  windows helpers: powerbi/CHECK.cmd, powerbi/INSTALL.cmd")


def validate(base: str) -> bool:
    ok = True
    for root, _dirs, files in os.walk(base):
        for fn in files:
            if fn.endswith(".json"):
                path = os.path.join(root, fn)
                try:
                    with open(path, encoding="utf-8") as f:
                        json.load(f)
                except Exception as e:  # noqa: BLE001
                    print(f"  INVALID JSON: {path}: {e}")
                    ok = False
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", metavar="PBIP_PATH",
                    help="Write into an existing Power BI Desktop project instead of "
                         "generating a standalone one. Pass the .pbip file or its folder.")
    args = ap.parse_args()

    if args.inject:
        target = args.inject
        base = os.path.dirname(os.path.abspath(target)) if target.endswith(".pbip") \
            else os.path.abspath(target)
        print(f"\nInjecting into existing project: {base}")
        build_semantic_model(base)
        build_report(base, inject=True)
    else:
        base = os.path.join(ROOT, "powerbi")
        print(f"\nBuilding standalone project: {base}")
        os.makedirs(base, exist_ok=True)
        wj(os.path.join(base, f"{NAME}.pbip"), {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/"
                       "pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        })
        build_semantic_model(base)
        build_report(base)
        copy_local_data(base)

    print("  validating JSON ...")
    ok = validate(base)
    print("  all JSON valid" if ok else "  FIX THE ERRORS ABOVE")

    if not args.inject and ok:
        package(base)
    print()


if __name__ == "__main__":
    main()
