# Power Automate expressions — copy-paste ready

Every expression the nine flows need, written out in full. Paste into the
**Expression** tab of the dynamic-content picker, not into the plain text box.

A note on how to read these: Power Automate action names in expressions use
underscores where the designer shows spaces. An action displayed as
`Get items pending tasks` is referenced as `body('Get_items_pending_tasks')`.
Rename an action and every expression referencing it breaks silently — the flow
saves fine and fails at runtime. Rename first, write expressions after.

> **What changed in the simplified build.** Sixteen sections, down from nineteen.
> Every expression that existed only to *store* a number the report can work out
> for itself has gone: breakdown response time and MTTR, spare line totals, the
> rolling three-month average, the breakdown-to-PM linkage, the approval lead
> time and the corrective work order. What is left either decides something at
> the moment it runs, or writes a fact nothing else can reconstruct.

---

## 1. The all-complete test (Flow 5 — the reset)

This is the single most important expression in the system. It decides whether a
cell's counter goes back to zero.

```
if(equals(length(body('Get_items_pending_tasks')?['value']), 0), true, false)
```

Used in a **Condition** where the left side is the expression above and the right
side is `true`.

`Get items pending tasks` must be a **Get items** action on `PM_Machine_Task` with
this OData filter:

```
WO_No eq '@{variables('varWO')}' and Task_Status ne 'Completed' and Task_Status ne 'Skipped'
```

Two things about that filter:

- **`ne 'Skipped'` is deliberate.** A skipped machine still lets the cell close, but
  the work order is flagged partial. Leaving Skipped out of the filter would hold
  a cell open forever behind one machine that is under overhaul.
- Both `WO_No` and `Task_Status` are indexed by `provision_lists.ps1`. Without
  those indexes this query stops working the day the list passes 5,000 items.

The simpler form works too and reads better in a condition:

```
empty(body('Get_items_pending_tasks')?['value'])
```

---

## 2. Mid-month proration (Flow 1 — the monthly import)

If a cell's PM reset fell inside the month being uploaded, only the portion of the
month's hours **after** the reset is posted to the new counter.

**Prorated by WORKING days, not calendar days.** `Actual_Std_Hours` is a capacity
figure, and capacity accrues on the days the plant runs. A reset landing next to a
run of Sundays would otherwise post hours the plant was never open to earn.

```
posted = Actual_Std_Hours × (working days after the reset) ÷ (working days in the month)
```

The two working-day counts come from the `Plant_Calendar` list, not from date
arithmetic. That is deliberate: no expression can know that the plant shut for
Pongal, and a hard-coded weekday rule is wrong for four days every January.

### Where the reset date comes from

**`Cell_Master.Last_PM_Date`** — read from the cell row the loop has already
fetched, *not* from the Excel row:

```
first(body('Get_item_cell')?['value'])?['Last_PM_Date']
```

> The work order's separate `Reset_Date` column is gone. It always held the same
> instant as `Last_PM_Date`, written by the same action in the same second, so
> the two could never legitimately disagree — and one date that cannot disagree
> with itself is one date. `Last_PM_Date` on the cell is also the more direct
> reading of what proration actually needs: *when was this counter last zeroed.*

### Step 1 — working days in the month

**Get items** on `Plant_Calendar`, rename **`Get items working days month`**:

```
Is_Working_Day eq 1 and Calendar_Date ge '@{variables('varMonthStart')}' and Calendar_Date le '@{variables('varMonthEnd')}'
```

```
varWorkingDaysInMonth : length(body('Get_items_working_days_month')?['value'])
```

### Step 2 — working days after the reset

**Get items** on `Plant_Calendar`, rename **`Get items working days after reset`**:

```
Is_Working_Day eq 1 and Calendar_Date gt '@{variables('varResetDate')}' and Calendar_Date le '@{variables('varMonthEnd')}'
```

`gt`, not `ge`. The reset day itself belongs to the **old** cycle — the PM happened
on it.

```
varWorkingDaysAfterReset : length(body('Get_items_working_days_after_reset')?['value'])
```

### Step 3 — the proration

