# 14 · Using an Existing SharePoint Site

The default build assumes a dedicated site called `PMSystem`. If you cannot get a
new site provisioned, the whole system runs just as well inside a site you already
have. This document is the complete list of what changes.

Short version: **the files go in a folder, the lists cannot.** Everything else is
three parameter values.

---

## 1 · What can and cannot live in a folder

| Thing | Goes in a folder? | Where it actually lives |
|-------|-------------------|-------------------------|
| The six master workbooks | Yes | `Documents/PM System/01 Master Data/` |
| Monthly standard-hours uploads | Yes | `Documents/PM System/02 Standard Hours/` |
| QR PDFs, photos, reference | Yes | `Documents/PM System/03 QR Codes/`, `04 Photos/` |
| The eight SharePoint **lists** | **No** | `/<site>/Lists/PM_WorkOrders`, etc. |

SharePoint lists are site-level objects. There is no such thing as a list inside a
document-library folder, and no way to nest one. The eight PM lists will appear in
the existing site's **Site contents** alongside whatever is already there. That is
not a problem, but it has three consequences, covered in §3.

---

## 2 · The folder layout

Create one folder in the existing site's document library and put the standard
structure underneath it, unchanged:

```
Documents/                          ← the existing library, already there
└── PM System/                      ← the one folder you create
    ├── 00 Reference/
    ├── 01 Master Data/
    ├── 02 Standard Hours/
    │   └── _History/
    ├── 03 QR Codes/
    └── 04 Photos/
```

Keep the numbered names exactly. The queries and the flows both match on them.

Name the top folder whatever you like — `PM System`, `Maintenance`, `PM` — you
will type that name into one parameter and one flow parameter, and nowhere else.

---

## 3 · The three consequences of sharing a site

### 3.1 Name collisions

Check **Site contents** before you build. Five of the eight lists have generic
names that another team could plausibly have used:

```
Breakdown_Reports        SparePart_Requests       SparePart_Replacements
Abnormality_Log          QR_Scan_Log
```

The other three (`PM_WorkOrders`, `PM_ChecklistResults`, `PM_Hour_Ledger`) are
already prefixed and are very unlikely to clash.

If a name is taken, rename the PM one — but rename it **everywhere**, because the
name is the binding in three places: the Power BI query, the SharePoint action in
each flow, and the `Patch()` target in the app. Search the package for the old
name and change every hit before you build anything. Doing this after the app is
built means re-adding the data source in Studio.

Safest option if you have any doubt: prefix all eight with `PM_` from the start.

### 3.2 Everyone on the site can see the PM lists

Members of the existing site inherit Edit rights on your new lists. Breakdown
reports, abnormality logs and technician names are visible to anyone who was
already a member.

If that is not acceptable, break inheritance per list:

> List settings → Permissions for this list → **Stop Inheriting Permissions** →
> remove the site Members group → add your own PM Members and PM Visitors groups.

Do this on all eight lists, and on the `PM System` folder, before you load any
real data. Doing it afterwards does not retroactively hide anything anyone
already saw.

Leave `Machine_Master` and `Cell_Master` inheriting if production supervisors on
that site have a reason to read them — that part is a judgement call.

### 3.3 Refresh speed

This is the one that actually bites, and it is the reason the queries changed.

`SharePoint.Files(siteUrl)` enumerates **every file in every library on the site**
before any filter is applied. On a dedicated PM site that is about twenty files.
On a busy departmental site it can be tens of thousands, and a refresh that took
fifteen seconds takes twenty minutes.

The model therefore uses `SharePoint.Contents`, which walks one folder at a time
and only touches the branch you name. `fnSpFolder` does the walking; `fnSpExcel`
and `fnStdHoursFolder` call it. Nothing enumerates the rest of the site.

---

## 4 · What you actually change

### 4.1 Power BI — three parameters

Home → Transform data → Manage parameters.

| Parameter | Dedicated site | Existing site |
|-----------|----------------|---------------|
| `SharePointSiteUrl` | `https://<tenant>.sharepoint.com/sites/PMSystem` | `https://<tenant>.sharepoint.com/sites/<ExistingSite>` |
| `SharePointLibrary` | `Documents` | `Documents` |
| `SharePointFolderPath` | *(blank)* | `PM System` |

