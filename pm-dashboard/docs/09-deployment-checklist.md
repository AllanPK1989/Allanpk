# 09 · Deployment Checklist

Work top to bottom. Each phase assumes the previous one is done.

## Phase 0 · Build it on dummy data (½ day)

- [ ] `pip install openpyxl qrcode[pil] pandas`
- [ ] `python3 scripts/generate_dummy_data.py`
- [ ] `python3 scripts/build_sharepoint_templates.py`
- [ ] `python3 scripts/generate_qr_codes.py`
- [ ] `python3 scripts/build_pbip.py`
- [ ] `python3 scripts/validate_pbip.py` — 818 checks; do not open Desktop until
      this passes
- [ ] Copy `powerbi/` to `C:\PM_Dashboard` (the CSVs ship inside it, and
      `LocalDataFolder` already points at `C:\PM_Dashboard\data`)
- [ ] Open `PM_Dashboard.pbip` in Power BI Desktop, refresh, check all ten
      pages render

**If the project will not open** — different Desktop versions accept different PBIR
schema versions. Recovery is five minutes:

1. Desktop ▸ new blank file ▸ Get data ▸ Text/CSV ▸ any file from `data/dummy`
2. File ▸ Save as ▸ **Power BI project (.pbip)** ▸ save as `PM_Dashboard.pbip`
3. Close Desktop
4. `python3 scripts/build_pbip.py --inject "C:/path/to/PM_Dashboard.pbip"`
5. Reopen

That keeps Desktop's own boilerplate and injects the model and pages into it.

## Phase 1 · SharePoint (1 day)

- [ ] Create the `PMSystem` team site
- [ ] Create the five document library folders (`00`–`04`) plus `02/_History`
- [ ] Create all eight lists from `00-reference/SharePoint_List_Schemas.xlsx`
- [ ] Set indexed columns on every list
- [ ] Turn on versioning, 50 major versions, on every list
- [ ] Set item-level permissions on `PM_WorkOrders`: read all, edit own
- [ ] Upload the six master workbooks to `01 Master Data/`
- [ ] Replace the dummy rows with your real cells, machines, technicians,
      checklists and spares
- [ ] Verify every `CellID` in Machine_Master exists in Cell_Master, and every
      `ChecklistID` exists in the checklist master. This is the number one cause
      of a machine that never gets scheduled.

## Phase 2 · The flows (2 days)

- [ ] Flow 1 · Validate Standard Hours Upload — test with a deliberately broken
      file and confirm it lands in `_Rejected/` with a useful email
- [ ] Flow 2 · Monthly PM Scheduler — build, then run in `Backload` mode against
      `_History/`
- [ ] Reconcile: does the ledger's last-PM date per cell match what the
      maintenance register actually says? Fix before going further.
- [ ] Flow 3 · Overdue Sweep
- [ ] Flow 4 · Abnormality Escalation
- [ ] Flow 5 · Spare Approval
- [ ] Flow 6 · Upload Reminder
- [ ] Turn on failure notifications for all six

## Phase 3 · The app (3 days)

- [ ] Build the seven screens from `04-powerapps-spec.md`
- [ ] Test the deep link by hand before touching a QR code:
      `...&source=qr&type=machine&id=MC-001`
- [ ] Test offline: aeroplane mode, complete a checklist, reconnect, confirm it flushes
- [ ] Test the borrowed-badge case: sign in as A, scan B's technician QR, confirm
      you still see A's list
- [ ] Publish and share with the Technicians security group as *User*
- [ ] Capture the environment ID, app ID and tenant ID from the published link

## Phase 4 · QR codes (½ day)

- [ ] `python3 scripts/generate_qr_codes.py <ENV_ID> <APP_ID> <TENANT_ID>`
- [ ] Print **one** machine label on plain paper and test it on three phones, in
      the real light, at the real spot, with a glove on
- [ ] Only then print the full set on polyester
- [ ] Fix labels at eye height by the operator panel, plus a spare inside the panel
- [ ] Print and issue technician badges
- [ ] Upload `qr_payload_index.csv` and the print PDFs to `03 QR Codes/`

## Phase 5 · Power BI to production (1 day)

- [ ] Set `SourceMode` = `SharePoint`
- [ ] Set `SharePointSiteUrl` to your site
- [ ] Refresh. Expect this to fail the first time — SharePoint list column internal
      names sometimes differ from display names. Fix in Power Query, not by renaming
      the list columns.
- [ ] Reconcile every KPI against a manual count for one month. Every one.
- [ ] Publish to a workspace
- [ ] Set the semantic model's credentials (OAuth2, organisational account)
- [ ] Scheduled refresh: 06:00, 14:00, 22:00 IST
- [ ] Turn on refresh failure notifications
- [ ] Create an app, give the technicians and supervisors viewer access
- [ ] Optional, two clicks: on page 5, drag `MachineID` into the Drillthrough well
      to make Machine 360 a proper drillthrough target as well as a slicer page

## Phase 6 · Go live (1 week, one cell)

- [ ] Pilot on **one cell** for a full month. Not the whole plant.
- [ ] Run paper and digital in parallel for that month, and reconcile weekly
- [ ] Sit with a technician on the floor for their first three scans and watch
      where they hesitate. That is your UX backlog.
- [ ] Review the Data Quality page every Monday
- [ ] Only after a clean month, roll out cell by cell

## Ongoing rhythm

| When | Who | What |
|------|-----|------|
| 5th working day | Production Planning | Upload the standard hours file |
| 6th | Scheduler flow | Ledger and work orders for the month |
| Daily 23:30 | Overdue flow | Status sweep and Teams digest |
| Weekly Mon | Maintenance Head | Data Quality page, then safety-critical failures, then the overdue list |
| Monthly | Maintenance Head | Compliance, MTBF/MTTR trend, spend per standard hour |
| Quarterly | Maintenance + Production | Are the 4000-hour thresholds still right for each cell? |
| Annually | Maintenance Engineer | Review the checklists themselves against actual failure modes |

## Things that will go wrong, and what they mean

| Symptom | Cause | Fix |
|---------|-------|-----|
| A cell is never scheduled | Its hours are not being uploaded | Data Quality page → Missing Std Hours Rows |
| Everything falls due in one month | Counters all started at zero | Run the back-load properly |
| Compliance is 100% and fail rate is 0% | Checklists are being clicked through | Check QR Verification % and failures within 15 days of PM |
| Refresh fails after go-live | SharePoint internal column names | Fix in Power Query |
| A view stops loading | 5,000-item list threshold | Index the columns; archive `QR_Scan_Log` |
| Technicians stop scanning | The label is unreadable or in the wrong place | Walk the floor and look at the labels |