```
if(
  equals(variables('varDayOfReset'), 0),
  float(items('Apply_to_each_row')?['Actual_Std_Hours']),
  mul(
    float(items('Apply_to_each_row')?['Actual_Std_Hours']),
    div(
      float(variables('varWorkingDaysAfterReset')),
      float(variables('varWorkingDaysInMonth'))
    )
  )
)
```

The `if` short-circuits the common case: no reset in this month means the whole
month's hours post, with no division and no chance of a divide-by-zero.

### The supporting variables

`varUploadMonth` — `YYYY-MM` read from the file's first data row:

```
first(body('List_rows_present_in_a_table')?['value'])?['Upload_Month']
```

`varMonthStart`:

```
concat(variables('varUploadMonth'), '-01')
```

`varMonthEnd`:

```
formatDateTime(
  addDays(
    startOfMonth(addToTime(concat(variables('varUploadMonth'), '-01T00:00:00Z'), 1, 'Month')),
    -1
  ),
  'yyyy-MM-dd'
)
```

That reads as: first of the upload month, add a month, step back a day. February
gives 28 or 29 correctly with no leap-year test anywhere.

`varDayOfReset` — the day of the month the reset happened, or `0` if it did not fall
in this month. Set inside the loop, **after** `Get item cell` has run:

```
if(
  and(
    not(empty(first(body('Get_item_cell')?['value'])?['Last_PM_Date'])),
    equals(
      formatDateTime(first(body('Get_item_cell')?['value'])?['Last_PM_Date'], 'yyyy-MM'),
      variables('varUploadMonth')
    )
  ),
  int(dayOfMonth(first(body('Get_item_cell')?['value'])?['Last_PM_Date'])),
  0
)
```

`varResetDate` — the reset date as `yyyy-MM-dd` for the OData filter:

```
if(
  equals(variables('varDayOfReset'), 0),
  variables('varMonthStart'),
  formatDateTime(first(body('Get_item_cell')?['value'])?['Last_PM_Date'], 'yyyy-MM-dd')
)
```

> **Order matters.** Both of these read the cell row, so `Get item cell` must be the
> first action inside the row loop. Set them before it and they read null, the
> proration short-circuits, and a mid-month reset silently posts the whole month.

### Guard: no working days on the calendar

If `Plant_Calendar` has not been maintained for this month, the divisor is zero and
the run fails at 2 a.m. Test before the loop:

```
equals(variables('varWorkingDaysInMonth'), 0)
```

If true, email the planner — *"the plant calendar has no working days for
2026-04; the monthly import cannot prorate"* — and **Terminate → Failed**.

`prepare_sharepoint_data.py` runs the same check at load time, so this should never
fire in practice. It is here because "should never happen" is not a control.

### Worked example (verified)

CELL-05 reported **780.0 h** for **2026-04**, and its PM reset landed on
**2026-04-02** (a Thursday).

```
April 2026            = 30 calendar days, 4 Sundays  ->  26 working days
reset 2026-04-02, working days strictly after       ->  24

posted to the NEW counter = 780.0 × 24/26 = 720.00 h
discarded (old cycle)     = 780.0 − 720.00 =  60.00 h
```

720.00 + 60.00 = 780.0. The month is fully accounted for — nothing lost, nothing
double-counted.

> For comparison, prorating by **calendar** days would post 728.00 h — 8 hours the
> plant was closed for. Small on one reset; it compounds every cycle, and always in
> the same direction for a cell whose PM habitually falls early in the month.

**Why this rule exists at all.** Without it the whole month's hours land on the
freshly zeroed counter, and every cell that resets mid-month runs its next PM
early — permanently, every cycle, getting worse each time.

### If you decide std hours are an EARNED figure after all

If `Actual_Std_Hours` turns out to be earned hours (standard time × units produced)
rather than capacity, switch back to calendar days: the shift pattern is already
inside an earned figure, and prorating by working days would apply it twice. The
change is one expression — replace the two `Get items` counts with:

```
mul(
  float(items('Apply_to_each_row')?['Actual_Std_Hours']),
  div(
    float(sub(int(variables('varDaysInMonth')), int(variables('varDayOfReset')))),
    float(variables('varDaysInMonth'))
  )
)
```

