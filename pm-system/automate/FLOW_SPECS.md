# Power Automate — build sheet for all 9 flows

Flows cannot be created from a file without a premium solution export, so this is a
**build sheet**: every trigger, every action in order, every setting and every
expression, written out so a maintenance engineer who has never built a flow can
follow it.

Every expression referenced here is written in full in `expressions.md`.

## What changed, and why it is fewer flows

Eleven flows became **nine**, and the ones that remain are shorter. Nothing the
system does was given up except one thing, named below.

| Was | Now | Why |
|---|---|---|
| **Spare Request + Approval** | **gone** | It ran a requisition-and-approval loop that the stores process already runs. The PM system needs to know what was *fitted* — cost, failure mode, which machine — and that is `Spare_Replaced`. It was the only flow here with no PM rule behind it. |
| **Follow-Up WO from a NOT OK** | **gone** | It raised a corrective work order overnight from a tick-box, into a queue nobody owned. Worse, it created `PM_WorkOrder` rows that Flow 2's open-work-order check could not tell apart from a real PM — so one unclosed corrective job would have suppressed that cell's next 4,000-hour trigger indefinitely. Follow-up is now a supervisor's decision, made from the **NOT OK Findings** view. |
| 8, 9, 11 | **7, 8, 9** | Renumbered so there are no gaps. Nothing is deployed yet, and a build sheet that skips two numbers invites "did I miss one?" on the day somebody hands this over. |

**What was actually lost.** Two things, both deliberate and both recoverable:

- **Approval lead time and the stock-at-request snapshot.** Gone with the spare
  request loop. If purchasing ever needs to argue a min-stock revision from
  evidence, that evidence now has to come from the stores system.
- **The scan that led nowhere.** `Scan_Log` recorded scans against machines with no
  open work order — a useful early signal that people are using the stickers before
  the process is ready for them. It cost a list, a flow branch and about 340 rows a
  year to keep something nobody had asked for. Flow 3 still *tells the technician*
  there is no open job; it just no longer files the fact. This is the first thing
  to reinstate if take-up is ever in doubt.

Everything else that came out was a number a flow used to calculate and store, and
the report now works out for itself — durations, MTTR, line totals, rolling
averages, flags. Those were never lost; they moved to where they cannot drift.

**The count that matters:** 9 flows instead of 11, and **25 writes into SharePoint
lists down to 16**. A write is the action most likely to fail at 2 a.m. and the only
kind that can leave a record half-finished, so nine fewer of them is the honest
measure of how much simpler this is to run.

---

## Before you start

| | |
|---|---|
| **Connections needed** | SharePoint, Office 365 Outlook, Microsoft Forms, Microsoft Teams, Excel Online (Business) |
| **All standard connectors** | Nothing here needs premium licensing |
| **Approvals** | **No longer needed.** The only approval in the system went with the spare request flow |
| **Owner account** | No service account is available, so these are built under an **individual account**. That is workable but carries a real risk — read `ASSUMPTIONS.md` §8.2 **before** you start, and add the two co-owners as you build each flow rather than afterwards |
| **Naming** | `PM-01 Monthly Std Hours Import` … `PM-09 Daily Digest`. The number is what makes the run history navigable at 7 a.m. |

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
test those three before anything else. The remaining six are independent of each
other and can be built in any order.

---

# The five forms

Every flow that a technician starts is triggered by a Microsoft Form. Build these
first — a flow cannot be built against a form that does not exist yet, because the
trigger has nothing to list.

| # | Form | Feeds | Questions | Machine Hub button |
|---|---|---|---|---|
| 1 | **PM Start** | Flow 3 | **2**, both pre-filled | ▶ START PM |
| 2 | **PM Checklist** | Flow 4 | 4 + the branched section | ☑ COMPLETE CHECKLIST |
| 3 | **Spare Replaced** | Flow 7 | 9 | 🔧 SPARE FITTED |
| 4 | **Breakdown Report** | Flow 6 | 14 | ⚠ REPORT BREAKDOWN |
| 5 | **Abnormality Log** | Flow 8 | 9 | 👁 LOG ABNORMALITY |

Every one of the five is reached from the card the QR sticker opens, in that order.
Nothing in this system asks a technician to find a link.

> **The Spare Request form is gone.** Requisition and approval are a stores process
> that already exists. What this system needs is what was *fitted*, and that is
> form 4.

## ⚠ The rule that will catch you out

A pre-filled link fills in answers **by position** — question 1 gets the first
value, question 2 the second. It does not use question names.

So on every form: **`Machine ID` is question 1, `Cell ID` is question 2**, and on
the checklist **`Checklist ID` is question 3**. Insert anything above them and every
sticker on the shop floor starts filling the wrong boxes — silently, with no error.
New questions go at the **bottom**, always.

## Settings, identical on all five

- **Anyone can respond** ✅ — the handsets share one login
- **Record name** ❌ — it would record the shared account, which is worse than
  nothing: it looks like attribution and is not
