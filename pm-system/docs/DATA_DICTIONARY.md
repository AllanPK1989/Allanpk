# Data Dictionary — EPQPL PM System

**14 lists, 138 columns.** Sheet names and column names here are **identical** to the
SharePoint list and column names, so moving from the dummy Excel files to SharePoint is
a source swap, not a rebuild.

**"Filled by" legend** — `Setup` = one-time master data you maintain ·
`Monthly` = your Excel upload · `Flow` = written automatically by Power Automate ·
`Form` = typed by the technician on a Microsoft Form · `Calc` = derived in Power BI.

**Golden rule:** a technician should never type anything a machine already knows.
Every column marked `Form` below is deliberately short — everything else is
pre-filled from the QR code or written by a flow.

## What is deliberately *not* here

This started at 16 lists and 224 columns. **58 columns and 2 whole lists were cut**,
against three rules applied in order:

| | Rule | Example of what went |
|---|---|---|
| 1 | **Derivable goes.** If a flow computed and stored it, and the report could work it out at read time, the stored copy is a liability — one more thing that can be left wrong by a flow that failed halfway. | `MTTR_Min`, `Duration_Min`, `Total_Cost_INR`, `NOT_OK_Count` |
| 2 | **Denormalised goes.** A copy of master data on a fact row is a second place the same fact can be wrong. | `Cell_Name` on five different lists |
| 3 | **Speculative goes.** Nothing reads it and no rule needs it. | `Preferred_Vendor`, `Tool_Required`, `Role_Scope` |

Two exceptions are load-bearing and worth knowing about, because they look like
rule 1 and rule 2 violations and are not:

- **`Next_PM_Due_Date_Calendar`** is stored even though it is `Last_PM_Date` plus a
  few months, because the **Cells Due This Month** view filters on it and CAML cannot
  do arithmetic.
- **`Check_Point`** and **`Unit_Cost_INR`** are copies of master values, kept so that
  rewording a checklist or raising a price does not rewrite last year's records.

Every cut is listed with its reason in `tools/essential_schema.py`, which is also what
the loader and the Power BI model read — so this dictionary cannot silently drift away
from what actually gets provisioned.

---

## 1. `Cell_Master` — the heart of the system

One row per production cell. This is where the 4,000-hour counter lives.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Cell_ID` | Text (PK) | Setup | Primary key. Every fact table joins here. Never reuse or renumber an ID — history breaks silently if you do. |
| `Cell_Name` | Text | Setup | Display label on every visual and email. |
| `Process_Area` | Choice | Setup | Groups cells (Element / Assembly / Filling / Curing / Testing / Packing) for area-wise compliance reporting and for balancing the monthly PM load across areas. |
| `Machine_Count` | Number | Setup | The expected number of machine tasks a work order should contain. Flow 2 compares the tasks it created against this — a mismatch means a machine was deactivated or missed, and it raises an alert. |
| `PM_Trigger_Hours` | Number | Setup | The 4,000 threshold, held per cell so you can tune one cell without changing code. A hard-coded 4000 anywhere in the system is a defect. |
| `Calendar_Backstop_Months` | Number | Setup | The 6-month maximum interval. Protects low-utilisation cells that would otherwise never reach 4,000 hours. |
| `Cum_Std_Hours_Since_PM` | Number | Flow | **The running counter.** Flow 1 adds each month's hours to it; Flow 5 sets it to 0 on cell PM completion. Drives the trigger, the RAG status and the forecast. |
| `Last_PM_Date` | Date | Flow | Stamped at reset. Shown on the QR machine hub, and used for the calendar backstop test. |
| `Next_PM_Due_Date_Calendar` | Date | Calc/Flow | `Last_PM_Date + Calendar_Backstop_Months`. Displayed alongside the hours-based projection so planners see both clocks. |
| `Owner_Supervisor` | Text | Setup | Who gets the escalation email when the cell goes overdue. |
| `Criticality` | Choice A/B/C | Setup | Prioritises the queue when two cells come due in the same week and you only have technicians for one. |
| `Active` | Yes/No | Setup | Set to No instead of deleting a decommissioned cell. Deleting orphans all its history. |

## 2. `Machine_Master` — one row per machine, carries the QR

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Machine_ID` | Text (PK) | Setup | Encoded in the QR sticker. Every scan, checklist, breakdown and spare record carries it. |
| `Machine_Name` | Text | Setup | Printed on the label and shown on the hub so the technician confirms he scanned the right machine. |
| `Cell_ID` | Text (FK) | Setup | **The link that makes cell-level PM work.** Flow 2 uses it to decide which machines belong in a cell's work order. |
| `Machine_Family` | Text | Setup | Groups similar equipment for reliability comparison ("all presses") independent of cell. |
| `Serial_No` | Text | Setup | Warranty claims and vendor calls — the first thing a vendor asks for. |
| `Location_Tag` | Text | Setup | Physical bay so a new technician can find the machine. |
| `Checklist_ID` | Text (FK) | Setup | Selects which of the 9 checklist sets applies. Change this one cell to re-assign a machine to a different checklist — no form rebuild. |
| `QR_Payload_URL` | Hyperlink | Setup | **What the QR sticker actually encodes.** Points to the Machine Hub filtered list view. Generated once, printed once, never edited casually — a change here means re-printing stickers. |
| `Criticality` | Choice A/B/C | Setup | Drives whether a breakdown raises an immediate Teams alert. |
| `Active` | Yes/No | Setup | An inactive machine is excluded when Flow 2 builds machine tasks, so a machine under overhaul does not block the cell from closing. |

