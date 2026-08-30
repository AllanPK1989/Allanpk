# Handover — EPQPL Cell-Based PM System

**One document. Read this first; everything else is detail it points at.**

| | |
|---|---|
| **What it is** | Preventive maintenance planning, scheduling and execution for the Pondicherry fuse plant |
| **Runs on** | SharePoint Online, Microsoft Forms, Power Automate, Power BI — all Microsoft 365 E3 |
| **Extra licence cost** | None |
| **Status** | Built and verified against 12 months of data. **Not yet provisioned to a live site** |
| **Effort to go live** | About 5 working days, plus 1 day UAT |
| **Repository** | `pm-system/` — 644 files |

---

## 1. What the system does

Ten rules. They are fixed — the build implements them, it does not reinterpret them.

1. **PM is triggered per CELL, not per machine.** A cell is 3–4 machines.
2. The trigger is **4,000 production standard hours** accumulated by that cell since
   its last PM — held per cell in `PM_Trigger_Hours`, never hard-coded.
3. **Calendar backstop at 6 months.** Whichever comes first wins.
4. **Amber warning at 90%** (3,600 h) so planning has lead time.
5. Actual hours arrive **monthly — one file, one row per cell** — and are added to
   the cell's running counter.
6. The counter **resets to zero only when the cell's work order completes.**
7. A work order holds **one task per machine**. It closes only when **every** machine
   task is done. Three of four is not done.
8. Technicians share one M365 login, so a **mandatory technician dropdown** on every
   form is the entire audit trail.
9. Every machine carries a **QR sticker** that opens that machine's hub.
10. A PM reset falling mid-month **prorates** that month's hours by **working days**.

### The one number to watch

**`Breakdowns After PM (7d)`** — breakdowns on a cell within seven days of a
completed PM on that same cell.

Compliance can read 100% while this climbs. When it does, the checklist is being
signed rather than performed, or it is checking the wrong things. It is the only
measure that tells you whether the PM is real.

On the 12 months of data supplied: **9 of 88 breakdowns (10.2%), carrying 34.4 of
the 299.5 hours of annual production loss.** Read it as a share, not a count.

---

## 2. What has been built

| Component | Contents |
|---|---|
| **SharePoint** | 16 lists, 224 columns, 5 document libraries, 12 views, 8 column-formatting files |
| **Data** | 2,822 rows, typed and validated, ready to load |
| **Power BI** | 17 tables, 42 relationships, 94 measures, 9 pages, 116 visuals, custom theme |
| **Power Automate** | Build sheets for 11 flows, every expression written out |
| **QR labels** | 30 labels, 50×30 mm, tested; printable A4 sheets |
| **Forms** | 5 forms specified, with the pre-filled-link procedure |
| **Documentation** | Runbook, assumptions, 35 UAT cases, 1-page bilingual shop-floor SOP |
| **Power Apps** | Phase 2 spec + licence business case (not licensed today) |

### Data loaded per list

```
Cell_Master              8      PM_WorkOrder            51
Technician_Master        6      PM_Machine_Task        193
Spare_Master            15      Checklist_Response     997
Checklist_Master        51      Scan_Log               336
Machine_Master          30      Breakdown_Log           88
Plant_Calendar         730      Spare_Request           64
StdHours_Monthly        96      Spare_Replaced          58
                                Abnormality_Log         44
                                PM_Plan_Calendar        55
                                                    ------
                                                     2,822
```

---

## 3. Decisions of record

All eight open questions are answered. These are settled — do not re-litigate them
without a reason, and record the reason if you do.

| # | Question | Decision |
|---|---|---|
| 1 | Do cancelled work orders count against compliance? | **No** — excluded from `PM Due Count` |
| 2 | Does a skipped machine block cell closure? | **No** — the cell closes, flagged partial |
| 3 | Is `Actual_Std_Hours` an actual or a capacity figure? | **Capacity** — so proration is by **working days** |
| 4 | Is the Tamil label wording right? | **Yes** — approved for print |
| 5 | Are Power Apps rights available? | **No** — go live on Forms; canvas app is Phase 2 |
| 6 | Who owns the eleven flows? | **An individual account** — see §6, this needs managing |
| 7 | Retention on `Scan_Log` / `Checklist_Response`? | **None** — keep everything |
| 8 | Is 4,000 hours right for every cell? | Held per cell; all eight currently 4,000 |

Full reasoning and consequences: `docs/ASSUMPTIONS.md` §8.

### The two that changed the build