- **Technician Name** is a **Choice**, **Required**, typed out from
  `Technician_Master` — never a text box. Free text produces "Murugan", "murugan s"
  and "MURUGAN S", and three months later nothing can be counted.

  **The one exception is PM Start**, and §"The form is one tap" under Flow 3 explains
  why.

---

## Form 1 — PM Start

| Q | Question | Type | Required | Goes to |
|---|---|---|---|---|
| 1 | Machine ID | Text | ✅ | *matched to the open task* |
| 2 | Cell ID | Text | ✅ | *context only* |

Both arrive pre-filled from the sticker. The technician taps **Submit** and nothing
else. That is the entire form.

---

## Form 2 — PM Checklist

| Q | Question | Type | Required | Goes to |
|---|---|---|---|---|
| 1 | Machine ID | Text | ✅ | `Machine_ID` |
| 2 | Cell ID | Text | ✅ | *context only* |
| 3 | Checklist ID | Choice — the 9 IDs | ✅ | `Checklist_ID`, **and the branch** |
| 4 | Technician Name | Choice | ✅ | `Tech_ID` |

`WO_No` is **not** asked. Flow 4 looks up the machine's open task and takes the work
order number off it — the technician already scanned the machine, so making them
retype a work order number would only create a second chance to get it wrong.

### Then: one section per checklist, reached by branching

There are **nine** checklists (`CL-PRESS` 8 items, `CL-FILL` 7, `CL-GEN` 6,
`CL-OVEN` 6, `CL-WELD` 6, `CL-TEST` 5, `CL-UTIL` 5, `CL-FEED` 4, `CL-VISION` 4).

Build **one form with nine sections**, not nine forms. Set question 3's branching so
each answer jumps to its own section, and write that checklist's real check-point
text into it. Pre-fill it from the machine's `Checklist_ID` and the technician never
touches it.

> The alternative — eight generic "Item 4 result" boxes — works for the flow and is
> useless to the person holding the phone, because nothing on screen says what item
> 4 actually is. Nine sections is more to build once and correct forever after.

**Two questions per check point**, written out with the check point as the title:

| Q | Question | Type | Required | Goes to |
|---|---|---|---|---|
| a | *«the check point text»* | Choice, 4 options below | ✅ | `Result` + `Follow_Up_Required` |
| b | Reading / observation | Text | — | `Measured_Value` **or** `Observation` |

The four options carry two facts in one tap:

| Option | `Result` | `Follow_Up_Required` |
|---|---|---|
| OK | `OK` | No |
| NOT OK — fixed on the spot | `NOT OK` | No |
| NOT OK — needs follow-up | `NOT OK` | **Yes** |
| N/A | `NA` | No |

> Follow-up is a real judgement, not a restatement of the result: a NOT OK that was
> cleaned up on the spot needs none, and an OK that looked marginal sometimes does.
> Folding it into the same tap keeps the distinction without adding a question to
> every line.

Where box **b** goes is decided by the master, not by the technician: Flow 4 reads
`Check_Type` for that item and writes the text to `Measured_Value` when it is
`Measurement`, and to `Observation` otherwise. **A measurement item with box b empty
is rejected** — a measurement checklist with no readings is a tick-box exercise;
with readings it is condition monitoring.

**Last question on the form:** `Photo` (File upload, optional, 1 file). Flow 4
attaches it to the rows marked NOT OK — which is what a photo on a PM checklist is
ever of.

---

## Form 3 — Spare Replaced

| Q | Question | Type | Required | Goes to |
|---|---|---|---|---|
| 1 | Machine ID | Text | ✅ | `Machine_ID` |
| 2 | Cell ID | Text | ✅ | `Cell_ID` |
| 3 | Replaced by | Choice | ✅ | `Replaced_By` |
| 4 | Replaced during | Choice — PM / Breakdown | ✅ | `Source_Type` |
| 5 | Work order or breakdown reference | Text | ✅ | `Source_Ref` |
| 6 | Spare code | Choice — from `Spare_Master` | ✅ | `Spare_Code` |
| 7 | Quantity used | Number | ✅ | `Qty_Used` |
| 8 | **Failure mode** | Choice — Wear / Contamination / Fatigue / Overload / Corrosion / Electrical / End of life / Other | ✅ | `Failure_Mode` |
| 9 | Warranty claim | Choice — Yes / No | ✅ | `Warranty_Claim` |

`Unit_Cost_INR` is copied by the flow from `Spare_Master` at the moment of use —
never typed, and never looked up later, so a price rise next year cannot rewrite
this year's cost.

> Question 8 is the one that pays for this whole form. Repeated "Contamination" on
> the same part is a filtration problem, not a spares problem, and no amount of
> buying more parts will fix it. Keep it mandatory.

---

## Form 4 — Breakdown Report

