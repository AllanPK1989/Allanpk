# 13 · Report Build Guide

Every page and every visual, in build order, with the exact fields to drop into each well. Build this by hand in Power BI Desktop — it does not depend on any file format matching your version.

> Generated from the same page definitions that produce the project files, so the two cannot describe different reports.

## Before you start

1. Finish the semantic model first: all 17 tables loaded, 28 relationships made, all 94 measures created. See `12-model-build-guide.md`.
2. **View ▸ Themes ▸ Browse for themes** ▸ `PM_Theme.json`. Do this before building visuals so every new visual picks up the fonts and colours.
3. Set the canvas on every page: **Format ▸ Canvas settings ▸ Type = Custom, Height 900, Width 1600**.
4. Turn off the visual header in reading view: **File ▸ Options ▸ Current file ▸ Report settings**.

## How to read this

Positions are in the same units Power BI shows under **Format ▸ General ▸ Properties ▸ Position and size**. Typing them in is faster and tidier than dragging, and it is what makes every page line up.

Where a field is written `Table[Column]` drag that column. Where it is written `[Measure]` drag the measure from the `_Measures` table.

---

## Page 1 Overview

Rename the page tab to **1 Overview**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiCompliance | Card (new card) | 24, 92, 247, 118 |
| v02KpiOverdue | Card (new card) | 285, 92, 247, 118 |
| v03KpiAvailability | Card (new card) | 546, 92, 247, 118 |
| v04KpiBreakdowns | Card (new card) | 807, 92, 247, 118 |
| v05KpiAbnormal | Card (new card) | 1068, 92, 247, 118 |
| v06KpiDueSoon | Card (new card) | 1329, 92, 247, 118 |
| v07TrendCompliance | Line and clustered column chart | 24, 226, 1030, 310 |
| v08CounterByCell | Clustered bar chart | 1068, 226, 508, 310 |
| v09CellPlan | Table | 24, 550, 1030, 326 |
| v10DowntimeByArea | Donut chart | 1068, 550, 508, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Preventive Maintenance Control Tower
PM compliance, machine availability and the forward plan, in one view
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiCompliance` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **PM compliance (of work due)**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Compliance %]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[PM Compliance % Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiOverdue` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Overdue work orders**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Overdue]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiAvailability` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **Machine availability**

| Field well | Drop in |
|------------|---------|
| Fields | `[Availability %]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[Availability % Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiBreakdowns` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Breakdowns reported**

| Field well | Drop in |
|------------|---------|
| Fields | `[Breakdowns]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiAbnormal` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Open abnormalities**

| Field well | Drop in |
|------------|---------|
| Fields | `[Open Abnormalities]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[Open Abnormality Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiDueSoon` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Cells due in next 3 months**

| Field well | Drop in |
|------------|---------|
| Fields | `[Cells Due Next 3 Months]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07TrendCompliance` — Line and clustered column chart

Position and size: **x 24, y 226, width 1030, height 310**

Title: **PM work orders completed and overdue, with compliance trend**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Date[MonthKey]` |
| Column y-axis | `[PM Completed]`, `[PM Overdue]` |
| Line y-axis | `[PM Compliance %]` |

Formatting:

- Legend: **on**

---

### `v08CounterByCell` — Clustered bar chart

Position and size: **x 1068, y 226, width 508, height 310**

Title: **Hour counter against the 4000 h threshold, by cell**

| Field well | Drop in |
|------------|---------|
| Y-axis | `Dim_Cell[CellName]` |
| X-axis | `[% to PM Threshold]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#1B6E8C`
- Legend: **off**
- Data labels: **on**, 9pt

---

### `v09CellPlan` — Table

Position and size: **x 24, y 550, width 1030, height 326**

Title: **Cell plan - where every counter stands and when the next PM lands**

| Field well | Drop in |
|------------|---------|
| Columns | `Dim_Cell[CellName]`, `[Last PM Date]`, `[Months Since Last PM]`, `[Current Counter Std Hrs]`, `[Hours to Next PM]`, `[% to PM Threshold]`, `[Projected Next PM Date]`, `[Projected Trigger Reason]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v10DowntimeByArea` — Donut chart

Position and size: **x 1068, y 550, width 508, height 326**

Title: **Unplanned downtime hours by area**

| Field well | Drop in |
|------------|---------|
| Legend | `Dim_Cell[Area]` |
| Values | `[Downtime Hours]` |

Formatting:

- Legend: **on**

---

## Page 2 PM Planning

Rename the page tab to **2 PM Planning**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiRunRate | Card (new card) | 24, 92, 247, 118 |
| v02KpiStd12M | Card (new card) | 285, 92, 247, 118 |
| v03KpiDuePeriod | Card (new card) | 546, 92, 247, 118 |
| v04KpiDue3M | Card (new card) | 807, 92, 247, 118 |
| v05KpiHoursTo | Card (new card) | 1068, 92, 247, 118 |
| v06KpiPct | Card (new card) | 1329, 92, 247, 118 |
| v07Forecast | Table | 24, 226, 1030, 310 |
| v08SlicerArea | Slicer | 1068, 226, 508, 150 |
| v09SlicerFY | Slicer | 1068, 390, 508, 146 |
| v10StdHoursTrend | Clustered column chart | 24, 550, 1030, 326 |
| v11LedgerMatrix | Matrix | 1068, 550, 508, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
PM Planning - the 4000 standard-hour counter
Standard hours accrue per cell from the monthly upload. At 4000 the whole cell is scheduled; the calendar backstop catches any cell that has gone 12 months without one
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiRunRate` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Run rate (3-month avg std hrs)**

| Field well | Drop in |
|------------|---------|
| Fields | `[Run Rate 3M Std Hrs]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiStd12M` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Standard hours, rolling 12 months**

| Field well | Drop in |
|------------|---------|
| Fields | `[Std Hours 12M]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiDuePeriod` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **Cells tripped in period**

| Field well | Drop in |
|------------|---------|
| Fields | `[Cells Due In Period]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiDue3M` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Cells due next 3 months**

| Field well | Drop in |
|------------|---------|
| Fields | `[Cells Due Next 3 Months]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiHoursTo` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Std hours to next PM**

| Field well | Drop in |
|------------|---------|
| Fields | `[Hours to Next PM]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiPct` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Counter vs threshold**

| Field well | Drop in |
|------------|---------|
| Fields | `[% to PM Threshold]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[% to PM Threshold Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07Forecast` — Table

Position and size: **x 24, y 226, width 1030, height 310**

Title: **Forward plan by cell - projection is the earlier of the hour run rate and the calendar backstop**

| Field well | Drop in |
|------------|---------|
| Columns | `Dim_Cell[CellName]`, `Dim_Cell[Area]`, `[Current Counter Std Hrs]`, `[Hours to Next PM]`, `[Run Rate 3M Std Hrs]`, `[Months to PM Projected]`, `[Projected Next PM Date]`, `[Projected Trigger Reason]`, `[Backstop Months Remaining]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v08SlicerArea` — Slicer

Position and size: **x 1068, y 226, width 508, height 150**

Title: **Area**

| Field well | Drop in |
|------------|---------|
| Field | `Dim_Cell[Area]` |

---

### `v09SlicerFY` — Slicer

Position and size: **x 1068, y 390, width 508, height 146**

Title: **Financial year**

| Field well | Drop in |
|------------|---------|
| Field | `Dim_Date[FinancialYear]` |

Formatting:

- Slicer settings ▸ Style: **Dropdown**

---

### `v10StdHoursTrend` — Clustered column chart

Position and size: **x 24, y 550, width 1030, height 326**

Title: **Standard hours uploaded per month, by cell**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Date[MonthKey]` |
| Y-axis | `[Std Hours]` |
| Legend | `Dim_Cell[CellName]` |

Formatting:

- Legend: **on**

---

### `v11LedgerMatrix` — Matrix

Position and size: **x 1068, y 550, width 508, height 326**

Title: **Closing counter by cell and month**

| Field well | Drop in |
|------------|---------|
| Rows | `Dim_Cell[CellName]` |
| Columns | `Dim_Date[MonthKey]` |
| Values | `[Current Counter Std Hrs]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

## Page 3 Monthly Schedule

Rename the page tab to **3 Monthly Schedule**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiTotal | Card (new card) | 24, 92, 247, 118 |
| v02KpiScheduled | Card (new card) | 285, 92, 247, 118 |
| v03KpiProgress | Card (new card) | 546, 92, 247, 118 |
| v04KpiOverdue | Card (new card) | 807, 92, 247, 118 |
| v05KpiDeferred | Card (new card) | 1068, 92, 247, 118 |
| v06KpiPlannedHrs | Card (new card) | 1329, 92, 247, 118 |
| v07PlanMatrix | Matrix | 24, 226, 1030, 310 |
| v08ByStatus | Clustered column chart | 1068, 226, 508, 310 |
| v09WoList | Table | 24, 550, 1552, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Monthly PM Schedule
Every work order the engine has raised, by month, cell and technician
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiTotal` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Work orders in view**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Work Orders]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiScheduled` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Not started**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Scheduled]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiProgress` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **In progress**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM In Progress]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiOverdue` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Overdue**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Overdue]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiDeferred` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Deferred**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Deferred]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiPlannedHrs` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Planned wrench hours**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Planned Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07PlanMatrix` — Matrix

