# Data Dictionary — EPQPL PM System

15 tables. Sheet names and column names here are **identical** to the SharePoint list
and column names, so moving from the dummy Excel files to SharePoint is a source swap,
not a rebuild.

**"Filled by" legend** — `Setup` = one-time master data you maintain ·
`Monthly` = your Excel upload · `Flow` = written automatically by Power Automate ·
`Form` = typed by the technician on a Microsoft Form · `Calc` = derived in Power BI.

**Golden rule:** a technician should never type anything a machine already knows.
Every column marked `Form` below is deliberately short — everything else is
pre-filled from the QR code or written by a flow.

---

## 1. `Cell_Master` — the heart of the system

One row per production cell. This is where the 4,000-hour counter lives.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Cell_ID` | Text (PK) | Setup | Primary key. Every fact table joins here. Never reuse or renumber an ID — history breaks silently if you do. |
| `Cell_Name` | Text | Setup | Display label on every visual and email. |
| `Plant` | Text | Setup | Filter for multi-plant rollout later. Keep it even with one plant. |
| `Process_Area` | Choice | Setup | Groups cells (Element / Assembly / Filling / Curing / Testing / Packing) for area-wise compliance reporting and for balancing the monthly PM load across areas. |
| `Machine_Count` | Number | Setup | The expected number of machine tasks a work order should contain. Flow 2 compares the tasks it created against this — a mismatch means a machine was deactivated or missed, and it raises an alert. |
| `PM_Trigger_Hours` | Number | Setup | The 4,000 threshold, held per cell so you can tune one cell without changing code. A hard-coded 4000 anywhere in the system is a defect. |
| `Calendar_Backstop_Months` | Number | Setup | The 6-month maximum interval. Protects low-utilisation cells that would otherwise never reach 4,000 hours. |
| `Cum_Std_Hours_Since_PM` | Number | Flow | **The running counter.** Flow 1 adds each month's hours to it; Flow 5 sets it to 0 on cell PM completion. Drives the trigger, the RAG status and the forecast. |
| `Last_PM_Date` | Date | Flow | Stamped at reset. Shown on the QR machine hub, and used for the calendar backstop test. |
| `Last_PM_WO_No` | Text | Flow | Back-reference to the work order that caused the last reset. Your audit trail when someone asks "why did this counter go to zero on the 14th?". |
| `Next_PM_Due_Date_Calendar` | Date | Calc/Flow | `Last_PM_Date + Calendar_Backstop_Months`. Displayed alongside the hours-based projection so planners see both clocks. |
| `Avg_Monthly_Std_Hours_L3M` | Number | Flow | Rolling 3-month average consumption. Divides into `Hours to Next PM` to give `Months to PM` and hence `Projected PM Date`. Three months smooths festival shutdowns without going stale. |
| `Owner_Supervisor` | Text | Setup | Who gets the escalation email when the cell goes overdue. |
| `Criticality` | Choice A/B/C | Setup | Prioritises the queue when two cells come due in the same week and you only have technicians for one. |
| `Active` | Yes/No | Setup | Set to No instead of deleting a decommissioned cell. Deleting orphans all its history. |

## 2. `Machine_Master` — one row per machine, carries the QR

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Machine_ID` | Text (PK) | Setup | Encoded in the QR sticker. Every scan, checklist, breakdown and spare record carries it. |
| `Machine_Name` | Text | Setup | Printed on the label and shown on the hub so the technician confirms he scanned the right machine. |
| `Cell_ID` | Text (FK) | Setup | **The link that makes cell-level PM work.** Flow 2 uses it to decide which machines belong in a cell's work order. |
| `Cell_Name` | Text | Setup | Denormalised label for label printing and offline views. |
| `Machine_Family` | Text | Setup | Groups similar equipment for reliability comparison ("all presses") independent of cell. |
| `Make` / `Model` / `Serial_No` | Text | Setup | Spare identification, warranty claims, vendor calls. `Serial_No` is what the vendor asks for first. |
| `Year_Installed` | Number | Setup | Age analysis against breakdown frequency — your evidence base for replacement capex. |
| `Location_Tag` | Text | Setup | Physical bay so a new technician can find the machine. |
| `Checklist_ID` | Text (FK) | Setup | Selects which of the 9 checklist sets applies. Change this one cell to re-assign a machine to a different checklist — no form rebuild. |
| `Checklist_Form_URL` | Hyperlink | Setup | Pre-filled Microsoft Forms link with `Machine_ID` and `Cell_ID` already populated. Rendered as the "Complete Checklist" button on the hub. |
| `Breakdown_Form_URL` | Hyperlink | Setup | Same, for the breakdown form. |
| `Spare_Request_Form_URL` | Hyperlink | Setup | Same, for spare request. |
| `Abnormality_Form_URL` | Hyperlink | Setup | Same, for the abnormality log. |
| `QR_Payload_URL` | Hyperlink | Setup | **What the QR sticker actually encodes.** Points to the Machine Hub filtered list view. Generated once, printed once, never edited casually — a change here means re-printing stickers. |
| `Criticality` | Choice A/B/C | Setup | Drives whether a breakdown raises an immediate Teams alert. |
| `Active` | Yes/No | Setup | An inactive machine is excluded when Flow 2 builds machine tasks, so a machine under overhaul does not block the cell from closing. |

