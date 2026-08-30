"""
build_report.py
---------------
Writes the PBIR report definition for PM_Dashboard.Report: nine pages, their
visuals, the theme registration and the report-level settings.

Layout follows one grid and does not deviate from it:
    canvas 1280 x 720, 24 px page margin, 12 columns, 16 px gutters
    column width 88, so an n-column span is 88n + 16(n-1)
    x of column i is 24 + 104i

Every visual gets a plain-English title stating the question it answers. A title
that says "Sum of Actual_Std_Hours" tells a reader what the field is called; a
title that says "Which cells will hit 4,000 hours in the next 90 days?" tells
them why they are looking at it.

    python tools/build_report.py
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PBI = os.path.join(ROOT, "powerbi")
NAME = "PM_Dashboard"
RPT = os.path.join(PBI, f"{NAME}.Report")
DEF = os.path.join(RPT, "definition")

VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.0.0/schema.json"
PG_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json"
PGS_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
RPT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json"

M = "_Measures"

# --- palette (mirrors theme/EPQPL_PM_Theme.json) ---------------------------
PRIMARY, ACCENT = "#0C3549", "#2E86AB"
GOOD, WARN, BAD = "#44C088", "#F0A202", "#ED7373"
TEXT, MUTED = "#1F2933", "#7B8794"
CARD, LINE = "#FFFFFF", "#E1E8EB"

# --- grid ------------------------------------------------------------------
def cw(n):        # width of an n-column span
    return 88 * n + 16 * (n - 1)


def cx(i):        # x of column index i (0-based)
    return 24 + 104 * i


HEADER_H = 62
KPI_Y, KPI_H = 74, 104
ROW2_Y = 194
FOOT_H = 40
FOOT_Y = 720 - 24 - FOOT_H


def kpi_x(i):
    """5 equal cards across the full content width."""
    w = (1232 - 4 * 16) // 5
    return 24 + (w + 16) * i, w


# --- field reference helpers -----------------------------------------------
def meas(name, table=M):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": table}},
                                  "Property": name}},
            "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def col(table, name):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}},
                                 "Property": name}},
            "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": f"'{v}'"}}}


def solid(hexcolor):
    return {"expr": {"ThemeDataColor": {"ColorId": 0, "Percent": 0}}} if hexcolor is None else \
        {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hexcolor}'"}}}}}


def color_by_measure(name, table=M):
    """Conditional colour driven by a DAX measure that returns a hex string."""
    return {"solid": {"color": {"expr": {"Measure": {
        "Expression": {"SourceRef": {"Entity": table}}, "Property": name}}}}}


def title_measure(name, table=M):
    """Marker for a title driven by a DAX measure rather than a literal string."""
    return {"__measure__": name, "__table__": table}


def title_obj(text, subtitle=None):
    # A title can be a literal or a measure that restates the live figure. A title
    # that moves with the filter gets read; a static one becomes wallpaper.
    if isinstance(text, dict) and "__measure__" in text:
        text_expr = {"expr": {"Measure": {
            "Expression": {"SourceRef": {"Entity": text["__table__"]}},
            "Property": text["__measure__"]}}}
    else:
        text_expr = lit(text)
    o = {"title": [{"properties": {
        "show": lit(True),
        "text": text_expr,
        "fontSize": lit(12),
        "fontColor": {"expr": {"Literal": {"Value": f"'{PRIMARY}'"}}},
        "alignment": lit("left"),
        "titleWrap": lit(True),
    }}]}
    if subtitle:
        o["subTitle"] = [{"properties": {
            "show": lit(True), "text": lit(subtitle), "fontSize": lit(9),
            "fontColor": {"expr": {"Literal": {"Value": f"'{MUTED}'"}}},
            "alignment": lit("left"),
        }}]
    return o


def container(name, x, y, w, h, z, tab, visual_type, query=None, objects=None,
              extra=None, hidden=False):
    v = {"visualType": visual_type, "drillFilterOtherVisuals": True}
    if query:
        v["query"] = {"queryState": query}
    if objects:
        v["objects"] = objects
    if extra:
        v.update(extra)
    c = {
        "$schema": VC_SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": tab},
        "visual": v,
    }
    if hidden:
        c["isHidden"] = True
    return c


def textbox(name, x, y, w, h, z, tab, runs, background=None, border=False):
    """runs = list of (text, size, colour, bold)."""
    paragraphs = [{"textRuns": [
        {"value": t,
         "textStyle": {"fontSize": f"{sz}pt", "color": c,
                       "fontWeight": "bold" if b else "normal",
                       "fontFamily": "Segoe UI"}}
        for (t, sz, c, b) in runs]}]
    objects = {"general": [{"properties": {"paragraphs": paragraphs}}]}
    if background:
        objects["background"] = [{"properties": {"show": lit(True), "color": solid(background),
                                                 "transparency": lit(0)}}]
    else:
        objects["background"] = [{"properties": {"show": lit(False)}}]
    objects["border"] = [{"properties": {"show": lit(bool(border)),
                                         "color": solid(LINE), "radius": lit(8)}}]
    objects["dropShadow"] = [{"properties": {"show": lit(False)}}]
    return container(name, x, y, w, h, z, tab, "textbox", objects=objects)


def page_header(title, question, page_no):
    """Dark band across the top, with the page's question as the subtitle."""
    band = container(
        "v00HeaderBand", 0, 0, 1280, HEADER_H, 100, 0, "shape",
        objects={
            "general": [{"properties": {"shapeType": lit("rectangle")}}],
            "fill": [{"properties": {"show": lit(True), "fillColor": solid(PRIMARY),
                                     "transparency": lit(0)}}],
            "outline": [{"properties": {"show": lit(False)}}],
            "dropShadow": [{"properties": {"show": lit(False)}}],
        })
    text = textbox("v01HeaderText", 24, 8, 900, 48, 101, 1, [
        (title, 15, "#FFFFFF", True),
        ("     " + question, 10, "#B9CBD4", False),
    ])
    stamp = textbox("v02HeaderStamp", 940, 18, 316, 30, 102, 2, [
        (f"EPQPL Pondicherry  ·  Preventive Maintenance  ·  Page {page_no} of 9",
         8, "#8FAAB8", False),
    ])
    return [band, text, stamp]


