# Power Automate — build sheet for all 11 flows

Flows cannot be created from a file without a premium solution export, so this is a
**build sheet**: every trigger, every action in order, every setting and every
expression, written out so a maintenance engineer who has never built a flow can
follow it.

Every expression referenced here is written in full in `expressions.md`.

## Before you start

| | |
|---|---|
| **Connections needed** | SharePoint, Office 365 Outlook, Microsoft Forms, Approvals, Microsoft Teams, Excel Online (Business) |
| **All standard connectors** | Nothing here needs premium licensing |
| **Owner account** | No service account is available, so these are built under an **individual account**. That is workable but carries a real risk — read `ASSUMPTIONS.md` §8.2 **before** you start, and add the two co-owners as you build each flow rather than afterwards |
| **Naming** | `PM-01 Monthly Std Hours Import` … `PM-11 Daily Digest`. The number is what makes the run history navigable at 7 a.m. |

### Two rules that will save you a day each

**Rename actions before writing expressions.** Expressions reference actions by
name with spaces replaced by underscores. Rename an action afterwards and the
expression breaks — the flow still saves, then fails at runtime with a null.

**Turn on `Configure run after` for every SharePoint write.** Default behaviour on
failure is to stop silently. Add a failure branch that emails a **shared mailbox**
— not the owner's inbox — or you will find out about a broken flow when someone asks
why a counter never reset.

**Add two co-owners to every flow as you build it.** Flow → Share → add both. Be
clear what this buys: co-owners can *edit and repair* the flow, but the flow still
runs on the **connections** belonging to whoever created them. If that account is
disabled the connections break regardless of who else owns the flow. Co-ownership
shortens the repair; it does not prevent the failure. `ASSUMPTIONS.md` §8.2 has the
reassignment procedure.

### Build order

Flows 1, 2 and 5 are the spine — the counter, the trigger and the reset. Build and
test those three before anything else. The remaining eight are independent of each
other and can be built in any order.

---

# Flow 1 — Monthly Std Hours Import

**The only file anyone uploads each month.** It adds each cell's hours to its
running counter, applying the proration rule if that cell's PM reset fell inside
the month.

| | |
|---|---|
| **Trigger** | SharePoint → *When a file is created (properties only)* |
| **Site / Library** | your site / `StdHours_Inbox` |
| **Concurrency** | **Off** (degree of parallelism 1). Two files processed at once would both read the same counter and one increment would be lost |

### Actions in order

1. **Initialize variable** `varUploadMonth` (String), value empty
2. **Initialize variable** `varMonthStart` (String), value empty
3. **Initialize variable** `varMonthEnd` (String), value empty
4. **Initialize variable** `varWorkingDaysInMonth` (Integer), value `0`
5. **Initialize variable** `varWorkingDaysAfterReset` (Integer), value `0`
6. **Initialize variable** `varDayOfReset` (Integer), value `0`
7. **Initialize variable** `varResetDate` (String), value empty
8. **Initialize variable** `varProratedHours` (Float), value `0`
9. **Initialize variable** `varValidCells` (Array), value `[]`
10. **Initialize variable** `varBadRows` (Array), value `[]`
11. **Initialize variable** `varSummary` (Array), value `[]`

8. **Excel Online (Business) → List rows present in a table**
   - Location: SharePoint site · Library: `StdHours_Inbox`
   - File: `triggerOutputs()?['body/{Identifier}']`
   - Table: `StdHours_Upload`
   - Rename to **`List rows present in a table`**

   > The upload template must contain a real Excel **table** named
   > `StdHours_Upload`, not just a sheet with that name. A named range or a bare
   > sheet is not readable by this connector, and the error it gives does not say so.

9. **Set variable** `varUploadMonth` →
   `first(body('List_rows_present_in_a_table')?['value'])?['Upload_Month']`

10. **Set variable** `varMonthStart` and `varMonthEnd` (`expressions.md` §2)