## 3. `Checklist_Master` — what "doing a PM" actually means

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Checklist_ID` | Text | Setup | Groups items into a set. Matches `Machine_Master.Checklist_ID`. |
| `Item_No` | Number | Setup | Fixed sequence. Keeps the Forms question order and the report Pareto aligned. Never renumber — insert as 3.1 style or append at the end. |
| `Check_Point` | Text | Setup | The instruction the technician reads. Written as an action, not a noun. |
| `Check_Type` | Choice | Setup | Visual / Measurement / Functional. Measurement items are the ones that must capture a number in `Measured_Value` — the flow enforces it. |
| `Acceptance_Standard` | Text | Setup | The pass criterion. **Without this a checklist is decoration** — "check the pressure" with no limit means every technician invents his own. |
| `Safety_Critical` | Yes/No | Setup | A NOT OK on a safety-critical item blocks the task from closing and escalates immediately, regardless of severity chosen. |
| `Expected_Time_Min` | Number | Setup | Summed per machine to estimate PM duration, which drives the man-hour forecast on the planning page. |
| `Active` | Yes/No | Setup | Retire a check point without losing its history in past responses. |

## 4. `Technician_Master`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Tech_ID` | Text (PK) | Setup | The value behind the mandatory dropdown on every form. **This is your entire audit trail** given the shared login. |
| `Tech_Name` | Text | Setup | What appears in the dropdown and on reports. |
| `Skill_Level` | Choice | Setup | Senior / Junior / Trainee. Used to check that a trainee is not the sole signatory on a criticality-A machine. |
| `Trade` | Choice | Setup | Mechanical / Electrical. Balances mixed-trade PM assignment. |
| `Active` | Yes/No | Setup | Removes a leaver from the dropdown without erasing their completed work. |

## 5. `Spare_Master`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Spare_Code` | Text (PK) | Setup | Joins requests and replacements to cost and stock. |
| `Spare_Description` | Text | Setup | Dropdown label on the request form. |
| `Category` | Choice | Setup | Mechanical / Electrical / Pneumatic / Instrument / Utility / Consumable — spend analysis by discipline. |
| `UOM` | Text | Setup | Prevents the classic "2 metres or 2 rolls?" issue. |
| `Unit_Cost_INR` | Currency | Setup | Copied onto the replacement row at the moment of use, which rolls into `Spare Cost per PM`. |
| `Min_Stock` | Number | Setup | Flow 7 alerts when `Current_Stock` drops below it. |
| `Current_Stock` | Number | Flow | Decremented on every replacement. Shown on the request form so a technician knows before asking. |
| `Lead_Time_Days` | Number | Setup | Combined with `Min_Stock` to flag items where a stock-out will stop a PM. |
| `Bin_Location` | Text | Setup | Printed on the issue slip. |
| `Active` | Yes/No | Setup | Hides superseded parts from the dropdown. |

## 6. `StdHours_Upload` (monthly Excel → `StdHours_Monthly` list)