and set `varDaysInMonth` to `int(dayOfMonth(variables('varMonthEnd')))`.

---

## 3. Adding to the running counter (Flow 1)

```
add(
  float(coalesce(first(body('Get_item_cell')?['value'])?['Cum_Std_Hours_Since_PM'], 0)),
  float(variables('varProratedHours'))
)
```

The counter comes from the **cell row**, not from the Excel row — the upload file
carries hours, not counters.

`coalesce` matters: a newly created cell has a null counter, not a zero, and
`add(null, 12)` fails the run.

---

## 4. Duplicate-upload guard (Flow 1)

Reject the file if this month already exists. **Get items** on `StdHours_Monthly`:

```
Upload_Month eq '@{variables('varUploadMonth')}'
```

Then a Condition on:

```
greater(length(body('Get_items_existing_month')?['value']), 0)
```

If true, move the file to `StdHours_Inbox/Rejected/`, email the uploader, and
**terminate the run as Failed**. Not Succeeded — a silently rejected upload looks
identical to a successful one on the run history, and nobody notices for a month.

---

## 5. Unmatched Cell_ID guard (Flow 1)

Validate **before** writing anything. One bad row stops the whole file rather than
importing half of it — a half-imported month is far harder to unpick than a
rejected one.

A **Select** action projects `Cell_ID` out of the cell master into an array
variable `varValidCells`:

```
item()?['Cell_ID']
```

Then, in a validation loop over the Excel rows:

```
contains(variables('varValidCells'), items('Apply_to_each_validate')?['Cell_ID'])
```

Append any row where that is `false` to `varBadRows`, and after the loop:

```
greater(length(variables('varBadRows')), 0)
```

If true, email the bad rows to the uploader, move the file to `Rejected/`, and
**Terminate → Failed**.

---

## 6. The PM trigger (Flow 2)

**Get items** on `Cell_Master`:

```
Active eq 1 and (Cum_Std_Hours_Since_PM ge 4000 or Last_PM_Date le '@{addDays(utcNow(),-183)}')
```

Note: 4,000 appears here as an OData literal because SharePoint's filter cannot
compare one column to another. The value is still authoritative in
`PM_Trigger_Hours` — re-check it inside the loop so a retuned cell behaves
correctly:

```
or(
  greaterOrEquals(
    float(coalesce(items('Apply_to_each_cell')?['Cum_Std_Hours_Since_PM'], 0)),
    float(coalesce(items('Apply_to_each_cell')?['PM_Trigger_Hours'], 4000))
  ),
  lessOrEquals(
    ticks(coalesce(items('Apply_to_each_cell')?['Last_PM_Date'], '1900-01-01')),
    ticks(addDays(utcNow(), mul(-30, int(coalesce(items('Apply_to_each_cell')?['Calendar_Backstop_Months'], 6)))))
  )
)
```

183 days is six months at 30.5 days. Use `addDays(utcNow(), -183)` in the OData
filter (which needs a literal) and the per-cell month arithmetic above inside the
loop (which does not).

### Does an open work order already exist?

```
empty(body('Get_items_open_wo')?['value'])
```

with the filter:

```
Cell_ID eq '@{items('Apply_to_each_cell')?['Cell_ID']}' and WO_Status ne 'Completed' and WO_Status ne 'Cancelled'
```

Without this test the flow raises a duplicate work order every single morning
until somebody closes the first one.

> This test is also the reason the old corrective-work-order flow had to go. It
> created `PM_WorkOrder` rows of its own, and every one of them looked to this
> filter exactly like an open PM — so an unclosed corrective job on a cell would
> have suppressed that cell's real 4,000-hour trigger indefinitely, with nothing
> anywhere reporting that it had.

### Work order number

```
concat('WO-', formatDateTime(utcNow(),'yyyyMMdd'), '-', items('Apply_to_each_cell')?['Cell_ID'])
```

Deterministic on purpose: if the flow is re-run on the same day for the same cell
the number collides visibly instead of quietly creating a second work order.

### Trigger type