## 3. `Checklist_Master` — what "doing a PM" actually means

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Checklist_ID` | Text | Setup | Groups items into a set. Matches `Machine_Master.Checklist_ID`. |
| `Checklist_Name` | Text | Setup | Title on the printed and digital checklist. |
| `Item_No` | Number | Setup | Fixed sequence. Keeps the Forms question order and the report Pareto aligned. Never renumber — insert as 3.1 style or append at the end. |
| `Check_Point` | Text | Setup | The instruction the technician reads. Written as an action, not a noun. |
| `Check_Type` | Choice | Setup | Visual / Measurement / Functional. Measurement items are the ones that must capture a number in `Measured_Value` — the flow enforces it. |
| `Acceptance_Standard` | Text | Setup | The pass criterion. **Without this a checklist is decoration** — "check the pressure" with no limit means every technician invents his own. |
| `Tool_Required` | Text | Setup | Drives the tool kitting list printed with the work order. |
| `Frequency` | Choice | Setup | Reserved for a future split into monthly/quarterly/annual subsets within one cell PM. |
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
| `Default_Shift` | Choice | Setup | Seeds the planned shift on the PM calendar. |
| `Contact_No` | Text | Setup | Escalation SMS. |
| `Role_Scope` | Text | Setup | What the person is authorised to close. |
| `Active` | Yes/No | Setup | Removes a leaver from the dropdown without erasing their completed work. |

## 5. `Spare_Master`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Spare_Code` | Text (PK) | Setup | Joins requests and replacements to cost and stock. |
| `Spare_Description` | Text | Setup | Dropdown label on the request form. |
| `Category` | Choice | Setup | Mechanical / Electrical / Pneumatic / Instrument / Utility / Consumable — spend analysis by discipline. |
| `UOM` | Text | Setup | Prevents the classic "2 metres or 2 rolls?" issue. |
| `ABC_Class` | Choice | Setup | Value class. Feeds the 9-box ABC-FMR matrix on the spares page. |
| `FMR_Class` | Choice | Setup | Fast / Medium / Rare movement. AR items (high value, rare) are the ones to review; CF items get bulk ordered. |
| `Unit_Cost_INR` | Currency | Setup | Multiplied by `Qty_Used` to give `Total_Cost_INR`, which rolls into `Spare Cost per PM`. |
| `Min_Stock` | Number | Setup | Flow 8 alerts when `Current_Stock` drops below it. |
| `Current_Stock` | Number | Flow | Decremented on every replacement. Shown on the request form so a technician knows before asking. |
| `Lead_Time_Days` | Number | Setup | Combined with `Min_Stock` to flag items where a stock-out will stop a PM. |
| `Bin_Location` | Text | Setup | Printed on the issue slip. |
| `Preferred_Vendor` | Text | Setup | Auto-fills the purchase requisition. |
| `Active` | Yes/No | Setup | Hides superseded parts from the dropdown. |