def footnote(name, lines, tab=90):
    """
    The 'how this is calculated' panel.

    Rendered as an always-visible footnote rather than a bookmark-toggled
    overlay. That is a deliberate trade: a footnote cannot be left switched off
    by the last person who used the report, and it survives a Desktop version
    change that a bookmark's stored exploration state may not.
    README_PowerBI.md documents how to convert it to a toggled panel if you
    prefer one.
    """
    runs = [("How this is calculated   ", 8, PRIMARY, True)]
    runs += [(l + "   ", 8, MUTED, False) for l in lines]
    return textbox(name, 24, FOOT_Y, 1232, FOOT_H, 90, tab, runs,
                   background=CARD, border=True)


def kpi_card(name, idx, tab, measure, label, colour_measure=None, ref_measure=None):
    x, w = kpi_x(idx)
    q = {"Values": {"projections": [meas(measure)]}}
    if ref_measure:
        q = {"Data": {"projections": [meas(measure)]},
             "ReferenceLabels": {"projections": [meas(ref_measure)]}}
    callout = {"fontSize": lit(28), "fontFamily": lit("Segoe UI Semibold")}
    if colour_measure:
        callout["color"] = color_by_measure(colour_measure)
    else:
        callout["color"] = solid(PRIMARY)
    objects = {
        "labels": [{"properties": callout}],
        "categoryLabels": [{"properties": {
            "show": lit(True), "fontSize": lit(9), "color": solid(MUTED)}}],
        "title": [{"properties": {"show": lit(True), "text": lit(label),
                                  "fontSize": lit(9), "alignment": lit("left"),
                                  "fontColor": {"expr": {"Literal": {"Value": f"'{MUTED}'"}}}}}],
        "border": [{"properties": {"show": lit(True), "color": solid(LINE), "radius": lit(8)}}],
    }
    return container(name, x, KPI_Y, w, KPI_H, 1000 + idx, tab, "card", q, objects)


def bar(name, x, y, w, h, z, tab, category, values, title, subtitle=None,
        visual="clusteredBarChart", series=None, data_labels=True,
        colour_measure=None, sort_desc_by=None):
    q = {"Category": {"projections": [category]},
         "Y": {"projections": values}}
    if series:
        q["Series"] = {"projections": [series]}
    objects = title_obj(title, subtitle)
    objects["labels"] = [{"properties": {"show": lit(bool(data_labels)), "fontSize": lit(9)}}]
    objects["categoryAxis"] = [{"properties": {"show": lit(True), "showAxisTitle": lit(False),
                                               "gridlineShow": lit(False), "fontSize": lit(9)}}]
    objects["valueAxis"] = [{"properties": {"show": lit(True), "showAxisTitle": lit(False),
                                            "gridlineShow": lit(False), "fontSize": lit(9)}}]
    if colour_measure:
        objects["dataPoint"] = [{"properties": {"fill": color_by_measure(colour_measure)}}]
    extra = {}
    if sort_desc_by:
        extra["sortDefinition"] = {"sort": [{"field": values[0]["field"], "direction": "Descending"}],
                                   "isDefaultSort": True}
    return container(name, x, y, w, h, z, tab, visual, q, objects, extra or None)


def column_chart(name, x, y, w, h, z, tab, category, values, title, subtitle=None,
                 visual="clusteredColumnChart", series=None):
    return bar(name, x, y, w, h, z, tab, category, values, title, subtitle,
               visual=visual, series=series)


def line(name, x, y, w, h, z, tab, category, values, title, subtitle=None):
    q = {"Category": {"projections": [category]}, "Y": {"projections": values}}
    objects = title_obj(title, subtitle)
    objects["labels"] = [{"properties": {"show": lit(True), "fontSize": lit(9)}}]
    objects["categoryAxis"] = [{"properties": {"show": lit(True), "showAxisTitle": lit(False),
                                               "gridlineShow": lit(False), "fontSize": lit(9),
                                               "concatenateLabels": lit(False)}}]
    objects["valueAxis"] = [{"properties": {"show": lit(True), "showAxisTitle": lit(False),
                                            "gridlineShow": lit(False), "fontSize": lit(9)}}]
    objects["lineStyles"] = [{"properties": {"strokeWidth": lit(3), "showMarker": lit(True)}}]
    return container(name, x, y, w, h, z, tab, "lineChart", q, objects)


def combo(name, x, y, w, h, z, tab, category, col_vals, line_vals, title, subtitle=None):
    q = {"Category": {"projections": [category]},
         "ColumnY": {"projections": col_vals},
         "LineY": {"projections": line_vals}}
    objects = title_obj(title, subtitle)
    objects["labels"] = [{"properties": {"show": lit(True), "fontSize": lit(9)}}]
    objects["categoryAxis"] = [{"properties": {"show": lit(True), "showAxisTitle": lit(False),
                                               "gridlineShow": lit(False), "fontSize": lit(9)}}]
    return container(name, x, y, w, h, z, tab, "lineClusteredColumnComboChart", q, objects)