10a. **Get items** — rename **`Get items working days month`**
    - List `Plant_Calendar`
    - Filter: `Is_Working_Day eq 1 and Calendar_Date ge '@{variables('varMonthStart')}' and Calendar_Date le '@{variables('varMonthEnd')}'`
    - **Set variable** `varWorkingDaysInMonth` = `length(body('Get_items_working_days_month')?['value'])`

10b. **Condition** — *plant calendar guard*
    - `equals(variables('varWorkingDaysInMonth'), 0)` is equal to `true`
    - **If yes:** email the planner that the plant calendar has no working days for
      this month, then **Terminate → Failed**.

    > `Actual_Std_Hours` is a capacity figure, so proration divides by working days.
    > An unmaintained calendar makes that divisor zero and the run dies at 2 a.m.
    > with an unhelpful message. Fail loudly and early instead.

11. **Get items** — rename **`Get items existing month`**
    - List `StdHours_Monthly`
    - Filter Query: `Upload_Month eq '@{variables('varUploadMonth')}'`

12. **Condition** — *duplicate upload guard*
    - `greater(length(body('Get_items_existing_month')?['value']), 0)` is equal to `true`
    - **If yes:** move the file to `StdHours_Inbox/Rejected/`, send an email saying
      which month was already loaded, then **Terminate → Failed**.

    > Terminate as **Failed**, not Succeeded. A rejected upload that shows green in
    > the run history looks identical to a good one, and nobody notices for a month.

13. **Get items** — rename **`Get items all cells`**
    - List `Cell_Master` · Filter: `Active eq 1`
14. **Select** — from `body('Get_items_all_cells')?['value']`, map to
    `item()?['Cell_ID']` → **Set variable** `varValidCells`

15. **Apply to each** over `body('List_rows_present_in_a_table')?['value']` —
    rename **`Apply to each validate`**
    - **Condition:** `contains(variables('varValidCells'), items('Apply_to_each_validate')?['Cell_ID'])`
      is equal to `false` → **Append to array** `varBadRows`

16. **Condition** — *stop on any bad row*
    - `greater(length(variables('varBadRows')), 0)` is equal to `true`
    - **If yes:** email the bad rows to the uploader, move the file to `Rejected/`,
      **Terminate → Failed**

    > One bad `Cell_ID` stops the whole file. A half-imported month is far harder to
    > unpick than a rejected one, because nothing on the surface says which half
    > landed.

17. **Apply to each** over the Excel rows — rename **`Apply to each row`**
    - **Concurrency: Off.** Parallel iterations would read the same counter.
    1. **Get items** — rename **`Get item cell`**
       - `Cell_Master`, filter `Cell_ID eq '@{items('Apply_to_each_row')?['Cell_ID']}'`
    2. **Set variable** `varDayOfReset` → the reset-day expression (§2)
    3. **Set variable** `varResetDate` → §2
    4. **Get items** — rename **`Get items working days after reset`**
       - `Plant_Calendar`, filter
         `Is_Working_Day eq 1 and Calendar_Date gt '@{variables('varResetDate')}' and Calendar_Date le '@{variables('varMonthEnd')}'`
       - **Set variable** `varWorkingDaysAfterReset` =
         `length(body('Get_items_working_days_after_reset')?['value'])`

       > `gt`, not `ge`. The reset day belongs to the **old** cycle — the PM happened
       > on it.

    5. **Set variable** `varProratedHours` → the proration expression (§2)
    6. **Create item** in `StdHours_Monthly`:

       | Field | Value |
       |---|---|
       | `Title` | `concat(variables('varUploadMonth'),' ',items('Apply_to_each_row')?['Cell_ID'])` |
       | `Upload_Month` | `variables('varUploadMonth')` |
       | `Cell_ID` / `Cell_Name` | from the Excel row |
       | `Actual_Std_Hours` | from the Excel row — **the raw figure, not the prorated one** |
       | `Production_Qty`, `Uploaded_By`, `Remarks` | from the Excel row |
       | `Upload_Date` | `utcNow()` |

       > Store the **raw** hours. The prorated figure is a posting adjustment, not
       > the truth about what the cell ran. Storing the adjusted number would
       > corrupt the three-month average and the whole forecast with it.

    7. **Update item** on `Cell_Master` — the counter:
       - `Cum_Std_Hours_Since_PM` → the add expression (§3)
       - `Avg_Monthly_Std_Hours_L3M` → the rolling average (§10)
    8. **Append to array** `varSummary` — cell, raw hours, working days used,
       prorated hours, new counter

