# Build Specification

Functional and technical specification for the Preventive Maintenance planning,
scheduling and tracking system: a Power BI dashboard, a QR-code-driven Power Apps
front end, the SharePoint file templates behind them, and a full sample dataset so
the whole thing works end to end before any real data exists.

This document is the source of truth for what the system does and why. Everything
in the repository was built to it, and everything can be rebuilt from it. Adjust
the values in **§1 Plant profile** to match your plant; the rest is settled.

Everything is regenerable by running scripts — there are no hand-edited output
files.

## 1 · Plant profile

- 8 production cells, 33 machines, 10 technicians, 42 spare part lines
- Machine families: CNC turning, CNC machining, gear hobbing/shaving, sealed
  quench and tempering furnaces, assembly stations, leak test, paint booth and
  curing oven, robotic welding, hydraulic press, conveyors, compressors, chillers
- Currency INR, financial year starts April, Indian public holidays
- 24 months of history ending this month, plus a 12-month forward forecast

## 2 · The scheduling rule — build this first, everything depends on it

Production standard hours accrue **per cell**, month by month, from an Excel file
uploaded monthly. Each cell carries a running counter:

```
opening(c, m) = carry-over from the previous cycle, else closing(c, m-1)
closing(c, m) = opening(c, m) + std_hours(c, m)

hours_due    = closing >= threshold(c)              -- default 4000
calendar_due = months_since_last_pm >= backstop(c)  -- default 12
triggered    = hours_due OR calendar_due

carry_over   = MAX(0, closing - threshold)          -- when triggered
trigger_type = "Std Hours" if hours_due else "Calendar Backstop"
```

When a cell trips, **the whole cell is scheduled**: one work order per active
machine in it. Hours past the threshold carry forward — a cell running hot must
never lose hours. `threshold` and `backstop` are per-cell columns defaulting from
a config table, so they can be retuned without touching code.

Forecast forward using the trailing 3-month average of uploaded hours. The
projected next PM date is the **earlier** of the hour projection and the calendar
backstop, and the model must say which of the two is driving it.

Implement this rule three times and keep them consistent:

1. `scripts/pm_core.py` — the executable reference spec, used to generate dummy data
2. A Power Automate flow specification — authoritative in production
3. Power BI measures — display and forecast only, never writes

## 3 · Dummy data

`scripts/generate_dummy_data.py`, seeded so it is reproducible. Write CSVs to
`data/dummy/`:

**Masters** — `Cell_Master`, `Machine_Master`, `Technician_Master`,
`PM_Checklist_Master`, `SparePart_Master`, `PM_Config`, `Dim_Date`

**Transactions** — `Cell_Standard_Hours`, `PM_Hour_Ledger`, `PM_WorkOrders`,
`PM_ChecklistResults`, `Breakdown_Reports`, `SparePart_Requests`,
`SparePart_Replacements`, `Abnormality_Log`, `QR_Scan_Log`

Make it realistic, not uniform:

- Cells with genuinely different loadings, so some trip every 3 months and at
  least one rides the 12-month calendar backstop
- Seasonal dips, month-to-month noise, a partial current month
- Work order statuses weighted to reality: mostly completed, a few late, a couple
  overdue, some deferred with a reason, future months Scheduled
- Real checklists — 9 to 14 tasks per machine family with objective acceptance
  standards ("6–9 %", "≤ 2.8 mm/s RMS", "stops within 1 s"), not "check the machine"
- Breakdown rates that scale with machine criticality
- Abnormalities arising both from failed checklist tasks and from walk-by scans
- Spare requests linked to both PMs and breakdowns, with a realistic spread of
  approval statuses

## 4 · SharePoint file templates

`scripts/build_sharepoint_templates.py` → `sharepoint-templates/`, organised:

```
00-reference/        SharePoint_List_Schemas.xlsx
01-master-data/      the six master workbooks, pre-filled
02-standard-hours/   blank monthly template, a filled sample, a history back-load
03-list-seed-data/   one workbook per SharePoint list, with the dummy rows
```

Every workbook must have:

- A **READ ME** sheet as sheet 1: purpose, data owner, update frequency, exact
  SharePoint path, numbered rules, and an explicit "do not" list (do not rename
  columns, do not add blank rows, do not merge cells, do not rename the sheet or
  the Excel table)
- A named Excel table over the data, so Power Query binds to a table name rather
  than a fragile cell range
- Data validation dropdowns on every choice column
- Frozen header row, dark header fill, autofilter, sensible column widths

The monthly upload template is the critical one. Its file name must be
`Cell_Standard_Hours_YYYY_MM.xlsx`, its sheet `Standard_Hours`, its table
`tblStdHours` — and the READ ME must say why in language a planner will read.

`SharePoint_List_Schemas.xlsx` lists every column of all eight lists with its
SharePoint type, choice values, required flag and whether it must be indexed.

## 5 · The QR code system

`scripts/generate_qr_codes.py`, taking environment ID, app ID and tenant ID as
arguments and defaulting to placeholders.

**Machine QR** (one per machine) encodes a Power Apps deep link
`...?source=qr&type=machine&id=<MachineID>` and opens a hub screen that answers, at
the top and in large type, *when was the last PM and when is the next one*, then
offers six actions: start PM checklist, report breakdown, request spare part,
record spare replaced, log abnormality, view full history.

**Technician QR** (one per person) encodes `...&type=tech&id=<TechID>` and opens
that person's PM work list.

**The technician's list must maintain itself.** A job leaves the list when the
machine QR is scanned and the checklist submitted. There is no "mark as done"
control anywhere — that is the design decision that makes attendance provable.