**Q3 — capacity, not actual.** Capacity accrues on the days the plant runs, so a
mid-month PM reset prorates by working days. Verified: CELL-05, April 2026, 780 h
reported, reset on the 2nd → 24 of 26 working days → **720.00 h** posted.
Calendar-day proration would have posted 728.00 h — 8 hours the plant was closed
for. Small once; it compounds every cycle in the same direction.

This added `Plant_Calendar`, the 16th list.

**Q5 — no Power Apps licence.** The system goes live on Forms. Nothing in the data
model, the flows or the report depends on the canvas app.

---

## 4. Going live — the five days

Follow `docs/IMPLEMENTATION_RUNBOOK.md` step by step. The shape of it:

| Day | Step | What happens |
|---|---|---|
| 1 (am) | 1 | Prepare and validate the data — must show **0 errors** |
| 1 (pm) | 2–3 | Provision SharePoint, load the data, **reconcile row counts** |
| 2 | 4 | Build the 5 Forms and the pre-filled links |
| 2 (pm) | 5 | Print, fit and **individually scan-test** the 30 QR labels |
| 3–4 | 6 | Build the 11 flows |
| 5 (am) | 7 | Open and publish the Power BI report |
| 5 (pm) | 8 | UAT — all 35 cases |
| 6 | 9 | Train, then go live **on a Monday** |

### Six things that will cost you a day each if you skip them

1. **Always `-WhatIf` first.** All three PowerShell scripts dry-run without touching
   the tenant and without needing the PnP module installed.
2. **Check one column's internal name after provisioning.** It must read
   `Field=Cell_ID`, not `Field=Cell%5Fx005f%5FID`. A mangled name breaks every
   query, expression and model reference, silently.
3. **Reconcile row counts after loading.** A short list is a silently dropped row and
   it will not announce itself later.
4. **Mark your holidays in `Plant_Calendar`** before the first monthly upload. It is
   seeded with Sundays off only — Pongal, Diwali and the annual shutdown are not
   guessed. Every unmarked holiday is a day the proration thinks you were running.
5. **In the Forms, hidden pre-filled fields come FIRST.** `Machine_ID` is always
   question 1, `Cell_ID` always question 2. Pre-fill populates by position; insert a
   question above them later and every sticker on the floor fills the wrong field.
6. **Run `--test` before printing stickers.** A wrong sticker takes a month to
   surface, by which time it has been scanned two hundred times against the wrong
   machine.

### Build the flows in this order

1, 2 and 5 are the spine — the counter, the trigger and the reset. Build and test
those three before anything else.

**Turn concurrency OFF on flows 1 and 5.** Both read a value, change it and write it
back. Two parallel runs would each read the same counter and one increment would be
lost — the first month two cells finish on the same afternoon.

---

## 5. Before you can call it live

Go-live is blocked until every **CRITICAL** UAT case passes. 18 of the 35 are
critical. These five matter most:

| Case | What it proves |
|---|---|
| **UAT-14** | Three of four machines complete and **nothing** resets |
| **UAT-15** | The fourth completes and all five `Cell_Master` fields move **in one version** |
| **UAT-19** | A mid-month reset prorates by working days to **720.00 h** — not 780, not 728 |
| **UAT-21** | A duplicate month upload is rejected and **terminates as Failed** |
| **UAT-30a** | The Monday heartbeat arrives on a clean week |

UAT-14 and UAT-15 together are the whole system. If the counter resets at three of
four, every PM interval is wrong from that day on and nothing on any dashboard will
show it.

---

## 6. The one live risk, and how it is managed

**The eleven flows are owned by an individual account.** No service account is
available. This works — but the failure mode is silent, so it is managed rather than
ignored.

### What actually breaks

A flow has **owners** and it has **connections**. Co-owners can edit and repair it.
The connections belong to the **single account that created them** — SharePoint,
Outlook, Forms, Teams, Approvals. When that account is disabled or unlicensed, every
connection breaks and all eleven flows stop, regardless of who else owns them.

**Co-ownership shortens the repair. It does not prevent the failure.** So the
question is not "can someone fix it" but "how long before anyone notices".

### The answer: the Monday heartbeat

Flow 11 sends the daily digest **only when something is outstanding** — otherwise it
stops being read within a fortnight. But that makes silence ambiguous: an empty inbox
means either "nothing outstanding" or "the flows died three weeks ago".

So Flow 11 also sends **every Monday when clean**, as a one-line
*"PM system healthy — nothing outstanding"*.