| Q | Question | Type | Required | Goes to |
|---|---|---|---|---|
| 1 | Machine ID | Text | ✅ | `Machine_ID` |
| 2 | Cell ID | Text | ✅ | `Cell_ID` |
| 3 | Reported by | Choice | ✅ | `Reported_By_Tech_ID` |
| 4 | Shift | Choice — A / B / C | ✅ | `Shift` |
| 5 | Breakdown type | Choice — Electrical / Mechanical / Pneumatic / Hydraulic / Tooling / Other | ✅ | `Breakdown_Type` |
| 6 | Symptom — what it did | Text, long | ✅ | `Symptom` |
| 7 | Root cause | Text, long | — | `Root_Cause` |
| 8 | Action taken | Text, long | — | `Action_Taken` |
| 9 | When was it responded to | Date + time | — | `Response_DateTime` |
| 10 | Repair started | Date + time | — | `Repair_Start` |
| 11 | Repair finished | Date + time | — | `Repair_End` |
| 12 | Production lost, minutes | Number | — | `Production_Loss_Min` |
| 13 | Status | Choice — Open / Under Repair / Closed | ✅ | `Status` |
| 14 | Has this happened before on this machine | Choice — Yes / No | ✅ | `Recurrence_Flag` |

`Reported_DateTime` is stamped by the flow. Response time and MTTR are **not asked
and not stored** — they are the gaps between questions 9, 10 and 11, and the report
subtracts them.

---

## Form 5 — Abnormality Log

| Q | Question | Type | Required | Goes to |
|---|---|---|---|---|
| 1 | Machine ID | Text | ✅ | `Machine_ID` |
| 2 | Cell ID | Text | ✅ | `Cell_ID` |
| 3 | Logged by | Choice | ✅ | `Logged_By` |
| 4 | Category | Choice — Safety / Quality / Leak / Noise / Vibration / Housekeeping / Other | ✅ | `Category` |
| 5 | What did you see | Text, long | ✅ | `Description` |
| 6 | Severity | Choice — High / Medium / Low | ✅ | `Severity` |
| 7 | Photo | File upload, 1 file | — | `Photo_Link` |
| 8 | Who should fix it | Choice — Maintenance / Production / Quality / Safety | ✅ | `Responsibility` |
| 9 | Fix by | Date | ✅ | `Target_Date` |

`Status` is set to `Open` by the flow. `Closed_Date` is filled in SharePoint by
whoever closes it — see the note under Flow 8.

---

## Making the pre-filled links

