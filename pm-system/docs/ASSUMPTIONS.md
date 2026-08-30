# Assumptions and judgement calls

Every decision made without an explicit instruction, why it was made that way, and
what to change if the assumption is wrong. Read this before go-live — a wrong
assumption here is much cheaper to fix now than after six months of data.

Anything marked **CONFIRM** needs a human answer before the system goes live.

---

## 1. Data model and identifiers

**1.1 IDs are uppercased and trimmed everywhere.**
`fnCleanKeys` applies `Text.Upper(Text.Trim(Text.Clean(...)))` to every key. A key
differing by a trailing space joins to nothing — the relationship still shows valid
in the model and just returns blank for those rows, silently, and you find out
months later when a cell's history looks thin.
*If wrong:* only if you ever need case-sensitive IDs, which nothing here does.

**1.2 An empty string key becomes null.**
An empty key is not a key. Nulling it makes a blank row visible in the model instead
of creating a phantom dimension member called `""` that quietly collects orphaned
facts.

**1.3 `Checklist_Response` joins on a composite key.**
Item 1 of `CL-PRESS` and item 1 of `CL-OVEN` are different checks, so the join is on
`Checklist_ID & "|" & Item_No`, built identically in `Dim_ChecklistItem` and
`Fact_ChecklistResponse`. Power BI has no composite relationships; the alternative
is a bidirectional many-to-many that wrecks the filter direction in ways nobody
predicts.
*If you change one, change the other.*

**1.4 `Cell_Master.Title` is populated from the primary key.**
SharePoint always has a `Title` column. Left blank you get a list of items all called
"Item", which makes search and every "send an email with a link" step useless.
Matching is always on the explicit key column, never on `Title`.

**1.5 Column internal names are created from field XML.**
`Add-PnPField` with a display name containing an underscore produces the internal
name `Cell_x005f_ID`. Every Power Query step, every flow expression and every model
reference would then have to use that mangled name. Creating from XML with
`Name`/`StaticName`/`DisplayName` all set keeps the dictionary name exact.

---

## 2. Business rules

**2.1 A cancelled work order is excluded from `PM Due Count`.**
It was not "due and not done", it was withdrawn. Counting it as a miss punishes the
right decision and makes compliance meaningless as a signal.
**CONFIRM** with the maintenance manager — some plants deliberately count
cancellations to make deferral visible.

**2.2 The calendar backstop is tested at `Calendar_Backstop_Months × 30.44` days.**
Flow 2's OData filter uses a literal `addDays(utcNow(), -183)` because SharePoint
cannot compare two columns; the per-cell re-check inside the loop uses real month
arithmetic. A cell could therefore appear in the filter up to two days before its
true backstop and be correctly rejected by the second test. That is the safe
direction — a false positive costs a skipped loop iteration, a false negative costs
a missed PM.

**2.3 A skipped machine still lets the cell close.**
`Task_Status = Skipped` is excluded from the pending-tasks filter, so one machine
under overhaul does not hold a cell open indefinitely. The work order is flagged
partial.
**This is the assumption most likely to cause harm.** "Machine running, will do next
time" repeated four times is how a PM system quietly dies. Review skips monthly —
`Skip_Reason` is mandatory precisely so that review is possible.
*If wrong:* remove `Task_Status ne 'Skipped'` from Flow 5's filter and a skip will
block closure.

**2.4 The reset quartet moves in one action.**
`Cum_Std_Hours_Since_PM`, `Last_PM_Date`, `Last_PM_WO_No`, `Reset_Applied` and
`Reset_Date` are set in a single `Update item`. Splitting them creates a window where
a failure leaves a zeroed counter with no `Last_PM_Date`, and nothing downstream can
distinguish that from a genuine reset.

**2.5 Proration is by calendar days, not working days.**
`posted = hours × (days_in_month − day_of_reset) / days_in_month`. Calendar days,
because the standard hours reported are already a measure of actual running — they
carry the shift pattern in them. Prorating by working days would apply the shift
pattern twice.
**CONFIRM** if your std-hours figure is a capacity number rather than an actual.

**2.6 Raw hours are stored; the prorated figure is a posting adjustment.**
`StdHours_Monthly.Actual_Std_Hours` holds what the cell actually ran. Only the
counter increment is prorated. Storing the adjusted figure would corrupt the
three-month average and the whole forecast with it.