```
if(
  greaterOrEquals(
    float(coalesce(items('Apply_to_each_cell')?['Cum_Std_Hours_Since_PM'], 0)),
    float(coalesce(items('Apply_to_each_cell')?['PM_Trigger_Hours'], 4000))
  ),
  'Std Hours',
  'Calendar Backstop'
)
```

### Priority, seeded from criticality and how far overdue

```
if(
  or(
    equals(items('Apply_to_each_cell')?['Criticality'], 'A'),
    greater(float(coalesce(items('Apply_to_each_cell')?['Cum_Std_Hours_Since_PM'],0)), 4200)
  ),
  'High',
  if(equals(items('Apply_to_each_cell')?['Criticality'], 'B'), 'Medium', 'Low')
)
```

### Planned dates

```
Planned_End_Date : addDays(utcNow(), 14)
Planned_Month    : formatDateTime(addDays(utcNow(), 7), 'yyyy-MM')
```

> There is no planned **start** date any more. On-time performance was only ever
> measured against `Planned_End_Date`, and a second date that nothing reads is a
> second date somebody has to keep truthful.

### Machine-count cross-check

After creating the tasks, compare what was created against what the cell declares:

```
equals(
  length(body('Get_items_active_machines')?['value']),
  int(coalesce(items('Apply_to_each_cell')?['Machine_Count'], 0))
)
```

If false, still create the work order but send an alert. A mismatch means a machine
was deactivated or missed, and a short work order will close early and reset a
counter it should not have.

---

## 7. Identifiers

```
Task_ID     : concat('TSK-', variables('varWO'), '-', items('Apply_to_each_machine')?['Machine_ID'])
Response_ID : concat('CR-', formatDateTime(utcNow(),'yyyyMMddHHmmss'), '-', triggerOutputs()?['body/Machine_ID'])
BD_ID       : concat('BD-', formatDateTime(utcNow(),'yyyyMMddHHmmss'))
Repl_ID     : concat('RPL-', formatDateTime(utcNow(),'yyyyMMddHHmmss'))
Abn_ID      : concat('ABN-', formatDateTime(utcNow(),'yyyyMMddHHmmss'))
Plan_ID     : concat('PLN-', variables('varPlanMonth'), '-', items('Apply_to_each_cell')?['Cell_ID'])
```

`Task_ID` is deterministic so a re-run cannot create two tasks for the same machine
on the same work order. The timestamped ones carry a second's resolution, which is
ample for submissions a human makes by hand.

---

## 8. Elapsed minutes on a checklist submission (Flow 4)

The task's own duration is no longer stored — the report subtracts `Scan_Start_Time`
from `Scan_End_Time` on every refresh and always agrees with the two timestamps,
which a stored third number could not promise.

The flow still works the figure out **in flight**, for one purpose: deciding whether
a checklist was closed implausibly fast.

```
div(
  sub(
    ticks(utcNow()),
    ticks(coalesce(first(body('Get_items_task')?['value'])?['Scan_Start_Time'], utcNow()))
  ),
  600000000
)
```

600,000,000 is the number of 100-nanosecond ticks in a minute. `coalesce` guards
the case where a checklist is submitted without a scan-in — which happens, and
should produce a duration of 0 rather than failing the run.

Compare it against the checklist's own expected time:

```
less(
  variables('varElapsedMin'),
  mul(0.3, float(variables('varExpectedTotalMin')))
)
```

A 45-minute checklist closed in 4 minutes is a pencil-whipped PM, and this is the
test that catches it.

---

## 9. Counting NOT OK answers on a checklist submission (Flow 4)

A Microsoft Form returns one field per question. Build an array of the results and
count:

```
length(
  filter(
    variables('varChecklistResults'),
    equals(item()?['Result'], 'NOT OK')
  )
)
```

Safety-critical findings, which block the task from closing regardless of the
severity anyone chose:

```
length(
  filter(
    variables('varChecklistResults'),
    and(
      equals(item()?['Result'], 'NOT OK'),
      equals(item()?['Safety_Critical'], true)
    )
  )
)
```

Then:

```
if(greater(variables('varSafetyCriticalCount'), 0), 'In Progress', 'Completed')
```

A safety-critical NOT OK leaves the task **In Progress**, so the cell cannot close
and the counter cannot reset until somebody deals with it.