## 6. `StdHours_Upload` (monthly Excel → `StdHours_Monthly` list)

**This is the only file you upload each month.** One row per cell, actual hours
consumed in the month that just ended.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Upload_Month` | Text `YYYY-MM` | Monthly | The month being reported. The flow rejects the file if this month already exists — that is your duplicate-upload guard. |
| `Cell_ID` | Text | Monthly | Matched against `Cell_Master`. An unmatched ID stops the whole file and emails you the bad row rather than importing half of it. |
| `Cell_Name` | Text | Monthly | Human check only. `Cell_ID` is what matches. |
| `Actual_Std_Hours` | Decimal | Monthly | **The number that drives everything.** Added to `Cum_Std_Hours_Since_PM`, prorated if a PM reset fell inside the month, and stored as history for the 3-month average and the forecast. |
| `Production_Qty` | Number | Monthly | Optional. Lets you sanity-check hours against output and later express PM interval in pieces if you prefer. |
| `Uploaded_By` | Text | Monthly | Accountability for the number. |
| `Upload_Date` | Date | Monthly | Detects late uploads, which delay every downstream trigger. |
| `Remarks` | Text | Monthly | Explains anomalies — shutdown, extra Sundays, trial run — so a spike is not mistaken for a data error six months later. |

## 7. `PM_WorkOrder` — one row per cell PM

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `WO_No` | Text (PK) | Flow | Work order number. The key every machine task, checklist row, spare and photo attaches to. |
| `Cell_ID` / `Cell_Name` | Text | Flow | Scope of the work order. |
| `Trigger_Type` | Choice | Flow | Std Hours / Calendar Backstop / Manual. Tells you what proportion of your PM is genuinely usage-driven versus time-driven. If most are Calendar Backstop, your 4,000-hour rule is set too high. |
| `Trigger_Hours_At_Creation` | Number | Flow | The counter value at the moment of trigger. Proves the rule fired correctly and shows overshoot — consistently seeing 4,300 means the monthly upload is too coarse. |
| `WO_Created_Date` | Date | Flow | Start of the ageing clock. |
| `Planned_Month` | Text `YYYY-MM` | Flow | Buckets the work order into a monthly plan. Drives the schedule page. |
| `Planned_Start_Date` / `Planned_End_Date` | Date | Flow/Setup | The commitment. On-time percentage is measured against `Planned_End_Date`, so this is the number production agrees to. |
| `Lead_Tech_ID` | Text | Flow | Owner of the cell PM. |
| `Priority` | Choice | Flow | High / Medium / Low, seeded from cell criticality and overdue days. |
| `Machines_In_Scope` | Number | Flow | Count of active machines in the cell. The denominator of `Cell Completion %`. |
| `Machines_Completed` | Number | Flow | Incremented on each machine task completion. **When it equals `Machines_In_Scope`, the reset fires.** |
| `WO_Status` | Choice | Flow | Planned / In Progress / Completed / Overdue / Cancelled. Everything on the tracking page keys off this. |
| `Actual_Start_Date` / `Actual_End_Date` | Date | Flow | From the first and last machine scans. Never typed. |
| `PM_Duration_Min` | Number | Flow | Sum of machine task durations. Feeds the man-hour forecast and cost of maintenance. |
| `Reset_Applied` | Yes/No | Flow | Confirms the counter was actually zeroed. A completed work order with `Reset_Applied = No` is a flow failure — put it on the daily digest. |
| `Reset_Date` | Date | Flow | Used by the proration rule in the next monthly upload. |
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
| `Assigned_Tech_ID` | Text | Flow/Setup | Who it is allotted to. Blank means anyone in the team may pick it up. |
| `Task_Status` | Choice | Flow | Pending / In Progress / Completed / Skipped. **The single field that controls the technician's list.** |
| `Scan_Start_Time` | DateTime | Flow | Written when the QR is scanned and "Start PM" submitted. |
| `Scan_End_Time` | DateTime | Flow | Written on checklist submission. |
| `Duration_Min` | Number | Flow | End minus start. Compare against summed `Expected_Time_Min` — a 45-minute checklist closed in 4 minutes is a pencil-whipped PM, and this column is how you catch it. |
| `Checklist_Response_ID` | Text | Flow | Link to the submitted checklist. |
| `NOT_OK_Count` | Number | Flow | Findings on this machine. Drives the follow-up work order and the quality-of-PM measures. |
| `Abnormality_Raised` | Yes/No | Flow | Whether an abnormality was logged during this PM. |
| `Spare_Used_Flag` | Yes/No | Flow | Whether parts were consumed. Links PM cost to the machine. |
| `Completed_By` | Text | Form | Technician from the mandatory dropdown. |
| `Completion_Date` | Date | Flow | Date stamp for reporting. |
| `Skip_Reason` | Text | Form | Mandatory if status is Skipped. **A skipped machine still lets the cell close but flags the work order as partial** — decide this consciously, and review skips monthly, because "machine running, will do next time" repeated four times is how a PM system quietly dies. |

## 9. `Checklist_Response` — one row per check point per machine per PM

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Response_ID` | Text (PK) | Flow | Row key. |
| `Submitted_DateTime` | DateTime | Flow | When the checklist was submitted. |
| `WO_No` / `Machine_ID` / `Cell_ID` / `Checklist_ID` | Text | Flow | Context keys, all pre-filled from the QR — the technician types none of them. |
| `Item_No` / `Check_Point` | Number / Text | Flow | Which check this row answers. Storing the text as well as the number means old records stay readable after the master is edited. |
| `Result` | Choice | Form | OK / NOT OK / NA. Drives `NOT OK %` and the findings Pareto. |
| `Measured_Value` | Decimal | Form | The reading, for Measurement-type checks. **This is what turns a checklist into condition monitoring** — a bearing running 48, 52, 57 °C across three PMs is a failure you can see coming. |
| `Observation` | Text | Form | What was seen. |
| `Photo_Link` | Hyperlink | Flow | Photo attachment for NOT OK items. Non-negotiable for disputes. |
| `Action_Taken` | Text | Form | Corrected on the spot, or deferred. |
| `Tech_ID` | Text | Form | Who checked. |
| `Follow_Up_Required` | Yes/No | Form | Triggers Flow 10 to raise a corrective work order. |
| `Follow_Up_WO` | Text | Flow | The corrective work order raised, closing the loop. |