def table(name, x, y, w, h, z, tab, projections, title, subtitle=None):
    q = {"Values": {"projections": projections}}
    objects = title_obj(title, subtitle)
    objects["grid"] = [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True),
                                       "rowPadding": lit(3)}}]
    objects["columnHeaders"] = [{"properties": {"fontSize": lit(9), "wordWrap": lit(True)}}]
    objects["values"] = [{"properties": {"fontSize": lit(9)}}]
    return container(name, x, y, w, h, z, tab, "tableEx", q, objects)


def matrix(name, x, y, w, h, z, tab, rows, columns, values, title, subtitle=None):
    q = {"Rows": {"projections": rows}, "Values": {"projections": values}}
    if columns:
        q["Columns"] = {"projections": columns}
    objects = title_obj(title, subtitle)
    objects["grid"] = [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True),
                                       "rowPadding": lit(3)}}]
    objects["columnHeaders"] = [{"properties": {"fontSize": lit(9)}}]
    objects["values"] = [{"properties": {"fontSize": lit(9)}}]
    objects["rowHeaders"] = [{"properties": {"fontSize": lit(9)}}]
    return container(name, x, y, w, h, z, tab, "pivotTable", q, objects)


def donut(name, x, y, w, h, z, tab, category, value, title, subtitle=None):
    q = {"Category": {"projections": [category]}, "Y": {"projections": [value]}}
    objects = title_obj(title, subtitle)
    objects["labels"] = [{"properties": {"show": lit(True), "fontSize": lit(9),
                                         "labelStyle": lit("Both")}}]
    objects["legend"] = [{"properties": {"show": lit(True), "position": lit("Bottom"),
                                         "fontSize": lit(9)}}]
    objects["slices"] = [{"properties": {"innerRadiusRatio": lit(60)}}]
    return container(name, x, y, w, h, z, tab, "donutChart", q, objects)


def slicer(name, x, y, w, h, z, tab, field, title, mode="Dropdown"):
    q = {"Values": {"projections": [field]}}
    objects = title_obj(title)
    objects["general"] = [{"properties": {"outlineWeight": lit(1)}}]
    objects["data"] = [{"properties": {"mode": lit(mode)}}]
    objects["header"] = [{"properties": {"show": lit(False)}}]
    return container(name, x, y, w, h, z, tab, "slicer", q, objects)


def scatter(name, x, y, w, h, z, tab, details, x_meas, y_meas, size, title, subtitle=None):
    q = {"Category": {"projections": [details]},
         "X": {"projections": [x_meas]},
         "Y": {"projections": [y_meas]}}
    if size:
        q["Size"] = {"projections": [size]}
    objects = title_obj(title, subtitle)
    objects["categoryLabels"] = [{"properties": {"show": lit(True), "fontSize": lit(8)}}]
    return container(name, x, y, w, h, z, tab, "scatterChart", q, objects)


# ===========================================================================
# Pages
# ===========================================================================
D, C, MC, T, S, CI = "Dim_Date", "Dim_Cell", "Dim_Machine", "Dim_Technician", "Dim_Spare", "Dim_ChecklistItem"
FW, FT, FR, FB, FS, FQ, FA, FP, FH = ("Fact_WorkOrder", "Fact_MachineTask",
                                      "Fact_ChecklistResponse", "Fact_Breakdown",
                                      "Fact_SpareReplaced", "Fact_SpareRequest",
                                      "Fact_Abnormality", "Fact_PlanCalendar",
                                      "Fact_StdHours")


def pg01():
    v = page_header("Executive PM Overview",
                    "Are we doing the preventive maintenance we said we would, and is it working?", 1)
    v += [
        kpi_card("v10KpiCompliance", 0, 10, "PM Compliance %", "PM COMPLIANCE",
                 colour_measure="Compliance Colour"),
        kpi_card("v11KpiOnTime", 1, 11, "PM On-Time %", "COMPLETED ON TIME"),
        kpi_card("v12KpiOverdue", 2, 12, "Overdue Cells Count", "CELLS OVERDUE NOW"),
        kpi_card("v13KpiAvailability", 3, 13, "Availability %", "AVAILABILITY",
                 colour_measure="Availability Colour"),
        kpi_card("v14KpiSpare", 4, 14, "Spare Cost MTD", "SPARE COST THIS MONTH"),

        matrix("v20CellStatus", cx(0), ROW2_Y, cw(7), 250, 2000, 20,
               rows=[col(C, "Cell_Name")], columns=None,
               values=[meas("Cum Std Hours"), meas("PM Trigger Hours"),
                       meas("Hours Utilisation %"), meas("Days Since Last PM"),
                       meas("First-Pass PM %"), meas("Total PM Man-Hours"),
                       meas("PM Status Flag")],
               title="Where does every cell stand against its own 4,000-hour trigger?",
               subtitle="Utilisation is against each cell's own PM_Trigger_Hours, never a hard-coded 4,000"),

        bar("v21TopCells", cx(7), ROW2_Y, cw(5), 250, 2001, 21,
            category=col(C, "Cell_Name"),
            values=[meas("Hours Utilisation %")],
            title=title_measure("Title - Cells At Risk"),
            subtitle="Amber from 90%, red at 100%",
            colour_measure="PM Status Colour", sort_desc_by=True),

        line("v30Trend", cx(0), 460, cw(7), 176, 2002, 30,
             category=col(D, "Month Year"),
             values=[meas("PM Compliance %"), meas("PM On-Time %")],
             title="Is compliance holding up over twelve months?",
             subtitle="Compliance counts what was finished; on-time counts what was finished by the date we promised"),

        column_chart("v31Breakdowns", cx(7), 460, cw(5), 176, 2003, 31,
                     category=col(D, "Month Year"),
                     values=[meas("Breakdowns After PM (7d)")],
                     title="Breakdowns within 7 days of a PM - is the PM working?",
                     subtitle="A rising bar here while compliance is green means the checklist is being signed, not done"),

        footnote("v90Info", [
            "PM Compliance % = completed work orders / work orders due, cancellations excluded.",
            "Hours Utilisation % = each cell's running counter / that cell's own PM_Trigger_Hours.",
            "A cell is OVERDUE when utilisation reaches 100% OR the calendar backstop date has passed - whichever comes first.",
            "Availability % uses production loss minutes, not repair time.",
        ]),
    ]
    return "pg01Overview", "Executive PM Overview", v


