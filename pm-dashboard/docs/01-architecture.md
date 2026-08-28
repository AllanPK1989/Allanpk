# 01 · Solution Architecture

## The shape of it

```
                     ┌──────────────────────────────────────────┐
   Production   ───► │  Cell_Standard_Hours_YYYY_MM.xlsx        │
   Planning          │  SharePoint ▸ 02 Standard Hours          │
   (monthly)         └───────────────┬──────────────────────────┘
                                     │
                                     ▼
                     ┌──────────────────────────────────────────┐
                     │  Power Automate ▸ Monthly PM Scheduler   │
                     │  • accrue hours per cell                 │
                     │  • trip at 4000 h  (or 12-month backstop)│
                     │  • write PM_Hour_Ledger                  │
                     │  • raise one work order per machine      │
                     └───────────────┬──────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
┌───────────────┐          ┌──────────────────┐        ┌────────────────────┐
│ SharePoint    │◄────────►│  Power Apps      │        │  Power BI          │
│ Lists (8)     │  read /  │  "PM Field App"  │        │  PM Dashboard      │
│ + Master data │  write   │                  │        │  (10 pages)        │
│   workbooks   │          │  opened by QR    │        │  scheduled refresh │
└───────────────┘          └────────┬─────────┘        └────────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    ▼                                ▼
          ┌──────────────────┐            ┌────────────────────┐
          │  MACHINE QR      │            │  TECHNICIAN QR     │
          │  one per machine │            │  one per person    │
          │  • last PM date  │            │  • my PM list      │
          │  • start PM      │            │  • auto-updates as │
          │  • breakdown     │            │    machines are    │
          │  • spare request │            │    scanned         │
          │  • spare fitted  │            │                    │
          │  • abnormality   │            │                    │
          └──────────────────┘            └────────────────────┘
```

## Why each piece is where it is

**SharePoint is the database.** Not because it is a good database — because it is
already licensed, already backed up, already governed by your tenant's retention
and DLP rules, and Power BI and Power Apps both speak to it natively with no
gateway. The cost is the 5,000-item view threshold, which is why the schema
reference marks certain columns as indexed.

**Power Apps does data capture.** Power BI cannot write. Anything a technician
types, photographs, or ticks goes through the app. The app is also what a QR code
opens — a QR code is just a deep link with a machine ID or a technician ID in the
query string.

**Power Automate owns the scheduling rule.** Not Power BI. This matters: a work
order is a record with an owner and an audit trail, not a row that appears and
disappears as somebody moves a slicer. The flow runs the 4000-hour rule once a
month, writes the ledger, and creates work orders. Power BI then *recomputes and
displays* the same arithmetic so anyone can see why a PM fell due — but the
dashboard is a mirror, never the source.

**Power BI does analysis and nothing else.** Read-only, three refreshes a day.

## Data flow, in order

| # | Event | Actor | Lands in |
|---|-------|-------|----------|
| 1 | Monthly standard hours uploaded | Production Planning | `02 Standard Hours` folder |
| 2 | Hours accrued, counters advanced | Scheduler flow | `PM_Hour_Ledger` list |
| 3 | Cell trips 4000 h (or 12-month backstop) | Scheduler flow | `PM_WorkOrders` list, one row per machine |
| 4 | Work orders assigned and levelled | Scheduler flow | `PM_WorkOrders.AssignedTechID` |
| 5 | Technician scans personal QR | Power Apps | reads open work orders for that TechID |
| 6 | Technician scans machine QR | Power Apps | `QR_Scan_Log`, work order → In Progress |
| 7 | Checklist completed | Power Apps | `PM_ChecklistResults`, work order → Completed |
| 8 | Failed task | Power Apps | `Abnormality_Log` (photo mandatory) |
| 9 | Breakdown / spare request / spare fitted / abnormality | Power Apps | respective list |
| 10 | Overdue sweep | Nightly flow | `PM_WorkOrders.Status` → Overdue |
| 11 | Refresh | Power BI service | dashboard |

## What deliberately is **not** here

- **No ERP or CMMS integration.** If you already run SAP PM or Maximo, this whole
  thing is the wrong answer — use their mobile module. This design assumes you
  don't, or that the ERP is not usable on the shop floor.
- **No live machine hour meters or PLC/IoT feed.** Scheduling is driven by
  production standard hours from a monthly Excel upload, as specified. If you
  later get real runtime data, only the scheduler flow changes; everything
  downstream stays put.
- **No offline-first custom app.** Power Apps offline collections cover a lost
  signal in a bay. If your plant has no Wi-Fi at all, that is a network project,
  not a dashboard project.

## Licensing you will actually need

| Component | Licence | Note |
|-----------|---------|------|
| SharePoint lists, Excel | Microsoft 365 E3/E5/Business | already have it |
| Power Apps (SharePoint data only) | Included in M365 for standard connectors | SharePoint, Outlook, Office 365 Users are standard |
| Power Automate (standard connectors) | Included in M365 | |
| Power BI report authoring | Power BI Pro (Desktop is free) | one Pro licence to publish |
| Report viewing | Power BI Pro per viewer, **or** Fabric F-SKU / Premium capacity | this is usually the real cost decision |

Confirm the Power Apps entitlement with whoever owns your tenant before you build.
Standard connectors are included; the moment anyone adds a premium connector
(Dataverse, SQL, custom connector) every user needs a per-user Power Apps licence.

## Semantic model shape

Star schema, single-direction many-to-one relationships throughout.

```
Dim_Cell ──< Dim_Machine ──< Fact_WorkOrders ──< Fact_ChecklistResults >── Dim_Checklist
   │              │   │              │
   │              │   ├──< Fact_Breakdowns
   │              │   ├──< Fact_SpareRequests      >── Dim_SparePart
   │              │   ├──< Fact_SpareReplacements  >── Dim_SparePart
   │              │   ├──< Fact_Abnormalities
   │              │   └──< Fact_ScanLog
   ├──< Fact_StdHours
   └──< Fact_HourLedger

Dim_Date ──< every fact that carries a date
Dim_Technician ──< Fact_WorkOrders, Fact_Abnormalities, Fact_ScanLog
```

Two modelling decisions worth knowing:

**Checklist results hang off the work order, not off `Dim_Machine` and `Dim_Date`
directly.** A checklist line only exists because a work order exists. Relating it
to all three would create two filter paths from `Dim_Date` (`Date → WorkOrder →
Checklist` and `Date → Checklist`) and Power BI would refuse one of them. Routing
through the work order also makes "completed work orders with no checklist
evidence" a question the model can actually answer.

**`Fact_WorkOrders` carries three date relationships, two of them inactive.**
`PlannedDate` is active because the plan is what people slice by. `ActualEndDate`
and `DueDate` are there for `USERELATIONSHIP` when you want completion-date or
due-date analysis, without a second date table.
