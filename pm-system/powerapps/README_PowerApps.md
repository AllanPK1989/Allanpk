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
| Cost | Included everywhere | Needs a Power Apps licence — **not available today** |
| Build effort | ~1 day | ~4–5 days |

**Both write to the identical lists with identical column names.** The eleven flows
do not care which one produced the row. That is the point of the design: you can go
live on Path A next week and move to Path B later without touching the data model,
the flows, or the Power BI report.

Keep Path A configured even after Path B is live. When a phone will not install the
app, or a contractor needs to log one breakdown, the Forms path still works and
still writes valid data.

## Status: Phase 2 — not licensed today

**There is no Power Apps licence available at present, so the system goes live on
Path A (Forms + list views).** Everything the brief asks for works that way.

Nothing in the data model, the eleven flows or the Power BI report depends on this
app. That is the point of the design — the canvas app is an alternative front end
over the same lists, not a foundation. It can be added at any time, or never.

This folder therefore serves two purposes:

1. **A costed Phase 2 spec**, ready to build the day a licence exists.
2. **Evidence for the licence request.** `docs/POWERAPPS_LICENCE_CASE.pptx` is the
   business case; this folder is what it points at when someone asks "what exactly
   would you build?"

### What to confirm when the licence question is reopened

Nothing here uses a premium connector, Dataverse, or a custom connector — only
SharePoint and Office 365 Users. Ask specifically about:

- canvas apps over **SharePoint lists only**
- **Power Apps for Microsoft 365** seeded use rights on your current plan, versus a
  paid per-app or per-user plan
- whether the tenant's DLP policy permits SharePoint + Office 365 Users in one app

Seeded rights change, and they are the kind of thing discovered to be wrong after a
system is in production — so get the answer in writing before building.

### One decision this forces today

**Print the QR stickers against the SharePoint Machine Hub URL**, which is what
`apply_views.ps1` emits. If the canvas app is licensed later, the payload becomes a
deep link and the 30 stickers have to be reprinted.

That is a known, accepted cost of starting on Forms. It is 30 labels and an hour on
the shop floor, not a redesign.

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
