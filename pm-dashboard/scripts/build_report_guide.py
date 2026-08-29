#!/usr/bin/env python3
"""
build_report_guide.py - generates the visual-by-visual build sheet for the report.

Generated from the same page definitions that produce the PBIR files, so the
hand-build route and the generated project cannot describe different reports.

Run:  python3 scripts/build_report_guide.py
Out:  docs/13-report-build-guide.md
"""
from __future__ import annotations
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_pbip as B  # noqa: E402

VISUAL_UI = {
    "cardVisual": "Card (new card)",
    "clusteredColumnChart": "Clustered column chart",
    "clusteredBarChart": "Clustered bar chart",
    "lineChart": "Line chart",
    "lineClusteredColumnComboChart": "Line and clustered column chart",
    "donutChart": "Donut chart",
    "tableEx": "Table",
    "pivotTable": "Matrix",
    "slicer": "Slicer",
    "textbox": "Text box",
}

# query role -> the field well Power BI shows for that visual type
WELLS = {
    "cardVisual": {"Data": "Fields", "ReferenceLabels": "Reference labels",
                   "AdditionalMeasure": "Additional measure"},
    "clusteredColumnChart": {"Category": "X-axis", "Y": "Y-axis", "Series": "Legend"},
    "clusteredBarChart": {"Category": "Y-axis", "Y": "X-axis", "Series": "Legend"},
    "lineChart": {"Category": "X-axis", "Y": "Y-axis", "Series": "Legend"},
    "lineClusteredColumnComboChart": {"Category": "X-axis", "ColumnY": "Column y-axis",
                                      "LineY": "Line y-axis", "Series": "Column legend"},
    "donutChart": {"Category": "Legend", "Y": "Values"},
    "tableEx": {"Values": "Columns"},
    "pivotTable": {"Rows": "Rows", "Columns": "Columns", "Values": "Values"},
    "slicer": {"Values": "Field"},
}


def literal(node):
    try:
        v = node["expr"]["Literal"]["Value"]
        return v[1:-1] if v.startswith("'") and v.endswith("'") else v
    except Exception:
        return None


def title_of(v):
    t = v["visual"].get("objects", {}).get("title")
    return literal(t[0]["properties"]["text"]) if t else None


