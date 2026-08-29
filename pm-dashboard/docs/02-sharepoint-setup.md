# 02 · SharePoint Setup

Everything the system reads or writes lives on one SharePoint site. Build it in
this order; each step depends on the one before.

## 1 · Create the site

A **Team site** (group-connected) called `PMSystem`, at
`https://<tenant>.sharepoint.com/sites/PMSystem`.

> **No rights to create a site?** You do not need one. Everything here works
> inside a site you already have, with the files under a single folder and the
> lists alongside the site's existing ones. Read **14 · Using an Existing
> SharePoint Site** first, then come back and follow this document from §3 —
> it lists the three parameters and two flow parameters that change.

Members:

| Group | Who | Rights |
|-------|-----|--------|
| Owners | Maintenance Head, one IT/Power Platform admin | Full control |
| Members | Maintenance planners, stores in-charge | Edit |
| Visitors | Technicians, production supervisors | Read |

Technicians are **Visitors**, not Members. They write through the Power App, which
runs under its own connection — they never need to touch the lists directly, and
you do not want them able to.

## 2 · Document library folders

In **Shared Documents**, create exactly these folders. The Power Query folder scan
depends on the names:

```
Shared Documents/
├── 00 Reference/                SharePoint_List_Schemas.xlsx, this documentation
├── 01 Master Data/              the six master workbooks
├── 02 Standard Hours/           Cell_Standard_Hours_YYYY_MM.xlsx  ← one per month
│   └── _History/                the one-time back-load file, parked out of scope
├── 03 QR Codes/                 machine-labels.pdf, technician-badges.pdf, index
└── 04 Photos/                   written by the app; do not organise by hand
```

Upload from `sharepoint-templates/` in this repo, keeping the folder numbers.

> The `_History` subfolder matters. `fnStdHoursFolder` reads one level of
> `02 Standard Hours` only, so the back-load file parked in `_History` does not
> get counted twice.

If these folders sit inside a parent folder rather than at the library root, put
that parent's name in the `SharePointFolderPath` parameter and change nothing
else. See document 14.

## 3 · Create the eight lists

Open `sharepoint-templates/00-reference/SharePoint_List_Schemas.xlsx`. It has one
row per column of every list — name, SharePoint type, choice values, required,
indexed.

| List | Written by | Rows/year (33 machines) |
|------|-----------|------------------------:|
| `PM_WorkOrders` | Scheduler flow, then the app | ~130 |
| `PM_ChecklistResults` | App | ~1 400 |
| `Breakdown_Reports` | App | ~100 |
| `SparePart_Requests` | App | ~60 |
| `SparePart_Replacements` | App | ~40 |
| `Abnormality_Log` | App | ~110 |
| `PM_Hour_Ledger` | Scheduler flow | 96 |
| `QR_Scan_Log` | App | ~800 |

For each list:

1. **+ New ▸ List ▸ Blank list**, named exactly as above (no spaces).
2. Add every column from the schema sheet, **in order**, with the stated type.
3. List settings ▸ Advanced ▸ set **Title** to not required; remove it from all
   views and from the form.
4. List settings ▸ Versioning ▸ **Create a version each time you edit** ▸ keep 50.
5. List settings ▸ Indexed columns ▸ add every column the schema marks
   `Indexed = Yes`.

### Why no Lookup columns

The schema deliberately uses plain text for `MachineID`, `CellID`, `TechID` and
`PartNo` rather than SharePoint Lookup columns. Lookups look tidy in the list UI
and then make Power BI refresh slow and brittle, cap you at 12 lookups per view,
and break the moment a referenced item is deleted. Store the ID as text; build the
relationship in the semantic model, where it belongs.

### Item-level permissions on `PM_WorkOrders`

List settings ▸ Advanced settings:

- **Read access:** All items
- **Create and Edit access:** Only their own

A technician sees the whole plan but can only change their own jobs. Combined with
the QR scan log, this is what makes "who closed this work order, and were they
actually at the machine" an answerable question.

## 4 · Load the master data

Upload the six workbooks from `sharepoint-templates/01-master-data/` into
`01 Master Data/`. They arrive pre-filled with the dummy plant so the dashboard
works on day one; replace the rows with your own when you are ready.

Order matters on first load, because of the ID references:

1. `Cell_Master.xlsx`
2. `Machine_Master.xlsx` — every `CellID` must exist in Cell_Master
3. `PM_Checklist_Master.xlsx` — every `ChecklistID` used by Machine_Master
4. `Technician_Master.xlsx`
5. `SparePart_Master.xlsx`
6. `PM_Config.xlsx`

## 5 · Back-load the standard hours history

Upload `Cell_Standard_Hours_History_BACKLOAD.xlsx` to
`02 Standard Hours/_History/`, then run the scheduler flow once in **back-load
mode** (see Flow 2). This builds the ledger from real history so counters and
last-PM dates start from where the plant actually is, rather than from zero.

Skip this and every cell starts at zero hours, which means nothing is scheduled
for the first three or four months and the dashboard looks broken.

## 6 · Retention

`QR_Scan_Log` is the highest-volume list and the least valuable after the fact.
Set a retention policy: keep 24 months, then move to an archive list or delete.
Do the same for `PM_ChecklistResults` only if your audit regime allows it — most
quality systems want seven years of PM evidence, so check before you delete
anything.

## 7 · Naming rules that are not negotiable

| Thing | Rule | Why |
|-------|------|-----|
| Monthly upload file | `Cell_Standard_Hours_YYYY_MM.xlsx` | the flow parses the month from the name |
| Sheet inside it | `Standard_Hours` | Power Query binds to it |
| Excel table inside it | `tblStdHours` | Power Query binds to it |
| List names | no spaces, exactly as in the schema | `fnSpList` looks them up by title |
| Master workbook table names | `tblCellMaster`, `tblMachineMaster`, … | hard-coded in `fnSource` |

Rename any of these and the refresh fails with a message that will not tell you
why. The READ ME sheet inside every template repeats this warning where the person
doing the renaming will actually see it.
