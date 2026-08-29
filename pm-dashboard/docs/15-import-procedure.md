# 15 · Import Procedure

Step by step, in order, from an empty site to a working dashboard. Every step
names the file it needs.

**Be honest with yourself about what "import" means here.** Three of the four
parts genuinely import — you paste or upload a file and the thing appears. The
Power App does not: Microsoft has no supported file format that builds a canvas
app from outside Studio, so that part is built by hand from the supplied
formulas. Section 4 says exactly why, so you do not waste an afternoon looking
for a shortcut that is not there.

| Part | Route | Time |
|------|-------|------|
| 1 · SharePoint lists | PowerShell script, or list-from-Excel | 20 min / 2 h |
| 2 · SharePoint files | Drag and drop | 15 min |
| 3 · Power BI model | One TMDL paste | 10 min |
| 4 · Power App | Built by hand from supplied Power Fx | 2 days |
| 5 · Flows | Built by hand from supplied definitions | 1–2 days |
| 6 · Report pages | Built by hand from the visual guide | 1–2 days |

---

## Before you start

Fill in the top of `05_Deployment/Deployment_Worksheet.xlsx` — sheet
**1 Tenant & App**. You will paste these values in several places and you do not
want to be hunting for them mid-build.

| You need | Looks like |
|----------|------------|
| Site URL | `https://<tenant>.sharepoint.com/sites/<SiteName>` |
| Library display name | `Documents` |
| PM folder (shared site only) | `PM System` |

---

## 1 · SharePoint lists

Two routes. Try A; fall back to B. They produce the same result.

### Route A — the provisioning script (20 minutes)

**File:** `02_SharePoint_Templates/Provision_PM_Lists.ps1`

It creates all eight lists with 157 columns — types, choice values, required
flags and indexed columns all set — turns on versioning, and makes the unused
Title column optional so the app and flows can write.

1. Install the module once per machine:
   ```powershell
   Install-Module PnP.PowerShell -Scope CurrentUser
   ```
2. Dry run against a **test** site first and read what it prints:
   ```powershell
   .\Provision_PM_Lists.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/TestSite" -WhatIfOnly
   ```
3. Run it for real on the test site, look at the lists, then run it on the real
   site.

The script is safe to re-run. It skips lists and columns that already exist and
never deletes anything, so if it stops half way you fix the cause and run it
again.

> **If it will not connect.** PnP.PowerShell 2.x and later need an Entra app
> registration of your own — the old shared multi-tenant app was retired. If
> your tenant has one, put its client ID in the `-ClientId` parameter. If you
> cannot get one, that is a hard stop for this route: use Route B. It is not
> worth escalating an app registration to save ninety minutes.

> This script has not been run against a live tenant — there was no tenant to
> test it on. It is deliberately plain PowerShell rather than a packaged import,
> so it fails one visible line at a time and you can comment out anything you do
> not like. Treat the first run as a test, which is why step 2 exists.

### Route B — create each list from Excel (about 2 hours)

**Files:** `02_SharePoint_Templates/03-list-seed-data/*.xlsx` (eight workbooks)
and `00-reference/SharePoint_List_Schemas.xlsx`

For each of the eight workbooks:

1. Site contents → **New** → **List** → **From Excel**.
2. Upload the workbook, choose the named table when prompted.
3. SharePoint guesses each column's type. It guesses badly: choice columns
   arrive as text, and numbers sometimes do too.
4. Open `SharePoint_List_Schemas.xlsx`, filter `ListName` to the list you just
   made, and fix every column whose type does not match the
   `SharePointColumnType` column. Paste the `ChoiceValues` cell into each choice
   column.
5. Set the `Indexed = Yes` columns as indexed columns in list settings. Skip
   this and you hit the 5,000-item view threshold once the log lists grow —
   which will happen in month three, not year three.
6. Delete the seed rows once you are happy. They are there to make the type
   guessing work, not to keep.

### Either route — finish with these

- **Item-level permissions on `PM_WorkOrders`:** read all items, edit own items.
  A technician should not be able to close somebody else's job.
- **Versioning on** for all eight, 50 major versions. Route A does this; Route B
  does not.
- **Shared site?** Break permission inheritance on all eight lists **now**,
  before real data goes in. See `14-existing-sharepoint-site.md` §3.2.

---

## 2 · SharePoint files

**Folder:** `02_SharePoint_Templates/`

Create this structure in the document library — at the library root on a
dedicated site, or inside your `PM System` folder on a shared one:

```
00 Reference/        01 Master Data/      02 Standard Hours/
02 Standard Hours/_History/               03 QR Codes/        04 Photos/
```

Then upload:

