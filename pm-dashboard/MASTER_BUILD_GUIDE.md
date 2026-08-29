# Master Build Guide

Build the whole system yourself, from an empty SharePoint site to a working
dashboard. Every step names the file you need and the document that covers it in
detail.

Nothing in this route depends on a Power BI project file matching your Desktop
version — you build the model and the report by hand, and save a normal `.pbix`.

---

## What you are building

| | |
|---|---|
| **Scheduling rule** | Standard hours accrue per cell from one monthly Excel upload. At **4000 hours the whole cell is scheduled** — one work order per machine. Hours past the threshold carry forward. A **12-month backstop** catches cells that never get there. |
| **Capture** | A Power Apps canvas app, opened by a QR code on every machine and every technician badge. Power BI cannot capture data; everything is written by the app. |
| **Automation** | Six Power Automate flows. Flow 2 owns the scheduling rule. |
| **Storage** | Eight SharePoint lists plus six master-data workbooks. |
| **Analytics** | A Power BI model — 17 tables, 28 relationships, 94 measures — and a 10-page report. |

## Time and order

| Phase | What | Who | Time |
|-------|------|-----|------|
| 0 | Decisions and access | You + Maintenance Head | half a day |
| 1 | SharePoint site, lists, master data | You | 1 day |
| 2 | The six flows | You | 2 days |
| 3 | The Power App | You | 3 days |
| 4 | QR codes | You | half a day |
| 5 | Power BI model | You | half a day |
| 6 | Power BI report | You | 1 day |
| 7 | Back-load, pilot, go live | You + one cell | 1 month |

Phases 1–2 must be done in order. Phase 5 can be done any time after Phase 1,
because it runs on the sample data. Do Phase 5 early if you want something to
show people while the rest is being built.

---

## Phase 0 · Decisions and access

### Get these before you start

- [ ] A SharePoint site you can create lists on, or an admin who will make one
- [ ] Power Apps and Power Automate available on your account (standard connectors
      are included with Microsoft 365 — confirm with whoever owns your tenant)
- [ ] Power BI Desktop installed, and a workspace to publish to
- [ ] Agreement on who owns the monthly standard-hours upload, **by name**

### Settle these, and write them on the worksheet

Open `05_Deployment/Deployment_Worksheet.xlsx` and fill in sheet 4.

1. **Is "standard hours" the same figure Production reports for efficiency?** If
   Maintenance and Production use two definitions, every scheduling argument for
   the next two years starts here.
2. **Is 4000 right?** It should roll up from OEM intervals per machine family. A
   round number someone picked is a fine start, but say so, and review it at the
   first quarterly.
3. **When a cell is due and Production will not release it — deferred or overdue?**
   The dashboard makes this visible from week one. Decide the policy now.
4. **Retention** on the scan log and checklist results. Quality systems commonly
   want seven years of PM evidence.

`10-open-decisions.md` covers all ten assumptions and what changing each one costs.

---

## Phase 1 · SharePoint

**Detail:** `02-sharepoint-setup.md`

### 1.1 Create the site

A **Team site** called `PMSystem`. Technicians go in as **Visitors**, not Members —
they write through the app, and you do not want them editing lists directly.

### 1.2 Create the folders

In **Shared Documents**, exactly these names — the Power Query folder scan depends
on them:

```
00 Reference/          01 Master Data/        02 Standard Hours/
02 Standard Hours/_History/                   03 QR Codes/          04 Photos/
```

### 1.3 Create the eight lists

Open `02_SharePoint_Templates/00-reference/SharePoint_List_Schemas.xlsx`. It has
one row per column of every list: name, type, choice values, required, indexed.

| List | Written by |
|------|-----------|
| `PM_WorkOrders` | Flow 2, then the app |
| `PM_ChecklistResults` | The app |
| `Breakdown_Reports` | The app |
| `SparePart_Requests` | The app |
| `SparePart_Replacements` | The app |
| `Abnormality_Log` | The app |
| `PM_Hour_Ledger` | Flow 2 |
| `QR_Scan_Log` | The app |

For each: create the columns in order, set **Title** to not required and hide it,
turn on versioning (50 versions), and add every column the schema marks
`Indexed = Yes`. Without the indexes you hit the 5,000-item view threshold once
the log lists grow.

On `PM_WorkOrders` only: **List settings ▸ Advanced ▸ Read access: All items,
Create and Edit access: Only their own.** A technician sees the whole plan but can
only change their own jobs.

> **Do not use Lookup columns** between these lists. They look tidy and then make
> Power BI refresh slow and brittle, cap you at 12 lookups per view, and break when
> a referenced item is deleted. Store the ID as plain text; the relationship belongs
> in the semantic model.

### 1.4 Load the master data

Upload from `02_SharePoint_Templates/01-master-data/` to `01 Master Data/`, **in
this order** — later files reference earlier IDs:

1. `Cell_Master.xlsx`
2. `Machine_Master.xlsx` — every `CellID` must exist in Cell_Master
3. `PM_Checklist_Master.xlsx` — every `ChecklistID` used by Machine_Master
4. `Technician_Master.xlsx`
5. `SparePart_Master.xlsx`
6. `PM_Config.xlsx`

