# Opening the Power BI project

## Fastest path — sample data, zero edits

1. Copy this folder so it sits at **`C:\PM_Dashboard`**. The `data` folder must end
   up at `C:\PM_Dashboard\data`.
2. Double-click **`PM_Dashboard.pbip`**.
3. **Home ▸ Refresh.**
4. **View ▸ Themes ▸ Browse for themes** ▸ pick `theme\PM_Theme.json`.

The `LocalDataFolder` parameter already points at `C:\PM_Dashboard\data`, so nothing
needs editing. Put the folder somewhere else and change that one parameter under
**Home ▸ Transform data ▸ Manage parameters**.

The theme is a separate import on purpose. Embedding a custom theme inside the
project is the single most version-fragile part of the file format, and it buys
five seconds.

## If Desktop refuses to open it

The `.pbip` format is versioned, and Desktop validates each wrapper file against a
pattern that changes between releases. If you get a message naming a `$schema`
property, **the model and the report are fine** — only the small wrapper files are
wrong for your build. Two ways to fix it, neither needing Python.

### Option A — let Desktop write the wrapper files (5 minutes, always works)

This is the reliable one. Desktop generates the version-sensitive files for *your*
build; you keep everything that matters from here.

1. Open Power BI Desktop. Check **File ▸ Options and settings ▸ Options ▸ Preview
   features** has **Power BI Project (.pbip) save option**, **Store semantic model
   using TMDL format** and **Enhanced report format (PBIR)** all ticked. Restart if
   you changed anything.
2. **Get data ▸ Text/CSV** ▸ any file from `data\` ▸ **Load**.
3. **File ▸ Save as ▸ Power BI project (.pbip)** ▸ save as `PM_Dashboard` into a new
   empty folder, say `C:\PM_Dashboard_New`.
4. **Close Power BI Desktop.** It must not be open for the next step.
5. In File Explorer, copy these two folders from here, overwriting what Desktop made:

   ```
   PM_Dashboard.SemanticModel\definition\     →  C:\PM_Dashboard_New\PM_Dashboard.SemanticModel\definition\
   PM_Dashboard.Report\definition\            →  C:\PM_Dashboard_New\PM_Dashboard.Report\definition\
   ```

   Copy the **`definition`** folders only. Leave Desktop's own `.pbip`, `.platform`,
   `definition.pbir` and `definition.pbism` files exactly as they are — those are the
   ones that have to match your version.
6. Copy `data\` and `theme\` across too.
7. Open `C:\PM_Dashboard_New\PM_Dashboard.pbip` and refresh.

### Option B — regenerate, if you have Python

```
python3 scripts/build_pbip.py --inject "C:/PM_Dashboard_New/PM_Dashboard.pbip"
python3 scripts/validate_pbip.py "C:/PM_Dashboard_New"
```

Same result as Option A, done for you.

## What the wrapper files must contain

For reference, in case you ever need to check them by hand. These values are taken
from Power BI projects published by Microsoft, and `scripts/validate_pbip.py`
enforces every one of them.

| File | `$schema` | Other |
|------|-----------|-------|
| `PM_Dashboard.pbip` | `…/fabric/pbip/pbipProperties/1.0.0/schema.json` | `version: "1.0"` |
| `…SemanticModel/.platform` | `…/fabric/gitIntegration/platformProperties/2.0.0/schema.json` | `type: SemanticModel` |
| `…SemanticModel/definition.pbism` | `…/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json` | `version: "4.2"` |
| `…Report/.platform` | `…/fabric/gitIntegration/platformProperties/2.0.0/schema.json` | `type: Report` |
| `…Report/definition.pbir` | `…/fabric/item/report/definitionProperties/2.0.0/schema.json` | `version: "4.0"` |
| `…Report/definition/report.json` | `…/fabric/item/report/definition/report/3.0.0/schema.json` | |
| `…/definition/pages/pages.json` | `…/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json` | |
| `…/pages/<page>/page.json` | `…/fabric/item/report/definition/page/2.0.0/schema.json` | |
| `…/visuals/<v>/visual.json` | `…/fabric/item/report/definition/visualContainer/2.4.0/schema.json` | |

There is no `version.json` in a PBIR report — if you see one, delete it.

## Switching to live SharePoint data

Two parameters, no model changes:

| Parameter | Set to |
|-----------|--------|
| `SourceMode` | `SharePoint` |
| `SharePointSiteUrl` | `https://<tenant>.sharepoint.com/sites/PMSystem` |

Then **Home ▸ Transform data ▸ Data source settings ▸ Edit Permissions ▸
Organizational account** and sign in. Refresh.

`fnSource` routes each table: the eight lists through `SharePoint.Tables`, the six
master workbooks through `SharePoint.Files`, and the monthly standard-hours uploads
through a folder combine that picks up new files automatically.

## Checking the project before you open it

```
python3 scripts/validate_pbip.py
```

813 checks: every JSON parses, every `$schema` matches the pattern Desktop enforces,
every relationship and visual field reference resolves against the model, every
measure's DAX references a real table, column or measure, folder names match the
`name` inside their JSON, `pages.json` agrees with what is on disk, and every column
the M layer types exists in the CSV it reads.

## First-refresh problems on live SharePoint

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SharePoint list not found: X` | List name differs from the schema | Rename the list, or edit the name in `fnSource` |
| A column is missing after refresh | SharePoint internal name differs from the display name | Fix in Power Query — do not rename the list column |
| `Implementation 2.0` join error | More than 12 Person or Lookup columns on a list | Drop `Implementation` and `ViewMode` in `fnSpList` to fall back to connector 1.0 |
| `File not found in SharePoint` | Master workbook is not in `01 Master Data/` | Move it, or edit `fnSource`'s `ExcelMap` |
| Standard hours table is empty | Files are in `_History/`, or named wrongly | Name must be `Cell_Standard_Hours_YYYY_MM.xlsx` with table `tblStdHours` |