> ### If no digest arrives on a Monday, the flows have stopped.
>
> That is the entire early-warning system. It costs one email a week. Put this
> sentence in front of whoever monitors the system.

### Three things to do while building, not after

1. **Add two named co-owners to every flow.** Flow → Share → add both.
2. **Point every failure branch at a shared mailbox**, not the owner's inbox. The
   built-in "email me if a flow fails" only reaches the owner — no use the day the
   owner's account *is* what broke.
3. **Export a flow package after UAT** (Power Automate → Export → Package) and keep
   the `.zip` with the repository. If the account is ever deleted rather than just
   unlicensed, the flows go with it.

### When the owning person changes role or leaves

Do it **before** the leaving date — once the licence is gone the connections are
already broken. Full procedure in `ASSUMPTIONS.md` §8.2. Budget half a day; it is
roughly forty connector steps across eleven flows.

---

## 7. Who does what, ongoing

| When | What | Who |
|---|---|---|
| **Every Monday** | **Confirm the heartbeat digest arrived. No digest = flows stopped** | Supervisor |
| Daily | Act on the digest: overdue cells, open work orders, unscanned machines, high-severity abnormalities, **reset failures first** | Supervisor |
| 1st–3rd | Upload the std-hours workbook to `StdHours_Inbox`; check the summary email | Planner |
| 5th | Review cells at 90%+; agree PM dates with production | Supervisor |
| **25th** | **Freeze next month's plan** in `PM_Plan_Calendar` | Supervisor |
| Monthly | Review every `Skip_Reason` from the month | Manager |
| Monthly | Review `Breakdowns After PM (7d)` — is the PM working? | Manager |
| Quarterly | Review the `Trigger_Type` split. Mostly Calendar Backstop means 4,000 is too high | Manager |
| Quarterly | Review `Min_Stock` against `Stock_At_Request` history | Stores |
| Each December | Mark next year's holidays and shutdown in `Plant_Calendar` | Planner |
| Year 4 | Extend `Plant_Calendar` past 2027-03-31; review `Scan_Log` archiving | IT |

**Freezing the plan on the 25th is what makes adherence honest.** Without it you can
measure "did we do it" but never "did we do it when we said we would" — and the
second question is the one production cares about.

---

## 8. Where everything lives

```
input/                  the three source workbooks + data dictionary (unmodified)

sharepoint/
  provision_lists.ps1   16 lists, 224 columns, indexes, 5 libraries
  apply_views.ps1       12 views + shop-floor column formatting
  load_data.ps1         batched CSV load with type conversion
  schema/*.json         one schema per list — the source of truth for the scripts
  views/_views.json     view definitions incl. "My Allotted PM List", "Machine Hub"
  data/*.csv            import-ready data, validation report, row counts

powerbi/
  PM_Dashboard.pbip     open this in Power BI Desktop
  m_queries/*.pq        22 commented Power Query scripts — source of truth
  dax/measures.dax      94 measures, each with a comment explaining it
  README_PowerBI.md     open, refresh, repoint to SharePoint

qr/
  generate_qr_labels.py --test decodes every label back to its own machine
  labels/               30 PNGs + printable PDF

automate/
  FLOW_SPECS.md         all 11 flows, action by action
  expressions.md        every expression, copy-paste ready

powerapps/              Phase 2 — specified and costed, not licensed
docs/
  IMPLEMENTATION_RUNBOOK.md   step-numbered, start to finish
  ASSUMPTIONS.md              every judgement call, with verified figures
  UAT_TEST_CASES.md           35 cases
  TECHNICIAN_SOP_1PAGE.md     print, laminate, put at every cell
  POWERAPPS_LICENCE_CASE.pptx business case for the Power Apps licence
  DATA_DICTIONARY.md          copy of the input dictionary
tools/                  data prep, model build, and the three verification scripts
```

### If you change something

`m_queries/*.pq` and `dax/measures.dax` are the source of truth for the Power BI
model. After editing either, with Power BI Desktop **closed**:

```bash
python tools/build_pbip.py       # embeds the queries and measures into TMDL
python tools/build_report.py     # regenerates pages, visuals, theme
python tools/validate_model.py   # every reference must resolve — run this last
```

---

## 9. How to prove it still works

Five gates. All runnable now, all currently passing.

```bash
python tools/prepare_sharepoint_data.py --strict   # 0 errors, 0 warnings, 2,822 rows
python tools/validate_model.py                     # 0 errors, 0 orphaned measures
python tools/verify_measures.py                    # 68 measures, none blank
python qr/generate_qr_labels.py --test             # 30/30 QR round-trip
pwsh sharepoint/provision_lists.ps1 -SiteUrl <url> -WhatIf   # 0 failures
```