> Both counts are used **inside this run** — one to decide the task status, one to
> address the alert — and neither is written to the task. The findings themselves
> are on the `Checklist_Response` rows, and counting rows is what a report is for.

---

## 10. Counter reset (Flow 5)

Three fields, **one** Update item action. Splitting them across two actions creates
a window where a failure leaves a zeroed counter with no `Last_PM_Date` — and
nothing downstream can tell that apart from a genuine reset.

```
Cum_Std_Hours_Since_PM    : 0
Last_PM_Date              : utcNow()
Next_PM_Due_Date_Calendar : addToTime(utcNow(), int(coalesce(first(body('Get_item_cell')?['value'])?['Calendar_Backstop_Months'], 6)), 'Month')
```

> It used to be five fields. `Last_PM_WO_No` is gone — SharePoint's own version
> history on the cell already answers *"why did this counter go to zero"*, and it
> answers it for every change, not just the last one. `Reset_Date` is gone with it,
> for the reason in §2.

On the work order, in its own Update item action:

```
WO_Status     : Completed
Reset_Applied : true
```

`Machines_Completed`, which drives the live completion bar, is updated on **every**
task completion rather than only at the end:

```
length(body('Get_items_completed_tasks')?['value'])
```

> The work order no longer stores its own start time, end time or total duration.
> All three are rollups of the task rows underneath it, and the model computes
> them at refresh: earliest `Scan_Start_Time`, latest `Scan_End_Time`, summed
> durations. That removes three writes from the most safety-critical flow in the
> system and removes any chance of a work order disagreeing with its own tasks.

---

## 11. Criticality-A alert test (Flow 6)

```
equals(first(body('Get_item_machine')?['value'])?['Criticality'], 'A')
```

---

## 12. Spare stock (Flow 7)

```
Unit_Cost_INR : float(first(body('Get_item_spare')?['value'])?['Unit_Cost_INR'])
Current_Stock : sub(int(first(body('Get_item_spare')?['value'])?['Current_Stock']), int(triggerOutputs()?['body/Qty_Used']))
```

Unit cost is **copied onto the replacement row** at the time of use, not looked up
at report time, so a price rise does not retrospectively rewrite last year's
maintenance cost. The line total is not stored — quantity times unit cost is
multiplication the report can do, and a stored product is a third number that can
disagree with the two it came from.

Below-minimum alert:

```
lessOrEquals(
  sub(int(first(body('Get_item_spare')?['value'])?['Current_Stock']), int(triggerOutputs()?['body/Qty_Used'])),
  int(first(body('Get_item_spare')?['value'])?['Min_Stock'])
)
```

Guard against negative stock — it means the physical count was already wrong:

```
if(
  less(sub(int(first(body('Get_item_spare')?['value'])?['Current_Stock']), int(triggerOutputs()?['body/Qty_Used'])), 0),
  0,
  sub(int(first(body('Get_item_spare')?['value'])?['Current_Stock']), int(triggerOutputs()?['body/Qty_Used']))
)
```

Send the alert either way — clamping the number quietly would hide a real stores
problem.

---

## 13. High-severity escalation and the 24-hour reminder (Flow 8)

```
equals(triggerOutputs()?['body/Severity'], 'High')
```

The follow-up uses a **Delay until**:

```
addHours(utcNow(), 24)
```

then re-reads the item and only sends if it is still open. This one is a **Get
item** by ID (the ID comes straight from the Create item action), so its body is the
item itself rather than a `value` array:

```
not(equals(body('Get_item_abnormality')?['Status'], 'Closed'))
```

Re-reading is the whole point. A reminder that fires regardless of whether the
problem was fixed teaches people to ignore reminders.

---

## 14. Daily digest (Flow 9)

Overdue cells:

```
Active eq 1 and (Cum_Std_Hours_Since_PM ge 4000 or Next_PM_Due_Date_Calendar le '@{utcNow()}')
```

Open work orders with their completion percentage:

```
WO_Status ne 'Completed' and WO_Status ne 'Cancelled'
```

```
div(
  mul(float(item()?['Machines_Completed']), 100),
  if(equals(int(item()?['Machines_In_Scope']), 0), 1, float(item()?['Machines_In_Scope']))
)
```