**2.7 A safety-critical NOT OK leaves the task `In Progress`.**
The cell cannot close and the counter cannot reset until it is dealt with —
regardless of the severity anyone selected on the form. The dictionary says a
safety-critical NOT OK "blocks the task from closing"; this is that rule implemented.

---

## 3. Measures

**3.1 `Avg Monthly Std Hours L3M` is anchored to the last month with data.**
Not to `TODAY()`. Anchoring to today makes the forecast collapse in the days before
a month's upload arrives — which is exactly when a planner looks at it.

**3.2 `Projected PM Date` rounds months UP.**
A cell needing 1.2 months of running is due in the second month. Rounding down would
schedule a PM before the hours exist to justify it.

**3.3 `Breakdowns After PM (7d)` is derived from dates, not from `Linked_PM_WO`.**
That column is empty for all 88 breakdowns in the supplied data and is only
populated by Flow 6 going forward. A measure depending on it would read **zero** on
history and look reassuring — the worst possible failure mode for the one number
that says whether the PM is working. The measure pairs breakdowns to completed PMs
on the same cell by date instead, and works either way.

**3.4 The 7-day window is inclusive at both ends.**
A breakdown on the PM completion date itself counts (gap = 0). It is the strongest
possible evidence that the PM caused it.

**3.5 `NOT OK %` excludes `NA` answers.**
A check that did not apply was not a check. Including it inflates the denominator
and flatters the rate.

**3.6 `Repeat Finding Count` requires *consecutive* cycles.**
A check point failing in January and again in November is two independent findings;
one failing in two consecutive PMs was not fixed the first time. Cycle order comes
from `Fact_MachineTask.Completion_Date`, which is exactly one PM cycle per machine.

**3.7 `Availability %` uses production loss, not MTTR.**
Production loss includes waiting for a technician, waiting for a part and restarting
the line. Using MTTR makes availability look flattering and wrong, and nobody
questions it because it looks good.

**3.8 `Findings Raised per PM` is labelled as thoroughness.**
Higher is better. If it is ever presented as "who raises the most problems", people
stop reporting findings within a month, the number then looks excellent, and it
means nothing. The page label says so explicitly and should stay that way.

**3.9 Counts return 0, ratios return blank.**
A card should read "0 overdue"; an empty denominator should not draw a misleading
0%.

---

## 4. Power BI

**4.1 Import mode, not DirectQuery.** The lists are small and the report is read far
more often than the data changes. DirectQuery would put a SharePoint query on every
slicer click.

**4.2 `Dim_Date` covers 2025-04-01 to 2027-03-31** — two Indian financial years,
enough that a report opened today still has next year's forecast dates to land on.
Extend the `CALENDAR` range in `Dim_Date.tmdl` before April 2027.

**4.3 One active date relationship per fact.** Second dates that genuinely matter
(`Planned_End_Date`, `Actual_End_Date`, `Target_Date`, `Approved_Date`) are inactive
and reached with `USERELATIONSHIP`. Two active date paths would make every date
filter ambiguous.

**4.4 No bidirectional filters anywhere.** They would create ambiguous paths between
`Dim_Cell` and `Dim_Machine` through any fact carrying both keys.

**4.5 The info panel is a footnote, not a bookmark toggle.**
A footnote cannot be left switched off by whoever used the report last, and it
survives a Desktop version change that a bookmark's stored exploration state may
not. `README_PowerBI.md` documents the two-minute conversion to a toggled panel.
*Trade-off:* it uses 40 px of every page.

**4.6 Two things must be finished in Desktop** — the drillthrough field on page 5
and the transparent Gantt offset series on page 3. Neither can be expressed in the
file format. Both are documented in `README_PowerBI.md` and take under a minute.

**4.7 `Cum_Std_Hours_Since_PM` is a snapshot.** It has no time dimension, so summing
it across cells is meaningful and summing it across months is not. No visual in the
report does the latter.

---

## 5. SharePoint

**5.1 One list per table, no lookup columns.** Lookups create join complexity in
Power Query and delegation problems in Power Apps, and they buy nothing here because
every key is already a clean text ID.

