# Implementation runbook

Step-numbered, start to finish. Written so a maintenance engineer who has never
built a flow can follow it.

**Total effort:** about 5 working days for Path A (Forms), 9–10 days for Path B
(canvas app). Do not compress it — step 4 (the Forms) and step 8 (UAT) are where
the mistakes get caught, and both are tempting to rush.

---

## Before you start

| Need | Detail |
|---|---|
| SharePoint site | A dedicated team site. **Do not** use an existing one — this creates 16 lists and 5 libraries |
| Permissions | Site Owner on that site |
| Licences | Microsoft 365 E3 or better. Power Automate and Forms are included |
| Service account | e.g. `svc-pm@yourcompany.com`, licensed, password not expiring. **All eleven flows are built under this account** |
| Workstation | Power BI Desktop, PowerShell 7, Python 3.9+ |
| Shop floor | At least one Android handset with a working camera |

### Why a service account

A flow owned by a person stops the day their licence is removed. That day arrives
without notice — a resignation, a role change, a licence audit — and the first
symptom is a counter that never resets, discovered weeks later.

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
```

```bash
pip install -r tools/requirements.txt
pip install -r qr/requirements.txt
```

---

## Step 1 — Prepare the data (30 min)

**1.1** Put the three workbooks and the dictionary in `input/`.

**1.2** Generate the import-ready CSVs and run the integrity checks:

```bash
python tools/prepare_sharepoint_data.py --strict
```

**1.3** Read `sharepoint/data/_VALIDATION_REPORT.md`. **It must show 0 errors.**

An ERROR means the row would break a documented integrity rule once it is in
SharePoint. Fix it in the source workbook and re-run. Do not load past it — a bad
`Cell_ID` that reaches production becomes a fact table full of orphaned rows that
join to nothing, and nothing announces it.

**1.4** Note the totals in `_ROW_COUNTS.csv`. You reconcile against these in step 3.

> Why CSVs rather than uploading the Excel file: SharePoint's "Import from Excel"
> guesses column types, and it guesses wrong on IDs that look numeric, on Yes/No,
> and on Indian-format dates. Every wrong guess is a column you have to delete and
> rebuild after the list already has data in it.

---

## Step 2 — Provision SharePoint (45 min)

**2.1** Create the site: **SharePoint → Create site → Team site**, named
`Maintenance`. Note the URL.

**2.2** Dry run first — always:

```powershell
cd sharepoint
.\provision_lists.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Maintenance" -WhatIf
```

Nothing is changed. It prints every list, every column and every index it would
create. Read it. Confirm 16 lists, 224 columns, 5 libraries.

**2.3** Run it for real:

```powershell
.\provision_lists.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Maintenance"
```

**2.4** Apply the views and the shop-floor formatting:

```powershell
.\apply_views.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Maintenance" -WhatIf
.\apply_views.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Maintenance"
```

**2.5** Check one column internal name. Open `Cell_Master` → **Settings → List
settings**, click `Cell_ID`, and look at the URL. It must end `Field=Cell_ID`,
**not** `Field=Cell%5Fx005f%5FID`.

> If it is mangled, the list was created by hand rather than by the script. Every
> Power Query step, every flow expression and every model reference would have to use
> the mangled name. Delete the column and let the script recreate it from field XML.

---

## Step 3 — Load the data (20 min)

**3.1** Dry run:

```powershell
.\load_data.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Maintenance" -WhatIf
```

Expect **2,822 rows, 0 conversion problems** (730 of them the plant calendar).

**3.2** Load:

```powershell
.\load_data.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/Maintenance"
```

**3.3 Reconcile.** Open each list and compare its item count against
`sharepoint/data/_ROW_COUNTS.csv`.

> A short list is a silently dropped row. It will not announce itself later — it
> will just make a number slightly wrong in a way nobody can trace.

**3.4** Spot-check five rows in `Cell_Master`: dates are real dates, `Active` is a
tick not the text "Yes", `Cum_Std_Hours_Since_PM` is a number.

**3.5 Mark your holidays in `Plant_Calendar`.** It is seeded with Sundays off and
nothing else. Festival holidays and the annual shutdown are plant-specific and were
deliberately **not** guessed.

> `Actual_Std_Hours` is a capacity figure, so a mid-month PM reset prorates by
> **working** days. Every holiday you do not mark is a day the proration thinks the
> plant was running. Pongal, Diwali and the annual shutdown are the ones that matter
> most in Pondicherry.

Open `Plant_Calendar`, filter to the next twelve months, and set `Day_Type` to
`Holiday` or `Shutdown` and `Is_Working_Day` to No on those dates. Do it before the
first monthly upload, and again each December for the year ahead.

---

## Step 4 — Build the Microsoft Forms (half a day)

**This step decides whether the technician has to type anything a machine already
knows.** Question order matters, and it is not obvious.

### 4.1 The rule: hidden pre-filled fields come FIRST

A pre-filled link populates answers **by position**. Question 1 gets the first
pre-fill value, question 2 the second, and so on. Add a question above them later
and every pre-filled sticker on the shop floor now populates the wrong field —
silently, with no error, until somebody notices `Machine_ID` in the shift box.

So: **`Machine_ID` is always question 1, `Cell_ID` always question 2.** Never insert
above them. Never reorder them. If you need a new question, append it.

### 4.2 Build each form

Five forms: **PM Start**, **PM Checklist**, **Breakdown Report**, **Spare Request**,
**Abnormality Log**.

For each:

1. **forms.office.com** → **New Form**, created **under the service account**
2. Question 1: **Text**, "Machine ID", **Required**
3. Question 2: **Text**, "Cell ID", **Required**
4. Question 3: **Choice**, "Technician Name", **Required** — paste all six names
   from `Technician_Master`

   > Mandatory on **every** form, never optional, never free text. Technicians share
   > one M365 login, so this dropdown is the entire audit trail the system will ever
   > have. Free text produces "Murugan", "murugan s" and "MURUGAN S", and three
   > months later nothing can be counted.

5. Then the questions specific to that form (see `automate/FLOW_SPECS.md`)
6. **Settings → Anyone can respond** (the handsets share one account)
7. **Settings → Record name → off** (it would record the shared account, which is
   worse than nothing — it looks like attribution and is not)

### 4.3 Make a pre-filled link

1. Open the form → **Collect responses** → **Get a link to prefill answers**
2. Fill in `Machine_ID` = `MC-01-001`, `Cell_ID` = `CELL-01`, leave the rest blank
3. **Get link**. You get something like:

```
https://forms.office.com/r/AbCdEf?id=xxxxx&r1a2b3c4=MC-01-001&r5d6e7f8=CELL-01
```

`r1a2b3c4` and `r5d6e7f8` are that form's question IDs. **They are stable for the
life of the form.**

### 4.4 Turn it into a per-machine URL

Substitute the machine ID into the pattern for all 30 machines:

```
https://forms.office.com/r/AbCdEf?id=xxxxx&r1a2b3c4={Machine_ID}&r5d6e7f8={Cell_ID}
```

Fastest way: paste the pattern into a spreadsheet column next to
`Machine_Master`, substitute with a formula, and paste the result back into the
`Checklist_Form_URL`, `Breakdown_Form_URL`, `Spare_Request_Form_URL` and
`Abnormality_Form_URL` columns.

**Test one on a phone before doing all 30.** Open the link and confirm the machine
and cell are already filled in and that the technician's first tap is the name
dropdown, not a keyboard.

### 4.5 Build the QR payload

The QR does **not** encode a form URL. It encodes the **Machine Hub view**, so a scan
lands on a page showing last PM date, cell hours and *all five* actions:

```
https://<tenant>.sharepoint.com/sites/Maintenance/Lists/Machine_Master/Machine%20Hub.aspx?FilterField1=Machine_ID&FilterValue1=MC-01-001&FilterType1=Text
```

`apply_views.ps1` prints this pattern with your site already substituted at the end
of its run.

Put it in `Machine_Master.QR_Payload_URL` for all 30 machines.

> **Generated once, printed once, never edited casually.** A change here means
> reprinting stickers. If you intend to use the canvas app (Path B), decide that
> **now** — the payload is a different URL and you do not want two print runs.

---

## Step 5 — Print and fit the QR labels (half a day)

**5.1** Regenerate against your real site and **test**:

```bash
python qr/generate_qr_labels.py --base-url https://<tenant>.sharepoint.com/sites/Maintenance --test
```

It must report **30 passed, 0 failed**. Do not print otherwise.

> A wrong sticker on a machine is a field problem that takes about a month to
> surface, and by then it has been scanned two hundred times against the wrong
> machine. Every one of those is a corrupt row you cannot easily unpick.

**5.2** Print `qr/labels/PM_QR_Labels.pdf` on **A4 polyester or vinyl** sticker
sheets, 3 × 8 pre-cut at 50 × 30 mm, **at 100% scale**.

> "Fit to page" shrinks the QR below the 25 mm minimum and the codes stop scanning
> reliably. Paper labels do not survive a fuse plant — oil wicks in and the code is
> gone in weeks.

**5.3** Fit at chest height, on a flat surface, away from the coolant spray line.
Over-laminate if you can.

**5.4** Walk the floor with a phone and scan **every one**. Confirm each opens the
hub for the machine it is stuck to. Two people, one hour, and it removes an entire
class of problem permanently.

---

## Step 6 — Build the flows (2 days)

Follow `automate/FLOW_SPECS.md`. Every expression is written out in
`automate/expressions.md`.

**Build order — this matters.** Flows 1, 2 and 5 are the spine: the counter, the
trigger and the reset. Build and test those three before anything else. The other
eight are independent and can follow in any order.

| Order | Flow | Time |
|---|---|---|
| 1 | PM-05 Cell Closure & Counter Reset | 3 h |
| 2 | PM-02 PM Trigger & Work Order Creation | 3 h |
| 3 | PM-01 Monthly Std Hours Import | 4 h |
| 4 | PM-03 Start PM (scan) | 1 h |
| 5 | PM-04 Checklist Submission | 3 h |
| 6 | PM-06 Breakdown Report | 1 h |
| 7 | PM-07 Spare Request + Approval | 2 h |
| 8 | PM-08 Spare Replaced | 1 h |
| 9 | PM-09 Abnormality Log | 1 h |
| 10 | PM-10 Follow-Up WO from NOT OK | 1 h |
| 11 | PM-11 Daily Digest | 2 h |

### Two rules that will each save you a day

**Rename actions before writing expressions.** Expressions reference actions by name
with spaces replaced by underscores. Rename an action afterwards and the expression
breaks — the flow saves fine and fails at runtime with a null.

**Set `Configure run after` on every SharePoint write.** The default on failure is to
stop silently. Add a failure branch that emails the owner, or you will find out
about a broken flow when someone asks why a counter never reset.

**Turn concurrency OFF on flows 1 and 5.** Both read a value, change it, and write it
back. Two parallel runs would each read the same counter and one increment would be
lost — the classic race, and it will happen the first month two cells finish on the
same afternoon.

---

## Step 7 — Build the Power BI report (half a day)

**7.1** Follow `powerbi/README_PowerBI.md`. Open `PM_Dashboard.pbip`, set
`pSourceFolder`, refresh.

**7.2** Finish the two things Desktop has to do:
- drag `Dim_Machine[Machine_ID]` into the **Drill through** well on page 5
- set the two Gantt offset series on page 3 to **no fill**

**7.3** Check every page opens with no visual errors.

**7.4** Cross-check the numbers:

```bash
python tools/verify_measures.py --asof 2026-08-30
```

Compare against the same measures in Desktop. They should agree. Expected values are
in `ASSUMPTIONS.md` §9.

**7.5** Repoint to SharePoint: `pSourceMode` → `SharePoint`, set `pSharePointSite`,
refresh.

**7.6** Publish to a workspace. Set scheduled refresh **06:00** and **14:00 IST**,
and set the SharePoint credentials under **Data source credentials**.

---

## Step 8 — UAT (1 day)

Work through `docs/UAT_TEST_CASES.md` in order. All 33 cases, recorded, with a name
and a date against each.

**Do not shorten this step.** The five that must pass before go-live:

| Case | What it proves |
|---|---|
| UAT-03 | A cell crossing 4,000 raises exactly one work order |
| UAT-07 | The 6-month backstop fires for a cell that never reaches 4,000 |
| UAT-14 | Three of four machines complete and **nothing** resets |
| UAT-15 | The fourth completes and all five `Cell_Master` fields move together |
| UAT-19 | A mid-month reset prorates to the hand-calculated figure |

UAT-14 and UAT-15 together are the whole system. If the counter resets when three of
four machines are done, every PM interval is wrong from that day on and nothing on
any dashboard will show it.

---

## Step 9 — Train and go live (1 day)

**9.1** Print `docs/TECHNICIAN_SOP_1PAGE.md`, laminate it, and put it at each cell.

**9.2** Train the technicians — 30 minutes, at a machine, not in a room:
- scan a sticker, look at the hub, read the counter
- start a PM, work a checklist, submit it
- report a breakdown
- **why the name dropdown matters** — say plainly that it is the only record of who
  did the work, and that a wrong name means someone else gets asked about it

**9.3** Train the supervisors — 1 hour:
- the `My Allotted PM List` view and how it empties
- the daily digest and what to act on first
- the Power BI planning page and the monthly PM plan
- approving spare requests

**9.4** Go live on a **Monday**, not a Friday. The first week generates questions and
you want a full week to answer them.

**9.5** Run the first monthly upload **with someone watching**. It is the step with
the most moving parts and the one nobody will remember in a year.

---

## Step 10 — The monthly routine

| When | What | Who |
|---|---|---|
| 1st–3rd | Upload the std-hours workbook to `StdHours_Inbox` | Planner |
| 1st–3rd | Check the import summary email; confirm every cell is listed | Planner |
| 5th | Review cells at 90%+; agree PM dates with production | Supervisor |
| 25th | **Freeze next month's plan** in `PM_Plan_Calendar` | Supervisor |
| Monthly | Review every `Skip_Reason` from the month | Manager |
| Monthly | Review `Breakdowns After PM (7d)` — is the PM working? | Manager |
| Quarterly | Review `Trigger_Type` split. Mostly Calendar Backstop means 4,000 is too high | Manager |
| Quarterly | Review `Min_Stock` against `Stock_At_Request` history | Stores |
| Each December | Mark next year's holidays and shutdown in `Plant_Calendar` | Planner |
| Year 4 | Extend `Plant_Calendar` past 2027-03-31; review `Scan_Log` archiving | IT |

**Freezing the plan on the 25th is what makes adherence honest.** Without a frozen
plan you can only measure "did we do it", never "did we do it when we said we would",
and the second question is the one production actually cares about.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Counter did not reset after all machines done | Flow 5 failed, or a task is `Pending` not `Completed` | Check the run history; check the `Get items pending tasks` filter |
| Two work orders for the same cell | Flow 2's open-WO check is missing or misconfigured | Cancel one; fix the condition |
| Monthly upload rejected | That month already exists | Check `StdHours_Monthly` for the existing rows |
| Counter jumped by a whole month after a mid-month PM | Proration not applied | Check `Reset_Date` is populated and in the uploaded month |
| Monthly import fails "divide by zero" or terminates naming a month | `Plant_Calendar` has no working days for that month | Add the month's dates and mark working days |
| Proration posts slightly too many hours | Holidays not marked in `Plant_Calendar` | Mark them; the divisor counts only working days |
| Scan opens a blank hub | `QR_Payload_URL` points at a renamed or deleted view | Re-run `apply_views.ps1`, update the column, reprint |
| Power BI shows blank columns after repointing | Mangled column internal names | Recreate the columns from field XML |
| Flow fails with "cannot convert null" | A null number in arithmetic | Wrap in `float(coalesce(x, 0))` |
| List view threshold error | A filtered column is not indexed | Re-run `provision_lists.ps1`; it is idempotent |
| Digest never arrives | It only sends when something is outstanding | That is intended — check the run history shows a skip |

---

## Handover checklist

- [ ] All 16 lists created, row counts reconciled against `_ROW_COUNTS.csv`
- [ ] `Plant_Calendar` holidays and shutdowns marked for the next 12 months
- [ ] Column internal names verified unmangled on at least three lists
- [ ] 12 views created; Machine Hub renders the five buttons on a phone
- [ ] 5 Forms built, technician dropdown mandatory on all five
- [ ] All 30 pre-filled URLs tested on a real phone
- [ ] 30 QR labels printed, fitted and **individually scan-tested**
- [ ] All 11 flows built, owned by the service account, failure alerts on
- [ ] Concurrency off on flows 1 and 5
- [ ] Power BI published, refresh scheduled, credentials set
- [ ] All 33 UAT cases passed and recorded
- [ ] SOP printed and laminated at each cell
- [ ] Technicians and supervisors trained
- [ ] `ASSUMPTIONS.md` §8 — flow ownership (§8.2) settled with IT
- [ ] First monthly upload run with someone watching
