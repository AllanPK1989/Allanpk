# Opening the Power BI project

## First: extract the zip properly

Right-click the zip ▸ **Extract All** ▸ choose a real folder such as `C:\PM_Dashboard`.

Do **not** double-click the `.pbip` from inside the zip. Windows extracts only the
file you clicked into a temporary folder, so the rest of the project is not there,
and Power BI reports:

```
ReportDefinition: Required artifact is missing in '...\PM_Dashboard.Report\definition.pbir'
```

That message means files are missing, not that anything is wrong with the project.
If the path in the error contains `AppData\Local\Temp\` and `.zip.`, this is what
happened.

## Then: check and open

Two scripts sit next to the project. Neither needs anything installed.

**`CHECK.cmd`** — double-click it. It confirms the extraction is complete: 17 table
files, 10 report pages, 107 visuals, 16 CSVs. If anything is missing it says so and
tells you why.

**`PM_Dashboard.pbip`** — if the check passes, try opening this. Then:

1. **Home ▸ Refresh** (`LocalDataFolder` already points at `C:\PM_Dashboard\data`;
   change it under **Home ▸ Transform data ▸ Manage parameters** if you extracted
   somewhere else).
2. **View ▸ Themes ▸ Browse for themes** ▸ `theme\PM_Theme.json`.

## If Desktop still refuses to open it — `INSTALL.cmd`

The half-dozen small wrapper files in a `.pbip` are versioned, and Desktop validates
each against rules that change between releases. Rather than guess at yours, let
Desktop write them and keep everything that matters from here. **Double-click
`INSTALL.cmd`** and it walks you through it:

1. In Desktop, **File ▸ Options ▸ Preview features**, tick **Power BI Project (.pbip)
   save option**, **Store semantic model using TMDL format** and **Enhanced report
   format (PBIR)**. Restart if you changed any.
2. **Get data ▸ Text/CSV** ▸ any file from `data\` ▸ **Load**.
3. **File ▸ Save as ▸ Power BI project** ▸ named exactly `PM_Dashboard`, into a new
   empty folder.
4. **Close Desktop.**
5. Run `INSTALL.cmd` and give it that folder.

It copies the semantic model definition, the 10 report pages, the data and the theme
in, and leaves Desktop's own `.pbip`, `.platform`, `definition.pbir`,
`definition.pbism` and `report.json` untouched — those are the version-sensitive
ones. Then open the project, point `LocalDataFolder` at the `data` folder, and
refresh.

This path cannot fail on a version mismatch, because none of the files it writes are
version-sensitive. The TMDL model and the PBIR pages are stable formats.

> If you have Python, `python3 scripts/build_pbip.py --inject "C:/PM_Dashboard/PM_Dashboard.pbip"`
> does the same thing.

## What the wrapper files must contain

For reference. These values are taken from Power BI projects published by Microsoft,
and `scripts/validate_pbip.py` enforces every one of them.

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

`report.json` here deliberately declares no `resourcePackages` and no custom
`themeCollection`. Both name files that must exist on disk, and a wrong reference is
exactly what `Required artifact is missing` means. That is why the theme is a
separate import, and why `INSTALL.cmd` keeps Desktop's own `report.json`.

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
