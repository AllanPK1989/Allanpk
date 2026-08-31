# EPQPL Cell-Based PM Planning, Scheduling & Tracking System

A complete preventive maintenance system for a fuse manufacturing plant, running on
SharePoint Online, Microsoft Forms, Power Automate, Power BI and (optionally) a
Power Apps canvas app.

## The rules the system implements

1. **PM is triggered per CELL, not per machine.** A cell is 3–4 machines.
2. The trigger is **4,000 production standard hours** accumulated by that cell since
   its last PM — held per cell, never hard-coded.
3. **Calendar backstop at 6 months**, whichever comes first.
4. **Amber warning at 90%** (3,600 h) so planning has lead time.
5. Actual hours arrive **monthly, one file, one row per cell**, and are added to the
   cell's running counter.
6. The counter resets to zero **only when the cell's work order completes**.
7. A work order contains **one task per machine**. It closes only when **every**
   machine task is done. Three of four is not done.
8. Technicians share one M365 login, so a **mandatory technician dropdown** on every
   form is the entire audit trail.
9. Every machine carries a **QR sticker** opening that machine's hub.
10. A PM reset falling mid-month **prorates** that month's hours by **working
    days**, read from a plant calendar — standard hours are a capacity figure.

## What is in the repository

```
input/                  the three source workbooks and the data dictionary (unmodified)

sharepoint/
  provision_lists.ps1   creates 16 lists, 224 columns, indexes, 5 libraries
  apply_views.ps1       12 views + the shop-floor column formatting
  load_data.ps1         batched CSV load with type conversion
  schema/*.json         one schema per list — the source of truth for the scripts
  views/_views.json     view definitions incl. "My Allotted PM List" and "Machine Hub"
  formatting/*.json     Machine Hub buttons, RAG data bars, status pills
  data/*.csv            import-ready data + validation report + row counts

powerbi/
  PM_Dashboard.pbip     open this in Power BI Desktop
  PM_Dashboard.SemanticModel/   TMDL: 17 tables, 42 relationships, 94 measures
  PM_Dashboard.Report/          PBIR: 9 pages, 116 visuals
  m_queries/*.pq        one commented Power Query script per table
  dax/measures.dax      every measure with a comment explaining it
  theme/                the report theme
  README_PowerBI.md     open, refresh, repoint to SharePoint

qr/
  generate_qr_labels.py 50 × 30 mm labels, ECC-H, 3 × 8 on A4, with --test
  labels/               30 PNGs + the printable PDF
  README_QR.md

automate/
  FLOW_SPECS.md         build sheet for all 11 flows, action by action
  expressions.md        every expression, copy-paste ready

powerapps/              Phase 2 — specified and costed, not licensed today
  README_PowerApps.md   how it relates to the Forms path, and the licence position
  CANVAS_APP_BUILD.md   screen-by-screen build sheet
  power_fx_formulas.md  every formula
  app_manifest.json     data sources, screens, globals

docs/
  STEP_BY_STEP_GUIDE.md/.docx START HERE if you are building it
  HANDOVER.md/.docx           START HERE if you are taking it over
  IMPLEMENTATION_RUNBOOK.md   step-numbered, start to finish
  ASSUMPTIONS.md              every judgement call, with verified figures
  UAT_TEST_CASES.md           35 cases
  TECHNICIAN_SOP_1PAGE.md     shop-floor SOP, printable, English + Tamil
  POWERAPPS_LICENCE_CASE.pptx business case for the Power Apps licence request
  DATA_DICTIONARY.md          copy of the input dictionary

tools/
  prepare_sharepoint_data.py    workbooks → typed CSVs + integrity checks
  generate_sharepoint_schema.py schema JSON generator
  build_pbip.py                 generates the semantic model from .pq + .dax
  build_report.py               generates the report pages
  validate_model.py             checks every reference resolves
  verify_measures.py            recomputes every measure independently of the DAX
```

## Start here

**Building it?** → **`docs/STEP_BY_STEP_GUIDE.md`** — the plain-English walkthrough,
stage by stage, with every command written out and no assumed SharePoint or Power BI
knowledge. Start here if you are the one doing the work.