## 10. `Scan_Log` — raw QR events

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Scan_ID` | Text (PK) | Flow | Event key. |
| `Scan_DateTime` | DateTime | Flow | Event time. |
| `Machine_ID` / `Cell_ID` | Text | Flow | What was scanned. |
| `Tech_ID` | Text | Form | Who scanned. |
| `Scan_Action` | Choice | Flow | Start PM / Complete PM / Breakdown / Spare Request / Abnormality / View. |
| `Device` | Text | Flow | Android / iOS / Kiosk — tells you which shop-floor device is failing when scans stop arriving. |
| `WO_No` | Text | Flow | Work order in force at scan time, if any. |
| `Comments` | Text | Form | Free note. |

*Why keep a raw log at all when tasks already have timestamps? Because it records the
scans that did **not** lead to a completion — the technician who started and walked
away, the machine scanned with no open work order. That gap is where adoption problems
show up first.*

## 11. `Breakdown_Log`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `BD_ID` | Text (PK) | Flow | Breakdown key. |
| `Reported_DateTime` | DateTime | Flow | Clock starts. |
| `Machine_ID` / `Cell_ID` | Text | Flow | Pre-filled from the QR. |
| `Reported_By_Tech_ID` | Text | Form | Reporter. |
| `Shift` | Choice | Form | Shift-wise breakdown pattern; a cluster in C shift is usually a skill or lighting problem, not a machine problem. |
| `Breakdown_Type` | Choice | Form | Mechanical / Electrical / Pneumatic / Hydraulic / Instrumentation / Utility. Directs the trade-wise Pareto and your training plan. |
| `Symptom` | Text | Form | What the operator saw. |
| `Root_Cause` | Text | Form | What was actually wrong. Keeping symptom and cause separate is what makes repeat-failure analysis possible. |
| `Action_Taken` | Text | Form | The fix. |
| `Response_DateTime` | DateTime | Form | Technician arrival. |
| `Repair_Start` / `Repair_End` | DateTime | Form | Wrench time window. |
| `Response_Time_Min` | Number | Calc | Arrival minus report. A team KPI, distinct from repair time. |
| `MTTR_Min` | Number | Calc | Repair end minus repair start. |
| `Production_Loss_Min` | Number | Form | Feeds `Downtime Hours` and `Availability %`. Usually longer than MTTR — capture it separately or availability will look flattering and wrong. |
| `Spare_Used` | Yes/No | Form | Links to `Spare_Replaced`. |
| `Status` | Choice | Form | Open / Closed. |
| `Recurrence_Flag` | Yes/No | Form | Same failure as before. Repeats are your PM improvement backlog. |
| `Linked_PM_WO` | Text | Flow | Set when the breakdown occurs within 7 days of a completed PM on that cell — this is what powers `Breakdowns After PM (7d)`, the measure that tells you whether the PM is effective or cosmetic. |

## 12. `Spare_Request`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Req_ID` | Text (PK) | Flow | Request key. |
| `Request_DateTime` | DateTime | Flow | Ageing and approval lead-time clock. |
| `WO_No` / `Machine_ID` / `Cell_ID` | Text | Flow | Cost attribution to the right machine and work order. |
| `Spare_Code` / `Spare_Description` | Text | Form | What is needed. |
| `Qty_Requested` | Number | Form | How many. |
| `Requested_By` | Text | Form | Technician dropdown. |
| `Urgency` | Choice | Form | Normal / Urgent / Breakdown. Breakdown-urgency requests skip the queue and alert immediately. |
| `Reason` | Choice | Form | PM replacement / Breakdown repair / Predictive finding / Stock top-up. Splits planned from unplanned spend — the number your finance team will ask for. |
| `Approval_Status` | Choice | Flow | Pending / Approved / Rejected, written back by the Approvals action. |
| `Approved_By` / `Approved_Date` | Text / Date | Flow | Approval audit. |
| `Issue_Status` / `Issued_Qty` / `Issue_Date` | Choice / Number / Date | Form | Store issue confirmation. The gap between approval and issue is where PMs actually stall. |
| `Stock_At_Request` | Number | Flow | Snapshot of stock at request time — evidence for a min-stock revision. |
| `Remarks` | Text | Form | Notes. |