**This is the only file you upload each month.** One row per cell, actual hours
consumed in the month that just ended.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Upload_Month` | Text `YYYY-MM` | Monthly | The month being reported. The flow rejects the file if this month already exists — that is your duplicate-upload guard. |
| `Cell_ID` | Text | Monthly | Matched against `Cell_Master`. An unmatched ID stops the whole file and emails you the bad row rather than importing half of it. |
| `Actual_Std_Hours` | Decimal | Monthly | **The number that drives everything.** Added to `Cum_Std_Hours_Since_PM`, prorated if a PM reset fell inside the month, and stored as history for the 3-month average and the forecast. |
| `Production_Qty` | Number | Monthly | Optional. Lets you sanity-check hours against output and later express PM interval in pieces if you prefer. |
| `Upload_Date` | Date | Monthly | Detects late uploads, which delay every downstream trigger. |
| `Remarks` | Text | Monthly | Explains anomalies — shutdown, extra Sundays, trial run — so a spike is not mistaken for a data error six months later. |

> **The supplied template has eight columns; six are used.** `Cell_Name` is looked up
> from `Cell_Master` — so renaming a cell renames it everywhere at once, instead of in
> every historical row — and `Uploaded_By` duplicates the **Created By** stamp
> SharePoint puts on every item without being asked. Flow 1 ignores both and the Power
> BI archive query reads only the six above, so delete them from the template whenever
> it suits or leave them and fill in two fewer cells a month. Files saved either way
> load correctly.
>
> **Do not rename or reorder the six that remain.** The Excel connector matches by
> column name, and a rename fails silently: the flow runs green, reads nothing, and
> posts a month of zeroes.

## 7. `PM_WorkOrder` — one row per cell PM

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `WO_No` | Text (PK) | Flow | Work order number. The key every machine task, checklist row, spare and photo attaches to. |
| `Cell_ID` | Text (FK) | Flow | Scope of the work order. The name is looked up from `Cell_Master`. |
| `Trigger_Type` | Choice | Flow | Std Hours / Calendar Backstop / Manual. Tells you what proportion of your PM is genuinely usage-driven versus time-driven. If most are Calendar Backstop, your 4,000-hour rule is set too high. |
| `Trigger_Hours_At_Creation` | Number | Flow | The counter value at the moment of trigger. Proves the rule fired correctly and shows overshoot — consistently seeing 4,300 means the monthly upload is too coarse. |
| `WO_Created_Date` | Date | Flow | Start of the ageing clock. |
| `Planned_Month` | Text `YYYY-MM` | Flow | Buckets the work order into a monthly plan. Drives the schedule page. |
| `Planned_End_Date` | Date | Flow | **The commitment.** On-time percentage is measured against it, so this is the number production agrees to. |
| `Priority` | Choice | Flow | High / Medium / Low, seeded from cell criticality and overdue days. |
| `Machines_In_Scope` | Number | Flow | Count of active machines in the cell. The denominator of `Cell Completion %`. |
| `Machines_Completed` | Number | Flow | Incremented on each machine task completion. **When it equals `Machines_In_Scope`, the reset fires.** |
| `WO_Status` | Choice | Flow | Planned / In Progress / Completed / Overdue / Cancelled. Everything on the tracking page keys off this. |
| `Reset_Applied` | Yes/No | Flow | Confirms the counter was actually zeroed. A completed work order with `Reset_Applied = No` is a flow failure — put it on the daily digest. |
| `Remarks` | Text | Form | Cancellation reason, deferral approval, notes. |

## 8. `PM_Machine_Task` — the technician's allotted list

One row per machine per work order. **This table is the technician-facing list.** The
`My Allotted PM List` view filters it to `Task_Status ≠ Completed`; a completed scan
flips the status and the row disappears from their list. That is the "auto-update".

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Task_ID` | Text (PK) | Flow | Line identifier. |
| `WO_No` | Text (FK) | Flow | Parent work order. The all-complete check counts pending rows with this key. |
| `Machine_ID` | Text (FK) | Flow | The machine to be scanned. |
| `Cell_ID` | Text (FK) | Flow | Lets the list be grouped by cell without a lookup. |
| `Task_Status` | Choice | Flow | Pending / In Progress / Completed / Skipped. **The single field that controls the technician's list.** |
| `Scan_Start_Time` | DateTime | Flow | Written when the QR is scanned and "Start PM" submitted. |
| `Scan_End_Time` | DateTime | Flow | Written on checklist submission. |
| `Completed_By` | Text | Form | Technician from the mandatory dropdown. |
| `Skip_Reason` | Text | Form | Mandatory if status is Skipped. **A skipped machine still lets the cell close but flags the work order as partial** — decide this consciously, and review skips monthly, because "machine running, will do next time" repeated four times is how a PM system quietly dies. |