| From | To |
|------|-----|
| `01-master-data/*.xlsx` (6 files) | `01 Master Data/` |
| `02-standard-hours/Cell_Standard_Hours_TEMPLATE.xlsx` | `02 Standard Hours/` |
| `02-standard-hours/..._2026_08_SAMPLE.xlsx` | `02 Standard Hours/` |
| `02-standard-hours/..._History_BACKLOAD.xlsx` | `02 Standard Hours/_History/` |
| `00-reference/SharePoint_List_Schemas.xlsx` | `00 Reference/` |

Do not rename the folders. Both the model and the flows match on these names.

Open each master workbook and replace the dummy plant with yours: your cells,
your machines, your technicians, your spares. Keep the column headers and the
named table — the queries bind to the table name, not the sheet.

---

## 3 · Power BI model

This is the one that genuinely collapses. One paste builds 17 tables, all their
Power Query, 28 relationships and 94 measures with their format strings and
display folders.

**File:** `01_Power_BI/PM_Model.tmdl`

1. Copy `01_Power_BI/data` to `C:\PM_Dashboard\data`. The default
   `LocalDataFolder` parameter already points there, so the sample data loads
   with no editing.
2. **Turn off auto date/time first.** File → Options and settings → Options →
   **Data Load**, and clear the auto date/time box under both *Global* and
   *Current File*.

   Do not skip this. This model has its own `Dim_Date`, and auto date/time would
   build a hidden date table behind every one of the thirty-odd date columns —
   a much larger model for no benefit. It also puts a `DateTableTemplate` object
   in a file you would otherwise call blank, which used to break the paste
   outright.
3. Open Power BI Desktop → **Blank report**.
4. **Model** ribbon → **TMDL view**.
5. Open `PM_Model.tmdl` in Notepad, select all, copy, paste into the TMDL
   editor.
6. Select **Apply**.
7. **Home** → **Refresh**.

You now have the complete model on the sample data. Check three things before
going further:

| Check | Expected |
|-------|----------|
| Data pane | 17 tables plus `_Measures` |
| Model view | 28 relationships, 3 of them dashed (inactive) |
| A card with `[PM Compliance %]` | a percentage, not blank or an error |

Then switch to live data by changing parameters only — Home → Transform data →
Manage parameters:

| Parameter | Set to |
|-----------|--------|
| `SourceMode` | `SharePoint` |
| `SharePointSiteUrl` | your site URL |
| `SharePointLibrary` | `Documents` |
| `SharePointFolderPath` | blank, or `PM System` on a shared site |

Refresh. No query is rewritten and no relationship moves.

### If Apply fails

The TMDL editor names the offending line in the Output pane. Two causes cover
almost everything:

| Message | Cause | Fix |
|---------|-------|-----|
| `Culture and Collation properties of the Model object may be changed only before any other object has been created` | An older copy of the script set the model's culture. The engine allows that only on a model containing nothing at all, and a file with auto date/time on already holds a `DateTableTemplate`. | Use the current `PM_Model.tmdl`. |
| `Power BI Data Source Version is only allowed to change from V1 to a higher version, Current version is '2'` | The script did not restate the property, so `createOrReplace` reset it to its V1 default — a downgrade. | Use the current `PM_Model.tmdl`, which restates it. If the message names a version other than 2, see below. |
| Unexpected indentation, or an object where a property was expected | The paste lost its tabs. TMDL is indentation-sensitive and some editors convert tabs to spaces. | Copy from Notepad, not from Word, a browser, or an email. |
| The same data source version error, but naming `'3'` | Your model is at V3 where the script assumes V2. | Change line 4 to `powerBI_V3`. See below. |

Applying twice is safe. `createOrReplace` replaces each object it names, so if a
first attempt stopped half way, fix the cause and paste the whole script again.

### The model properties, and why line 4 restates one

`createOrReplace` replaces the model **object**, which resets every property the
script does not restate back to its default. Deleting a property from the script
therefore does not stop it being written — it makes it default. Line 4 exists for
exactly one property whose default is wrong:

| Property | Default | Why the script does what it does |
|----------|---------|----------------------------------|
| `defaultPowerBIDataSourceVersion` | V1 | A real model is at V2 or V3, and the engine refuses the downgrade to V1. So the script **restates it at the model's current value**, making the assignment a no-op. |
| `culture`, `collation` | matches | Cannot be assigned at all once the model holds any object. Their defaults match what the model already has, so letting them reset changes nothing. The script must **not** set them. |
| everything else | matches | Left to reset harmlessly. |

**If line 4's value does not match your model.** The script says `powerBI_V2`
because that is what Desktop reported. If your file is at V3 you will get the
same error again, naming `'3'`. Change line 4 to:

```
		defaultPowerBIDataSourceVersion: powerBI_V3
```

Two tabs of indentation, and whatever value the error message says is current.
To check before pasting rather than after: open TMDL view on the blank file and
read the first few lines — Desktop shows the model's own properties there.

