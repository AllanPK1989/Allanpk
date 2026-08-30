# Power Apps — the technician front end

## What this is, and how it relates to the Forms path

The system is built so the shop floor can be driven **two ways**, over the same
SharePoint lists and the same flows:

| | **Path A — Forms + list views** | **Path B — Canvas app** |
|---|---|---|
| Technician sees | QR → SharePoint Machine Hub → 5 buttons → Microsoft Form | QR → app opens on that machine → tabbed screens |
| Offline | No | Yes, with `SaveData` / `LoadData` |
| Scanning | The phone camera app opens the URL | Barcode reader control **inside** the app |
| Checklist | One long form, all items at once | One item at a time, with the acceptance standard on screen |
| Cost | Included everywhere | Needs Power Apps rights (see below) |
| Build effort | ~1 day | ~4–5 days |

**Both write to the identical lists with identical column names.** The eleven flows
do not care which one produced the row. That is the point of the design: you can go
live on Path A next week and move to Path B later without touching the data model,
the flows, or the Power BI report.

Keep Path A configured even after Path B is live. When a phone will not install the
app, or a contractor needs to log one breakdown, the Forms path still works and
still writes valid data.

## Licensing — check this before you build

A canvas app using **only** the SharePoint connector uses standard connectors, and
Microsoft 365 plans have historically included seeded Power Apps rights covering
exactly that. Seeded rights change, and they are the kind of thing that is
discovered to be wrong after a system is in production.

**Confirm with whoever owns licensing in your organisation before starting**, and
ask specifically about:

- canvas apps over **SharePoint lists only** (no Dataverse, no custom connectors)
- **Power Apps for Microsoft 365** seeded use rights on your plan
- whether the tenant's DLP policy permits SharePoint + Office 365 Users in one app

Nothing in this build uses a premium connector, Dataverse, or a custom connector.
If the answer comes back that Power Apps is not available, Path A delivers the same
system.

## Files here

| File | What it is |
|---|---|
| `CANVAS_APP_BUILD.md` | Screen-by-screen build sheet: every control, every property, every formula |
| `power_fx_formulas.md` | The formulas on their own, copy-paste ready |
| `app_manifest.json` | Data sources, screens, collections and variables — the map |

## The shape of the app

```
   QR scan
      │
      ▼
┌─────────────────┐
│  scrHome        │  Technician picks their name ONCE per session
│                 │  (shared login - this is the whole audit trail)
└────────┬────────┘
         │
    ┌────┴─────────────────────────────┐
    ▼                                  ▼
┌─────────────────┐          ┌─────────────────┐
│ scrMyList       │          │ scrMachineHub   │  ← QR lands here
│ allotted PM     │─ tap ───▶│ identity + 5    │
│ (auto-updates)  │          │ actions         │
└─────────────────┘          └────────┬────────┘
                                      │
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼
   scrStartPM    scrChecklist    scrBreakdown   scrSpare      scrAbnormality
```

## Three decisions that matter

**The technician name is picked once per session and stored in a global.** Every
technician signs in with the same M365 login, so `User().Email` identifies nothing.
The dropdown is the entire audit trail. It is mandatory on every screen and it is
never free text — free text produces "Murugan", "murugan s", "MURUGAN S" and three
months later nobody can count anything.

**The allotted list is a filtered gallery, not a stored list.** Its filter is
`Task_Status <> "Completed"`. When a checklist submission flips that field the row
leaves the gallery on the next refresh. There is no sync, no state to go stale, and
nothing to reconcile — the same mechanism as the SharePoint view in Path A.

**Delegation is designed for, not discovered.** `Filter()` on
`Checklist_Response` with a non-delegable predicate silently returns the first 500
rows and gives you a number that looks plausible and is wrong. Every query in
`power_fx_formulas.md` is written delegable, against the columns
`provision_lists.ps1` indexes. Turn **App settings → Advanced → Data row limit** down
to **500** during development: a query that breaks delegation then breaks visibly
instead of hiding behind a 2,000-row cushion.
