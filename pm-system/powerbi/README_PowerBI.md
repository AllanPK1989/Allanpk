# Power BI — how to open, refresh and repoint

## What is in this folder

```
PM_Dashboard.pbip                  entry point — open this in Power BI Desktop
PM_Dashboard.SemanticModel/        TMDL: 17 tables, 42 relationships, 94 measures
PM_Dashboard.Report/               PBIR: 9 pages, 116 visuals
theme/EPQPL_PM_Theme.json          report theme (also registered inside the report)
m_queries/*.pq                     one Power Query script per table, commented
dax/measures.dax                   every measure, with a comment block each
```

The `.pq` and `.dax` files are the **source of truth**. The TMDL embeds them.
After editing either, rebuild:

```
python tools/build_pbip.py      # model: embeds the .pq files and the measures
python tools/build_report.py    # report: pages, visuals, theme registration
python tools/validate_model.py  # checks every reference resolves — run this last
```

Power BI Desktop must be **closed** while those run; it holds the project files open.

---

## Opening it — two routes

### Route A: open the project directly (try this first)

1. Put the three workbooks in a folder, e.g. `C:\EPQPL_PM\input`.
2. Double-click `PM_Dashboard.pbip`.
3. Desktop will ask for the parameter values. Set `pSourceFolder` to your folder.
4. **Refresh**.

### Route B: if your Desktop version rejects the project file

Desktop writes version-specific boilerplate. If Route A gives a schema error,
generate that boilerplate on your own machine and drop this content into it:

1. Open Power BI Desktop → **Get data → Excel** → pick `01_PM_Master_Data.xlsx` →
   load any one sheet → **File → Save As → Power BI project (.pbip)** → save as
   `PM_Dashboard` into a scratch folder. That produces a valid empty project.
2. Close Desktop.
3. Copy **over** the new project:
   - `PM_Dashboard.SemanticModel/definition/` (whole folder)
   - `PM_Dashboard.Report/definition/` (whole folder)
   - `PM_Dashboard.Report/StaticResources/`
4. Reopen the `.pbip`. Everything loads together.

Keep the `.platform` and `definition.pbism` / `definition.pbir` files that
**Desktop** generated — those carry the version-specific bits.

---

## Repointing to SharePoint — one parameter

This is the whole switch. **Home → Transform data → Manage parameters**:

| Parameter | Development | Production |
|---|---|---|
| `pSourceMode` | `Excel` | `SharePoint` |
| `pSourceFolder` | `C:\EPQPL_PM\input` | *(ignored)* |
| `pSharePointSite` | *(ignored)* | `https://<tenant>.sharepoint.com/sites/Maintenance` |
| `pStdHoursArchiveFolder` | blank, or a folder of monthly files | the synced `StdHours_Archive` path |

Change `pSourceMode` to `SharePoint`, set `pSharePointSite`, refresh. Nothing else
is edited.

**Why it is only one parameter.** Every table goes through `fnGetTable`, and that
function is the only code in the model that knows which source it is talking to.
Because the data dictionary made every sheet name and column name identical to its
SharePoint list and column name, both paths return the same shape and every step
downstream is unchanged.

In the Service: **Semantic model → Settings → Parameters**, then set credentials
for the SharePoint source under **Data source credentials** (OAuth2).

### Standard hours: a folder, not a file

`Fact_StdHours` appends **every** workbook in `pStdHoursArchiveFolder` rather than
reading one file, so a new month appears on the next refresh with no query change.
Point it at the SharePoint `StdHours_Archive` library and it keeps working. Leave
it blank and the query falls back to the single template workbook, which is what
the dummy data uses.

---

## Model shape

**Star schema.** Six dimensions fan out to ten facts. Every relationship is
single-direction, one-to-many, dimension → fact. Nothing is bidirectional — a
bidirectional filter would create ambiguous paths between `Dim_Cell` and
`Dim_Machine` through any fact carrying both keys.

```
Dim_Cell ──────┬─→ Fact_StdHours          Dim_Date ─→ (one ACTIVE date per fact)
Dim_Machine ───┼─→ Fact_WorkOrder
Dim_Technician ┼─→ Fact_MachineTask
Dim_Spare ─────┼─→ Fact_ChecklistResponse
Dim_ChecklistItem→ Fact_ScanLog / Breakdown / SpareRequest
Dim_Date ──────┴─→ SpareReplaced / Abnormality / PlanCalendar
```

**Inactive date relationships** exist where a second clock genuinely matters.
Reach them with `USERELATIONSHIP`:

| Fact | Active date | Inactive | Measure that uses it |
|---|---|---|---|
| `Fact_WorkOrder` | `WO_Created_Date` | `Planned_End_Date` | `Planned WO Count` |
| `Fact_WorkOrder` | `WO_Created_Date` | `Actual_End_Date` | `Completed WO Count (by Actual Date)` |
| `Fact_Abnormality` | `Logged_Date` | `Target_Date` | *(available, not yet on a page)* |
| `Fact_SpareRequest` | `Request_Date` | `Approved_Date` | *(available, not yet on a page)* |