**5.2 Versioning on, 50 major versions.** The version history is how you answer "why
did this counter go to zero on the 14th" when the audit trail is otherwise one
shared login.

**5.3 `5S / Housekeeping` is the choice value.** The dictionary abbreviates it to
`5S`; the supplied data uses the longer form. The data wins, because that is what
the CSVs load.

**5.4 `Frequency` allows Quarterly and Annual** even though the data only contains
`Monthly (per PM cycle)`. The dictionary says the column is reserved for a future
split, so the choice values exist ready.

**5.5 `Machine_Family` is text, not a choice.** 28 distinct values that will grow
with every new machine type. A choice column would need editing on every purchase.

**5.6 20 indexes maximum per list, and every filtered column is indexed.** Without
them, a list past 5,000 items throws the list view threshold error and the flow
reading it stops working — usually about eight months after go-live, with no warning.

---

## 6. QR labels

**6.1 Error correction level H (30%).** Shop-floor stickers get oil on them and get
half covered by a cable tie. A code that stops scanning after four months teaches
people the system is broken.

**6.2 Minimum 25 mm square.** Below that a mid-range Android camera struggles at the
distance a technician actually holds a phone, in the light a shop floor actually has.

**6.3 The Tamil line is omitted when no Tamil font is present**, rather than printed
as empty boxes. A row of boxes on a sticker looks broken and undermines confidence in
every other sticker on the floor.

**6.4 Tamil text contains no Latin characters.** A Tamil font has no Latin glyphs, so
an embedded "PM" renders as two boxes. The line reads
"தொடங்கும் முன் ஸ்கேன் செய்யவும்" — *scan before starting*.
**CONFIRM** the wording with a Tamil-speaking supervisor before printing 30 stickers.

**6.5 Label text is auto-fitted, never clipped.** Machine_ID is the one thing on the
sticker that must always be readable.

---

## 7. Power Apps (added at your request)

**7.1 The original brief said no Power Apps; you asked for it, so both paths are
built.** Path A (Forms + list views) and Path B (canvas app) write to identical
lists with identical column names, and the eleven flows do not care which produced
the row. Path A remains configured as the fallback for a phone that will not install
the app.

**7.2 Licensing is not assumed.** The app uses only the SharePoint and Office 365
Users connectors — no premium connector, no Dataverse, no custom connector.
**CONFIRM seeded Power Apps rights with your licensing owner before building.**
If the answer is no, Path A delivers the same system.

**7.3 The technician name is not remembered across sessions.** A shared handset would
otherwise attribute the next person's work to whoever used it last — worse than no
attribution, because it looks authoritative.

**7.4 Spare requests are blocked offline.** `Stock_At_Request` must be the real
number at the moment of asking; capturing it against a cached figure makes the
evidence worthless. Better to block with a clear reason than to record a number that
is quietly wrong.

**7.5 The app never resets a counter, creates a work order, or computes a cost.**
Those rules live in flows, in one place, where they can be tested. Duplicating a rule
into the app is how the two start disagreeing.

---

## 8. Open questions — **CONFIRM before go-live**

| # | Question | Default taken |
|---|---|---|
| 1 | Should cancelled work orders count against compliance? | Excluded |
| 2 | Should a skipped machine block cell closure? | No — it closes, flagged partial |
| 3 | Is `Actual_Std_Hours` an actual or a capacity figure? | Actual — proration is by calendar days |
| 4 | Is the Tamil label wording right? | "தொடங்கும் முன் ஸ்கேன் செய்யவும்" |
| 5 | Are seeded Power Apps rights available on your plan? | Assumed yes; Path A works if not |
| 6 | Who owns the eleven flows? | A service account, not a person |
| 7 | Retention on `Scan_Log` and `Checklist_Response`? | None — they will grow indefinitely |
| 8 | Is 4,000 hours right for every cell? | Held per cell in `PM_Trigger_Hours`, all set to 4,000 |

---

## 9. Verified against the supplied dummy data

Recompute at any time:

```bash
python tools/verify_measures.py --asof 2026-08-30
```

Every measure below was recomputed in Python independently of the DAX. **68
measures, none blank, none in error.** The three calculations the system's
credibility rests on are hand-worked below.

