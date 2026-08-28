# 05 · Power Automate Flows

Six flows. Flow 2 is the important one — it owns the scheduling rule.

| # | Flow | Trigger | Owns |
|---|------|---------|------|
| 1 | Validate Standard Hours Upload | File created in `02 Standard Hours` | Rejecting bad uploads before they poison the ledger |
| 2 | **Monthly PM Scheduler** | Flow 1 succeeds, or manual, or 6th of month | The 4000-hour rule, the ledger, work order creation |
| 3 | Overdue Sweep | Daily 23:30 | Moving lapsed work orders to Overdue |
| 4 | Abnormality Escalation | Item created in `Abnormality_Log` | Getting High-severity items in front of a human |
| 5 | Spare Approval | Item created in `SparePart_Requests` | Routing approvals by value |
| 6 | Upload Reminder | 5th and 8th of month | Chasing a missing standard-hours file |

---

## Flow 1 · Validate Standard Hours Upload

**Trigger:** *When a file is created (properties only)* — library `Shared Documents`,
folder `02 Standard Hours`.

**Steps**

1. **Parse the file name.** Reject anything that does not match
   `Cell_Standard_Hours_YYYY_MM.xlsx`.

   ```
   FileMonth: concat(split(replace(triggerOutputs()?['body/{Name}'],
       'Cell_Standard_Hours_',''),'.')[0])          →  "2026_09"
   MonthKey:  replace(variables('FileMonth'), '_', '-')  →  "2026-09"
   ```

2. **List rows in the table** `tblStdHours` (Excel Online for Business).

3. **Validate.** Fail the run with a clear message on any of:

   | Check | Message |
   |-------|---------|
   | `MonthKey` in a row ≠ month in the file name | "Row month does not match the file name" |
   | A `CellID` not in `Cell_Master` | "Unknown cell: X" |
   | An active cell missing from the file | "Missing cell: X" |
   | `StdHours` blank, negative, or non-numeric | "Invalid StdHours for cell X" |
   | `StdHours` more than 3× the cell's `BaselineMonthlyStdHrs` | "Implausible value for cell X — confirm before proceeding" |
   | The month already has ledger rows | branch to **restatement** (see Flow 2) |

4. **On failure:** move the file to `02 Standard Hours/_Rejected/`, email the
   uploader with the specific failed check, stop. Do not half-process a bad file.

5. **On success:** call Flow 2.

The implausibility check is the one people skip and then regret. A cell that
normally earns 900 hours suddenly showing 9 000 because someone typed hours into
the minutes column will trip four PMs that nobody needs.

---

## Flow 2 · Monthly PM Scheduler

**Trigger:** child flow called by Flow 1; also a manual trigger for back-load and
restatement; also a safety-net recurrence on the 6th.

**Inputs:** `MonthKey`, `Mode` (`Normal` | `Backload` | `Restate`).

### Step 1 — Load state

- `Get items` from `Cell_Master` where `Active eq 'Yes'`
- `Get items` from `PM_Hour_Ledger` for the month **before** `MonthKey`
- `Get items` from `PM_WorkOrders` where `Status eq 'Completed'`, to find each
  cell's last PM date

### Step 2 — For each cell, apply the rule

```
Opening    = coalesce(previous ledger row .CarryOverAfterPM, previous .ClosingStdHrs, 0)
Added      = StdHours for this cell and month from the upload
Closing    = add(Opening, Added)

Threshold  = coalesce(cell.PMIntervalStdHrs, config.DefaultPMIntervalStdHrs)   // 4000
Backstop   = coalesce(cell.CalendarBackstopMonths, 12)                          // 12

MonthsSince   = dateDifference(LastPMDate, monthEnd) in months
HoursDue      = greaterOrEquals(Closing, Threshold)
CalendarDue   = greaterOrEquals(MonthsSince, Backstop)
Triggered     = or(HoursDue, CalendarDue)

CarryOver     = if(Triggered, max(0, sub(Closing, Threshold)), Closing)
TriggerType   = if(HoursDue, 'Std Hours', 'Calendar Backstop')
```

### Step 3 — Write the ledger row

One row into `PM_Hour_Ledger` per cell per month, always — triggered or not. The
ledger is the audit trail; a month with no row is a gap nobody can explain later.

### Step 4 — Raise work orders where triggered

For each triggered cell:

1. `CycleID` = `<CellID>-C<nn>`, where `nn` is `count(previous cycles) + 1`.
2. `Get items` from `Machine_Master` where `CellID eq '<cell>' and Active eq 'Yes'`.
3. Build the month's working days (exclude weekends and the holiday list in
   `PM_Config`).
4. Spread machines across those days: machine *j* of *n* gets working day
   `floor(len(days) * (j+1) / (n+1))`.