## 9. `Checklist_Response` — one row per check point per machine per PM

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Response_ID` | Text (PK) | Flow | Row key. |
| `Submitted_DateTime` | DateTime | Flow | When the checklist was submitted. |
| `WO_No` | Text (FK) | Flow | Taken off the machine's open task, never typed. |
| `Machine_ID` | Text (FK) | Flow | Pre-filled from the QR. The cell is reachable through it, so it is not stored again here. |
| `Checklist_ID` | Text (FK) | Flow | Pre-filled from the machine, and what the form branches on. |
| `Item_No` | Number | Flow | Which check this row answers. |
| `Check_Point` | Text | Flow | The wording as it stood on the day. Storing the text as well as the number is what keeps an old record readable after the master is reworded. |
| `Result` | Choice | Form | OK / NOT OK / NA. Drives `NOT OK %` and the findings Pareto. |
| `Measured_Value` | Decimal | Form | The reading, for Measurement-type checks. **This is what turns a checklist into condition monitoring** — a bearing running 48, 52, 57 °C across three PMs is a failure you can see coming. |
| `Observation` | Text | Form | What was seen. |
| `Photo_Link` | Hyperlink | Flow | Photo attachment for NOT OK items. Non-negotiable for disputes. |
| `Tech_ID` | Text | Form | Who checked. |
| `Follow_Up_Required` | Yes/No | Form | Puts the finding on the **NOT OK Findings** view, where a supervisor decides whether it needs a work order. |

## 10. `Breakdown_Log`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `BD_ID` | Text (PK) | Flow | Breakdown key. |
| `Reported_DateTime` | DateTime | Flow | Clock starts. |
| `Machine_ID` | Text (FK) | Flow | Pre-filled from the QR. |
| `Cell_ID` | Text (FK) | Flow | Pre-filled from the QR. |
| `Reported_By_Tech_ID` | Text | Form | Reporter. |
| `Shift` | Choice | Form | Shift-wise breakdown pattern; a cluster in C shift is usually a skill or lighting problem, not a machine problem. |
| `Breakdown_Type` | Choice | Form | Mechanical / Electrical / Pneumatic / Hydraulic / Instrumentation / Utility. Directs the trade-wise Pareto and your training plan. |
| `Symptom` | Text | Form | What the operator saw. |
| `Root_Cause` | Text | Form | What was actually wrong. Keeping symptom and cause separate is what makes repeat-failure analysis possible. |
| `Action_Taken` | Text | Form | The fix. |
| `Response_DateTime` | DateTime | Form | Technician arrival. |
| `Repair_Start` | DateTime | Form | Wrench time starts. |
| `Repair_End` | DateTime | Form | Wrench time ends. MTTR is the gap, worked out by the report — it is not stored. |
| `Production_Loss_Min` | Number | Form | Feeds `Downtime Hours` and `Availability %`. Usually longer than MTTR — capture it separately or availability will look flattering and wrong. |
| `Status` | Choice | Form | Open / Closed. |
| `Recurrence_Flag` | Yes/No | Form | Same failure as before. Repeats are your PM improvement backlog. |

## 11. `Spare_Replaced`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Repl_ID` | Text (PK) | Flow | Row key. |
| `Replaced_DateTime` | DateTime | Flow | When fitted. |
| `Source_Type` | Choice | Flow | PM / Breakdown. Separates preventive from reactive spend. |
| `Source_Ref` | Text | Flow | The `WO_No` or `BD_ID` it belongs to. |
| `Machine_ID` | Text (FK) | Flow | Cost per machine. |
| `Cell_ID` | Text (FK) | Flow | Cost per cell. |
| `Spare_Code` | Text (FK) | Form | Part fitted. The description is looked up from `Spare_Master`. |
| `Qty_Used` | Number | Form | Decrements `Current_Stock`. |
| `Unit_Cost_INR` | Currency | Flow | Copied from `Spare_Master` at the time of use, so old records keep their historical price. |
| `Failure_Mode` | Choice | Form | Wear / Fatigue / Electrical burnout / Contamination / Corrosion / Overload / End of rated life / Improper handling. **The most valuable column in this table** — repeated "Contamination" on the same part is a filtration problem, not a spares problem. |
| `Replaced_By` | Text | Form | Technician. |
| `Warranty_Claim` | Yes/No | Form | Flags a claim opportunity that would otherwise be missed. |

