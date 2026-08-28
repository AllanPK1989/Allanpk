# 03 · The PM Scheduling Engine

This is the rule everything else serves. Read this page before changing anything.

## The rule, in one paragraph

Production standard hours accrue **per cell**, month by month, from the monthly
Excel upload. Each cell carries a running counter. When that counter reaches the
cell's threshold — **4000 standard hours** by default — the **whole cell** is
scheduled for PM: one work order per active machine in the cell. Whatever hours
overshoot the threshold **carry forward** into the next cycle, so a cell running
hot never loses hours. Separately, if a cell has gone **12 months** without a PM
it is scheduled anyway, whatever the counter says.

## The arithmetic

For cell *c* in month *m*:

```
opening(c, m)  = carry_over from the previous cycle, else closing(c, m-1)
closing(c, m)  = opening(c, m) + std_hours(c, m)

hours_due      = closing(c, m) >= threshold(c)
calendar_due   = months_since_last_pm(c, m) >= backstop(c)
pm_triggered   = hours_due OR calendar_due

carry_over(c)  = MAX(0, closing(c, m) - threshold(c))     when triggered
trigger_type   = "Std Hours" if hours_due else "Calendar Backstop"
```

`threshold(c)` comes from `Cell_Master.PMIntervalStdHrs`, falling back to
`PM_Config.DefaultPMIntervalStdHrs` (4000).
`backstop(c)` comes from `Cell_Master.CalendarBackstopMonths` (12).

Note that `carry_over` uses the same formula for both trigger types. A
calendar-triggered PM happens with the counter below the threshold, so the
subtraction floors at zero and the counter simply restarts. That is intentional:
the machine has just been serviced, so the clock starts again.

### Worked example — CELL-01, threshold 4000

| Month | Opening | Uploaded | Closing | Triggered | Type | Carry over |
|-------|--------:|---------:|--------:|-----------|------|-----------:|
| 2026-01 | 1 240 | 1 180 | 2 420 | No | | 2 420 |
| 2026-02 | 2 420 | 1 095 | 3 515 | No | | 3 515 |
| 2026-03 | 3 515 | 1 260 | 4 775 | **Yes** | Std Hours | 775 |
| 2026-04 | 775 | 980 | 1 755 | No | | 1 755 |

The 775 hours the cell earned past the threshold in March are not thrown away —
they open April's counter. Over a year this is the difference between roughly
three PM cycles and four on a hard-running cell.

### Worked example — CELL-08, low utilisation

| Month | Opening | Uploaded | Closing | Months since last PM | Triggered | Type |
|-------|--------:|---------:|--------:|---------------------:|-----------|------|
| 2026-06 | 3 180 | 320 | 3 500 | 10 | No | |
| 2026-07 | 3 500 | 295 | 3 795 | 11 | No | |
| 2026-08 | 3 795 | 310 | 4 105 | 12 | **Yes** | Std Hours |

Here the hour threshold happened to land the same month as the backstop. When
both fire together the ledger records **Std Hours**, because that is the
condition that would have fired first on a normal run-rate. A press shop running
at 250 h/month would trip the backstop first and the ledger would say so.

## Forecasting

The plan needs a forward view, and the only honest basis for one is the recent
run rate:

```
run_rate(c)        = mean of the last 3 months of uploaded std hours
months_to_pm(c)    = CEILING( (threshold - counter) / run_rate )
hours_date(c)      = end of month( latest_ledger_month + months_to_pm )
calendar_date(c)   = end of month( last_pm_date + backstop_months )
projected_date(c)  = MIN( hours_date, calendar_date )
```

`Projected Trigger Reason` tells you which of the two won. When a cell shows
"Calendar backstop", that is a cell whose utilisation has dropped — worth a
conversation with Production before you spend maintenance hours on it.

Three months is a deliberate choice: one month is noise, twelve months lags a
real change in loading. It is configurable in `PM_Config.ForecastRunRateMonths`.

## Where the rule lives — three times

The same arithmetic is implemented in three places. If you change the rule,
change all three or the dashboard will disagree with the work orders.

| Where | File | Role |
|-------|------|------|
| **Scheduler flow** | `docs/05-power-automate-flows.md` → Flow 2 | **Authoritative.** Creates the ledger rows and the work orders. |
| Power BI | `Fact_HourLedger` + the `01 Standard Hours` measures | Displays and forecasts. Never writes. |
| Reference implementation | `scripts/pm_core.py` → `run_pm_engine()` | Generates the dummy data and is the executable spec. Test rule changes here first. |

## Work order generation

When a cell trips in month *m*:

1. One work order per row in `Machine_Master` where `CellID = c` and `Active = Yes`.
2. `PlanMonth = m`, `DueDate = last calendar day of m`.
3. `PlannedDate` spread across the working days of the month, ordered by machine,
   so five machines in a cell do not all land on the 1st.
4. `AssignedTechID` round-robin across technicians whose `PrimaryArea` matches the
   cell's `Area`, respecting `DailyCapacityMin` against `Machine_Master.PMStdMinutes`.
5. `TriggerType` and `TriggerStdHrs` stamped onto every work order, so months later
   anyone can see exactly why this job existed.
6. `CycleID = <CellID>-C<nn>` groups the whole cell's work orders into one cycle.

## Deliberate design decisions worth knowing

**The whole cell goes together, not machine by machine.** This is what you asked
for and it is also right for a cell: you are taking a production line down, and
taking it down five separate times to service five machines costs more production
than it saves maintenance. The trade-off is that a lightly used machine in a
hard-running cell gets serviced more often than it strictly needs. If that starts
to hurt, `docs/10-open-decisions.md` describes the per-machine weighting variant.

**Hours accrue even when nobody does anything.** If Production stops uploading,
counters freeze and nothing is ever scheduled. This is the single most likely
failure mode of the whole system, which is why `Missing Std Hours Rows` is a KPI
on the Data Quality page rather than a footnote.

**A restated month reprocesses forward.** Uploading a corrected file for June does
not just fix June — every carry-over after June changes. The flow deletes ledger
rows from that month forward and replays. Work orders already *completed* are left
alone; work orders still Scheduled for a cycle that no longer trips are cancelled
with a reason.

**Deferred is not the same as overdue.** Deferred is a decision, with an approver
and a reason. Overdue is a failure. Keeping them apart is the difference between
a compliance number you can act on and one people argue about.