Position and size: **x 24, y 226, width 1030, height 310**

Title: **Work orders by cell and plan month**

| Field well | Drop in |
|------------|---------|
| Rows | `Dim_Cell[CellName]` |
| Columns | `Fact_WorkOrders[PlanMonth]` |
| Values | `[PM Work Orders]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v08ByStatus` — Clustered column chart

Position and size: **x 1068, y 226, width 508, height 310**

Title: **Work orders by status and month**

| Field well | Drop in |
|------------|---------|
| X-axis | `Fact_WorkOrders[PlanMonth]` |
| Y-axis | `[PM Work Orders]` |
| Legend | `Fact_WorkOrders[Status]` |

Formatting:

- Legend: **on**

---

### `v09WoList` — Table

Position and size: **x 24, y 550, width 1552, height 326**

Title: **Work order list**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_WorkOrders[WOID]`, `Dim_Cell[CellName]`, `Dim_Machine[MachineName]`, `Fact_WorkOrders[TriggerType]`, `Fact_WorkOrders[PlannedDate]`, `Fact_WorkOrders[DueDate]`, `Fact_WorkOrders[AssignedTechName]`, `Fact_WorkOrders[Shift]`, `Fact_WorkOrders[Status]`, `[Checklist Completion %]`, `Fact_WorkOrders[MachineQRScanned]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