def textbox_text(v):
    try:
        paras = v["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
        return "\n".join("".join(r.get("value", "") for r in p.get("textRuns", []))
                         for p in paras)
    except Exception:
        return ""


out = ["# 13 · Report Build Guide",
       "",
       "Every page and every visual, in build order, with the exact fields to drop into "
       "each well. Build this by hand in Power BI Desktop — it does not depend on any "
       "file format matching your version.",
       "",
       "> Generated from the same page definitions that produce the project files, so the "
       "two cannot describe different reports.",
       "",
       "## Before you start", "",
       "1. Finish the semantic model first: all 17 tables loaded, 28 relationships made, "
       "all 94 measures created. See `12-model-build-guide.md`.",
       "2. **View ▸ Themes ▸ Browse for themes** ▸ `PM_Theme.json`. Do this before "
       "building visuals so every new visual picks up the fonts and colours.",
       "3. Set the canvas on every page: **Format ▸ Canvas settings ▸ Type = Custom, "
       "Height 900, Width 1600**.",
       "4. Turn off the visual header in reading view: **File ▸ Options ▸ Current file ▸ "
       "Report settings**.",
       "",
       "## How to read this", "",
       "Positions are in the same units Power BI shows under **Format ▸ General ▸ "
       "Properties ▸ Position and size**. Typing them in is faster and tidier than "
       "dragging, and it is what makes every page line up.",
       "",
       "Where a field is written `Table[Column]` drag that column. Where it is written "
       "`[Measure]` drag the measure from the `_Measures` table.",
       "",
       "---", ""]

n_pages = n_vis = 0
for factory in B.PAGES:
    p = factory()
    n_pages += 1
    out += [f"## Page {p.display}", "",
            f"Rename the page tab to **{p.display}**.", "",
            "| Visual | Type | Position (x, y, w, h) |",
            "|--------|------|------------------------|"]
    for v in p.visuals:
        vt = v["visual"]["visualType"]
        pos = v["position"]
        label = title_of(v) or ("header band" if v["name"] == "v00Header" else "—")
        out.append(f"| {v['name']} | {VISUAL_UI.get(vt, vt)} | "
                   f"{pos['x']}, {pos['y']}, {pos['width']}, {pos['height']} |")
    out.append("")

    for v in p.visuals:
        vt = v["visual"]["visualType"]
        pos = v["position"]
        n_vis += 1
        out += [f"### `{v['name']}` — {VISUAL_UI.get(vt, vt)}", "",
                f"Position and size: **x {pos['x']}, y {pos['y']}, "
                f"width {pos['width']}, height {pos['height']}**", ""]
        t = title_of(v)
        if t:
            out += [f"Title: **{t}**", ""]
        if vt == "textbox":
            txt = textbox_text(v)
            if txt:
                out += ["Text box content:", "", "```", txt, "```", "",
                        "Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. "
                        "First line 20pt bold white, second line 10pt `#A9C2D0`.", ""]
            out += ["---", ""]
            continue

        qs = v["visual"].get("query", {}).get("queryState", {})
        if qs:
            wells = WELLS.get(vt, {})
            out += ["| Field well | Drop in |", "|------------|---------|"]
            for role, block in qs.items():
                fields = []
                for proj in block["projections"]:
                    ref = proj["queryRef"]
                    tbl, col = ref.split(".", 1)
                    fields.append(f"`[{col}]`" if tbl == "_Measures" else f"`{tbl}[{col}]`")
                out.append(f"| {wells.get(role, role)} | {', '.join(fields)} |")
            out.append("")

        objs = v["visual"].get("objects", {})
        notes = []
        if "dataPoint" in objs:
            c = literal(objs["dataPoint"][0]["properties"]["fill"]["solid"]["color"])
            if c:
                notes.append(f"Format ▸ Columns/Bars ▸ Colour: `{c}`")
        if "legend" in objs:
            shown = literal(objs["legend"][0]["properties"]["show"]) == "true"
            notes.append(f"Legend: **{'on' if shown else 'off'}**")
        if "labels" in objs:
            notes.append("Data labels: **on**, 9pt")
        if "calloutValue" in objs:
            col = objs["calloutValue"][0]["properties"].get("color", {})
            m = col.get("solid", {}).get("color", {}).get("expr", {}).get("Measure", {})
            if m:
                notes.append(f"Callout value ▸ Colour ▸ **fx** ▸ Format style "
                             f"*Field value* ▸ `[{m['Property']}]`")
            notes.append("Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**")
        if vt in ("tableEx", "pivotTable"):
            notes.append("Column headers `#173C52` background, white bold 9pt. "
                         "Values 9pt, alternating rows `#F2F5F7`")
        if "data" in objs and vt == "slicer":
            notes.append("Slicer settings ▸ Style: **Dropdown**")
        if notes:
            out += ["Formatting:", ""] + [f"- {n}" for n in notes] + [""]
        out += ["---", ""]

out += ["## After every page is built", "",
        "1. **View ▸ Page view ▸ Fit to page** on each page.",
        "2. Set tab order on each page: **View ▸ Selection ▸ Tab order**, top-left to "
        "bottom-right. Screen readers follow this.",
        "3. Add alt text to every chart: **Format ▸ General ▸ Alt text**. The generator "
        "cannot write anything meaningful for you and a chart with no alt text is "
        "invisible to a screen reader.",
        "4. Page 5 (Machine 360) uses a machine slicer. To make it a drillthrough target "
        "as well: select the page, then drag `Dim_Machine[MachineID]` into the "
        "**Drillthrough** well in the Visualizations pane.",
        "5. Save. If you save as `.pbix` none of the file-format problems in "
        "`11-opening-the-pbip.md` apply to you at all.",
        ""]

path = os.path.join(ROOT, "docs", "13-report-build-guide.md")
open(path, "w", encoding="utf-8").write("\n".join(out))
print(f"  docs/13-report-build-guide.md  ({n_pages} pages, {n_vis} visuals, "
      f"{len(out)} lines)")