`verify_measures.py` recomputes every headline measure in plain Python,
**independently of the DAX**, so the two can be compared rather than one trusted. It
hand-works the three calculations the system's credibility rests on:
`Breakdowns After PM (7d)`, `Projected PM Date`, and mid-month proration. Expected
values are in `ASSUMPTIONS.md` §9.

Run these after any change. A measure nobody has checked against a known answer is a
number, not a fact.

---

## 10. Troubleshooting — the ones that actually happen

| Symptom | Cause | Fix |
|---|---|---|
| **No digest on a Monday** | **The flows have stopped** | Check `My flows` for a disabled flow or an "Invalid connection" banner — usually the owning account. `ASSUMPTIONS.md` §8.2 |
| Counter did not reset after all machines done | Flow 5 failed, or a task is `Pending` not `Completed` | Check the run history and the `Get items pending tasks` filter |
| Two work orders for the same cell | Flow 2's open-WO check missing | Cancel one, fix the condition |
| Counter jumped a whole month after a mid-month PM | Proration not applied | Check `Reset_Date` is populated and inside the uploaded month |
| Monthly import fails naming a month | `Plant_Calendar` has no working days for it | Add the dates and mark working days |
| Proration posts slightly too many hours | Holidays not marked in `Plant_Calendar` | Mark them — the divisor counts working days only |
| Scan opens a blank hub | `QR_Payload_URL` points at a renamed view | Re-run `apply_views.ps1`, update the column, reprint |
| Power BI blank columns after repointing | Mangled column internal names | Recreate those columns from field XML |
| Flow fails "cannot convert null" | A null number in arithmetic | Wrap in `float(coalesce(x, 0))` |
| List view threshold error | A filtered column is not indexed | Re-run `provision_lists.ps1` — it is idempotent |

---

## 11. Known limits — stated, not hidden

- **Two things must be finished by hand in Power BI Desktop**: the drillthrough field
  on page 5, and setting the Gantt offset series to no-fill on page 3. Neither can be
  expressed in the file format. Both take under a minute; both are in
  `README_PowerBI.md`.
- **The Power BI info panel is a footnote, not a bookmark toggle.** It uses 40 px of
  every page. A footnote cannot be left switched off by whoever used the report last.
  Conversion steps are in `README_PowerBI.md` if you prefer a toggle.
- **`Checklist_Response` reaches the 5,000-item list view threshold around year 5.**
  Not a storage problem — a query one. The indexes already protect against it;
  review archiving in year 4.
- **QR stickers are printed against the SharePoint hub URL.** If Power Apps is
  licensed later the payload becomes a deep link and all 30 need reprinting. A known,
  accepted cost of starting on Forms.
- **The licence business case deck has not been visually proof-read** — the rendering
  tool was unavailable when it was produced. It opens correctly and passes structural
  checks; give it one pass before presenting.
- **The dummy data is dummy data.** Every figure quoted in this handover comes from
  the 12 months supplied for building and testing. Re-run `verify_measures.py`
  against real data once loaded.

---

## 12. First week checklist

- [ ] Decide **which individual account** owns the flows and Forms
- [ ] Identify the **two co-owners** and the **shared mailbox** for failure alerts
- [ ] Create the SharePoint site
- [ ] Run all three PowerShell scripts with `-WhatIf`, then for real
- [ ] Reconcile row counts against `_ROW_COUNTS.csv`
- [ ] Verify one column's internal name is unmangled
- [ ] Mark holidays and the annual shutdown in `Plant_Calendar` for 12 months
- [ ] Build the 5 Forms — pre-filled fields first, technician dropdown mandatory
- [ ] Test one pre-filled link on a real phone before building all 30
- [ ] `python qr/generate_qr_labels.py --base-url <site> --test` → 30/30
- [ ] Print on polyester at 100% scale, fit, and scan-test every one
- [ ] Build flows 5, 2, 1 first; concurrency OFF on 1 and 5
- [ ] Two co-owners on all 11 flows, failure branches to the shared mailbox
- [ ] Export the flow package to `.zip`
- [ ] Publish Power BI, schedule refresh 06:00 and 14:00 IST
- [ ] All 35 UAT cases, recorded with a name and date
- [ ] Print and laminate the SOP at every cell
- [ ] Put *"no Monday digest = flows stopped"* in the handover note
- [ ] Go live on a Monday. Run the first monthly upload with someone watching