5. Assign a technician: round-robin over `Technician_Master` where
   `PrimaryArea eq cell.Area and Active eq 'Yes'`, skipping anyone whose assigned
   `PMStdMinutes` for that day already exceeds `DailyCapacityMin`.
6. `Create item` in `PM_WorkOrders`:

   | Field | Value |
   |-------|-------|
   | `WOID` | `WO-` + 5-digit sequence |
   | `CycleID`, `CellID`, `MachineID` | from above |
   | `PMType` | `PM-4000` |
   | `TriggerType`, `TriggerStdHrs` | from step 2 — stamped so the reason survives |
   | `PlanMonth` | `MonthKey` |
   | `PlannedDate` | from step 4 |
   | `DueDate` | last calendar day of `MonthKey` |
   | `AssignedTechID` | from step 5 |
   | `Status` | `Scheduled` |
   | `ChecklistTotalTasks` | count of tasks for the machine's `ChecklistID` |
   | `StdMinutes` | `Machine_Master.PMStdMinutes` |

7. Notify each technician: an adaptive card in Teams listing their new work
   orders, with a deep link to the app.

### Step 5 — Mode handling

**`Backload`** — iterate every month in
`02 Standard Hours/_History/Cell_Standard_Hours_History.xlsx` oldest-first,
running steps 2–3 for each. **Skip step 4**: do not raise work orders for historical
cycles that were done on paper. Instead set each cell's last-PM date from the
history you have. Run this once, at go-live.

**`Restate`** — a corrected file for a month that already has ledger rows:

1. Delete `PM_Hour_Ledger` rows for that cell from `MonthKey` forward.
2. Replay steps 2–4 for each month, oldest first, to today.
3. Work orders already `Completed` are left untouched — they happened.
4. Work orders still `Scheduled` for a cycle that no longer trips are set to
   `Deferred` with `Remarks = "Cancelled — cycle removed by restatement of <MonthKey>"`.
5. Email the Maintenance Head a before/after summary. A restatement that silently
   changes the plan is how people stop trusting the system.

### Step 6 — Forecast rows

After the actuals, project the next 12 months into `PM_Hour_Ledger` with
`Scenario = 'Forecast'`, using the trailing 3-month run rate. Delete and rewrite
these every run — they are a projection, not a record.

---

## Flow 3 · Overdue Sweep

Daily at 23:30.

```
Get items: PM_WorkOrders
  where Status in ('Scheduled','In Progress')
    and DueDate lt '@{addDays(utcNow(), -1 * config.OverdueGraceDays)}'
Update each: Status = 'Overdue'
```

Then post one digest to the maintenance Teams channel — the count by cell and the
five oldest. One message a day, not one per work order; a channel nobody reads is
worse than no channel.

---

## Flow 4 · Abnormality Escalation

Trigger: item created in `Abnormality_Log`.

- `Severity = High` → email + Teams message to the Maintenance Head immediately,
  with the photo attached.
- `EscalationRequired = Yes` and still Open after 24 h → escalate to the Plant Head.
- Weekly Monday 08:00 digest of everything open past 30 days, to the Maintenance
  Head and the area supervisors.

---

## Flow 5 · Spare Approval

Trigger: item created in `SparePart_Requests`.

```
if TotalCostINR <= config.SpareApprovalLimitINR   → approver = Maintenance Head
else                                              → approver = Plant Head
if Urgency = 'Emergency'                          → also notify Stores immediately
```

Uses the **Approvals** connector so the decision is auditable. On approve, set
`Status = 'Approved'`, `ApprovedDate`, `ApprovedBy`. On reject, `Status = 'Rejected'`
and require a `RejectionReason`. Stores sets `Issued` when the part physically
leaves the counter — not the flow, a person.

---

## Flow 6 · Upload Reminder

5th of the month, 09:00: if no `Cell_Standard_Hours_YYYY_MM.xlsx` exists for the
previous month, email Production Planning with the template attached.
Repeat on the 8th, copying the Plant Head.

This is a two-line flow that protects the entire system. Without the upload,
counters do not move, nothing is ever scheduled, and the dashboard quietly shows
green while no maintenance is being planned at all.

---

## Error handling, for all flows

- Configure run-after on a **Scope** so any failure lands in one place.
- Failure action: email the flow owner with the run URL and the failing step.
- Never let a flow fail silently. Turn on failure notifications in the flow's
  settings for every one of these.
- `PM_Hour_Ledger` and `PM_WorkOrders` writes should be idempotent: check for an
  existing row for the same `CellID` + `MonthKey` (or `CycleID` + `MachineID`)
  before creating. A retried run must not double-schedule a cell.