18. **Move file** → `StdHours_Archive`

    > Power BI's folder query points at `StdHours_Archive`, so archiving is not
    > tidying up — it is what makes the month visible to the report.

19. **Send an email (V2)** — the summary table, with a column showing where
    proration was applied and a line for any cell that crossed its trigger.

### Test it

Upload a month for a cell whose reset fell mid-month and check the posted figure
against the hand-worked example in `expressions.md` §2 — **720.00 h**, not 780 and
not 728. Then upload the same file again and confirm it is rejected.

Also blank out a month of `Plant_Calendar` and confirm the flow terminates as Failed
with a message naming the month, rather than dividing by zero.

---

# Flow 2 — PM Trigger & Work Order Creation

| | |
|---|---|
| **Trigger** | Recurrence — daily at **05:00 India Standard Time** |

05:00 so the supervisor's list is ready before the A shift starts at 06:00.

### Actions

1. **Get items** — rename **`Get items due cells`**
   - `Cell_Master`
   - Filter: `Active eq 1 and (Cum_Std_Hours_Since_PM ge 4000 or Last_PM_Date le '@{addDays(utcNow(),-183)}')`
   - Top count 100

2. **Apply to each** over the result — rename **`Apply to each cell`**

   1. **Condition** — re-check against the cell's **own** thresholds using the
      per-cell expression in §6.

      > The OData filter has to use a literal 4000 because SharePoint cannot
      > compare two columns. This second test uses `PM_Trigger_Hours` and
      > `Calendar_Backstop_Months` from the row, so a cell you have retuned
      > behaves correctly. **A hard-coded 4000 that actually decides anything is
      > a defect.**

   2. **Get items** — rename **`Get items open wo`**
      - `PM_WorkOrder`, filter
        `Cell_ID eq '...' and WO_Status ne 'Completed' and WO_Status ne 'Cancelled'`
   3. **Condition:** `empty(body('Get_items_open_wo')?['value'])` is equal to `true`

      > Without this the flow raises a duplicate work order every morning until
      > someone closes the first one.

   4. **Set variable** `varWO` → the work order number expression (§6)
   5. **Get items** — rename **`Get items active machines`**
      - `Machine_Master`, filter `Cell_ID eq '...' and Active eq 1`
   6. **Create item** in `PM_WorkOrder`:

      | Field | Value |
      |---|---|
      | `WO_No` / `Title` | `variables('varWO')` |
      | `Cell_ID` / `Cell_Name` | from the cell |
      | `Trigger_Type` | the trigger-type expression (§6) |
      | `Trigger_Hours_At_Creation` | the cell's current counter |
      | `WO_Created_Date` | `utcNow()` |
      | `Planned_Start_Date` / `Planned_End_Date` / `Planned_Month` | §6 |
      | `Lead_Tech_ID` | leave blank for the supervisor to assign |
      | `Priority` | the priority expression (§6) |
      | `Machines_In_Scope` | `length(body('Get_items_active_machines')?['value'])` |
      | `Machines_Completed` | `0` |
      | `WO_Status` | `Planned` |
      | `Reset_Applied` | `false` |

   7. **Apply to each** over the active machines — **Create item** in
      `PM_Machine_Task`: `Task_ID` (§7), `WO_No`, `Machine_ID`, `Cell_ID`,
      `Task_Status = Pending`, `NOT_OK_Count = 0`,
      `Abnormality_Raised = false`, `Spare_Used_Flag = false`

      > `Task_ID` is deterministic, so a re-run cannot create two tasks for the
      > same machine on the same work order.

   8. **Condition** — machine-count cross-check (§6). If it fails, still proceed
      but send an alert.

      > A short work order closes early and resets a counter it should not have.
      > That is a silent data-integrity failure, so it gets its own alert rather
      > than a log line.

   9. **Send an email (V2)** to `Owner_Supervisor` — work order number, cell,
      machine count, planned dates, and a direct link to the
      `My Allotted PM List` view.