## 13. `Spare_Replaced`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Repl_ID` | Text (PK) | Flow | Row key. |
| `Replaced_DateTime` | DateTime | Flow | When fitted. |
| `Source_Type` | Choice | Flow | PM / Breakdown. Separates preventive from reactive spend. |
| `Source_Ref` | Text | Flow | The `WO_No` or `BD_ID` it belongs to. |
| `Machine_ID` / `Cell_ID` | Text | Flow | Cost per machine and per cell. |
| `Spare_Code` / `Spare_Description` | Text | Form | Part fitted. |
| `Qty_Used` | Number | Form | Decrements `Current_Stock`. |
| `Unit_Cost_INR` | Currency | Flow | Copied from `Spare_Master` at the time of use, so old records keep their historical price. |
| `Total_Cost_INR` | Currency | Flow | `Qty_Used × Unit_Cost_INR`. Rolls up to `Spare Cost per PM`. |
| `Old_Part_Condition` | Choice | Form | Worn / Damaged / Burnt / Leaking / End of life. |
| `Failure_Mode` | Choice | Form | Wear / Fatigue / Electrical burnout / Contamination / Corrosion / Overload / End of rated life / Improper handling. **The most valuable column in this table** — repeated "Contamination" on the same part is a filtration problem, not a spares problem. |
| `Replaced_By` | Text | Form | Technician. |
| `Expected_Life_Hours` | Number | Form | Actual observed life. Compare against it over time to set genuine replacement intervals instead of guessing. |
| `Warranty_Claim` | Yes/No | Form | Flags a claim opportunity that would otherwise be missed. |
| `Remarks` | Text | Form | Notes. |