def pg02():
    v = page_header("PM Planning & Hours Forecast",
                    "Which cells will hit 4,000 hours next, and how much technician time will that take?", 2)
    v += [
        kpi_card("v10KpiDueSoon", 0, 10, "Cells Due Soon Count", "CELLS AT 90% OR MORE"),
        kpi_card("v11KpiHoursLeft", 1, 11, "Hours to Next PM", "HOURS LEFT IN TOTAL"),
        kpi_card("v12KpiL3M", 2, 12, "Avg Monthly Std Hours L3M", "AVG MONTHLY HOURS (L3M)"),
        kpi_card("v13KpiForecast", 3, 13, "Forecast PM Count", "PMs FORECAST THIS MONTH"),
        kpi_card("v14KpiManHours", 4, 14, "Forecast Man-Hours", "MAN-HOURS FORECAST"),

        bar("v20Utilisation", cx(0), ROW2_Y, cw(6), 250, 2000, 20,
            category=col(C, "Cell_Name"),
            values=[meas("Hours Utilisation %")],
            title="How close is each cell to its trigger?",
            subtitle="Reference lines at 90% (plan now) and 100% (raise the work order)",
            colour_measure="PM Status Colour", sort_desc_by=True),

        table("v21Projection", cx(6), ROW2_Y, cw(6), 250, 2001, 21,
              projections=[col(C, "Cell_ID"), col(C, "Cell_Name"),
                           meas("Cum Std Hours"), meas("Hours to Next PM"),
                           meas("Avg Monthly Std Hours L3M"), meas("Months to PM"),
                           meas("Projected PM Date"), meas("Calendar Due Date"),
                           meas("Days to Calendar Due"), meas("Next PM Due Date"),
                           meas("Total Std Hours"), meas("Production Qty")],
              title="When is each cell actually due - by hours, by calendar, and which comes first?",
              subtitle="Next PM Due Date is the earlier of the two clocks"),

        combo("v30Workload", cx(0), 460, cw(8), 176, 2002, 30,
              category=col(D, "Month Year"),
              col_vals=[meas("Forecast PM Count")],
              line_vals=[meas("Forecast Man-Hours")],
              title="How many cell PMs fall in each of the next six months, and what is the man-hour load?",
              subtitle="Bars are PM count; the line is estimated man-hours from the checklist master"),

        bar("v31Trigger", cx(8), 460, cw(4), 176, 2003, 31,
            category=col(FW, "Trigger_Type"),
            values=[meas("PM Due Count"), meas("Calendar-Triggered PM %")],
            title="Are PMs firing on hours or on the calendar backstop?",
            subtitle="Mostly Calendar Backstop means the 4,000-hour rule is set too high"),

        footnote("v90Info", [
            "Projected PM Date = today + ROUNDUP(Hours to Next PM / Avg Monthly Std Hours L3M) months.",
            "Rounded UP: a cell needing 1.2 months of running is due in the second month, not the first.",
            "Calendar Due Date = Last_PM_Date + the cell's own Calendar_Backstop_Months.",
            "Forecast Man-Hours comes from summed Expected_Time_Min in the checklist master, not from past actuals.",
        ]),
    ]
    return "pg02Planning", "PM Planning & Hours Forecast", v


