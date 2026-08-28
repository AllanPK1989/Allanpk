# Opening this project and connecting the data

## Fastest path — dummy data, zero edits

1. Unzip (or copy) this folder so it sits at **`C:\PM_Dashboard`**.
   The `data` folder must end up at `C:\PM_Dashboard\data`.
2. Double-click **`PM_Dashboard.pbip`**. Power BI Desktop opens it.
3. **Home ▸ Refresh.**

That is the whole connection. The `LocalDataFolder` parameter already defaults to
`C:\PM_Dashboard\data`, so nothing needs editing.

Put it somewhere else and you change one value: **Home ▸ Transform data ▸ Manage
parameters ▸ `LocalDataFolder`** → the full path to the `data` folder, then Refresh.

## Switching to live SharePoint data

Two parameters, no model changes:

| Parameter | Set to |
|-----------|--------|
| `SourceMode` | `SharePoint` |
| `SharePointSiteUrl` | `https://<tenant>.sharepoint.com/sites/PMSystem` |

Then **Home ▸ Transform data ▸ Data source settings ▸ Edit Permissions ▸
Organizational account** and sign in. Refresh.

`fnSource` routes each table to the right place: the eight lists go through
`SharePoint.Tables`, the six master workbooks through `SharePoint.Files`, and the
monthly standard-hours uploads through a folder combine that picks up any new
`Cell_Standard_Hours_YYYY_MM.xlsx` automatically.

## If the project will not open

PBIR schema versions move with Power BI Desktop releases, and this project was
generated rather than saved by Desktop. If it refuses to load:

1. Desktop ▸ new blank file ▸ **Get data ▸ Text/CSV** ▸ pick any file from `data/`
2. **File ▸ Save as ▸ Power BI project (.pbip)** ▸ name it `PM_Dashboard`
3. Close Desktop
4. From the repo root:
   ```
   python3 scripts/build_pbip.py --inject "C:/path/to/PM_Dashboard.pbip"
   python3 scripts/validate_pbip.py "C:/path/to"
   ```
5. Reopen

That keeps Desktop's own boilerplate and writes the model and the ten pages into it.

## Checking the project before you open it

```
python3 scripts/validate_pbip.py
```

692 checks: every JSON parses, every relationship and every visual field reference
resolves against the model, every measure's DAX references a real table, column or
measure, page and visual folder names match their JSON, `pages.json` agrees with
what is on disk, and every column the M layer types exists in the CSV it reads.

## What is in here

```
PM_Dashboard.pbip                  ← open this
PM_Dashboard.SemanticModel/        17 tables · 94 measures · 28 relationships
PM_Dashboard.Report/               10 pages · 107 visuals · registered theme
data/                              16 CSVs, 6 794 rows
theme/PM_Theme.json                the theme, standalone, for manual import
```

## Known first-refresh issues on live SharePoint

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SharePoint list not found: X` | List name differs from the schema | Rename the list, or edit the name in `fnSource` |
| A column is missing after refresh | SharePoint internal name differs from the display name | Fix in Power Query — do not rename the list column |
| `Implementation 2.0` join error | More than 12 Person or Lookup columns on a list | Drop `Implementation` and `ViewMode` in `fnSpList` to fall back to connector 1.0 |
| `File not found in SharePoint` | Master workbook is not in `01 Master Data/` | Move it, or edit the path in `fnSource`'s `ExcelMap` |
| Standard hours table is empty | Files are in `_History/`, or named wrongly | Name must be `Cell_Standard_Hours_YYYY_MM.xlsx` with table `tblStdHours` |