---

# Flow 3 — Start PM (scan)

| | |
|---|---|
| **Trigger** | Microsoft Forms → *When a new response is submitted* — form **PM Start** |

### Actions

1. **Get response details**
2. **Create item** in `Scan_Log`: `Scan_ID` (§7), `Scan_DateTime = utcNow()`,
   `Machine_ID` and `Cell_ID` (pre-filled hidden fields), `Tech_ID` (**mandatory
   dropdown**), `Scan_Action = Start PM`, `Device`, `Comments`
3. **Get items** — rename **`Get items task`**
   - `PM_Machine_Task`, filter
     `Machine_ID eq '...' and Task_Status ne 'Completed' and Task_Status ne 'Skipped'`
4. **Condition:** `greater(length(body('Get_items_task')?['value']), 0)`
   - **No:** write the scan to `Scan_Log` anyway with `WO_No` blank, and reply that
     there is no open work order for this machine.

     > This is the orphan scan the raw log exists to capture. It is not an error —
     > it is the earliest visible sign of an adoption problem, and it only shows up
     > if you record it.

5. **Condition** — do not overwrite a scan-in that already happened:
   `empty(first(body('Get_items_task')?['value'])?['Scan_Start_Time'])`
6. **Update item** on `PM_Machine_Task`: `Task_Status = In Progress`,
   `Scan_Start_Time = utcNow()`, `Assigned_Tech_ID` = the technician
7. **Update item** on `PM_WorkOrder` — if `WO_Status` is `Planned`, set
   `In Progress` and stamp `Actual_Start_Date`

   > Step 5 is what makes a duplicate scan harmless. A technician who scans twice
   > because the page was slow must not restart his own clock — otherwise
   > `Duration_Min` reads four minutes for a forty-minute job.

---

# Flow 4 — Checklist Submission

| | |
|---|---|
| **Trigger** | Microsoft Forms → *When a new response is submitted* — form **PM Checklist** |

### Actions

1. **Get response details**
2. **Initialize variable** `varChecklistResults` (Array)
3. **Get items** — `Checklist_Master`, filter
   `Checklist_ID eq '...' and Active eq 1`, order by `Item_No`
4. **Apply to each** check point — build the array, one object per item:
   `Item_No`, `Check_Point`, `Result`, `Measured_Value`, `Safety_Critical`
5. **Apply to each** over `varChecklistResults` — **Create item** in
   `Checklist_Response`: `Response_ID` (§7), `Submitted_DateTime = utcNow()`,
   context keys pre-filled from the QR, `Result`, `Measured_Value`, `Observation`,
   `Action_Taken`, `Tech_ID`, `Follow_Up_Required`

   > **Measurement-type checks must capture a number.** Enforce it here: if
   > `Check_Type = Measurement` and `Measured_Value` is empty, fail the row and ask
   > for a reading. A measurement checklist with no readings is a tick-box exercise;
   > with readings it is condition monitoring.

6. **Set variable** `varNotOkCount` → §9
7. **Set variable** `varSafetyCriticalCount` → §9
8. **Update item** on `PM_Machine_Task`:
   - `Task_Status` → §9 (**In Progress** if any safety-critical NOT OK, else
     **Completed**)
   - `Scan_End_Time = utcNow()`, `Duration_Min` → §8
   - `NOT_OK_Count`, `Completed_By`, `Completion_Date`, `Checklist_Response_ID`
9. **Condition** — safety-critical found → Teams message + email to the supervisor,
   marked as blocking closure
10. **Condition** — `Duration_Min` less than 30% of the summed `Expected_Time_Min`
    → flag for review

    > A 45-minute checklist closed in 4 minutes is a pencil-whipped PM. This is the
    > column that catches it, and catching it quietly in a report nobody opens is
    > the same as not catching it.