Machines not yet scanned:

```
Task_Status eq 'Pending'
```

High-severity abnormalities past their target date:

```
Status ne 'Closed' and Severity eq 'High' and Target_Date lt '@{utcNow()}'
```

Completed work orders where the reset never fired — a flow failure that would
otherwise go unnoticed:

```
WO_Status eq 'Completed' and Reset_Applied eq 0
```

Send when there is something outstanding **or** it is Monday, so the digest keeps
meaning something without silence becoming ambiguous:

```
or(
  equals(
    dayOfWeek(convertFromUtc(utcNow(), 'India Standard Time')),
    1
  ),
  greater(
    add(add(add(add(
      length(body('Get_items_overdue_cells')?['value']),
      length(body('Get_items_open_wo')?['value'])),
      length(body('Get_items_not_scanned')?['value'])),
      length(body('Get_items_overdue_abn')?['value'])),
      length(body('Get_items_reset_failures')?['value'])
    ),
    0
  )
)
```

`dayOfWeek` returns 0 for Sunday, so Monday is `1`. Convert to IST first: the flow
fires at 06:30 IST, which is 01:00 UTC the same day, and testing the UTC day-of-week
directly would work by luck rather than by design — and stop working the moment
somebody reschedules the flow an hour earlier.

Note the fifth count. `Get_items_reset_failures` was in the digest's sections but
missing from this test, so a run where the *only* problem was a completed work order
that never reset its counter would have been silently skipped — which is precisely
the failure the section exists to surface.

To vary the body on a clean Monday, reuse the same five-way count on its own:

```
greater(
  add(add(add(add(
    length(body('Get_items_overdue_cells')?['value']),
    length(body('Get_items_open_wo')?['value'])),
    length(body('Get_items_not_scanned')?['value'])),
    length(body('Get_items_overdue_abn')?['value'])),
    length(body('Get_items_reset_failures')?['value'])
  ),
  0
)
```

True → the full digest with its tables. False → the one-line healthy message.

**Why the heartbeat exists at all.** The flows run on one individual's connections.
Without a scheduled all-clear, an empty inbox means either "nothing outstanding" or
"the flows stopped weeks ago", and there is no way to tell them apart until damage
has already been done. One email a week removes the ambiguity. See
`docs/ASSUMPTIONS.md` §8.2.

---

## 15. Date and time helpers

| Need | Expression |
|---|---|
| Today, date only | `formatDateTime(utcNow(), 'yyyy-MM-dd')` |
| This month | `formatDateTime(utcNow(), 'yyyy-MM')` |
| Last month | `formatDateTime(addToTime(utcNow(), -1, 'Month'), 'yyyy-MM')` |
| First of this month | `startOfMonth(utcNow())` |
| Last day of this month | `addDays(startOfMonth(addToTime(utcNow(),1,'Month')), -1)` |
| Days between two dates | `div(sub(ticks(b), ticks(a)), 864000000000)` |
| Six months ago | `addToTime(utcNow(), -6, 'Month')` |
| India Standard Time | `convertFromUtc(utcNow(), 'India Standard Time', 'yyyy-MM-dd HH:mm')` |

**Store UTC, display IST.** SharePoint stores UTC. Every timestamp written by a
flow should be `utcNow()`; convert only when building an email or a card that a
person reads. Storing local time makes the first daylight-saving-free year look
fine and then quietly breaks every duration calculation the moment anyone opens
a second site in another zone.

---

## 16. Null-safety patterns worth using everywhere

| Risk | Guard |
|---|---|
| Null number in arithmetic | `float(coalesce(x, 0))` |
| Null text in `concat` | `coalesce(x, '')` |
| Empty array indexed at `[0]` | test `greater(length(arr), 0)` first |
| Optional Forms answer | `if(empty(triggerOutputs()?['body/rXXXX']), '', triggerOutputs()?['body/rXXXX'])` |
| Lookup that found nothing | `first(body('Get_items')?['value'])?['Field']` returns null rather than erroring |

The single most common cause of a 2 a.m. flow failure in a system like this is
`add(null, 5)`. Wrap every number that comes out of a list read.