**Taking it over?** → **`docs/HANDOVER.md`** — what the system does, what is built,
the eight decisions of record, the one live risk and how it is managed, who does what
ongoing, and how to prove it still works.

Both point at `docs/IMPLEMENTATION_RUNBOOK.md` for the fine print.

Word versions of both are in `docs/` alongside the markdown. Regenerate after any
edit so they cannot drift from the source:

```bash
node tools/build_docx.js docs/STEP_BY_STEP_GUIDE.md
node tools/build_docx.js docs/HANDOVER.md
```

## Quick start

```bash
pip install -r tools/requirements.txt -r qr/requirements.txt

# 1. prepare and validate the data
python tools/prepare_sharepoint_data.py --strict

# 2. provision SharePoint (dry run first, always)
pwsh sharepoint/provision_lists.ps1 -SiteUrl https://<tenant>.sharepoint.com/sites/Maintenance -WhatIf
pwsh sharepoint/provision_lists.ps1 -SiteUrl https://<tenant>.sharepoint.com/sites/Maintenance
pwsh sharepoint/apply_views.ps1     -SiteUrl https://<tenant>.sharepoint.com/sites/Maintenance
pwsh sharepoint/load_data.ps1       -SiteUrl https://<tenant>.sharepoint.com/sites/Maintenance

# 3. print the QR labels (test before printing)
python qr/generate_qr_labels.py --base-url https://<tenant>.sharepoint.com/sites/Maintenance --test

# 4. open powerbi/PM_Dashboard.pbip, then follow docs/IMPLEMENTATION_RUNBOOK.md
```

Then work through **`docs/IMPLEMENTATION_RUNBOOK.md`** from step 1.

## Regenerating the Power BI project

`m_queries/*.pq` and `dax/measures.dax` are the source of truth. After editing
either (Power BI Desktop **closed**):

```bash
python tools/build_pbip.py       # embeds the queries and measures into TMDL
python tools/build_report.py     # regenerates pages, visuals, theme registration
python tools/validate_model.py   # every reference must resolve — run this last
```

## Verifying it works

Three independent checks, all runnable now:

```bash
python tools/prepare_sharepoint_data.py   # 0 errors, 0 warnings on the supplied data
python tools/validate_model.py            # 0 errors, 0 orphaned measures
python tools/verify_measures.py           # 68 measures recomputed, none blank
python qr/generate_qr_labels.py --test    # 30/30 QR codes round-trip
pwsh sharepoint/provision_lists.ps1 -SiteUrl https://example.sharepoint.com/sites/x -WhatIf
```

`verify_measures.py` recomputes every headline measure in plain Python,
independently of the DAX, and hand-works the three calculations the system's
credibility rests on: `Breakdowns After PM (7d)`, `Projected PM Date`, and mid-month
proration. Expected values are recorded in `docs/ASSUMPTIONS.md` §9.

## The one number to watch

**`Breakdowns After PM (7d)`** — breakdowns on a cell within seven days of a
completed PM on that same cell.

Compliance can read 100% while this climbs. When it does, the checklist is being
signed rather than performed, or it is checking the wrong things. It is the only
measure that tells you whether the PM is real.

On the supplied data it is **9 of 88 breakdowns (10.2%)**. Read it as a share, not a
count.

## Two paths for the shop floor

| | **Path A — Forms + list views** | **Path B — Canvas app** |
|---|---|---|
| Cost | Included in M365 E3 | Needs a Power Apps licence — **not available today** |
| Build | ~1 day | ~4–5 days |
| Offline | No | Yes |
| Barcode | Phone camera opens the URL | Reader inside the app |

Both write to **identical lists with identical column names**, and the eleven flows
do not care which produced the row.

**The system goes live on Path A.** No Power Apps licence is available today, and
nothing in the data model, the flows or the report depends on the canvas app. Path B
stays in the repository as a costed Phase 2 spec, with the business case for the
licence in `docs/POWERAPPS_LICENCE_CASE.pptx`.

Print the stickers against the **SharePoint Machine Hub** URL. If the app is
licensed later the payload changes and the 30 labels have to be reprinted — a known,
accepted cost of starting on Forms.