---

# Flow 5 — Cell Closure & Counter Reset

**The most important flow in the system.** It is the only thing allowed to zero a
counter.

| | |
|---|---|
| **Trigger** | SharePoint → *When an item is created or modified* — list `PM_Machine_Task` |
| **Concurrency** | **Off.** Four machines finishing together must not each try to close the cell |

### Actions

1. **Condition:** `equals(triggerOutputs()?['body/Task_Status'], 'Completed')` —
   otherwise **Terminate → Succeeded**
2. **Set variable** `varWO` = `triggerOutputs()?['body/WO_No']`
3. **Get items** — rename **`Get items pending tasks`**
   - `PM_Machine_Task`
   - Filter: `WO_No eq '@{variables('varWO')}' and Task_Status ne 'Completed' and Task_Status ne 'Skipped'`
4. **Get items** — rename **`Get items completed tasks`**
   - Filter: `WO_No eq '...' and Task_Status eq 'Completed'`
5. **Update item** on `PM_WorkOrder` — `Machines_Completed` =
   `length(body('Get_items_completed_tasks')?['value'])`

   > Update this on **every** task completion, not only at the end. It is what
   > drives the live completion bar on the tracking page, and a bar that only moves
   > at the end tells nobody anything.

6. **Condition — the all-complete test:**

   ```
   if(equals(length(body('Get_items_pending_tasks')?['value']), 0), true, false)
   ```

   **If no:** terminate. The cell is not finished; one machine scanned is not enough.

   **If yes:**

   1. **Get items** — rename **`Get items all tasks`** (for durations and start time)
   2. **Get item** — rename **`Get item cell`** on `Cell_Master`
   3. **Get items** — rename **`Get items l3m`** on `StdHours_Monthly`, filter
      `Cell_ID eq '...'`, order by `Upload_Month desc`, **Top count 3**
   4. **Update item** on `PM_WorkOrder`: `WO_Status = Completed`,
      `Actual_End_Date = utcNow()`, `Actual_Start_Date` = earliest scan (§10),
      `PM_Duration_Min` = sum of task durations, `Reset_Applied = true`,
      `Reset_Date = utcNow()`
   5. **Update item** on `Cell_Master` — **one action, all five fields** (§10)

      > Integrity rule 3: `Cum_Std_Hours_Since_PM`, `Last_PM_Date`,
      > `Last_PM_WO_No`, `Reset_Applied` and `Reset_Date` move **together or not at
      > all**. Splitting them across two Update actions creates a window where a
      > failure leaves a zeroed counter with no `Last_PM_Date` — and nothing
      > downstream can tell that apart from a real reset.

   6. **Update item** on `PM_Plan_Calendar` — set `Adherence_Status` to `On Time` or
      `Delayed` by comparing the actual end against `Planned_Date`
   7. **Send an email (V2)** — cell PM complete, counter reset to zero, next due
      dates on both clocks

### Test it

Complete three of four machine tasks and confirm **nothing** resets. Complete the
fourth and confirm all five `Cell_Master` fields change in the same version. This
is UAT-14 and UAT-15.

---

# Flow 6 — Breakdown Report

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Breakdown Report** |

1. **Get response details**
2. **Get item** — rename **`Get item machine`** on `Machine_Master`
3. **Create item** in `Breakdown_Log` — `BD_ID` (§7), `Reported_DateTime`,
   machine and cell pre-filled, `Reported_By_Tech_ID`, `Shift`, `Breakdown_Type`,
   `Symptom`, `Root_Cause`, `Action_Taken`, the three timestamps,
   `Response_Time_Min` and `MTTR_Min` (§8), `Production_Loss_Min`, `Status`
4. **Get items** — rename **`Get items recent pm`** — completed PM on this cell in
   the last 7 days
5. **Update item** — set `Linked_PM_WO` (§11)
6. **Condition** — machine criticality A (§12) → **Teams: Post a message** to the
   maintenance channel + email the supervisor

   > Only criticality A alerts immediately. Alerting on every breakdown trains
   > people to mute the channel, and then the one that mattered is muted too.