If a **different** property name appears in an error, the same rule applies: add
it under `model Model` at the value the message says is current. Anything except
`culture` and `collation`, which must stay out.


## 4 · Power App

**There is no import file for this, and I am not going to pretend otherwise.**

Microsoft's supported formats do not give a route in. `.msapp` needs the Power
Platform CLI, which needs .NET, which will not be on a locked-down machine.
`.pa.yaml` is documented as read-only — "not used when an app is loading" — so
it cannot build an app. And the YAML that Power Apps Studio's code view accepts
on paste is whatever format Studio currently emits, which I cannot generate
blind and cannot test. Shipping a YAML file that fails to paste would waste more
of your time than building the screens.

So the app is built by hand, from two files that make that as mechanical as
possible:

**Files:** `07_Power_App/PM_Field_App.html` (working prototype) and
`07_Power_App/POWERFX_REFERENCE.md` (every control's formula)

1. Open the prototype in Edge. Walk all seven screens. Show it to the
   maintenance team and get the flow agreed **before** you build anything —
   changing a screen in the prototype costs nothing, changing it in Studio costs
   an afternoon.
2. In Power Apps, create a blank canvas app, **Tablet** layout.
3. Add the eight lists as data sources (Data → Add data → SharePoint → your
   site).
4. Build the seven screens. For each control, the reference gives the exact
   control name, the property, and the Power Fx to paste into the formula bar.
5. `04-powerapps-spec.md` has the screen-by-screen detail: navigation, variables,
   and what each screen must validate.

**One shortcut that is real.** Once you have built one control the way you want
it — a work-order card, say — right-click it → **View code**, copy, then paste
it back to duplicate it. That is Power Apps Studio's own format so it always
works, and it saves the repetitive part. It just cannot bootstrap the first one.

---

## 5 · Flows

**No import package either, for the same reason.** Power Automate's
Import Package (Legacy) takes a `.zip` with a particular manifest structure. I
have no reference package to copy that structure from and no Power Automate to
test against, so a package I built would probably fail on upload — and a failed
package tells you nothing about what was wrong.

What you get instead is every flow's logic in full, plus a build guide generated
from those definitions so the two cannot disagree.

**Files:** `06_Flows/definitions/*.json` (6 workflow definitions) and
`06_Flows/BUILD_GUIDE.md`

Build them in this order — flow 2 is the one that matters, the other five
support it:

| # | Flow | Trigger |
|---|------|---------|
| 1 | Validate Std Hours Upload | File created in `02 Standard Hours` |
| 2 | **Monthly PM Scheduler** | Manual / scheduled — owns the 4000-hour rule |
| 3 | Overdue Sweep | Nightly |
| 4 | Abnormality Escalation | Item created in `Abnormality_Log` |
| 5 | Spare Approval Routing | Item created in `SparePart_Requests` |
| 6 | Missing Upload Reminder | Monthly |

For each flow, the JSON shows every action, its inputs and its `runAfter` order;
the build guide turns that into click-by-click steps. Set **Site Address** to
your site in every SharePoint action. On a shared site, also set flow 1's
`StdHoursFolderId` to `/Shared Documents/PM System/02 Standard Hours` — note
`Shared Documents` here where Power BI wants `Documents`.

Test flow 2 with `Mode = Backload` against the history file before you let it
run for real. It is the only flow that creates work orders, and a wrong run
creates them for every machine.

---

## 6 · Report pages

**File:** `04_Documentation/Documentation.html` → **Report Build Guide**

10 pages, 107 visuals. For each one it names the visual type as it appears in
the Visualizations pane and which field goes in which well. Build the Overview
page first — it is the one people will look at — then the rest in any order.

The theme is in `01_Power_BI/theme/`. View → Themes → Browse for themes.

---

## Order of work

Only two dependencies really constrain you:

```
1 lists ──┬── 4 app        (needs the lists to bind to)
          └── 5 flows      (needs the lists to write to)
2 files ───── 3 model ───── 6 report
```

The model and report run entirely on the sample data, so **do part 3 first if
you want something to show people** while the rest is being built. That is
usually the right call — a working dashboard on dummy data gets a project
funded; a half-built app does not.

---

## When each part is done

| Part | Done means |
|------|------------|
| 1 | Eight lists, columns match the schema workbook, `PM_WorkOrders` has item-level permissions |
| 2 | Six folders, master workbooks hold your plant, not the dummy one |
| 3 | 17 tables, 28 relationships, a card showing a real compliance percentage |
| 4 | A technician can scan a machine QR, complete a checklist, and the work order closes |
| 5 | Flow 2 in backload mode reproduces the history without creating duplicate work orders |
| 6 | All 10 pages populate with no blank visuals |