## 14. `Abnormality_Log`

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Abn_ID` | Text (PK) | Flow | Row key. |
| `Logged_DateTime` | DateTime | Flow | Ageing clock. |
| `Machine_ID` / `Cell_ID` | Text | Flow | Pre-filled from the QR. |
| `Logged_By` | Text | Form | Technician. |
| `Category` | Choice | Form | Safety / Quality / Air Leak / Oil Leak / Abnormal Noise / Vibration / Overheating / Contamination / 5S. Air-leak entries feed straight into your compressed-air reduction work. |
| `Description` | Text | Form | What is abnormal. |
| `Severity` | Choice | Form | High / Medium / Low. High triggers immediate escalation and a 24-hour follow-up reminder. |
| `Photo_Link` | Hyperlink | Flow | Evidence. |
| `Immediate_Action` | Text | Form | Containment done on the spot. |
| `Responsibility` | Text | Form | Who owns the permanent fix. |
| `Target_Date` | Date | Form | Commitment date. Overdue items appear on the daily digest. |
| `Status` | Choice | Form | Open / In Progress / Closed. |
| `Closed_Date` / `Closure_Remarks` | Date / Text | Form | Closure evidence. |
| `Converted_To_WO` | Yes/No | Flow | Whether it became a corrective work order. |

## 15. `PM_Plan_Calendar` — the frozen monthly plan

Without this table you can only measure "did we do it", never "did we do it when we
said we would". Freeze the plan on the 25th; adherence is then honest.

| Column | Type | Filled by | What the system does with it |
|---|---|---|---|
| `Plan_ID` | Text (PK) | Flow | Plan row key. |
| `Plan_Month` | Text `YYYY-MM` | Flow | The plan period. |
| `Cell_ID` / `Cell_Name` | Text | Flow | Cell planned. |
| `Planned_Date` | Date | Setup | The agreed date, negotiated with production. |
| `Planned_Shift` | Choice | Setup | Which shift the window falls in. |
| `Planned_Tech_ID` | Text | Setup | Allocation, and the input to the workload-balance visual. |
| `Estimated_Duration_Hrs` | Decimal | Calc | Summed `Expected_Time_Min` across the cell's machines. This is the number you show production when asking for a window. |
| `Plan_Version` | Text | Setup | `V1`, `V1 Forecast`, `V2`. Forecast rows are projections beyond the frozen month and are excluded from adherence. |
| `Frozen_Date` | Date | Flow | When the plan was locked. After this, changes create a V2 row rather than editing V1. |
| `WO_No` | Text | Flow | Links plan to the actual work order. Blank on forecast rows. |
| `Adherence_Status` | Choice | Flow | On Time / Delayed / Overdue / Cancelled / Forecast. Feeds `Schedule Adherence %`. |

---

## Cross-table integrity rules

1. `PM_Machine_Task` row count for a work order must equal `Machines_In_Scope`.
2. A work order may only be `Completed` when no task is `Pending` or `In Progress`.
3. `Cum_Std_Hours_Since_PM` may only be set to 0 by Flow 5, and only together with
   `Last_PM_Date`, `Last_PM_WO_No` and `Reset_Applied = Yes`. All four move together
   or none do.
4. Every `Checklist_Response` must have a parent `PM_Machine_Task`.
5. `Total_Cost_INR` must equal `Qty_Used × Unit_Cost_INR` on every row.
6. Never delete a master row. Set `Active = No`.