---

# Flow 7 — Spare Request + Approval

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Spare Request** |

1. **Get response details**
2. **Get item** — rename **`Get item spare`** on `Spare_Master`
3. **Create item** in `Spare_Request` — `Req_ID` (§7), context keys,
   `Spare_Code`, `Qty_Requested`, `Requested_By`, `Urgency`, `Reason`,
   `Approval_Status = Pending`,
   `Stock_At_Request` = the spare's current stock

   > `Stock_At_Request` is a snapshot taken now. It is the evidence for a
   > min-stock revision six months later, when nobody remembers what the shelf
   > looked like.

4. **Condition** — `Urgency` is `Breakdown` → Teams alert immediately and skip the
   queue
5. **Start and wait for an approval** — *Approve/Reject – First to respond*
   - Assigned to: the cell's `Owner_Supervisor`
   - Details: machine, part, quantity, current stock, reason, urgency
6. **Update item** — `Approval_Status` from the outcome, `Approved_By`,
   `Approved_Date = utcNow()`
7. **Send an email (V2)** to the requester with the outcome and any comment

---

# Flow 8 — Spare Replaced

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Spare Replaced** |

1. **Get response details**
2. **Get item** — rename **`Get item spare`**
3. **Create item** in `Spare_Replaced` — `Repl_ID` (§7), `Replaced_DateTime`,
   `Source_Type` (PM or Breakdown), `Source_Ref`, machine and cell,
   `Spare_Code`, `Qty_Used`, `Unit_Cost_INR` and `Total_Cost_INR` (§13),
   `Old_Part_Condition`, **`Failure_Mode`**, `Replaced_By`,
   `Expected_Life_Hours`, `Warranty_Claim`

   > `Failure_Mode` is the most valuable column in this table. Repeated
   > "Contamination" on the same part is a filtration problem, not a spares
   > problem, and no amount of buying more parts will fix it. Make it **mandatory**
   > on the form.

4. **Update item** on `Spare_Master` — decrement `Current_Stock` (§13, with the
   negative-stock clamp)
5. **Condition** — stock at or below minimum (§13) → email stores and the
   supervisor with part, bin, vendor and **lead time**

   > Include the lead time. One below minimum with a 30-day lead time is a
   > different problem from one with a 3-day lead time, and the alert should say
   > which one it is.

6. **Update item** on `PM_Machine_Task` — set `Spare_Used_Flag = true`

---

# Flow 9 — Abnormality Log

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Abnormality Log** |

1. **Get response details**
2. **Create item** in `Abnormality_Log` — `Abn_ID` (§7), `Logged_DateTime`,
   machine and cell pre-filled, `Logged_By`, `Category`, `Description`,
   `Severity`, `Immediate_Action`, `Responsibility`, `Target_Date`,
   `Status = Open`
3. **Condition** — `Severity` is `High` (§15):
   - **Teams: Post a message** to the maintenance channel
   - **Send an email (V2)** to the supervisor and the plant head
   - **Delay until** `addHours(utcNow(), 24)`
   - **Get item** again, and **only if still open** (§15) send the follow-up

   > Re-reading before the reminder is the whole point. A reminder that fires
   > whether or not the problem was fixed teaches people to ignore reminders, and
   > then the reminder system is worth nothing.

4. **Update item** on `PM_Machine_Task` — `Abnormality_Raised = true` if raised
   during a PM

---

# Flow 10 — Follow-Up Work Order from a NOT OK

| | |
|---|---|
| **Trigger** | Recurrence — daily at **06:00 IST** |

1. **Get items** on `Checklist_Response`, filter
   `Follow_Up_Required eq 1 and Follow_Up_WO eq null` (§17)
2. **Apply to each:**
   1. **Create item** in `PM_WorkOrder` — `WO_No` = `CWO-…` (§17),
      `Trigger_Type = Manual`, `Priority` from severity, `WO_Status = Planned`,
      `Remarks` = the check point and the observation
   2. **Create item** in `PM_Machine_Task` for that one machine
   3. **Update item** on `Checklist_Response` — write `Follow_Up_WO` back

      > Writing the number back is what closes the loop. Without it the same
      > finding raises a fresh corrective work order every morning, and within a
      > week nobody trusts the corrective queue.