1. Open a form → **Collect responses** → **Get a link to prefill answers**
2. Type `MC-01-001` into Machine ID, `CELL-01` into Cell ID (and on the checklist,
   pick the machine's checklist in question 3). Leave everything else blank.
3. **Get link.** You get something like:

```
https://forms.office.com/r/AbCdEf?id=xxxxx&r1a2b3c4=MC-01-001&r5d6e7f8=CELL-01
```

Those `r1a2b3c4` codes are that form's question IDs. They are stable for the life
of the form.

4. Cut that link into pieces and paste them over the placeholders in
   `sharepoint/formatting/Machine_Master.MachineHub.view.json`:

   | Placeholder | What to paste |
   |---|---|
   | `FORM_<NAME>_UPTO_MACHINE` | everything before the machine ID, e.g. `https://forms.office.com/r/AbCdEf?id=xxxxx&r1a2b3c4=` |
   | `FORM_<NAME>_UPTO_CELL` | the next key with its `&` and `=`, e.g. `&r5d6e7f8=` |
   | `FORM_CHECKLIST_UPTO_CLID` | the checklist form's third key, same shape |

   **Eleven placeholders across the five forms, set once.** The Machine Hub builds
   the rest of every link from the row it is drawing, so there is nothing
   per-machine to maintain — where the old design had 120 URLs typed into a
   spreadsheet, each one a chance to point a button at the wrong machine.

   Copy and paste both halves out of one real link. Retyping an eight-character
   question ID by hand produces a button that opens the form with nothing filled
   in, and nothing about it looks wrong until somebody uses it.

**Test one on a real phone before you go further.** Open it and check the machine
and cell are already filled, and that the first thing you have to touch is a real
question — not the keyboard.

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

**1–10. Initialize variable**, one action each:

| # | Name | Type | Initial value |
|---|---|---|---|
| 1 | `varUploadMonth` | String | *(empty)* |
| 2 | `varMonthStart` | String | *(empty)* |
| 3 | `varMonthEnd` | String | *(empty)* |
| 4 | `varWorkingDaysInMonth` | Integer | `0` |
| 5 | `varWorkingDaysAfterReset` | Integer | `0` |
| 6 | `varDayOfReset` | Integer | `0` |
| 7 | `varResetDate` | String | *(empty)* |
| 8 | `varProratedHours` | Float | `0` |
| 9 | `varValidCells` | Array | `[]` |
| 10 | `varBadRows` | Array | `[]` |

> There is no `varSummary` array any more. The confirmation email is built from the
> rows the flow has already read rather than from a parallel copy maintained
> alongside them.

11. **Excel Online (Business) → List rows present in a table**
    - Location: SharePoint site · Library: `StdHours_Inbox`
    - File: `triggerOutputs()?['body/{Identifier}']`
    - Table: `StdHours_Upload`
    - Rename to **`List rows present in a table`**

    > The upload template must contain a real Excel **table** named
    > `StdHours_Upload`, not just a sheet with that name. A named range or a bare
    > sheet is not readable by this connector, and the error it gives does not say so.
    >
    > **Two of the template's eight columns are no longer used.** `Cell_Name` is
    > looked up from `Cell_Master`, and `Uploaded_By` duplicates the **Created By**
    > stamp SharePoint puts on every item. This flow ignores both, and the Power BI
    > archive query reads only the six that remain — so you can delete those two
    > columns from the template whenever it suits, or leave them and have two fewer
    > cells to fill in each month. Files saved in either shape load correctly.
    >
    > **Do not reorder or rename the remaining six.** The Excel connector reads by
    > column name, so a rename is silent: the flow runs, finds nothing, and posts a
    > month of zeroes.

12. **Set variable** `varUploadMonth` →
    `first(body('List_rows_present_in_a_table')?['value'])?['Upload_Month']`

13. **Set variable** `varMonthStart`, then **Set variable** `varMonthEnd`
    (`expressions.md` §2)

14. **Get items** — rename **`Get items working days month`**
    - List `Plant_Calendar`
    - Filter: `Is_Working_Day eq 1 and Calendar_Date ge '@{variables('varMonthStart')}' and Calendar_Date le '@{variables('varMonthEnd')}'`
15. **Set variable** `varWorkingDaysInMonth` = `length(body('Get_items_working_days_month')?['value'])`

16. **Condition** — *plant calendar guard*
    - `equals(variables('varWorkingDaysInMonth'), 0)` is equal to `true`
    - **If yes:** email the planner that the plant calendar has no working days for
      this month, then **Terminate → Failed**.

    > `Actual_Std_Hours` is a capacity figure, so proration divides by working days.
    > An unmaintained calendar makes that divisor zero and the run dies at 2 a.m.
    > with an unhelpful message. Fail loudly and early instead.

17. **Get items** — rename **`Get items existing month`**
    - List `StdHours_Monthly` · Filter: `Upload_Month eq '@{variables('varUploadMonth')}'`

18. **Condition** — *duplicate upload guard*
    - `greater(length(body('Get_items_existing_month')?['value']), 0)` is equal to `true`
    - **If yes:** move the file to `StdHours_Inbox/Rejected/`, send an email saying
      which month was already loaded, then **Terminate → Failed**.

    > Terminate as **Failed**, not Succeeded. A rejected upload that shows green in
    > the run history looks identical to a good one, and nobody notices for a month.

19. **Get items** — rename **`Get items all cells`**
    - List `Cell_Master` · Filter: `Active eq 1`
20. **Select** — from `body('Get_items_all_cells')?['value']`, map to
    `item()?['Cell_ID']` → **Set variable** `varValidCells`

21. **Apply to each** over `body('List_rows_present_in_a_table')?['value']` —
    rename **`Apply to each validate`**
    - **Condition:** `contains(variables('varValidCells'), items('Apply_to_each_validate')?['Cell_ID'])`
      is equal to `false` → **Append to array** `varBadRows`

22. **Condition** — *stop on any bad row*
    - `greater(length(variables('varBadRows')), 0)` is equal to `true`
    - **If yes:** email the bad rows to the uploader, move the file to `Rejected/`,
      **Terminate → Failed**

    > One bad `Cell_ID` stops the whole file. A half-imported month is far harder to
    > unpick than a rejected one, because nothing on the surface says which half
    > landed.

23. **Apply to each** over the Excel rows — rename **`Apply to each row`**
    - **Concurrency: Off.** Parallel iterations would read the same counter.

    1. **Get items** — rename **`Get item cell`**
       - `Cell_Master`, filter `Cell_ID eq '@{items('Apply_to_each_row')?['Cell_ID']}'`

       > **This must be the first action in the loop.** The three steps below all
       > read the cell row it fetches. Put them above it and they read null, the
       > proration short-circuits, and a mid-month reset silently posts a full month.

    2. **Set variable** `varDayOfReset` → §2, reading `Last_PM_Date` off the cell
    3. **Set variable** `varResetDate` → §2
    4. **Get items** — rename **`Get items working days after reset`**
       - `Plant_Calendar`, filter
         `Is_Working_Day eq 1 and Calendar_Date gt '@{variables('varResetDate')}' and Calendar_Date le '@{variables('varMonthEnd')}'`
    5. **Set variable** `varWorkingDaysAfterReset` =
       `length(body('Get_items_working_days_after_reset')?['value'])`

       > `gt`, not `ge`. The reset day belongs to the **old** cycle — the PM happened
       > on it.

    6. **Set variable** `varProratedHours` → the proration expression (§2)
    7. **Create item** in `StdHours_Monthly` — **six fields**:

       | Field | Value |
       |---|---|
       | `Title` | `concat(variables('varUploadMonth'),' ',items('Apply_to_each_row')?['Cell_ID'])` |
       | `Upload_Month` | `variables('varUploadMonth')` |
       | `Cell_ID` | from the Excel row |
       | `Actual_Std_Hours` | from the Excel row — **the raw figure, not the prorated one** |
       | `Production_Qty` | from the Excel row |
       | `Upload_Date` | `utcNow()` |
       | `Remarks` | from the Excel row |

       > Store the **raw** hours. The prorated figure is a posting adjustment, not
       > the truth about what the cell ran. Storing the adjusted number would
       > corrupt the three-month average and the whole forecast with it.
       >
       > No `Cell_Name` — the report looks it up from `Cell_Master`, so a cell that
       > gets renamed is renamed everywhere at once instead of in every historical
       > row. No `Uploaded_By` either: SharePoint stamps **Created By** on every
       > item without being asked.

    8. **Update item** on `Cell_Master` — **one field**:
       - `Cum_Std_Hours_Since_PM` → the add expression (§3)

       > It used to write the rolling three-month average here as well. The report
       > now averages `StdHours_Monthly` directly, over the last months that
       > actually have data — which is both more accurate and one less number that
       > can be left stale by a failed run.

24. **Move file** → `StdHours_Archive`

    > Power BI's folder query points at `StdHours_Archive`, so archiving is not
    > tidying up — it is what makes the month visible to the report.

25. **Send an email (V2)** — the summary table, with a column showing where
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
      > someone closes the first one. It is also why corrective work orders are no
      > longer raised automatically — see §6.

   4. **Set variable** `varWO` → the work order number expression (§6)
   5. **Get items** — rename **`Get items active machines`**
      - `Machine_Master`, filter `Cell_ID eq '...' and Active eq 1`
   6. **Create item** in `PM_WorkOrder` — **eleven fields**:

      | Field | Value |
      |---|---|
      | `WO_No` / `Title` | `variables('varWO')` |
      | `Cell_ID` | from the cell |
      | `Trigger_Type` | the trigger-type expression (§6) |
      | `Trigger_Hours_At_Creation` | the cell's current counter |
      | `WO_Created_Date` | `utcNow()` |
      | `Planned_End_Date` / `Planned_Month` | §6 |
      | `Priority` | the priority expression (§6) |
      | `Machines_In_Scope` | `length(body('Get_items_active_machines')?['value'])` |
      | `Machines_Completed` | `0` |
      | `WO_Status` | `Planned` |
      | `Reset_Applied` | `false` |

      > No `Cell_Name` (looked up), no `Planned_Start_Date` (on-time is measured
      > against the end date only) and no `Lead_Tech_ID` — that one was never
      > populated by any flow, because the allocation lives on `PM_Plan_Calendar`.

   7. **Apply to each** over the active machines — **Create item** in
      `PM_Machine_Task`, **five fields**: `Task_ID` (§7), `WO_No`, `Machine_ID`,
      `Cell_ID`, `Task_Status = Pending`

      > `Task_ID` is deterministic, so a re-run cannot create two tasks for the
      > same machine on the same work order.
      >
      > It used to seed three more: `NOT_OK_Count`, `Abnormality_Raised` and
      > `Spare_Used_Flag`. All three were answers to questions the report asks
      > better — *count the findings*, *is there an abnormality on this machine
      > during this job*, *is there a replacement against it* — and each of them
      > could be left wrong by any flow that failed halfway.

   8. **Condition** — machine-count cross-check (§6). If it fails, still proceed
      but send an alert.

      > A short work order closes early and resets a counter it should not have.
      > That is a silent data-integrity failure, so it gets its own alert rather
      > than a log line.

   9. **Send an email (V2)** to `Owner_Supervisor` — work order number, cell,
      machine count, planned end date, and a direct link to the
      `My Allotted PM List` view.

---

# Flow 3 — Start PM (scan)

The shortest flow in the system: **two reads, two conditions, two writes.** It
exists to stamp one timestamp, and that timestamp is what makes a forty-minute job
distinguishable from a four-minute one.

| | |
|---|---|
| **Trigger** | Microsoft Forms → *When a new response is submitted* — form **PM Start** |

### Actions

1. **Get response details**
2. **Get items** — rename **`Get items task`**
   - `PM_Machine_Task`, filter
     `Machine_ID eq '...' and Task_Status ne 'Completed' and Task_Status ne 'Skipped'`
3. **Condition:** `greater(length(body('Get_items_task')?['value']), 0)`
   - **No:** **Send an email (V2)** back to the shop-floor mailbox — *"no open PM
     work order for MC-01-004"* — and **Terminate → Succeeded**.

     > Terminate as **Succeeded**: nothing failed. Somebody scanned a machine that
     > has no job on it, which is a process question, not a system error.
     >
     > This used to be filed in `Scan_Log` as well. That list is gone, so the scan
     > that led nowhere is now reported and not recorded. If adoption is ever in
     > question, reinstating `Scan_Log` is the first thing to do — see the top of
     > this file.

4. **Condition** — do not overwrite a scan-in that already happened:
   `empty(first(body('Get_items_task')?['value'])?['Scan_Start_Time'])`
   - **If yes:** **Update item** on `PM_Machine_Task` — `Task_Status = In Progress`,
     `Scan_Start_Time = utcNow()`
   - **If no:** do nothing.

     > This is what makes a duplicate scan harmless. A technician who scans twice
     > because the page was slow must not restart his own clock — otherwise the
     > job reads four minutes instead of forty, and the pencil-whipping check in
     > Flow 4 fires on an honest technician.

5. **Update item** on `PM_WorkOrder` — if `WO_Status` is `Planned`, set `In Progress`.

   > No `Actual_Start_Date` stamp. The work order's real start is the earliest
   > `Scan_Start_Time` across its tasks, which the report takes directly and which
   > cannot disagree with the tasks it came from.

### The form is one tap

**PM Start has no technician question.** Machine and cell arrive pre-filled from
the sticker, so the whole interaction is: scan, tap *Start PM*, tap *Submit*.

That is a deliberate exception to the rule that every form carries the mandatory
technician dropdown. The dropdown exists because the technicians share one M365
login and it is the only audit trail the system has — but an audit trail has to be
*recorded* to be one, and nothing on `PM_Machine_Task` now holds who started a job.
`Completed_By`, stamped by Flow 4, is the record that matters and the one every
report reads. A dropdown whose answer is thrown away is friction on a sticker
somebody has to tap with an oily glove.

**Every other form keeps the dropdown, mandatory.**

---

# Flow 4 — Checklist Submission

| | |
|---|---|
| **Trigger** | Microsoft Forms → *When a new response is submitted* — form **PM Checklist** |

### Actions

1. **Get response details**
2. **Initialize variable** `varChecklistResults` (Array)
3. **Initialize variable** × 4, one action each: `varNotOkCount` (Integer),
   `varSafetyCriticalCount` (Integer), `varElapsedMin` (Float),
   `varExpectedTotalMin` (Float)
4. **Get items** — rename **`Get items checklist`** — `Checklist_Master`, filter
   `Checklist_ID eq '...' and Active eq 1`, order by `Item_No`
5. **Get items** — rename **`Get items task`** — the open task for this machine
   (needed for `Scan_Start_Time`)
6. **Apply to each** check point from `Get items checklist` — build one object per
   item, pairing the master row with the technician's two answers:

   | Built from the master | Built from the form |
   |---|---|
   | `Item_No`, `Check_Point`, `Check_Type`, `Safety_Critical`, `Expected_Time_Min` | the four-option choice, the free-text box |

   Split the choice into its two facts:

   | Answer | `Result` | `Follow_Up_Required` |
   |---|---|---|
   | OK | `OK` | No |
   | NOT OK — fixed on the spot | `NOT OK` | No |
   | NOT OK — needs follow-up | `NOT OK` | **Yes** |
   | N/A | `NA` | No |

   and route the text box by the master's `Check_Type` — to `Measured_Value` when it
   is `Measurement`, to `Observation` otherwise.

   > **Measurement-type checks must capture a number.** Enforce it here: if
   > `Check_Type = Measurement` and the box is empty, fail the row and ask for a
   > reading. A measurement checklist with no readings is a tick-box exercise; with
   > readings it is condition monitoring.

7. **Apply to each** over `varChecklistResults` — **Create item** in
   `Checklist_Response`, **thirteen fields**: `Response_ID` (§7),
   `Submitted_DateTime = utcNow()`, `WO_No` (from `Get items task`), `Machine_ID`,
   `Checklist_ID`, `Item_No`, `Check_Point`, `Result`, `Measured_Value`,
   `Observation`, `Photo_Link` *(on NOT OK rows only)*, `Tech_ID`,
   `Follow_Up_Required`

   > `WO_No` is taken off the open task, not asked on the form. The technician
   > already scanned the machine; making them retype a work order number only
   > creates a second chance to get it wrong.
   >
   > `Check_Point` is stored as text, not left as a lookup, and that is on purpose:
   > reword the master checklist next year and last year's records still say what
   > was actually checked. No `Cell_ID` — it is reachable through the machine. No
   > `Action_Taken` — `Observation` was already the box people wrote in, and two
   > boxes reliably got one answer.

8. **Set variable** `varNotOkCount` → §9
9. **Set variable** `varSafetyCriticalCount` → §9
10. **Update item** on `PM_Machine_Task` — **three fields**:
    - `Task_Status` → §9 (**In Progress** if any safety-critical NOT OK, else
      **Completed**)
    - `Scan_End_Time = utcNow()`
    - `Completed_By` = the technician from the dropdown

    > Four more used to be written here — `Duration_Min`, `NOT_OK_Count`,
    > `Completion_Date` and `Checklist_Response_ID`. Each was arithmetic or a
    > cross-reference the report does at refresh: end minus start, count the NOT OK
    > rows, the date part of the end time, and the `WO_No` + `Machine_ID` pair that
    > already links a response to its task.

11. **Condition** — safety-critical found → Teams message + email to the supervisor,
    marked as blocking closure
12. **Set variable** `varElapsedMin` → §8, and `varExpectedTotalMin` = summed
    `Expected_Time_Min` from `Get items checklist`
13. **Condition** — `varElapsedMin` less than 30% of `varExpectedTotalMin`
    → email the supervisor, flagged for review

    > A 45-minute checklist closed in 4 minutes is a pencil-whipped PM. The number
    > is no longer stored anywhere, but the flow still works it out in flight and
    > still raises it — because catching this quietly in a report nobody opens is
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

   1. **Get items** — rename **`Get item cell`** on `Cell_Master`, filter
      `Cell_ID eq '@{triggerOutputs()?['body/Cell_ID']}'`
   2. **Update item** on `PM_WorkOrder`: `WO_Status = Completed`,
      `Reset_Applied = true`
   3. **Update item** on `Cell_Master` — **one action, all three fields** (§10):
      `Cum_Std_Hours_Since_PM = 0`, `Last_PM_Date = utcNow()`,
      `Next_PM_Due_Date_Calendar`

      > Integrity rule 3: these three move **together or not at all**. Splitting
      > them across two Update actions creates a window where a failure leaves a
      > zeroed counter with no `Last_PM_Date` — and nothing downstream can tell that
      > apart from a real reset.

   4. **Update item** on `PM_Plan_Calendar` — set `Adherence_Status` to `On Time` or
      `Delayed` by comparing the latest task `Scan_End_Time` against `Planned_Date`
   5. **Send an email (V2)** — cell PM complete, counter reset to zero, next due
      dates on both clocks

### What came out of this flow

Two **Get items** actions and four writes. The work order no longer stores
`Actual_Start_Date`, `Actual_End_Date`, `PM_Duration_Min` or `Reset_Date`, and the
cell no longer stores `Last_PM_WO_No` or a recalculated three-month average. That
retired the `Get items all tasks` read (it existed only to sum durations and find
the earliest start) and the `Get items l3m` read (only for the average).

The rollups did not disappear — the model computes all three from the task rows at
every refresh, so a work order can no longer disagree with the tasks underneath it.
And "which work order zeroed this counter" is answered by SharePoint's own version
history on the cell, for every reset rather than only the most recent.

### Test it

Complete three of four machine tasks and confirm **nothing** resets. Complete the
fourth and confirm all three `Cell_Master` fields change in the same version. This
is UAT-14 and UAT-15.

---

# Flow 6 — Breakdown Report

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Breakdown Report** |

1. **Get response details**
2. **Get items** — rename **`Get item machine`** on `Machine_Master`
3. **Create item** in `Breakdown_Log` — **sixteen fields**: `BD_ID` (§7),
   `Reported_DateTime`, `Machine_ID` and `Cell_ID` pre-filled, `Reported_By_Tech_ID`,
   `Shift`, `Breakdown_Type`, `Symptom`, `Root_Cause`, `Action_Taken`,
   `Response_DateTime`, `Repair_Start`, `Repair_End`, `Production_Loss_Min`,
   `Status`, `Recurrence_Flag`
4. **Condition** — machine criticality A (§11) → **Teams: Post a message** to the
   maintenance channel + email the supervisor

   > Only criticality A alerts immediately. Alerting on every breakdown trains
   > people to mute the channel, and then the one that mattered is muted too.

### What came out

Two actions — the `Get items recent pm` lookup and the `Linked_PM_WO` write-back —
plus four stored columns. `Response_Time_Min` and `MTTR_Min` are subtractions
between timestamps on the same row. `Spare_Used` is *"does a replacement exist
against this breakdown"*. And `Linked_PM_WO` was already redundant: the **Breakdowns
within 7 days of a PM** measure derives that relationship from dates by design, so
that it works on history loaded before any of these flows existed.

> All four timestamps — reported, response, repair start and repair end — stay,
> because nothing can reconstruct them. What was removed is the arithmetic between
> them.

---

# Flow 7 — Spare Replaced

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Spare Replaced** |

1. **Get response details**
2. **Get items** — rename **`Get item spare`** on `Spare_Master`
3. **Create item** in `Spare_Replaced` — **twelve fields**: `Repl_ID` (§7),
   `Replaced_DateTime`, `Source_Type` (PM or Breakdown), `Source_Ref`, `Machine_ID`,
   `Cell_ID`, `Spare_Code`, `Qty_Used`, `Unit_Cost_INR` (§12), **`Failure_Mode`**,
   `Replaced_By`, `Warranty_Claim`

   > `Failure_Mode` is the most valuable column in this table. Repeated
   > "Contamination" on the same part is a filtration problem, not a spares
   > problem, and no amount of buying more parts will fix it. Make it **mandatory**
   > on the form.
   >
   > `Unit_Cost_INR` is copied here at the time of use — that one *is* worth storing,
   > because a price rise next year must not rewrite this year's maintenance cost.
   > `Total_Cost_INR` is not: it is that number times `Qty_Used`, and a stored
   > product is a third figure that can disagree with the two it came from.
   > `Spare_Description` is looked up. `Old_Part_Condition` restated `Failure_Mode`
   > in softer words, and `Expected_Life_Hours` and `Remarks` were read by nothing.

4. **Update item** on `Spare_Master` — decrement `Current_Stock` (§12, with the
   negative-stock clamp)
5. **Condition** — stock at or below minimum (§12) → email stores and the
   supervisor with part, bin, vendor and **lead time**

   > Include the lead time. One below minimum with a 30-day lead time is a
   > different problem from one with a 3-day lead time, and the alert should say
   > which one it is.

### What came out

The `Update item` on `PM_Machine_Task` that set `Spare_Used_Flag = true`. A
replacement row carries `Machine_ID` and `Source_Ref`, so *"was a spare used on this
task"* is a question the model answers by looking, not a flag a flow has to
remember to set — and the flag was wrong every time this flow failed after step 3.

---

# Flow 8 — Abnormality Log

| | |
|---|---|
| **Trigger** | Microsoft Forms → **Abnormality Log** |

1. **Get response details**
2. **Create item** in `Abnormality_Log` — **twelve fields**: `Abn_ID` (§7),
   `Logged_DateTime`, `Machine_ID` and `Cell_ID` pre-filled, `Logged_By`,
   `Category`, `Description`, `Severity`, `Photo_Link`, `Responsibility`,
   `Target_Date`, `Status = Open`

   > The thirteenth column, `Closed_Date`, is filled by whoever closes the item in
   > SharePoint. No flow writes it, and no flow should — a date stamped by a
   > schedule would say the problem was fixed on a day nobody looked at it.
3. **Condition** — `Severity` is `High` (§13):
   - **Teams: Post a message** to the maintenance channel
   - **Send an email (V2)** to the supervisor and the plant head
   - **Delay until** `addHours(utcNow(), 24)`
   - **Get item** again, and **only if still open** (§13) send the follow-up

   > Re-reading before the reminder is the whole point. A reminder that fires
   > whether or not the problem was fixed teaches people to ignore reminders, and
   > then the reminder system is worth nothing.

### What came out

The `Update item` on `PM_Machine_Task` that set `Abnormality_Raised = true`, plus
`Immediate_Action` (the description was already the box people used),
`Closure_Remarks` (`Closed_Date` is the fact that matters) and `Converted_To_WO`
(follow-up is a view-driven decision now — see Flow 9's note below).

---

# Flow 9 — Daily Digest

| | |
|---|---|
| **Trigger** | Recurrence — daily at **06:30 IST** |

06:30, half an hour after the A shift starts, so it reflects a real morning.

1. **Get items** — `Get items overdue cells` (§14)
2. **Get items** — `Get items open wo` (§14)
3. **Get items** — `Get items not scanned` (§14)
4. **Get items** — `Get items overdue abn` (§14)
5. **Get items** — `Get items reset failures` — completed work orders with
   `Reset_Applied eq 0`

   > A completed work order whose counter never zeroed is a flow failure. It shows
   > up nowhere else, so it belongs on the digest.

6. **Condition** — send if something is outstanding **OR it is Monday** (§14)

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

## Where follow-up work went

The corrective work order is now a **decision**, not an overnight job.

`Checklist_Response.Follow_Up_Required` is still captured on the form, and the
**NOT OK Findings** view on `Checklist_Response` is filtered to exactly those rows,
newest first, showing machine, check point, observation and who raised it. The
supervisor works that view and raises a work order when one is warranted.

Three reasons this is better than the flow that did it automatically:

1. **It stopped the PM trigger.** An auto-raised corrective work order was a
   `PM_WorkOrder` row like any other, and Flow 2's open-work-order check could not
   tell it apart from a live PM. One unclosed corrective job on a cell would have
   suppressed that cell's next 4,000-hour trigger for as long as it stayed open —
   silently, with nothing reporting it.
2. **Nobody owned the queue.** A work order raised at 06:00 by a schedule has no
   author to chase it. One raised by a supervisor who looked at the finding does.
3. **It needed a column to remember itself.** `Follow_Up_WO` existed only so the
   same finding could not raise a second work order tomorrow. A view needs no such
   bookkeeping.

If the volume of findings ever makes this unworkable by hand, the flow comes back —
but raising into a **separate list**, not into `PM_WorkOrder`.

---

## Testing the whole chain

Follow `docs/UAT_TEST_CASES.md` in order. The six that must pass before go-live:

| Case | What it proves |
|---|---|
| UAT-03 | A cell crossing 4,000 in the monthly upload raises exactly one work order |
| UAT-07 | The 6-month backstop fires for a low-utilisation cell that never reaches 4,000 |
| UAT-14 | Three of four machines complete and **nothing** resets |
| UAT-15 | The fourth completes and all three `Cell_Master` fields move together |
| UAT-19 | A mid-month reset prorates by working days to 720.00 h |
| UAT-30a | The Monday heartbeat arrives on a clean week — the only way a stopped flow becomes visible |

## Monitoring the flows themselves

- **Power Automate → My flows → Analytics** weekly. A flow with a rising failure
  rate is usually a null that only appears with certain data.
- Set **failure notifications** on all nine to a **shared mailbox**. The built-in
  "send me an email if a flow fails" reaches the owner only, which is no use the day
  the owner's account is the thing that broke.
- The digest's reset-failure section is your canary for Flow 5 having half-worked,
  which is the failure that costs the most and announces itself the least.
- **The Monday heartbeat is your canary for the flows themselves.** No digest on a
  Monday means they have stopped — most likely a broken connection on the owning
  account. Check `My flows` for a disabled flow or an "Invalid connection" banner.
