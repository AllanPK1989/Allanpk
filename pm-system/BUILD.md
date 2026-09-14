# BUILD — how to build and run this system, start to finish

**Read this first.** It is the only document you need open to build the system.
Everything else is detail you go and fetch when a step tells you to.

| | |
|---|---|
| **What you are building** | A preventive-maintenance system for EPQPL Pondicherry: 8 cells, 30 machines, PM triggered per cell at 4,000 accumulated standard hours with a 6-month calendar backstop |
| **Runs on** | SharePoint Online, Power Automate, Microsoft Forms, Power BI — all Microsoft 365 E3, **no extra licence** |
| **Total effort** | About **6 working days**, one person |

## ✅ No Python needed

**This build uses PowerShell and a web browser. Nothing else.** Every file Python
would have produced is already generated and included — the 14 data files, the 14
schema files, the Power BI model, all of it.

| You need | Why | Usually already installed? |
|---|---|---|
| **PowerShell 7** + the `PnP.PowerShell` module | Creates the SharePoint lists and loads the data | PowerShell 7 is a standard Microsoft download; the module installs from the PowerShell Gallery with one command |
| **A web browser** | Generates the QR stickers | Yes |
| **Power BI Desktop** | Opens and publishes the dashboard | Standard Microsoft download |
| **A Microsoft 365 account** with Site Owner rights on a SharePoint site | Everything | Yes |