def pg03():
    v = page_header("Monthly Schedule & Adherence",
                    "Did we do the PM in the month we froze the plan for?", 3)
    v += [
        slicer("v05MonthSlicer", cx(0), KPI_Y, cw(2), KPI_H, 500, 5,
               col(D, "Month Year"), "Month"),
        kpi_card("v11KpiAdherence", 1, 11, "Schedule Adherence %", "SCHEDULE ADHERENCE"),
        kpi_card("v12KpiPlanned", 2, 12, "Planned WO Count", "PLANNED THIS MONTH"),
        kpi_card("v13KpiDone", 3, 13, "Completed WO Count (by Actual Date)", "COMPLETED THIS MONTH"),
        kpi_card("v14KpiDelay", 4, 14, "Avg PM Delay (Days)", "AVG DELAY (DAYS)"),

        bar("v20Gantt", cx(0), ROW2_Y, cw(7), 250, 2000, 20,
            category=col(C, "Cell_Name"),
            values=[meas("Gantt Planned Offset (Days)"), meas("Gantt Planned Duration (Days)"),
                    meas("Gantt Actual Offset (Days)"), meas("Gantt Actual Duration (Days)")],
            title="Planned window versus actual window, per cell",
            subtitle="Set the first series to no fill in the format pane - it is the invisible offset that positions the bar",
            visual="barChart", data_labels=False),

        donut("v21Adherence", cx(7), ROW2_Y, cw(5), 250, 2001, 21,
              category=col(FP, "Adherence_Status"),
              value=meas("Schedule Adherence %"),
              title="How did the frozen plan actually land?",
              subtitle="Forecast rows are excluded - you cannot miss a date you never committed to"),

        table("v30Delayed", cx(0), 460, cw(12), 176, 2002, 30,
              projections=[col(FW, "WO_No"), col(FW, "Cell_Name"), col(FW, "Priority"),
                           col(FW, "Planned_End_Date"), col(FW, "Actual_End_Date"),
                           col(FW, "Delay_Days"), col(FW, "WO_Status"), col(FW, "Lead_Tech_ID")],
              title="Which work orders missed their committed end date, and by how many days?",
              subtitle="Negative delay means finished early"),

        footnote("v90Info", [
            "Adherence is measured against PM_Plan_Calendar (frozen on the 25th), not against the work order's own planned date, which can be edited after the fact.",
            "Plan_Version 'V1 Forecast' rows are projections beyond the frozen month and never count in the denominator.",
            "The Gantt bars are a stacked bar: an invisible offset series then a visible duration series.",
        ]),
    ]
    return "pg03Schedule", "Monthly Schedule & Adherence", v


def pg04():
    v = page_header("Live Work Order Tracking",
                    "What is open right now, and what is stopping each cell from closing?", 4)
    v += [
        kpi_card("v10KpiOpen", 0, 10, "PM In Progress Count", "WORK ORDERS IN PROGRESS"),
        kpi_card("v11KpiOverdue", 1, 11, "PM Overdue Count", "PAST PLANNED END DATE"),
        kpi_card("v12KpiPending", 2, 12, "Machine Tasks Pending", "MACHINE TASKS OPEN"),
        kpi_card("v13KpiNotScanned", 3, 13, "Machines Not Scanned", "NOT YET SCANNED"),
        kpi_card("v14KpiReset", 4, 14, "Reset Not Applied Count", "COMPLETED BUT NOT RESET"),

        table("v20OpenWO", cx(0), ROW2_Y, cw(7), 250, 2000, 20,
              projections=[col(FW, "WO_No"), col(FW, "Cell_Name"), col(FW, "WO_Status"),
                           col(FW, "Priority"), meas("Cell Completion %"),
                           col(FW, "Machines_In_Scope"), col(FW, "Machines_Completed"),
                           col(FW, "Planned_End_Date")],
              title="Which open work orders are closest to closing?",
              subtitle="A cell resets its counter only when completion reaches 100% - three of four is still zero"),

        matrix("v21TaskMatrix", cx(7), ROW2_Y, cw(5), 250, 2001, 21,
               rows=[col(MC, "Machine_ID")],
               columns=[col(FT, "Task_Status")],
               values=[meas("Machine Tasks Total")],
               title="Which machine is holding its cell open?",
               subtitle="Rows are machines, columns are task status"),

        table("v30NotScanned", cx(0), 460, cw(6), 176, 2002, 30,
              projections=[col(FT, "Machine_ID"), col(FT, "Cell_ID"), col(FT, "WO_No"),
                           col(FT, "Assigned_Tech_ID"), col(FT, "Task_Status")],
              title="Which machines in an open work order has nobody started?",
              subtitle="Pending with no scan-in time - the supervisor's chase list"),

        column_chart("v31Ageing", cx(6), 460, cw(6), 176, 2003, 31,
                     category=col(C, "Cell_Name"),
                     values=[meas("Open WO Ageing (Days)")],
                     title="How long has each cell's open work order been sitting?",
                     subtitle="Days since the work order was raised"),

        footnote("v90Info", [
            "Cell Completion % = completed machine tasks / total machine tasks in the work order.",
            "The work order closes and the counter resets only when every machine task in the cell is Completed.",
            "A Skipped machine still lets the cell close but flags the work order as partial - review skips monthly.",
            "Machines Not Scanned counts Pending tasks with no Scan_Start_Time.",
        ]),
    ]
    return "pg04Tracking", "Live Work Order Tracking", v