3. **Send an email (V2)** — the corrective work orders raised today

---

# Flow 11 — Daily Digest

| | |
|---|---|
| **Trigger** | Recurrence — daily at **06:30 IST** |

06:30, half an hour after the A shift starts, so it reflects a real morning.

1. **Get items** — `Get items overdue cells` (§16)
2. **Get items** — `Get items open wo` (§16)
3. **Get items** — `Get items not scanned` (§16)
4. **Get items** — `Get items overdue abn` (§16)
5. **Get items** — `Get items reset failures` — completed work orders with
   `Reset_Applied eq 0`

   > A completed work order whose counter never zeroed is a flow failure. It shows
   > up nowhere else, so it belongs on the digest.

6. **Condition** — send if something is outstanding **OR it is Monday** (§16)

   > A digest that arrives every day whether or not anything is wrong stops being
   > read within a fortnight. Skipping the clean days is what keeps it meaningful.
   >
   > **But silence has to mean one thing, not two.** The flows run on one person's
   > connections (see `ASSUMPTIONS.md` §8.2). If the digest only ever arrives when
   > there is a problem, an empty inbox means either "nothing outstanding" or "the
   > flows died three weeks ago" — and you cannot tell which until something has
   > already gone wrong.
   >
   > Sending **on Mondays regardless** fixes that for the cost of one email a week.
   > Tuesday to Sunday it stays quiet unless there is something to act on.

7. **Create HTML table** for each section
8. **Send an email (V2)** and **Teams: Post an adaptive card** to the maintenance
   channel

   On a clean Monday, skip the tables and send the single line:

   ```
   PM system healthy - nothing outstanding.
   Counters, triggers and escalations all ran. Next check Monday.
   ```

   **The rule for whoever reads it: if no digest arrives on a Monday, the flows have
   stopped.** That sentence belongs in the handover note, not just here — it is the
   entire early-warning system.

### Digest layout

```
PM DAILY DIGEST — <date, IST>

  OVERDUE CELLS            n     cell, counter/trigger, days since last PM, supervisor
  OPEN WORK ORDERS         n     WO, cell, completion %, planned end, days open
  NOT YET SCANNED          n     machine, cell, WO, assigned technician
  HIGH-SEVERITY OVERDUE    n     abnormality, machine, target date, owner
  RESET FAILURES           n     WO, cell, completed date        <- investigate first
```

Reset failures go last in the layout but first in the reading order that matters:
everything else is work to do, that one is the system lying to you.

---

## Testing the whole chain

Follow `docs/UAT_TEST_CASES.md` in order. The five that must pass before go-live:

| Case | What it proves |
|---|---|
| UAT-03 | A cell crossing 4,000 in the monthly upload raises exactly one work order |
| UAT-07 | The 6-month backstop fires for a low-utilisation cell that never reaches 4,000 |
| UAT-14 | Three of four machines complete and **nothing** resets |
| UAT-15 | The fourth completes and all five `Cell_Master` fields move together |
| UAT-19 | A mid-month reset prorates by working days to 720.00 h |
| UAT-30a | The Monday heartbeat arrives on a clean week — the only way a stopped flow becomes visible |

## Monitoring the flows themselves

- **Power Automate → My flows → Analytics** weekly. A flow with a rising failure
  rate is usually a null that only appears with certain data.
- Set **failure notifications** on all eleven to a **shared mailbox**. The built-in
  "send me an email if a flow fails" reaches the owner only, which is no use the day
  the owner's account is the thing that broke.
- The digest's reset-failure section is your canary for Flow 5 having half-worked,
  which is the failure that costs the most and announces itself the least.
- **The Monday heartbeat is your canary for the flows themselves.** No digest on a
  Monday means they have stopped — most likely a broken connection on the owning
  account. Check `My flows` for a disabled flow or an "Invalid connection" banner.