Generate PNGs at error-correction level H, plus print-ready HTML label sheets
(4 machine labels per A4, 8 technician badges per A4) with real physical specs, and
a payload index CSV. Include a section in the docs that is honest about what a QR
code does and does not secure: identity comes from the Microsoft 365 sign-in, the
code is just a pointer, and a borrowed badge must still show the signed-in person's
own list.

## 6 · The Power BI project

`scripts/build_pbip.py` writes a full PBIP project — TMDL semantic model plus PBIR
report — and also supports `--inject <existing.pbip>` for writing into a project
Power BI Desktop created, in case the from-scratch project will not open on a given
Desktop version.

**Model.** Star schema: `Dim_Date` (generated in M, marked as a date table),
`Dim_Cell`, `Dim_Machine`, `Dim_Technician`, `Dim_SparePart`, `Dim_Checklist`,
`Config`, and fact tables for standard hours, the hour ledger, work orders,
checklist results, breakdowns, spare requests, spare replacements, abnormalities
and the scan log. Single-direction many-to-one relationships; inactive
relationships for the alternate date roles.

**Source switching.** Three Power Query parameters — `SourceMode`
(`Local` | `SharePoint`), `LocalDataFolder`, `SharePointSiteUrl` — and a single
`fnSource(logicalName)` function that routes to a local CSV, a SharePoint list, or
a named Excel table in the document library. Go-live is one parameter change. Add a
folder-combine function for the monthly standard-hours uploads so a new file just
appears on refresh, with no query editing.

**Measures.** Around 90, on a dedicated `_Measures` table, in display folders:
context, standard hours and the counter, PM execution, checklist quality,
reliability, spare parts, abnormalities, technician, data quality, dynamic titles.
Every measure gets a format string and a one-line description written for a
maintenance manager, not a modeller.

Include these specifically, because they are what make the dashboard worth having:

- `% to PM Threshold`, `Hours to Next PM`, `Projected Next PM Date`,
  `Projected Trigger Reason`
- `PM Compliance %` measured against work orders **actually due**, not all raised
- `QR Verification %` and `Desk Closed WOs` — closed without anyone at the machine
- `Breakdowns Within 15d of PM` and `PM Induced Failure %` — the sharpest available
  measure of whether PMs are being done or merely signed off
- `Technician Utilisation %` against real capacity
- `Missing Std Hours Rows` — because if the upload stops, nothing is ever scheduled
- Colour measures returning hex, for conditional KPI formatting

**Report.** Ten pages at 1600 × 900:

1. Overview — the control tower
2. PM Planning — counters, run rate, forward plan
3. Monthly Schedule — cell × month matrix and the work order list
4. Execution & Quality — compliance next to checklist fail rate
5. Machine 360 — the QR landing page in dashboard form
6. Reliability — MTBF, MTTR, Pareto, bad actors, post-PM failures
7. Spare Parts — requested vs consumed, emergency share, spend per standard hour
8. Abnormalities — ageing matters more than volume
9. Technician — load balance shown before performance
10. Data Quality — every number here should read zero

**Design.** Deep slate ink `#0F2A3D`, teal accent `#1B6E8C`, paper `#F2F5F7`, white
cards, hairline borders. Green `#2F9E7E` / amber `#D08B2C` / red `#C4553B` reserved
strictly for status — nothing decorative is ever a status colour. Segoe UI, 30 pt
callouts, 11 pt titles, 9 pt labels. Every page: 76 px header band, six KPI cards,
two content rows, identical grid. Categories over five members go horizontal. No
3-D, no gauges, no gradients, no drop shadows. Ship a matching Power BI theme JSON
both registered in the report and standalone for manual import.

Validate every JSON file after writing and report the result.

## 7 · Documentation

`docs/`, numbered:

1. Architecture — including why each component is where it is, and what is
   deliberately out of scope
2. SharePoint setup — folders, all eight lists, indexed columns, item-level
   permissions, and the naming rules that are not negotiable
3. The scheduling engine — the rule, two worked numeric examples (one hot cell
   carrying hours forward, one low-utilisation cell hitting the calendar backstop),
   and where the rule lives in all three implementations
4. Power Apps spec — every screen, with real Power Fx for `App.OnStart` deep-link
   handling, the last-PM lookup, checklist materialisation, and submit validation
5. Power Automate flows — six flows, with the scheduling flow specified step by
   step, including back-load mode and restatement (a corrected month must reprocess
   every carry-over after it)
6. The QR system — payloads, physical label specs, and an honest security section
7. Dashboard design — page by page, with the reasoning behind each choice
8. DAX measure library — **generated from the measure definitions**, so it cannot
   drift from the model
9. Deployment checklist — phased, with a recovery path if the PBIP will not open,
   and a table of things that will go wrong and what each symptom means
10. Open decisions — every assumption made, suggestions worth adding, and the
    questions to settle before go-live

Write for a maintenance manager who is technical but not a Power Platform
developer. Explain the reasoning, not just the steps. Say plainly where something
is a trade-off.

## 8 · Engineering rules

- Scripts, not hand-written output. Every generated file must be reproducible.
- The scheduling rule is defined once in `pm_core.py` and referenced everywhere
  else. If it is copy-pasted, it will drift.
- Documentation that can be generated from code must be generated from code.
- Dummy data must exercise every branch — including the calendar backstop, a
  deferred work order, a rejected spare request and an open high-severity
  abnormality — or the dashboard will look right and be untested.
- Be explicit about what Power BI cannot do. It cannot capture data. Every write
  goes through Power Apps.
- Where a real decision is being made, record it in the docs rather than hiding it
  in code.

Build order: scaffold the folders and `pm_core.py` first, then the sample data.
Check the scheduling engine's output distribution — status mix, trigger-type mix,
compliance rate — before building anything on top of it. If the sample data does
not exercise the calendar backstop, a deferred work order and an open high-severity
abnormality, the dashboard will look right and be untested.