def pg05():
    v = page_header("Machine 360",
                    "Everything known about one machine - right-click any machine elsewhere and drill through to here", 5)
    v += [
        kpi_card("v10KpiLastPM", 0, 10, "Days Since Last PM", "DAYS SINCE LAST PM"),
        kpi_card("v11KpiNotOk", 1, 11, "NOT OK Count", "FINDINGS ON THIS MACHINE"),
        kpi_card("v12KpiBreakdowns", 2, 12, "Breakdown Count", "BREAKDOWNS"),
        kpi_card("v13KpiMttr", 3, 13, "MTTR (Min)", "MTTR (MIN)"),
        kpi_card("v14KpiSpare", 4, 14, "Spare Cost", "SPARE COST"),

        table("v20History", cx(0), ROW2_Y, cw(6), 250, 2000, 20,
              projections=[col(FT, "WO_No"), col(FT, "Completion_Date"), col(FT, "Task_Status"),
                           col(FT, "Duration_Min"), col(FT, "NOT_OK_Count"), col(FT, "Completed_By")],
              title="PM history for this machine",
              subtitle="Duration well below the checklist's expected time is the signature of a signed-not-done PM"),

        table("v21Findings", cx(6), ROW2_Y, cw(6), 250, 2001, 21,
              projections=[col(FR, "Submitted_DateTime"), col(FR, "Check_Point"),
                           col(FR, "Result"), col(FR, "Measured_Value"),
                           col(FR, "Observation"), col(FR, "Action_Taken")],
              title="Every check point result, newest first",
              subtitle="Measured_Value across successive PMs is what turns a checklist into condition monitoring"),

        table("v30Breakdowns", cx(0), 460, cw(6), 176, 2002, 30,
              projections=[col(FB, "Reported_DateTime"), col(FB, "Breakdown_Type"),
                           col(FB, "Symptom"), col(FB, "Root_Cause"),
                           col(FB, "MTTR_Min"), col(FB, "Production_Loss_Min")],
              title="Breakdown history",
              subtitle="Symptom and root cause kept separate - that is what makes repeat-failure analysis possible"),

        table("v31Spares", cx(6), 460, cw(6), 176, 2003, 31,
              projections=[col(FS, "Replaced_DateTime"), col(FS, "Spare_Description"),
                           col(FS, "Qty_Used"), col(FS, "Total_Cost_INR"),
                           col(FS, "Failure_Mode")],
              title="Parts fitted to this machine",
              subtitle="Repeated Contamination on the same part is a filtration problem, not a spares problem"),

        footnote("v90Info", [
            "This page is a drillthrough on Machine_ID. Right-click a machine in any visual on any page and choose Drill through > Machine 360.",
            "Add the drillthrough field in Desktop: select this page, then drag Dim_Machine[Machine_ID] into the Drill through well.",
        ]),
    ]
    return "pg05Machine360", "Machine 360", v


def pg06():
    v = page_header("Checklist Findings & Abnormalities",
                    "What are the PMs finding, and is any of it being fixed?", 6)
    v += [
        kpi_card("v10KpiChecked", 0, 10, "Checklist Items Checked", "CHECK POINTS COMPLETED"),
        kpi_card("v11KpiNotOk", 1, 11, "NOT OK %", "NOT OK RATE"),
        kpi_card("v12KpiSafety", 2, 12, "Safety-Critical NOT OK Count", "SAFETY-CRITICAL FINDINGS"),
        kpi_card("v13KpiOpenAbn", 3, 13, "Open Abnormalities", "ABNORMALITIES OPEN"),
        kpi_card("v14KpiRepeat", 4, 14, "Repeat Finding Count", "REPEAT FINDINGS"),

        line("v20NotOkTrend", cx(0), ROW2_Y, cw(6), 250, 2000, 20,
             category=col(D, "Month Year"),
             values=[meas("NOT OK %")],
             title="Is the finding rate rising or falling?",
             subtitle="A rate falling to zero is not success - it usually means people have stopped looking"),

        bar("v21Pareto", cx(6), ROW2_Y, cw(6), 250, 2001, 21,
            category=col(CI, "Check_Point_Short"),
            values=[meas("NOT OK Count"), meas("Follow-Up Raised Count")],
            title="Which check points fail most often, and how many became corrective work?",
            subtitle="The top three are your PM improvement backlog",
            sort_desc_by=True),

        table("v30Safety", cx(0), 460, cw(6), 176, 2002, 30,
              projections=[col(FR, "Submitted_DateTime"), col(FR, "Machine_ID"),
                           col(FR, "Check_Point"), col(FR, "Measured_Value"),
                           col(FR, "Observation"), col(FR, "Follow_Up_WO")],
              title="Safety-critical findings - every one of these blocks the task from closing",
              subtitle="Escalated immediately regardless of the severity anyone selected"),

        bar("v31AbnFunnel", cx(6), 460, cw(6), 176, 2003, 31,
            category=col(FA, "Status"),
            values=[meas("Open Abnormalities"), meas("High Severity Open"),
                    meas("Overdue Abnormalities"), meas("Abnormality Ageing (Days)")],
            title="Where do abnormalities get stuck, and for how long?",
            subtitle="Ageing stops at the closed date, so a closed item's age does not keep growing"),

        footnote("v90Info", [
            "NOT OK % = NOT OK responses / responses that returned OK or NOT OK. NA answers are excluded - a check that did not apply was not a check.",
            "Repeat Finding = the same check point NOT OK on the same machine in two CONSECUTIVE PM cycles - it was not actually fixed the first time.",
            "Safety_Critical is set per check point in Checklist_Master.",
        ]),
    ]
    return "pg06Findings", "Checklist Findings & Abnormalities", v