## Page 4 Execution & Quality

Rename the page tab to **4 Execution & Quality**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiCompliance | Card (new card) | 24, 92, 247, 118 |
| v02KpiCompletion | Card (new card) | 285, 92, 247, 118 |
| v03KpiChecklist | Card (new card) | 546, 92, 247, 118 |
| v04KpiFailRate | Card (new card) | 807, 92, 247, 118 |
| v05KpiQr | Card (new card) | 1068, 92, 247, 118 |
| v06KpiDuration | Card (new card) | 1329, 92, 247, 118 |
| v07ComplianceTrend | Line chart | 24, 226, 769, 310 |
| v08FailByType | Clustered bar chart | 807, 226, 769, 310 |
| v09Overdue | Table | 24, 550, 1030, 326 |
| v10SafetyFails | Clustered column chart | 1068, 550, 508, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
PM Execution and Checklist Quality
Not just whether the PM was closed - whether it was actually done, and done at the machine
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiCompliance` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **On-time compliance**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Compliance %]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[PM Compliance % Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiCompletion` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Completion rate**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Completion %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiChecklist` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **Checklist answered**

| Field well | Drop in |
|------------|---------|
| Fields | `[Checklist Completion %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiFailRate` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Checklist fail rate**

| Field well | Drop in |
|------------|---------|
| Fields | `[Checklist Fail Rate %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiQr` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Closed with a machine scan**

| Field well | Drop in |
|------------|---------|
| Fields | `[QR Verification %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiDuration` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Actual vs standard time**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Duration vs Std %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07ComplianceTrend` — Line chart

Position and size: **x 24, y 226, width 769, height 310**

Title: **PM compliance and checklist fail rate by month**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Date[MonthKey]` |
| Y-axis | `[PM Compliance %]`, `[Checklist Fail Rate %]` |

Formatting:

- Legend: **on**

---

### `v08FailByType` — Clustered bar chart

Position and size: **x 807, y 226, width 769, height 310**

Title: **Checklist failures by machine type**

| Field well | Drop in |
|------------|---------|
| Y-axis | `Dim_Machine[MachineType]` |
| X-axis | `[Checklist Tasks Not OK]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#C4553B`
- Legend: **off**
- Data labels: **on**, 9pt

---

### `v09Overdue` — Table

Position and size: **x 24, y 550, width 1030, height 326**

Title: **Open and overdue work orders - oldest first**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_WorkOrders[WOID]`, `Dim_Machine[MachineName]`, `Fact_WorkOrders[DueDate]`, `Fact_WorkOrders[AssignedTechName]`, `Fact_WorkOrders[Status]`, `[Open WO Ageing Days]`, `Fact_WorkOrders[Remarks]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v10SafetyFails` — Clustered column chart

Position and size: **x 1068, y 550, width 508, height 326**

Title: **Safety-critical checklist failures by cell**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Cell[CellName]` |
| Y-axis | `[Safety Critical Fails]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#C4553B`
- Legend: **off**
- Data labels: **on**, 9pt

---

## Page 5 Machine 360

Rename the page tab to **5 Machine 360**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01SlicerMachine | Slicer | 24, 92, 300, 118 |
| v02KpiLastPm | Card (new card) | 338, 92, 236, 118 |
| v03KpiMonths | Card (new card) | 588, 92, 236, 118 |
| v04KpiBreak | Card (new card) | 838, 92, 236, 118 |
| v05KpiDown | Card (new card) | 1088, 92, 236, 118 |
| v06KpiMtbf | Card (new card) | 1338, 92, 236, 118 |
| v07PmHistory | Table | 24, 226, 769, 310 |
| v08BreakHistory | Table | 807, 226, 769, 310 |
| v09Spares | Table | 24, 550, 769, 326 |
| v10Abnormal | Table | 807, 550, 769, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Machine 360
The page a machine QR code opens - last PM, history, breakdowns, spares and open abnormalities
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01SlicerMachine` — Slicer

Position and size: **x 24, y 92, width 300, height 118**

Title: **Machine**

| Field well | Drop in |
|------------|---------|
| Field | `Dim_Machine[MachineName]` |

Formatting:

- Slicer settings ▸ Style: **Dropdown**

---

### `v02KpiLastPm` — Card (new card)

Position and size: **x 338, y 92, width 236, height 118**

Title: **Last PM done**

| Field well | Drop in |
|------------|---------|
| Fields | `[Last PM Date]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiMonths` — Card (new card)

Position and size: **x 588, y 92, width 236, height 118**

Title: **Months since last PM**

| Field well | Drop in |
|------------|---------|
| Fields | `[Months Since Last PM]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiBreak` — Card (new card)

Position and size: **x 838, y 92, width 236, height 118**

Title: **Breakdowns**

| Field well | Drop in |
|------------|---------|
| Fields | `[Breakdowns]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiDown` — Card (new card)

Position and size: **x 1088, y 92, width 236, height 118**

Title: **Downtime hours**

| Field well | Drop in |
|------------|---------|
| Fields | `[Downtime Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiMtbf` — Card (new card)

Position and size: **x 1338, y 92, width 236, height 118**

Title: **MTBF (hours)**

| Field well | Drop in |
|------------|---------|
| Fields | `[MTBF Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07PmHistory` — Table

Position and size: **x 24, y 226, width 769, height 310**

Title: **PM history**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_WorkOrders[WOID]`, `Fact_WorkOrders[PlanMonth]`, `Fact_WorkOrders[ActualEndDate]`, `Fact_WorkOrders[AssignedTechName]`, `Fact_WorkOrders[Status]`, `Fact_WorkOrders[PMResult]`, `[Checklist Completion %]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v08BreakHistory` — Table

Position and size: **x 807, y 226, width 769, height 310**

Title: **Breakdown history**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_Breakdowns[BreakdownID]`, `Fact_Breakdowns[ReportedDate]`, `Fact_Breakdowns[FailureMode]`, `Fact_Breakdowns[RootCause]`, `Fact_Breakdowns[DowntimeMinutes]`, `Fact_Breakdowns[Status]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v09Spares` — Table

Position and size: **x 24, y 550, width 769, height 326**

Title: **Spares replaced on this machine**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_SpareReplacements[ReplacedDate]`, `Fact_SpareReplacements[PartNo]`, `Fact_SpareReplacements[PartName]`, `Fact_SpareReplacements[QtyReplaced]`, `Fact_SpareReplacements[OldPartCondition]`, `[Spare Consumption Value]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v10Abnormal` — Table

Position and size: **x 807, y 550, width 769, height 326**

Title: **Abnormalities logged against this machine**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_Abnormalities[AbnormalityID]`, `Fact_Abnormalities[ReportedDate]`, `Fact_Abnormalities[Category]`, `Fact_Abnormalities[Severity]`, `Fact_Abnormalities[Status]`, `Fact_Abnormalities[Description]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

## Page 6 Reliability

Rename the page tab to **6 Reliability**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiBreak | Card (new card) | 24, 92, 247, 118 |
| v02KpiDown | Card (new card) | 285, 92, 247, 118 |
| v03KpiMttr | Card (new card) | 546, 92, 247, 118 |
| v04KpiMtbf | Card (new card) | 807, 92, 247, 118 |
| v05KpiAvail | Card (new card) | 1068, 92, 247, 118 |
| v06KpiInduced | Card (new card) | 1329, 92, 247, 118 |
| v07Pareto | Clustered bar chart | 24, 226, 1030, 310 |
| v08MttrTrend | Line and clustered column chart | 1068, 226, 508, 310 |
| v09BadActors | Table | 24, 550, 1030, 326 |
| v10ByCategory | Donut chart | 1068, 550, 508, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Breakdown and Reliability Analysis
Where the losses are, what causes them, and whether the PM programme is actually preventing them
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiBreak` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Breakdowns**

| Field well | Drop in |
|------------|---------|
| Fields | `[Breakdowns]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiDown` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Downtime hours**

| Field well | Drop in |
|------------|---------|
| Fields | `[Downtime Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiMttr` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **MTTR (hours)**

| Field well | Drop in |
|------------|---------|
| Fields | `[MTTR Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiMtbf` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **MTBF (hours)**

| Field well | Drop in |
|------------|---------|
| Fields | `[MTBF Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiAvail` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Availability**

| Field well | Drop in |
|------------|---------|
| Fields | `[Availability %]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[Availability % Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiInduced` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Failures within 15d of PM**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Induced Failure %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07Pareto` — Clustered bar chart

Position and size: **x 24, y 226, width 1030, height 310**

Title: **Downtime hours by failure mode - work the top of this list**

| Field well | Drop in |
|------------|---------|
| Y-axis | `Fact_Breakdowns[FailureMode]` |
| X-axis | `[Downtime Hours]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#C4553B`
- Legend: **off**
- Data labels: **on**, 9pt

---

### `v08MttrTrend` — Line and clustered column chart

Position and size: **x 1068, y 226, width 508, height 310**

Title: **Breakdowns and MTTR by month**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Date[MonthKey]` |
| Column y-axis | `[Breakdowns]` |
| Line y-axis | `[MTTR Hours]` |

Formatting:

- Legend: **on**

---

### `v09BadActors` — Table

Position and size: **x 24, y 550, width 1030, height 326**

Title: **Bad actors - highest loss machines**

| Field well | Drop in |
|------------|---------|
| Columns | `Dim_Machine[MachineName]`, `Dim_Cell[CellName]`, `Dim_Machine[Criticality]`, `[Breakdowns]`, `[Downtime Hours]`, `[MTTR Hours]`, `[MTBF Hours]`, `[Availability %]`, `[Breakdowns Within 15d of PM]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v10ByCategory` — Donut chart

Position and size: **x 1068, y 550, width 508, height 326**

Title: **Breakdowns by failure category**

| Field well | Drop in |
|------------|---------|
| Legend | `Fact_Breakdowns[FailureCategory]` |
| Values | `[Breakdowns]` |

Formatting:

- Legend: **on**

---

## Page 7 Spare Parts

Rename the page tab to **7 Spare Parts**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiReqVal | Card (new card) | 24, 92, 247, 118 |
| v02KpiConsVal | Card (new card) | 285, 92, 247, 118 |
| v03KpiPending | Card (new card) | 546, 92, 247, 118 |
| v04KpiEmergency | Card (new card) | 807, 92, 247, 118 |
| v05KpiBelowMin | Card (new card) | 1068, 92, 247, 118 |
| v06KpiSpendHr | Card (new card) | 1329, 92, 247, 118 |
| v07ByCategory | Clustered bar chart | 24, 226, 769, 310 |
| v08RequestTrend | Clustered column chart | 807, 226, 769, 310 |
| v09TopParts | Table | 24, 550, 769, 326 |
| v10BelowMin | Table | 807, 550, 769, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Spare Parts - requests, consumption and cost
Requested is not the same as consumed. The gap between the two is where the money leaks
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiReqVal` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Requested value**

| Field well | Drop in |
|------------|---------|
| Fields | `[Spare Request Value]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiConsVal` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Consumed value**

| Field well | Drop in |
|------------|---------|
| Fields | `[Spare Consumption Value]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiPending` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **Pending approvals**

| Field well | Drop in |
|------------|---------|
| Fields | `[Pending Approvals]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiEmergency` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Emergency requests**

| Field well | Drop in |
|------------|---------|
| Fields | `[Emergency Request %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiBelowMin` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Parts below minimum**

| Field well | Drop in |
|------------|---------|
| Fields | `[Parts Below Min Stock]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiSpendHr` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Spend per std hour**

| Field well | Drop in |
|------------|---------|
| Fields | `[Spend per Std Hour]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07ByCategory` — Clustered bar chart

Position and size: **x 24, y 226, width 769, height 310**

Title: **Consumption value by part category**

| Field well | Drop in |
|------------|---------|
| Y-axis | `Dim_SparePart[Category]` |
| X-axis | `[Spare Consumption Value]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#1B6E8C`
- Legend: **off**
- Data labels: **on**, 9pt

---

### `v08RequestTrend` — Clustered column chart

Position and size: **x 807, y 226, width 769, height 310**

Title: **Requests by status and month**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Date[MonthKey]` |
| Y-axis | `[Spare Requests]` |
| Legend | `Fact_SpareRequests[Status]` |

Formatting:

- Legend: **on**

---

### `v09TopParts` — Table

Position and size: **x 24, y 550, width 769, height 326**

Title: **Top consuming parts**

| Field well | Drop in |
|------------|---------|
| Columns | `Dim_SparePart[PartNo]`, `Dim_SparePart[PartName]`, `Dim_SparePart[Category]`, `[Spares Replaced Qty]`, `[Spare Consumption Value]`, `[Avg Approval TAT Days]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v10BelowMin` — Table

Position and size: **x 807, y 550, width 769, height 326**

Title: **Stock below minimum as at the last stock upload**

| Field well | Drop in |
|------------|---------|
| Columns | `Dim_SparePart[PartNo]`, `Dim_SparePart[PartName]`, `Dim_SparePart[CurrentStock]`, `Dim_SparePart[MinStock]`, `Dim_SparePart[LeadTimeDays]`, `Dim_SparePart[StoreBin]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

## Page 8 Abnormalities

Rename the page tab to **8 Abnormalities**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiTotal | Card (new card) | 24, 92, 247, 118 |
| v02KpiOpen | Card (new card) | 285, 92, 247, 118 |
| v03KpiHigh | Card (new card) | 546, 92, 247, 118 |
| v04KpiAged | Card (new card) | 807, 92, 247, 118 |
| v05KpiClosure | Card (new card) | 1068, 92, 247, 118 |
| v06KpiDays | Card (new card) | 1329, 92, 247, 118 |
| v07ByCategory | Clustered bar chart | 24, 226, 769, 310 |
| v08BySeverity | Clustered column chart | 807, 226, 769, 310 |
| v09OpenList | Table | 24, 550, 1552, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Abnormality Log
The early warning layer. Every one of these is a breakdown that has not happened yet
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiTotal` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Logged**

| Field well | Drop in |
|------------|---------|
| Fields | `[Abnormalities]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiOpen` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Open**

| Field well | Drop in |
|------------|---------|
| Fields | `[Open Abnormalities]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[Open Abnormality Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiHigh` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **High severity open**

| Field well | Drop in |
|------------|---------|
| Fields | `[High Severity Open]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiAged` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Open beyond 30 days**

| Field well | Drop in |
|------------|---------|
| Fields | `[Abnormalities Open Over 30d]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiClosure` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Closure rate**

| Field well | Drop in |
|------------|---------|
| Fields | `[Abnormality Closure %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiDays` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Avg days to close**

| Field well | Drop in |
|------------|---------|
| Fields | `[Avg Abnormality Closure Days]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07ByCategory` — Clustered bar chart

Position and size: **x 24, y 226, width 769, height 310**

Title: **Abnormalities by category**

| Field well | Drop in |
|------------|---------|
| Y-axis | `Fact_Abnormalities[Category]` |
| X-axis | `[Abnormalities]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#D08B2C`
- Legend: **off**
- Data labels: **on**, 9pt

---

### `v08BySeverity` — Clustered column chart

Position and size: **x 807, y 226, width 769, height 310**

Title: **Abnormalities raised by month and severity**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Date[MonthKey]` |
| Y-axis | `[Abnormalities]` |
| Legend | `Fact_Abnormalities[Severity]` |

Formatting:

- Legend: **on**

---

### `v09OpenList` — Table

Position and size: **x 24, y 550, width 1552, height 326**

Title: **Open abnormalities**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_Abnormalities[AbnormalityID]`, `Fact_Abnormalities[ReportedDate]`, `Dim_Machine[MachineName]`, `Dim_Cell[CellName]`, `Fact_Abnormalities[Category]`, `Fact_Abnormalities[Severity]`, `Fact_Abnormalities[Description]`, `Fact_Abnormalities[ReportedByName]`, `Fact_Abnormalities[Status]`, `Fact_Abnormalities[OwnerFunction]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

## Page 9 Technician

Rename the page tab to **9 Technician**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiHeadcount | Card (new card) | 24, 92, 247, 118 |
| v02KpiWoPer | Card (new card) | 285, 92, 247, 118 |
| v03KpiWrench | Card (new card) | 546, 92, 247, 118 |
| v04KpiCapacity | Card (new card) | 807, 92, 247, 118 |
| v05KpiUtil | Card (new card) | 1068, 92, 247, 118 |
| v06KpiScans | Card (new card) | 1329, 92, 247, 118 |
| v07LoadByTech | Clustered column chart | 24, 226, 769, 310 |
| v08ComplianceByTech | Clustered bar chart | 807, 226, 769, 310 |
| v09Scorecard | Table | 24, 550, 1552, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Technician Workload and Performance
Load balance first, performance second - an overloaded technician is a compliance problem, not an attitude problem
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiHeadcount` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Technicians active**

| Field well | Drop in |
|------------|---------|
| Fields | `[Technicians Active]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiWoPer` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Work orders per person**

| Field well | Drop in |
|------------|---------|
| Fields | `[WOs per Technician]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiWrench` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **Wrench hours**

| Field well | Drop in |
|------------|---------|
| Fields | `[PM Wrench Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiCapacity` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **Capacity hours**

| Field well | Drop in |
|------------|---------|
| Fields | `[Technician Capacity Hours]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiUtil` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Utilisation**

| Field well | Drop in |
|------------|---------|
| Fields | `[Technician Utilisation %]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiScans` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Machine QR scans**

| Field well | Drop in |
|------------|---------|
| Fields | `[Machine Scans]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07LoadByTech` — Clustered column chart

Position and size: **x 24, y 226, width 769, height 310**

Title: **Wrench hours against capacity, by technician**

| Field well | Drop in |
|------------|---------|
| X-axis | `Dim_Technician[TechName]` |
| Y-axis | `[PM Wrench Hours]`, `[Technician Capacity Hours]` |

Formatting:

- Legend: **on**

---

### `v08ComplianceByTech` — Clustered bar chart

Position and size: **x 807, y 226, width 769, height 310**

Title: **On-time compliance by technician**

| Field well | Drop in |
|------------|---------|
| Y-axis | `Dim_Technician[TechName]` |
| X-axis | `[PM Compliance %]` |

Formatting:

- Format ▸ Columns/Bars ▸ Colour: `#2F9E7E`
- Legend: **off**
- Data labels: **on**, 9pt

---

### `v09Scorecard` — Table

Position and size: **x 24, y 550, width 1552, height 326**

Title: **Technician scorecard**

| Field well | Drop in |
|------------|---------|
| Columns | `Dim_Technician[TechName]`, `Dim_Technician[Shift]`, `Dim_Technician[SkillGroup]`, `Dim_Technician[PrimaryArea]`, `[PM Work Orders]`, `[PM Completed]`, `[PM Compliance %]`, `[PM Wrench Hours]`, `[Technician Utilisation %]`, `[Checklist Fail Rate %]`, `[Machine Scans]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

## Page 10 Data Quality

Rename the page tab to **10 Data Quality**.

| Visual | Type | Position (x, y, w, h) |
|--------|------|------------------------|
| v00Header | Text box | 0, 0, 1600, 76 |
| v01KpiIssues | Card (new card) | 24, 92, 247, 118 |
| v02KpiMissing | Card (new card) | 285, 92, 247, 118 |
| v03KpiDesk | Card (new card) | 546, 92, 247, 118 |
| v04KpiNoChecklist | Card (new card) | 807, 92, 247, 118 |
| v05KpiLatest | Card (new card) | 1068, 92, 247, 118 |
| v06KpiAsOf | Card (new card) | 1329, 92, 247, 118 |
| v07UploadMatrix | Matrix | 24, 226, 1552, 310 |
| v08DeskClosed | Table | 24, 550, 769, 326 |
| v09RefreshNote | Text box | 807, 550, 769, 326 |

### `v00Header` — Text box

Position and size: **x 0, y 0, width 1600, height 76**

Text box content:

```
Data Quality and Refresh
The dashboard is only as honest as its inputs. Everything on this page should read zero
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

### `v01KpiIssues` — Card (new card)

Position and size: **x 24, y 92, width 247, height 118**

Title: **Total issues**

| Field well | Drop in |
|------------|---------|
| Fields | `[Data Quality Issues]` |

Formatting:

- Callout value ▸ Colour ▸ **fx** ▸ Format style *Field value* ▸ `[Data Quality Color]`
- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v02KpiMissing` — Card (new card)

Position and size: **x 285, y 92, width 247, height 118**

Title: **Missing upload rows**

| Field well | Drop in |
|------------|---------|
| Fields | `[Missing Std Hours Rows]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v03KpiDesk` — Card (new card)

Position and size: **x 546, y 92, width 247, height 118**

Title: **Closed without a scan**

| Field well | Drop in |
|------------|---------|
| Fields | `[Desk Closed WOs]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v04KpiNoChecklist` — Card (new card)

Position and size: **x 807, y 92, width 247, height 118**

Title: **No checklist evidence**

| Field well | Drop in |
|------------|---------|
| Fields | `[WOs Without Checklist]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v05KpiLatest` — Card (new card)

Position and size: **x 1068, y 92, width 247, height 118**

Title: **Latest upload month**

| Field well | Drop in |
|------------|---------|
| Fields | `[Latest Std Hours Month]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v06KpiAsOf` — Card (new card)

Position and size: **x 1329, y 92, width 247, height 118**

Title: **Data as of**

| Field well | Drop in |
|------------|---------|
| Fields | `[Data As Of]` |

Formatting:

- Callout value: 30pt Segoe UI Semibold. Card ▸ Label: **off**

---

### `v07UploadMatrix` — Matrix

Position and size: **x 24, y 226, width 1552, height 310**

Title: **Standard hours uploaded, by cell and month - any blank cell is a missing upload**

| Field well | Drop in |
|------------|---------|
| Rows | `Dim_Cell[CellName]` |
| Columns | `Dim_Date[MonthKey]` |
| Values | `[Std Hours]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v08DeskClosed` — Table

Position and size: **x 24, y 550, width 769, height 326**

Title: **Completed work orders with no machine QR scan**

| Field well | Drop in |
|------------|---------|
| Columns | `Fact_WorkOrders[WOID]`, `Dim_Machine[MachineName]`, `Fact_WorkOrders[ActualEndDate]`, `Fact_WorkOrders[AssignedTechName]`, `Fact_WorkOrders[MachineQRScanned]`, `[Checklist Completion %]` |

Formatting:

- Column headers `#173C52` background, white bold 9pt. Values 9pt, alternating rows `#F2F5F7`

---

### `v09RefreshNote` — Text box

Position and size: **x 807, y 550, width 769, height 326**

Text box content:

```
Refresh and ownership

The semantic model refreshes three times a day (06:00, 14:00, 22:00 IST). SharePoint lists and workbooks in Microsoft 365 refresh from the cloud, so no gateway is needed.

Missing upload rows: chase Production Planning. Until a cell's hours are loaded, its counter does not move and no PM will ever be scheduled for it.

Closed without a scan: the technician closed the job without being at the machine, or the QR label is damaged. Check the label first, then have the conversation.

No checklist evidence: the work order was closed outside the app. This should be impossible once item-level permissions are set correctly.
```

Format ▸ Effects ▸ Background: `#0F2A3D`, transparency 0. First line 20pt bold white, second line 10pt `#A9C2D0`.

---

## After every page is built

1. **View ▸ Page view ▸ Fit to page** on each page.
2. Set tab order on each page: **View ▸ Selection ▸ Tab order**, top-left to bottom-right. Screen readers follow this.
3. Add alt text to every chart: **Format ▸ General ▸ Alt text**. The generator cannot write anything meaningful for you and a chart with no alt text is invisible to a screen reader.
4. Page 5 (Machine 360) uses a machine slicer. To make it a drillthrough target as well: select the page, then drag `Dim_Machine[MachineID]` into the **Drillthrough** well in the Visualizations pane.
5. Save. If you save as `.pbix` none of the file-format problems in `11-opening-the-pbip.md` apply to you at all.