Each workbook opens on a **READ ME** sheet with its rules. Replace the sample rows
with your own plant. Keep the sheet name and the Excel table name exactly as they
are — Power Query binds to them.

**The single most common cause of a machine that never gets scheduled** is a
`CellID` in Machine_Master that does not exist in Cell_Master. Check it before you
move on.

### 1.5 Upload the standard-hours history

Fill `02_SharePoint_Templates/02-standard-hours/Cell_Standard_Hours_History_BACKLOAD.xlsx`
with as much real history as you have, and put it in `02 Standard Hours/_History/`.
You will process it in Phase 7.

---

## Phase 2 · The six flows

**Detail:** `flows/BUILD_GUIDE.md` — every action, every expression.

Build them **in a solution**, not in *My flows*. Solutions are what make flows
movable between environments later; retrofitting that is painful.

| # | Flow | Trigger | Owns |
|---|------|---------|------|
| 1 | Validate Standard Hours Upload | File created in `02 Standard Hours` | Rejecting a bad file before it reaches the ledger |
| 2 | **Monthly PM Scheduler** | Called by Flow 1, or manually | **The 4000-hour rule** |
| 3 | Overdue Sweep | Daily 23:30 | Moving lapsed work orders to Overdue |
| 4 | Abnormality Escalation | Item created in `Abnormality_Log` | High severity to a person, immediately |
| 5 | Spare Approval | Item created in `SparePart_Requests` | Routing approval by value |
| 6 | Upload Reminder | 5th and 8th of the month | Chasing a missing upload |

Turn on **failure notifications** on all six (⋯ ▸ Settings). A flow that fails
silently is worse than no flow.

**Action names matter.** Expressions reference other actions by name, so a renamed
action breaks everything downstream. Use the names in the guide exactly.

**Flow 2 concurrency must be 1** on both loops — the machine index is shared state.
The guide flags this at the action.

Before moving on, run Flow 2 by hand once with a made-up month and check it writes
one `PM_Hour_Ledger` row per active cell.

---

## Phase 3 · The Power App

**Detail:** `POWERFX_REFERENCE.md` — every control, every formula, in build order.

**Try the prototype first:** open `07_Power_App/PM_Field_App.html`. It is all seven
screens with the same rules, running on the sample data. Walk the technician
journey, show it to the maintenance team, get it signed off — *then* build. Each
screen in the prototype shows the exact Power Fx that implements it.

1. Power Apps ▸ **Create ▸ Blank app ▸ Canvas ▸ Phone**. Name it `PM Field App`.
2. Add the SharePoint connector and all eight lists, plus the six master workbooks.
3. Create the screens: `scrHome`, `scrMachineHub`, `scrMyPMList`, `scrChecklist`,
   `scrBreakdown`, `scrSpareRequest`, `scrSpareReplaced`, `scrAbnormality`,
   `scrMachineHistory`.
4. Work through `POWERFX_REFERENCE.md` control by control.
5. Publish, and share with the Technicians security group as **User**.
6. Copy the **Web link** from the app's Details page — you need it in Phase 4.

### The rules that make it worth building

| Rule | Why |
|------|-----|
| A checklist can only start from a machine QR scan in the same session | Stops desk closure |
| Every screen entry writes to `QR_Scan_Log` | Attendance is provable, not asserted |
| Photo mandatory on any Not OK and on every abnormality | An abnormality without a photo does not get fixed |
| Mandatory tasks block submit | Partial PMs stop being signed off as complete |
| `ReportedDateTime` is `Now()`, never editable | MTTR stays honest |
| The technician QR shows the signed-in user's list, not the badge's | A borrowed badge cannot close someone else's work |

Test the last one explicitly: sign in as A, scan B's badge, confirm you still see
A's list.

---

## Phase 4 · QR codes

**Detail:** `06-qr-code-system.md`

1. Open `03_QR_Codes/QR_Generator.html` in Edge or Chrome. It runs entirely in the
   browser — nothing to install, no network used.
2. Paste the app **Web link** from Phase 3. It reads the three IDs out of it.
3. Paste your machine list straight out of `Machine_Master.xlsx` (select the rows
   including the header, copy, paste over the box).
4. **Generate**, then **Print / save as PDF**.

**Print one label on plain paper first.** Tape it where it will live, and scan it
with three different phones, in the real light at that spot, with a glove on. Only
then print the batch on polyester.

Fix labels at eye height by the operator panel, out of the coolant spray line, plus
a spare inside the electrical cabinet door.

> If the app is ever republished to a **different environment**, the IDs change and
> every label must be reprinted. Do the environment move before you print.

---

## Phase 5 · The Power BI model

**Detail:** `12-model-build-guide.md` — paste-ready Power Query for all 17 tables,
all 28 relationships, and where the 94 measures go.

You can do this before Phases 2–4 are finished. It runs on the sample CSVs, so you
get something to show while the rest is being built.