`Dim_Date` is generated in DAX with `CALENDAR`, covers **2025-04-01 to 2027-03-31**
(two Indian financial years) and is marked as the date table — without that mark
the time-intelligence functions return wrong answers silently rather than erroring.

---

## The nine pages

| # | Page | The question it answers |
|---|---|---|
| 1 | Executive PM Overview | Are we doing the PM we said we would, and is it working? |
| 2 | PM Planning & Hours Forecast | Which cells hit 4,000 hours next, and what will that cost in technician time? |
| 3 | Monthly Schedule & Adherence | Did we do it in the month we froze the plan for? |
| 4 | Live Work Order Tracking | What is open now, and what is stopping each cell from closing? |
| 5 | Machine 360 | Everything known about one machine (drillthrough) |
| 6 | Checklist Findings & Abnormalities | What are the PMs finding, and is any of it being fixed? |
| 7 | Breakdown & Reliability | Is preventive maintenance actually preventing anything? |
| 8 | Spares & Cost | What is maintenance costing, and which parts will stop a PM? |
| 9 | Technician Performance | Who is doing the work, how thoroughly, is the load shared? |

### Two things to finish in Desktop

Both are 60-second jobs that the file format cannot express on its own.

**1. The drillthrough field on page 5.** Select `Machine 360`, then drag
`Dim_Machine[Machine_ID]` into the **Drill through** well in the Visualizations
pane. Right-clicking a machine anywhere else then offers *Drill through → Machine 360*.

**2. The Gantt offset series on page 3.** `v20Gantt` is a stacked bar whose first
series is an **invisible offset** that positions the visible bar. Select the visual
→ Format → Bars → Colors → set `Gantt Planned Offset (Days)` and
`Gantt Actual Offset (Days)` to **no fill / 100% transparency**. What remains reads
as a planned-vs-actual timeline. (Power BI has no native Gantt; this is the standard
construction.)

### Optional: turn the info footnote into a toggled panel

Each page carries a "How this is calculated" footnote across the bottom. It is
always visible on purpose — a footnote cannot be left switched off by whoever used
the report last. To make it a toggled panel instead:

1. Select the footnote visual (`v90Info`) → **View → Selection** → hide it.
2. **View → Bookmarks → Add**, name it `Info Off`. Show the visual, add `Info On`.
3. Both bookmarks: right-click → untick **Data**, tick **Display** and
   **Selected visuals** (with `v90Info` selected) so the bookmark cannot disturb
   anyone's filters.
4. **Insert → Buttons → Information**, then **Action → Bookmark → Info On**.

---

## Design rules the pages follow

- Canvas 1280 × 720. 12-column grid, 88 px columns, 16 px gutters, 24 px margin.
  Nothing touches an edge.
- One KPI row across the top of every page, five cards, equal width.
- Palette: primary `#0C3549`, accent `#2E86AB`, positive `#44C088`,
  warning `#F0A202`, negative `#ED7373`, canvas `#F5F7F8`, card `#FFFFFF`,
  text `#1F2933`, muted `#7B8794`. Segoe UI throughout.
  **No default Power BI blue anywhere** — the theme replaces the whole palette.
- No 3D, no gradients, no pie chart with more than four slices.
- Data labels on, gridlines off, axis titles only where the unit is ambiguous.
- Every visual title states the question it answers, not the field it plots.

The RAG thresholds in the report match the SharePoint column formatting exactly
(`>=100%` red, `>=90%` amber, `>=75%` blue, below that green), so a cell that is
amber on the shop-floor list is amber on the manager's dashboard.

---

## Refresh and scheduling

- **Import mode**, not DirectQuery. The lists are small and the report is read far
  more often than the data changes; DirectQuery against SharePoint would be slower
  and would put a query on the list every time somebody moved a slicer.
- Schedule two refreshes a day: **06:00** (before the shift) and **14:00**.
- The monthly std-hours import lands early in the month; the 06:00 refresh on the
  2nd or 3rd picks it up.

### If a refresh fails

| Symptom | Cause | Fix |
|---|---|---|
| "The key didn't match any rows in the table" | A sheet or list name changed | Check `fnGetTable`'s `ExpectedColumns` map against the source |
| Blank columns after switching to SharePoint | Column internal name is mangled (`Cell_x005f_ID`) | The list was built by hand, not by `provision_lists.ps1`. Recreate the column from field XML |
| Dates off by a month | A `YYYY-MM` text column was read as a date | `Upload_Month` and `Planned_Month` must stay **text** |
| Std hours doubled for one month | The same month was uploaded twice | `Fact_StdHours` de-duplicates on `Upload_Month` + `Cell_ID`; check `StdHours_Monthly` for the duplicate row and delete it |
| Refresh times out on `Checklist_Response` | List past the delegation limit | Confirm the indexes from `provision_lists.ps1` are present |

---

## Verifying the numbers

`tools/verify_measures.py` recomputes every headline measure from the prepared
CSVs in plain Python, independently of the DAX, and prints hand-worked examples for
the three calculations the system's credibility rests on:

```
python tools/verify_measures.py --asof 2026-08-30
```

Compare its output against the same measures in Desktop. They should agree.
The expected values on the supplied dummy data are recorded in
`docs/ASSUMPTIONS.md`.