That is the whole list. There is a Python toolkit in `tools/` that regenerates the
data and runs extra cross-checks — **it is optional**, it is covered in
[Appendix A](#appendix-a), and you can build, test and run the entire system without
ever touching it.

---

## The six stages

| # | Stage | Time | You end with |
|---|---|---:|---|
| 0 | [Set up and check the files](#stage-0) | 30 min | PowerShell ready, files confirmed present |
| 1 | [Provision SharePoint](#stage-1) | 3 h | 14 lists, 138 columns, 11 views, 5 libraries |
| 2 | [Load and verify the data](#stage-2) | 1 h | 2,422 rows, every check passing |
| 3 | [Build the forms](#stage-3) | 4 h | 5 Forms, wired into the Machine Hub |
| 4 | [Print and fit the QR stickers](#stage-4) | 4 h | 30 stickers, every one scan-tested |
| 5 | [Build the flows](#stage-5) | 2 days | 9 automations running unattended |
| 6 | [Power BI, UAT, go live](#stage-6) | 1.5 days | 9-page dashboard, 36 UAT cases signed off |

**Do the stages in order.** Stage 5 cannot be built before Stage 3 exists, because a
flow's trigger has nothing to point at. Stage 4 needs Stage 1 done, because the
sticker points at a view that has to exist.

---

## The one decision to make before you start

**Who owns this?** Every flow and every form is created under one Microsoft 365
account, and that account's connections are what the flows run on.

There is no service account available, so it will be an individual's account. That
works, but understand what it means: **if that account is ever disabled or loses its
licence, every connection breaks and all nine flows stop** — regardless of who else
you add as a co-owner. Co-ownership shortens the repair; it does not prevent the
failure.

Pick someone who is not about to change role. Add two co-owners to every flow as you
build it. And know the warning sign, which is built into the system: **the daily
digest sends a one-line "PM system healthy" every Monday even when nothing is wrong.
No digest on a Monday means the flows have stopped.**

Full reasoning and the reassignment procedure: `docs/ASSUMPTIONS.md` §8.2.

---

<a name="stage-0"></a>
## Stage 0 — Set up and check the files · 30 minutes

### Install PowerShell 7 and the SharePoint module

Download PowerShell 7 from Microsoft and install it. Then open it and run:

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
```

`-Scope CurrentUser` installs it for you alone, so it does not need an administrator.

### Confirm the files arrived intact

Everything you need is already in this folder. Check the four that matter:

```powershell
cd sharepoint
Get-ChildItem data\*.csv   | Measure-Object      # expect Count : 14
Get-ChildItem schema\*.json | Measure-Object     # expect Count : 15  (14 lists + manifest)
Get-Content data\_ROW_COUNTS.csv | Measure-Object -Line   # expect Lines : 15  (header + 14)
Test-Path ..\qr\browser\qr_labels.html           # expect True
```

If those four are right, the data is complete and you can build.

> **Where the data came from.** The 14 CSVs were generated from the three workbooks in
> `input/` and validated against six cross-table integrity rules — unique keys, a work
> order's task count matching its machine count, a completed work order having no open
> tasks, the counter reset moving all three cell fields together, every checklist
> response having a parent task, and every completed work order having a scanned-out
> task to date it by. They passed with **0 errors and 0 warnings**;
> `sharepoint/data/_VALIDATION_REPORT.md` is that run's report. You do not need to
> rerun it — but [Appendix A](#appendix-a) says how if you ever want to.

---

<a name="stage-1"></a>
## Stage 1 — Provision SharePoint · 3 hours

**What you are doing:** creating the lists, columns, indexes, views and libraries.

### 1.1 Dry-run first

Every script supports `-WhatIf`, which shows exactly what it would do without
touching the tenant.

```powershell
cd sharepoint
.\provision_lists.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance" -WhatIf
```

> ### ⚠ If it fails asking for admin approval
>
> Many corporate tenants block unapproved applications, and the error does not tell
> you what to do. Someone with Entra (Azure AD) rights registers one, **once**:
>
> ```powershell
> Register-PnPEntraIDAppForInteractiveLogin `
>     -ApplicationName "EPQPL PM Provisioning" `
>     -Tenant yourcompany.onmicrosoft.com -Interactive
> ```
>
> It prints a client id. Pass it as `-ClientId "<id>"` to **all four** scripts from
> then on.
>
> **Confirm this before provisioning day.** It is ten minutes for whoever holds the
> rights, and half a day lost if you discover it at 9 a.m. on the morning.

### 1.2 Run for real

```powershell
.\provision_lists.ps1 -SiteUrl "<your site>"    # 14 lists, 138 columns, 5 libraries
.\apply_views.ps1     -SiteUrl "<your site>"    # 11 views + shop-floor formatting
```

### 1.3 Check the internal names are not mangled

Open `Cell_Master` → List settings → click `Cell_ID` and read the browser address bar.
It must say `Field=Cell_ID`, **not** `Field=Cell%5Fx005f%5FID`.

If it is mangled, the Power BI model will load blank columns and nothing will tell you
why. The field XML sets `Name`, `StaticName` and `DisplayName` identically to prevent
exactly this — but check, because it is five seconds now and a lost afternoon later.

*(Stage 2's verification script checks this across all 138 columns automatically.)*

---

<a name="stage-2"></a>
## Stage 2 — Load and verify the data · 1 hour

```powershell
.\load_data.ps1 -SiteUrl "<your site>" -WhatIf   # dry run first
.\load_data.ps1 -SiteUrl "<your site>"           # 2,422 rows
```

### Then prove it worked

```powershell
.\verify_load.ps1 -SiteUrl "<your site>"
```

This is your gate. It checks the seven things that go wrong quietly:

1. Every list exists, with every column
2. **No column name was mangled** into `Cell_x005f_ID`
3. **Row counts reconcile** against `data\_ROW_COUNTS.csv`, list by list
4. **Every column a view filters on is indexed** — an unindexed filter works
   perfectly until the list passes 5,000 items, then fails silently, years later
5. Every view was created
6. Every document library was created
7. **No completed work order left its counter unreset** — the failure that costs most
   and announces itself least

It must end with:

```
  Everything checks out. SharePoint is provisioned and loaded correctly.
```

A list short by even one row means a row was dropped silently. Find it now, not in six
months.

### ⚠ Then mark your holidays

Open the **`Plant_Calendar`** list and set `Is_Working_Day = No` for Pongal, Diwali and
any plant shutdown.

This list is the divisor in the mid-month proration rule — it is what stops a cell that
resets mid-month from being credited hours the plant was never open to earn.
**Maintain it every December for the year ahead.** If it runs out, the monthly import
terminates with a message naming the month rather than dividing by zero.

---

<a name="stage-3"></a>
## Stage 3 — Build the forms · 4 hours

**What you are doing:** building the five Microsoft Forms the technicians fill in.
This is the fiddliest stage. Take your time.

**Every question on every form, with the column it lands in, is in
`automate/FLOW_SPECS.md` §"The five forms".** Build from there, not from memory.

| # | Form | Questions | Machine Hub button |
|---|---|---:|---|
| 1 | PM Start | **2**, both pre-filled | ▶ START PM |
| 2 | PM Checklist | 4 + nine branched sections | ☑ COMPLETE CHECKLIST |
| 3 | Spare Replaced | 9 | 🔧 SPARE FITTED |
| 4 | Breakdown Report | 14 | ⚠ REPORT BREAKDOWN |
| 5 | Abnormality Log | 9 | 👁 LOG ABNORMALITY |

### ⚠ The rule that will catch you out

**A pre-filled link fills answers by POSITION, not by name.**

So on every form `Machine ID` is question 1 and `Cell ID` is question 2 — and on the
checklist, `Checklist ID` is question 3. Insert anything above them and every sticker
on the shop floor starts filling the wrong boxes, silently, with no error. **New
questions go at the bottom, always.**

### Settings, identical on all five

- **Anyone can respond** ✅ — the handsets share one login
- **Record name** ❌ — it would record the shared account, which looks like
  attribution and is not
- **Technician Name** is a mandatory **Choice**, typed out from `Technician_Master`.
  Never a text box: free text gives you "Murugan", "murugan s" and "MURUGAN S", and
  then nothing can be counted.
  - **The one exception is PM Start**, which asks nothing at all. Nothing stores who
    started a job — `Completed_By` on the checklist is the record that matters — so a
    dropdown there would be a tap that throws its answer away.

### Then wire up the Machine Hub — 11 placeholders, set once

For each form: **Collect responses → Get a link to prefill answers**, fill in
`MC-01-001` and `CELL-01`, and **Get link**. You get something like:

```
https://forms.office.com/r/AbCdEf?id=xxxxx&r1a2b3c4=MC-01-001&r5d6e7f8=CELL-01
```

Cut it in two and paste the halves into
`sharepoint/formatting/Machine_Master.MachineHub.view.json`:

| Placeholder | What to paste |
|---|---|
| `FORM_<NAME>_UPTO_MACHINE` | everything before the machine ID |
| `FORM_<NAME>_UPTO_CELL` | the next key with its `&` and `=` |
| `FORM_CHECKLIST_UPTO_CLID` | the checklist form's third key |

**Copy and paste both halves out of a real link.** Retyping an eight-character
question id by hand gives you a button that opens the form with nothing filled in,
and nothing about it looks wrong until somebody uses it.

Then push the formatting up:

```powershell
.\apply_views.ps1 -SiteUrl "<your site>"
```

**Test one on a real phone before you go on.** The first thing you touch should be a
real question — not the keyboard.

---

<a name="stage-4"></a>
## Stage 4 — Print and fit the QR stickers · 4 hours

**No install. Open a file in your browser.**

1. Open **`qr/browser/qr_labels.html`** by double-clicking it. It runs entirely on your
   machine — no network, no Python, no Node.js.
2. Paste your SharePoint site address.
3. Click **Generate**. It builds 30 stickers and checks each one before showing them.
4. **Scan the first label off your screen with a real phone.** It must open the Machine
   Hub filtered to `MC-01-001`.
5. Click **Print**.

Full detail, including what the page checks and what it cannot: `qr/browser/README_QR_BROWSER.md`.

### Print settings

| Setting | Value | Why |
|---|---|---|
| Paper | **Polyester or vinyl**, 3 × 8 pre-cut at 50 × 30 mm | Paper does not survive a fuse plant — oil soaks in and the code is gone in weeks |
| Scale | **100% / Actual size** | "Fit to page" shrinks the code below what a phone reads reliably |
| Printer | **Laser**, not inkjet | Inkjet runs the moment someone wipes the machine with solvent |
| Margins | **None**, headers and footers **off** | Otherwise every label shifts and the pre-cut sheet no longer lines up |

Stick them at **chest height**, flat, away from coolant spray.

**Then walk the floor and scan every single one.** Two people, one hour — the last
printed page is a fitting checklist for exactly this. It removes an entire class of
problem permanently.

---

<a name="stage-5"></a>
## Stage 5 — Build the flows · 2 days

**What you are doing:** building the nine automations that make the system run by
itself. This is the biggest stage.

Open `automate/FLOW_SPECS.md` — every flow, every action in order, every setting.
`automate/expressions.md` has every formula written out to copy and paste.

### Build in this order

| Order | Flow | What it does | Time |
|---|---|---|---:|
| 1st | **PM-05** Cell Closure & Reset | Zeroes the counter when the last machine in a cell is done | 3 h |
| 2nd | **PM-02** PM Trigger | Raises the work order at 4,000 hours or 6 months | 3 h |
| 3rd | **PM-01** Monthly Hours Import | Adds each month's hours to the counters | 4 h |
| then | PM-03, PM-04 | Scan in, checklist submission | 4 h |
| then | PM-06, PM-07, PM-08 | Breakdown, spare fitted, abnormality | 3 h |
| last | PM-09 | Daily digest | 2 h |

**Flows 5, 2 and 1 are the spine.** Get those three working before anything else.

### Three rules that will each save you a day

**1. Rename actions before you write expressions.** Expressions reference actions by
name with spaces replaced by underscores. Rename an action afterwards and the
expression breaks — the flow still saves, then fails at runtime with a null.

**2. Turn concurrency OFF on flows 1 and 5.** Both touch the running counter. Two
parallel runs would read the same value and one increment would be lost.

**3. Route failure alerts to a shared mailbox**, not the owner's inbox. The built-in
"email me if a flow fails" reaches the owner only, which is no use the day the
owner's account is the thing that broke.

And add your two co-owners to each flow **as you build it**. Doing it later across
nine flows is an hour nobody ever schedules.

---

<a name="stage-6"></a>
## Stage 6 — Power BI, UAT, go live · 1.5 days

### 6.1 Open and repoint the report

Open `powerbi/PM_Dashboard.pbip` in Power BI Desktop. **Home → Transform data →
Manage parameters**, set `pSourceMode` to `SharePoint` and `pSiteUrl` to your site.
Refresh.

The whole model swaps source through **one function** (`fnGetTable`), so this is a
parameter change, not a rebuild.

**One thing to finish by hand:** on page 5, select `Machine 360` and drag
`Dim_Machine[Machine_ID]` into the **Drill through** well. It cannot be expressed in
the file format. It takes under a minute.

### 6.2 Cross-check the numbers

Open the dashboard and confirm these four against `docs/ASSUMPTIONS.md` §9:

| Measure | Expected on the supplied data |
|---|---|
| `Breakdowns After PM (7d)` | **7** of 88 (8.0%) |
| `PM Compliance %` | **89.6%** (43 of 48) |
| `Reset Not Applied Count` | **0** |
| `Schedule Adherence %` | **54.9%** (28 of 51 committed rows) |

Every measure in the model was independently recomputed and checked before delivery;
§9.4 of `ASSUMPTIONS.md` lists all 65 with their values.

### 6.3 UAT — all 36 cases

`docs/UAT_TEST_CASES.md`, in order. Record a name and a date against each; an
unrecorded test is an untested system. **Test on a separate SharePoint site** — several
cases deliberately corrupt data to prove a guard works.

The six that must pass before go-live:

| Case | What it proves |
|---|---|
| UAT-03 | A cell crossing 4,000 raises exactly one work order |
| UAT-07 | The 6-month backstop fires for a low-utilisation cell |
| UAT-14 | Three of four machines complete and **nothing** resets |
| UAT-15 | The fourth completes and all three cell fields move together |
| UAT-19 | A mid-month reset prorates by working days to **720.00 h** |
| UAT-30a | The Monday heartbeat arrives on a clean week |

UAT-14 and UAT-15 together are the whole system. If the counter resets at three of
four, every PM interval is wrong from that day on and no dashboard will tell you.

### 6.4 Train and go live

- **Technicians, 30 min:** scan, start, checklist, submit. Why the name dropdown
  matters — it is the only record of who did the work. (`docs/TECHNICIAN_SOP_1PAGE.md`
  is a one-pager to print and laminate at every cell.)
- **Supervisors, 1 h:** the allotted list, the daily digest, the **NOT OK Findings**
  view and deciding which findings become work orders.
- **Go live on a Monday**, not a Friday. Run the first monthly upload with someone
  watching.

---

## Where everything lives

```
BUILD.md                    <- you are here
README.md                   what this is, in one page

docs/
  STEP_BY_STEP_GUIDE.md     the plain-English walkthrough (also .docx)
  HANDOVER.md               the single hand-over summary  (also .docx)
  IMPLEMENTATION_RUNBOOK.md the same steps, full technical detail
  DATA_DICTIONARY.md        every one of the 138 columns, and why it exists
  ASSUMPTIONS.md            every judgement call, with verified figures
  UAT_TEST_CASES.md         36 cases
  TECHNICIAN_SOP_1PAGE.md   shop-floor sheet, print and laminate
  POWERAPPS_LICENCE_CASE.pptx   business case for the Phase 2 canvas app

sharepoint/
  provision_lists.ps1       14 lists, 138 columns, indexes, 5 libraries
  apply_views.ps1           11 views + shop-floor column formatting
  load_data.ps1             batched CSV load with type conversion
  verify_load.ps1           seven post-load checks - your gate
  schema/                   one JSON per list — what the scripts read
  views/, formatting/       view definitions and the Machine Hub card
  data/                     import-ready CSVs, validation report, row counts

automate/
  FLOW_SPECS.md             5 forms and 9 flows, action by action
  expressions.md            every expression, copy-paste ready

qr/browser/                 open qr_labels.html in a browser - no install
powerbi/PM_Dashboard.pbip   open this in Power BI Desktop
powerapps/                  Phase 2 — specified and costed, not licensed
input/                      the three supplied workbooks, unmodified
tools/                      OPTIONAL Python toolkit - see Appendix A
```

---

## What this system deliberately does not record

Four things. None is recoverable from history, so if one matters, **reinstate it
before go-live, not after** — `docs/ASSUMPTIONS.md` §10 has the full reasoning.

1. **The scan that led nowhere** — a QR scan against a machine with no open work
   order. The technician is still told; the fact is no longer filed. This is the
   first thing to bring back if take-up is ever in doubt.
2. **Spare approval lead time and stock at the moment of asking** — the requisition
   loop was removed because the stores process already runs it.
3. **Who *started* a PM**, as distinct from who finished it.
4. **Make, model and year installed** — asset-register detail.

---

<a name="appendix-a"></a>
## Appendix A — the optional Python toolkit

**You do not need any of this to build, test or run the system.** Everything it
produces is already in the repository. It is here for whoever maintains the system
later, and for the day the source data changes.

| Script | What it does | When you would want it |
|---|---|---|
| `tools/prepare_sharepoint_data.py` | Rebuilds the 14 CSVs from the workbooks in `input/`, enforcing six integrity rules | The source data changed and you need a fresh load file |
| `tools/generate_sharepoint_schema.py` | Rebuilds the 14 schema files and the manifest | You added or removed a column |
| `tools/verify_measures.py` | Recomputes 65 dashboard measures in plain Python, independently of the DAX | You want the dashboard's numbers checked by something other than the dashboard |
| `tools/validate_model.py` | Confirms every reference in every visual, relationship and measure resolves | You edited the Power BI model |
| `tools/check_consistency.py` | 46 checks that the schema, data, model, flows, views and all documents agree | You changed anything and want one command that says whether it still hangs together |
| `qr/generate_qr_labels.py` | The original QR generator, with optical decode verification | You prefer a command line to the browser page |

If you can run Python 3.9+:

```bash
pip install -r tools/requirements.txt
python3 tools/check_consistency.py
```

**The browser QR page and the Python QR generator produce the same thing.** Both were
verified by optically decoding all 30 rendered labels back to their own machine's link —
30/30 from each. Use whichever your environment allows.