`SharePointSiteUrl` is the **site** URL. Not the folder, not the library, and not
the address bar of the page you happen to be looking at. It ends at the site name:

```
https://contoso.sharepoint.com/sites/Manufacturing            ← correct
https://contoso.sharepoint.com/sites/Manufacturing/Shared%20Documents/Forms/AllItems.aspx  ← wrong
```

`SharePointLibrary` is the library's **display name**. On an English tenant the
default library shows as `Documents` even though its URL says `Shared Documents`
— use `Documents`. On a non-English tenant it will be the localised word. You do
not have to guess: put anything in, refresh, and the error names every library on
the site so you can copy the right one.

`SharePointFolderPath` accepts nested paths (`Maintenance/PM System`) and tolerates
leading and trailing slashes.

### 4.2 Power Automate — two flow parameters

Only Flow 1 (upload validation) and Flow 6 (missing-upload reminder) touch files.
Both already carry the folder as a parameter:

| Flow | Parameter | Change to |
|------|-----------|-----------|
| 1 · Validate Std Hours Upload | `StdHoursFolderId` | `/Shared Documents/PM System/02 Standard Hours` |
| 6 · Missing Upload Reminder | `StdHoursLibraryId` | `Shared Documents` *(unchanged)* |

Note the folder path uses `Shared Documents`, not `Documents` — the file
connector uses the URL name where Power Query uses the display name. This is
inconsistent of SharePoint, not of this system.

In every flow, set **Site Address** to the existing site. The other four flows
only touch lists, so the site address is the only change they need.

One bonus: because Flow 1's trigger is scoped to that folder, it will not fire on
unrelated files people drop elsewhere in the library. On a shared site that
matters — an unscoped trigger would run on every document anyone uploads.

### 4.3 Power Apps

Add each of the eight lists as a data source from the existing site. Nothing else
changes; the app never references a folder.

If you renamed a list under §3.1, use the new name — the `Patch()` and
`Filter()` targets in the Power Fx reference all use the list name directly.

### 4.4 QR codes

No change. The codes encode the app ID and screen parameters, not the site.

---

## 5 · Ten-minute check before you build the rest

Do this once, with only the master workbooks uploaded, and you will find any
site-level problem before it costs you a day.

1. Create the `PM System` folder and `01 Master Data` under it.
2. Upload `Cell_Master.xlsx` and nothing else.
3. In Power BI, set the three parameters from §4.1, set `SourceMode` to
   `SharePoint`, and refresh **only** the `Dim_Cell` query.
4. It should return 8 rows in a few seconds.

| What you see | What it means |
|--------------|---------------|
| 8 rows, fast | Correct. Carry on. |
| `Document library not found: 'Documents'. Libraries on this site: …` | Copy the right name from the message into `SharePointLibrary`. |
| `Folder not found: 'PM System' while walking …` | Folder name typo, or it is in a different library. |
| `File not found in SharePoint: PM System/01 Master Data/Cell_Master.xlsx` | Library and folder are right, the file is not where you think. |
| Credential prompt | Sign in with an Organizational account, not a Microsoft account. |
| Access denied | You have read rights on the site but not the library, or the site blocks external sharing of the library. |
| Correct rows but slow (minutes) | You are still on a `SharePoint.Files` query — you are running an old copy of the model. |

---

## 6 · What this costs you

Nothing structural. Two honest downsides:

**Site lifecycle is not yours.** If the existing site is archived, has a retention
policy applied, or gets its permissions restructured by whoever owns it, the PM
system is affected and you will not necessarily be told first. Find out who owns
the site and tell them the lists are now load-bearing.

**Storage and versioning are shared.** The `04 Photos` folder grows — breakdown
and abnormality photos from the app. Budget roughly 2–5 MB per work order with
photos. On a site already near its quota this matters; check the quota now rather
than in month four.

If a dedicated site becomes available later, moving is not painful: the lists can
be recreated and repopulated from a Power Automate copy, and the three parameters
plus two flow parameters point at the new site. Nothing in the model, the report
or the app has the site name baked into it.