1. Copy the `data` folder somewhere stable, e.g. `C:\PM_Dashboard\data`.
2. New Power BI Desktop file ▸ **Transform data**.
3. Create the 3 parameters and 5 functions.
4. Create the 17 table queries. **Close & apply.**
5. Create the 28 relationships in Model view.
6. Create the `_Measures` table and all 94 measures from
   `08-dax-measure-library.md`, one display folder at a time.
7. Sanity check: a card with `[PM Compliance %]` and one with `[Std Hours]` should
   both show a number.

**Switching to live data later is two parameters:** `SourceMode` to `SharePoint`
and `SharePointSiteUrl` to your site. Nothing else in the model changes.

---

## Phase 6 · The report

**Detail:** `13-report-build-guide.md` — all 10 pages and 107 visuals, with the
exact field wells and positions.

1. **View ▸ Themes ▸ Browse for themes** ▸ `theme/PM_Theme.json`. Do this *before*
   building visuals so each one picks up the fonts and colours.
2. Canvas on every page: **Format ▸ Canvas settings ▸ Custom, 1600 × 900**.
3. Build page by page. Type the positions in rather than dragging — it is faster
   and it is what makes the pages line up.

| Page | What it answers |
|------|-----------------|
| 1 Overview | Is the PM programme healthy? |
| 2 PM Planning | When is each cell next due, and is it hours or the calendar driving it? |
| 3 Monthly Schedule | What has been raised, and who has it? |
| 4 Execution & Quality | Was the PM done, or just closed? |
| 5 Machine 360 | Everything about one machine |
| 6 Reliability | Where are the losses, and is PM preventing them? |
| 7 Spare Parts | Requested vs consumed, and what it costs |
| 8 Abnormalities | What is about to become a breakdown? |
| 9 Technician | Who is overloaded? |
| 10 Data Quality | Can I trust any of the above? |

Save as `.pbix`. Then publish, set credentials to **Organizational account**, and
schedule refresh at 06:00, 14:00 and 22:00.

---

## Phase 7 · Back-load, pilot, go live

### 7.1 Back-load the history

Run Flow 2 in **Backload** mode, once per historical month, oldest first, from the
history workbook. **Skip work order creation** for those months — historical PMs
were done on paper.

Then reconcile: does each cell's last-PM date in the ledger match your maintenance
register? Fix this before anything else. Every carry-over depends on it.

Skip the back-load and every cell starts at zero hours, nothing is scheduled for
three or four months, and the dashboard looks broken.

### 7.2 First real month

Upload one real `Cell_Standard_Hours_YYYY_MM.xlsx` and watch Flow 1 → Flow 2 run.
Check the work orders that appear against what you expected. If a cell you expected
did not trip, look at its ledger row — opening, added, closing, threshold. One of
those four is wrong, and the row tells you which.

### 7.3 Pilot on one cell

One cell, one full month. Not the whole plant.

- Run paper and digital in parallel, reconcile weekly
- Sit with a technician for their first three scans and watch where they hesitate —
  that is your UX backlog
- Review the Data Quality page every Monday

Only after a clean month, roll out cell by cell.

### 7.4 The ongoing rhythm

| When | Who | What |
|------|-----|------|
| 5th working day | Production Planning | Upload the standard hours |
| 6th | Flow 2 | Ledger and work orders |
| Daily 23:30 | Flow 3 | Overdue sweep and digest |
| Weekly Monday | Maintenance Head | Data Quality, then safety-critical failures, then overdue |
| Monthly | Maintenance Head | Compliance, MTBF/MTTR trend, spend per standard hour |
| Quarterly | Maintenance + Production | Are the 4000-hour thresholds still right? |
| Annually | Maintenance Engineer | Review the checklists against actual failure modes |

---

## The two things that will actually break this

**The monthly upload is a single point of failure.** If it stops, counters freeze,
nothing is ever scheduled, and the dashboard still looks green. That is why
`Missing Std Hours Rows` is a KPI, why page 10 exists, and why one of the six flows
does nothing but chase the file. Name an owner and a backup.

**Compliance alone can be gamed.** 100% compliance with a 0% checklist fail rate
and rising post-PM failures means the checklists are being clicked through, not
worked through. That is why those three measures share a page. Read them together
or not at all.

---

## Where everything is

| You need | Look in |
|----------|---------|
| The whole system, explained | `04_Documentation/Documentation.html` |
| SharePoint list schemas | `02_SharePoint_Templates/00-reference/` |
| Master data templates | `02_SharePoint_Templates/01-master-data/` |
| The monthly upload template | `02_SharePoint_Templates/02-standard-hours/` |
| Flow build steps | `06_Flows/BUILD_GUIDE.md` |
| Power Fx for every control | `07_Power_App/POWERFX_REFERENCE.md` |
| The app, running | `07_Power_App/PM_Field_App.html` |
| QR generator | `03_QR_Codes/QR_Generator.html` |
| Model build steps | `12-model-build-guide.md` |
| Report build steps | `13-report-build-guide.md` |
| All 94 measures | `08-dax-measure-library.md` |
| Your tenant details | `05_Deployment/Deployment_Worksheet.xlsx` |