def pg07():
    v = page_header("Breakdown & Reliability",
                    "Is preventive maintenance actually preventing anything?", 7)
    v += [
        kpi_card("v10KpiMttr", 0, 10, "MTTR (Min)", "MTTR (MIN)"),
        kpi_card("v11KpiMtbf", 1, 11, "MTBF (Hrs)", "MTBF (HRS)"),
        kpi_card("v12KpiAvail", 2, 12, "Availability %", "AVAILABILITY",
                 colour_measure="Availability Colour"),
        kpi_card("v13KpiAfterPM", 3, 13, "Breakdowns After PM (7d)", "BREAKDOWNS WITHIN 7 DAYS OF A PM"),
        kpi_card("v14KpiResponse", 4, 14, "Avg Response Time (Min)", "AVG RESPONSE (MIN)"),

        line("v20MttrTrend", cx(0), ROW2_Y, cw(6), 250, 2000, 20,
             category=col(D, "Month Year"),
             values=[meas("MTTR (Min)"), meas("Avg Response Time (Min)")],
             title="Are we repairing faster, or just arriving faster?",
             subtitle="Response time is arrival; MTTR is wrench time. They move for different reasons"),

        bar("v21CausePareto", cx(6), ROW2_Y, cw(6), 250, 2001, 21,
            category=col(FB, "Breakdown_Type"),
            values=[meas("Breakdown Count"), meas("Total Production Loss (Hrs)"),
                    meas("Open Breakdowns"), meas("Repeat Breakdown Count")],
            title="Which failure types cost the most production time?",
            subtitle="Count and lost hours rarely rank the same - fix for the hours",
            sort_desc_by=True),

        column_chart("v30AfterPM", cx(0), 460, cw(6), 176, 2002, 30,
                     category=col(C, "Cell_Name"),
                     values=[meas("Breakdowns After PM (7d)"), meas("Breakdowns After PM %")],
                     title=title_measure("Title - Breakdowns After PM"),
                     subtitle="This is the measure that says whether the PM is real. Read the percentage, not the count"),

        table("v31Repeats", cx(6), 460, cw(6), 176, 2003, 31,
              projections=[col(FB, "Machine_ID"), col(FB, "Breakdown_Type"),
                           col(FB, "Symptom"), col(FB, "Root_Cause"),
                           meas("Breakdown Count"), meas("Total Production Loss (Hrs)")],
              title="Which failures keep coming back?",
              subtitle="Repeats are the PM improvement backlog - each one is a check point that does not exist yet"),

        footnote("v90Info", [
            "Breakdowns After PM (7d) counts breakdowns on a cell within 7 days of a completed PM on that same cell, derived from dates rather than from Linked_PM_WO, so it works on history loaded before the flow existed.",
            "Availability % = (loading hours - downtime hours) / loading hours, where downtime uses production loss minutes, not MTTR.",
            "MTBF (Hrs) = loading hours / breakdown count. Loading hours are the standard hours actually consumed.",
        ]),
    ]
    return "pg07Reliability", "Breakdown & Reliability", v


def pg08():
    v = page_header("Spares & Cost",
                    "What is maintenance costing, and which parts are about to stop a PM?", 8)
    v += [
        kpi_card("v10KpiCost", 0, 10, "Spare Cost", "TOTAL SPARE COST"),
        kpi_card("v11KpiPerPM", 1, 11, "Spare Cost per PM", "COST PER CELL PM"),
        kpi_card("v12KpiUnplanned", 2, 12, "Unplanned Spare Cost", "UNPLANNED SPEND"),
        kpi_card("v13KpiPending", 3, 13, "Requests Pending Approval", "AWAITING APPROVAL"),
        kpi_card("v14KpiBelowMin", 4, 14, "Stock Below Min Count", "PARTS BELOW MINIMUM"),

        combo("v20CostTrend", cx(0), ROW2_Y, cw(6), 250, 2000, 20,
              category=col(D, "Month Year"),
              col_vals=[meas("Planned Spare Cost"), meas("Unplanned Spare Cost")],
              line_vals=[meas("Spare Cost per PM")],
              title="Is spend shifting from planned to unplanned?",
              subtitle="Unplanned overtaking planned is the clearest sign a PM programme is losing"),

        bar("v21TopSpares", cx(6), ROW2_Y, cw(6), 250, 2001, 21,
            category=col(S, "Spare_Description"),
            values=[meas("Spare Cost"), meas("Qty Replaced"), meas("Warranty Claims Flagged")],
            title="Which ten parts consume the budget?",
            subtitle="Value and frequency rank differently - both are shown",
            sort_desc_by=True),

        scatter("v30AbcFmr", cx(0), 460, cw(6), 176, 2002, 30,
                details=col(S, "Spare_Description"),
                x_meas=meas("Qty Replaced"),
                y_meas=meas("Spare Cost"),
                size=meas("Stock Value (INR)"),
                title="ABC-FMR: which parts are high value and rarely used?",
                subtitle="Top-left (high value, rare) is the review list; bottom-right (low value, fast) gets bulk ordered"),

        table("v31Stock", cx(6), 460, cw(6), 176, 2003, 31,
              projections=[col(S, "Spare_Code"), col(S, "Spare_Description"),
                           col(S, "Current_Stock"), col(S, "Min_Stock"),
                           col(S, "Lead_Time_Days"), col(S, "Stockout_Risk_Score"),
                           meas("Avg Approval Lead Time (Days)"), meas("Avg Issue Lead Time (Days)"),
                           meas("Approved Not Issued Count"), col(S, "Preferred_Vendor")],
              title="Which parts will stop a PM if they run out?",
              subtitle="Risk score weights how far below minimum a part is by how long it takes to replace"),

        footnote("v90Info", [
            "Unit cost is copied onto each replacement row at the time of use, so a price rise does not retrospectively rewrite last year's maintenance cost.",
            "Spare Cost per PM uses PM-sourced replacements only, divided by completed cell PMs.",
            "Stockout Risk Score = (1 - current/minimum, floored at 0) x lead time days.",
        ]),
    ]
    return "pg08Spares", "Spares & Cost", v