## 12. `Abnormality_Log`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Abn_ID` | Text (PK) | Flow | Row key. |
| `Logged_DateTime` | DateTime | Flow | Ageing clock. |
| `Machine_ID` | Text (FK) | Flow | Pre-filled from the QR. |
| `Cell_ID` | Text (FK) | Flow | Pre-filled from the QR. |
| `Logged_By` | Text | Form | Technician. |
| `Category` | Choice | Form | Safety / Quality / Air Leak / Oil Leak / Abnormal Noise / Vibration / Overheating / Contamination / 5S. Air-leak entries feed straight into your compressed-air reduction work. |
| `Description` | Text | Form | What is abnormal. |
| `Severity` | Choice | Form | High / Medium / Low. High triggers immediate escalation and a 24-hour follow-up reminder. |
| `Photo_Link` | Hyperlink | Flow | Evidence. |
| `Responsibility` | Text | Form | Who owns the permanent fix. |
| `Target_Date` | Date | Form | Commitment date. Overdue items appear on the daily digest. |
| `Status` | Choice | Form | Open / In Progress / Closed. |
| `Closed_Date` | Date | Form | When it was actually fixed. Ageing is measured against it. |

## 13. `PM_Plan_Calendar` — the frozen monthly plan

Without this table you can only measure "did we do it", never "did we do it when we
said we would". Freeze the plan on the 25th; adherence is then honest.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Plan_ID` | Text (PK) | Flow | Plan row key. |
| `Plan_Month` | Text `YYYY-MM` | Flow | The plan period. |
| `Cell_ID` | Text (FK) | Flow | Cell planned. |
| `Planned_Date` | Date | Setup | The agreed date, negotiated with production. |
| `Planned_Tech_ID` | Text | Setup | Allocation, and the input to the workload-balance visual. |
| `Plan_Version` | Text | Setup | `V1`, `V1 Forecast`, `V2`. Forecast rows are projections beyond the frozen month and are excluded from adherence. |
| `WO_No` | Text | Flow | Links plan to the actual work order. Blank on forecast rows. |
| `Adherence_Status` | Choice | Flow | On Time / Delayed / Overdue / Cancelled / Forecast. Feeds `Schedule Adherence %`. |


## 14. `Plant_Calendar` — which days the plant actually runs

One row per calendar day. Three columns, and the smallest list here does the most
surprising amount of work.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Calendar_Date` | Date (PK) | Setup | One row per day, generated for the years you load. |
| `Is_Working_Day` | Yes/No | Setup | **The proration divisor.** Flow 1 counts the working days in the month and the working days after a mid-month PM reset, and posts hours in that ratio. |
| `Day_Type` | Choice | Setup | Working / Weekly Off / Holiday / Shutdown. Says *why* a day is not a working day. |

**Why a list and not a formula.** `Actual_Std_Hours` is a capacity figure, so capacity
accrues on the days the plant runs. No expression can know that the plant shut for
Pongal, and a hard-coded "Sundays are off" rule is wrong for four days every January.
Maintaining this list once a year is what keeps the counter honest.

**Maintain it every December**, for the year ahead. If it runs out, Flow 1 divides by
zero — so it terminates as Failed with a message naming the month instead, and
`prepare_sharepoint_data.py` refuses to load a month that has no working days at all.

---
---

## Cross-table integrity rules

1. `PM_Machine_Task` row count for a work order must equal `Machines_In_Scope`.
2. A work order may only be `Completed` when no task is `Pending` or `In Progress`.
3. `Cum_Std_Hours_Since_PM` may only be set to 0 by Flow 5, and only together with
   `Last_PM_Date` and `Next_PM_Due_Date_Calendar`, in a single Update action. All
   three move together or none do. A work order marked `Completed` with
   `Reset_Applied = No` is the visible symptom of this rule being broken, and it has
   its own section on the daily digest.
4. Every `Checklist_Response` must have a parent `PM_Machine_Task`.
5. **A `Completed` work order must have at least one task with a `Scan_End_Time`.**
   The work order no longer stores its own end date — the model takes the latest scan
   across its tasks. That makes a stored rollup impossible to contradict, but it moves
   the failure: a completed work order with nothing scanned out has no date at all and
   drops silently out of `Breakdowns After PM`, `PM On-Time %` and `Avg PM Delay`. A
   missing row reads as good news on all three, which is the wrong direction to fail
   in. See `ASSUMPTIONS.md` §9.1 for what this rule is guarding against.
6. Never delete a master row. Set `Active = No`.

> There used to be a sixth rule — that the stored line total equal quantity times
> unit cost on every row. It retired with the column it policed. A product the
> report computes cannot disagree with its own factors, so there is nothing left
> to check.

`tools/prepare_sharepoint_data.py --strict` enforces all six at load time and refuses
to write a CSV that breaks one.