### 9.1 Hand-worked: `Breakdowns After PM (7d)`

**9 of 88 breakdowns (10.2%)** fell within 7 days of a completed PM on the same cell.

| BD_ID | Cell | Breakdown | PM completed | Gap |
|---|---|---|---|---|
| BD-3012 | CELL-03 | 2025-10-01 | 2025-09-30 | 1 day |
| BD-3034 | CELL-03 | 2025-10-05 | 2025-09-30 | 5 days |
| BD-3068 | CELL-04 | 2025-10-06 | 2025-10-03 | 3 days |
| BD-3072 | CELL-05 | 2025-10-19 | 2025-10-17 | 2 days |
| BD-3058 | CELL-07 | 2026-01-01 | 2025-12-30 | 2 days |
| BD-3007 | CELL-05 | 2026-02-12 | 2026-02-12 | 0 days |
| BD-3014 | CELL-07 | 2026-03-01 | 2026-02-22 | 7 days |
| BD-3049 | CELL-06 | 2026-04-23 | 2026-04-18 | 5 days |
| *(one further row)* | | | | |

BD-3007 at a gap of 0 is the strongest evidence in the set: the machine broke down
on the day its cell PM completed.

Read it as a **share**, not a count. A rising count during a period of rising PM
volume is expected; a rising share is the warning.

### 9.2 Hand-worked: `Projected PM Date`

`Hours to Next PM ÷ Avg Monthly Std Hours L3M` → months, rounded **up**, added to
today (2026-08-30). L3M window 2026-06 … 2026-08.

| Cell | Counter | Trigger | Remaining | L3M avg | Months | Projected | Calendar due | First |
|---|---:|---:|---:|---:|---:|---|---|---|
| CELL-01 | 980 | 4,000 | 3,020 | 715 | 4.23 | 2027-01-30 | 2026-08-29 | **calendar** |
| CELL-02 | 3,720 | 4,000 | 280 | 789 | 0.35 | 2026-09-30 | 2026-08-14 | **calendar** |
| CELL-03 | 980 | 4,000 | 3,020 | 758 | 3.98 | 2026-12-30 | 2026-11-26 | **calendar** |
| CELL-04 | 2,400 | 4,000 | 1,600 | 778 | 2.06 | 2026-11-30 | 2027-01-25 | hours |
| CELL-05 | 4,180 | 4,000 | 0 | 754 | 0.00 | 2026-08-30 | 2026-10-01 | **hours — overdue now** |
| CELL-06 | 2,980 | 4,000 | 1,020 | 853 | 1.20 | 2026-10-30 | 2027-02-08 | hours |
| CELL-07 | 1,650 | 4,000 | 2,350 | 768 | 3.06 | 2026-12-30 | 2027-01-22 | hours |
| CELL-08 | 3,450 | 4,000 | 550 | 716 | 0.77 | 2026-09-30 | 2027-01-23 | hours |

Three of eight cells are governed by the **calendar backstop**, not by hours. That is
the rule earning its keep: CELL-01 at 25% of its trigger would otherwise go
untouched for over a year.

### 9.3 Hand-worked: mid-month proration

CELL-05, month **2026-04**, reset on **2026-04-02**:

```
Actual_Std_Hours reported   = 780.0 h
days in month               = 30
day of reset                = 2
days after reset            = 30 − 2 = 28

posted to the NEW counter   = 780.0 × 28/30 = 728.00 h
discarded (old cycle)       = 780.0 − 728.00 =  52.00 h

check: 728.00 + 52.00 = 780.0 h    the month is fully accounted for
```

Without this rule the whole 780 h lands on the freshly zeroed counter and the cell
runs its next PM early — permanently, every cycle, getting worse each time.

### 9.4 All measures, recomputed

Recomputed at `--asof 2026-08-30`:

| Measure | Value | Unit |
|---|---:|---|
| `PM Due Count` | 48 |  |
| `PM Completed Count` | 43 |  |
| `PM Overdue Count` | 2 |  |
| `PM In Progress Count` | 2 |  |
| `PM Compliance %` | 0.8958 | % |
| `PM On-Time Count` | 21 |  |
| `PM On-Time %` | 0.4884 | % |
| `Schedule Adherence %` | 0.549 | % |
| `Avg PM Delay (Days)` | 0.5116 | days |
| `Calendar-Triggered PM %` | 0.25 | % |
| `Cum Std Hours` | 20,340 | h |
| `PM Trigger Hours` | 32,000 | h |
| `Hours to Next PM` | 11,660 | h |
| `Hours Utilisation %` | 0.6356 | % |
| `Avg Monthly Std Hours L3M (all cells)` | 6,131.7 | h/month |
| `Total Std Hours` | 74,619.7 | h |
| `Production Qty` | 13,465,232 |  |
| `Cells Due Soon Count` | 2 | cells |
| `Overdue Cells Count` | 3 | cells |
| `Machine Tasks Total` | 193 |  |
| `Machine Tasks Completed` | 168 |  |
| `Machine Tasks Pending` | 25 |  |
| `Cell Completion %` | 0.8705 | % |
| `Avg PM Duration (Hrs)` | 1.5571 | h |
| `Total PM Man-Hours` | 261.6 | h |
| `First-Pass PM %` | 0.2093 | % |
| `Expected PM Duration (Min)` | 6,962 | min |
| `PM Duration vs Expected %` | 2.2545 | % |
| `Machines Not Scanned` | 18 |  |
| `Open WO Ageing (Days)` | 9.4 | days |
| `Reset Not Applied Count` | 0 |  |
| `Checklist Items Checked` | 997 |  |
| `NOT OK Count` | 94 |  |
| `NOT OK %` | 0.0943 | % |
| `Safety-Critical NOT OK Count` | 15 |  |
| `Follow-Up Raised Count` | 39 |  |
| `Open Abnormalities` | 12 |  |
| `High Severity Open` | 3 |  |
| `Abnormality Ageing (Days)` | 55.5 | days |
| `Overdue Abnormalities` | 12 |  |
| `Repeat Finding Count` | 2 |  |
| `Breakdown Count` | 88 |  |
| `MTTR (Min)` | 172.7159 | min |
| `Avg Response Time (Min)` | 20.9659 | min |
| `Loading Hours` | 74,619.7 | h |
| `Downtime Hours` | 299.4833 | h |
| `MTBF (Hrs)` | 847.9511 | h |
| `Availability %` | 0.996 | % |
| `Breakdowns After PM (7d)` | 9 |  |
| `Breakdowns After PM %` | 0.1023 | % |
| `Repeat Breakdown Count` | 17 |  |
| `Open Breakdowns` | 0 |  |
| `Spare Cost` | 319,160 | INR |
| `Planned Spare Cost` | 146,970 | INR |
| `Unplanned Spare Cost` | 172,190 | INR |
| `Spare Cost per PM` | 3,417.907 | INR/PM |
| `Qty Replaced` | 128 |  |
| `Requests Pending Approval` | 12 |  |
| `Avg Approval Lead Time (Days)` | 1 | days |
| `Approved Not Issued Count` | 0 |  |
| `Stock Below Min Count` | 1 |  |
| `Stock Value (INR)` | 221,390 | INR |
| `Warranty Claims Flagged` | 15 |  |
| `PMs Completed by Tech (max)` | 34 | tasks |
| `Avg Task Duration by Tech` | 93.4286 | min |
| `Findings Raised per PM` | 0.5595 | findings/PM |
| `Active Technicians` | 6 |  |
| `Workload Imbalance` | 14 | tasks |

### 9.5 Sanity checks worth noting

- **`Reset Not Applied Count` = 0.** Every completed work order zeroed its counter —
  integrity rule 3 holds across all 43.
- **`PM Duration vs Expected %` = 2.25.** Tasks take about twice the checklist's
  expected time. In production, a figure well *below* 1.0 is the alarm — that is a
  checklist being signed rather than done.
- **`First-Pass PM %` = 20.9%.** Four in five PMs find something. That is a healthy
  number; a first-pass rate near 100% usually means nobody is looking.
- **`Availability %` = 99.6%** on dummy data. Realistic for a fuse plant with short
  stoppages, but check `Production_Loss_Min` is being captured honestly — if people
  record repair time instead, this number flatters.
- **`Schedule Adherence %` = 54.9%** against 51 committed plan rows, with 4 forecast
  rows correctly excluded.