def pg09():
    v = page_header("Technician Performance",
                    "Who is doing the work, how thoroughly, and is the load shared fairly?", 9)
    v += [
        kpi_card("v10KpiActive", 0, 10, "Active Technicians", "TECHNICIANS ACTIVE"),
        kpi_card("v11KpiCompleted", 1, 11, "Machine Tasks Completed", "MACHINE TASKS COMPLETED"),
        kpi_card("v12KpiDuration", 2, 12, "Avg Task Duration by Tech", "AVG TASK DURATION (MIN)"),
        kpi_card("v13KpiFindings", 3, 13, "Findings Raised per PM", "FINDINGS PER PM"),
        kpi_card("v14KpiImbalance", 4, 14, "Workload Imbalance", "WORKLOAD SPREAD"),

        bar("v20ByTech", cx(0), ROW2_Y, cw(6), 250, 2000, 20,
            category=col(T, "Tech_Label"),
            values=[meas("PMs Completed by Tech")],
            title="How many machine tasks has each technician completed?",
            subtitle="Attribution comes from the mandatory name dropdown - technicians share one login, so this is the only audit trail there is",
            sort_desc_by=True),

        bar("v21Thorough", cx(6), ROW2_Y, cw(6), 250, 2001, 21,
            category=col(T, "Tech_Label"),
            values=[meas("Findings Raised per PM")],
            title="Who finds the most per PM? Higher is more thorough, not worse",
            subtitle="The technician at the BOTTOM of this chart is the one to review. Say so out loud, or people stop reporting findings",
            sort_desc_by=True),

        column_chart("v30Workload", cx(0), 460, cw(7), 176, 2002, 30,
                     category=col(D, "Month Year"),
                     values=[meas("Machine Tasks Completed")],
                     series=col(T, "Tech_Label"),
                     title="Is the monthly load shared, or carried by two people?",
                     visual="columnChart"),

        table("v31Detail", cx(7), 460, cw(5), 176, 2003, 31,
              projections=[col(T, "Tech_Name"), col(T, "Skill_Level"), col(T, "Trade"),
                           meas("PMs Completed by Tech"), meas("Avg Task Duration by Tech"),
                           meas("Avg PM Duration (Hrs)"), meas("PM Duration vs Expected %"),
                           meas("Findings Raised per PM"), meas("Abnormalities Raised by Tech")],
              title="Technician summary",
              subtitle="Skill level matters: a trainee should not be the sole signatory on a criticality-A machine"),

        footnote("v90Info", [
            "Every technician signs in with the same M365 account, so the mandatory Technician Name dropdown on each form is the entire attribution trail. It is never optional and never free text.",
            "Findings Raised per PM measures thoroughness. Ranking people by 'fewest findings' teaches them to stop reporting - the number then looks excellent and means nothing.",
            "Avg Task Duration compared against the checklist's Expected_Time_Min is how a pencil-whipped PM is caught.",
        ]),
    ]
    return "pg09Technician", "Technician Performance", v


PAGES = [pg01, pg02, pg03, pg04, pg05, pg06, pg07, pg08, pg09]


def main():
    if os.path.isdir(os.path.join(DEF, "pages")):
        shutil.rmtree(os.path.join(DEF, "pages"))

    order, total_visuals = [], 0
    for fn in PAGES:
        pname, display, visuals = fn()
        order.append(pname)
        pdir = os.path.join(DEF, "pages", pname)
        os.makedirs(os.path.join(pdir, "visuals"), exist_ok=True)

        page = {"$schema": PG_SCHEMA, "name": pname, "displayName": display,
                "displayOption": "FitToPage", "width": 1280, "height": 720}
        if pname == "pg05Machine360":
            page["type"] = "Drillthrough"
        with open(os.path.join(pdir, "page.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(page, fh, indent=2)
            fh.write("\n")

        seen = set()
        for vis in visuals:
            if vis["name"] in seen:
                raise SystemExit(f"{pname}: duplicate visual name {vis['name']}")
            seen.add(vis["name"])
            vdir = os.path.join(pdir, "visuals", vis["name"])
            os.makedirs(vdir, exist_ok=True)
            with open(os.path.join(vdir, "visual.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(vis, fh, indent=2)
                fh.write("\n")
        total_visuals += len(visuals)
        print(f"  {pname:<18} {display:<36} {len(visuals):>2} visuals")

    with open(os.path.join(DEF, "pages", "pages.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"$schema": PGS_SCHEMA, "pageOrder": order, "activePageName": order[0]},
                  fh, indent=2)
        fh.write("\n")

    # Report settings and theme registration.
    report = {
        "$schema": RPT_SCHEMA,
        "themeCollection": {
            "customTheme": {"name": "EPQPL_PM_Theme", "type": "RegisteredResources"}
        },
        "resourcePackages": [{
            "name": "RegisteredResources",
            "type": "RegisteredResources",
            "items": [{"name": "EPQPL_PM_Theme.json", "path": "EPQPL_PM_Theme.json",
                       "type": "CustomTheme"}],
        }],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultFilterActionIsDataFilter": True,
            "useNewFilterPaneExperience": True,
            "allowChangeFilterTypes": True,
            "disableFilterPaneSearch": False,
        },
    }
    with open(os.path.join(DEF, "report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(DEF, "version.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"version": "1.0"}, fh, indent=2)
        fh.write("\n")

    res = os.path.join(RPT, "StaticResources", "RegisteredResources")
    os.makedirs(res, exist_ok=True)
    shutil.copy(os.path.join(PBI, "theme", "EPQPL_PM_Theme.json"),
                os.path.join(res, "EPQPL_PM_Theme.json"))

    print(f"\n  {len(order)} pages, {total_visuals} visuals, theme registered.")


if __name__ == "__main__":
    main()
