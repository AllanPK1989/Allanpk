# Data Validation Report

Generated: 2026-09-14 12:52
Source: `input`  ->  Output: `sharepoint/data`

**0 error(s), 0 warning(s), 13 column group(s) excluded by design.**

An ERROR means the row would break a documented integrity rule once it is in
SharePoint. Fix it in the source workbook and re-run - do not load past it.
A WARN is something worth knowing that does not block the load.

## Row counts

| # | List | Rows | Columns |
|---|---|---:|---:|
| 1 | `Cell_Master` | 8 | 12 |
| 2 | `Technician_Master` | 6 | 5 |
| 3 | `Spare_Master` | 15 | 10 |
| 4 | `Checklist_Master` | 51 | 8 |
| 5 | `Machine_Master` | 30 | 10 |
| 6 | `Plant_Calendar` | 730 | 3 |
| 7 | `StdHours_Monthly` | 96 | 6 |
| 8 | `PM_WorkOrder` | 51 | 13 |
| 9 | `PM_Machine_Task` | 193 | 9 |
| 10 | `Checklist_Response` | 997 | 13 |
| 11 | `Breakdown_Log` | 88 | 16 |
| 12 | `Spare_Replaced` | 58 | 12 |
| 13 | `Abnormality_Log` | 44 | 13 |
| 14 | `PM_Plan_Calendar` | 55 | 8 |

**Total rows: 2,422**

## Errors

None. All error checks passed.

## Warnings

None. All warning checks passed.

## Columns excluded by design

| List | Rule | Detail |
|---|---|---|
| `Cell_Master` | `excluded-by-design` | source columns not loaded: ['Plant', 'Last_PM_WO_No', 'Avg_Monthly_Std_Hours_L3M'] |
| `Technician_Master` | `excluded-by-design` | source columns not loaded: ['Default_Shift', 'Contact_No', 'Role_Scope'] |
| `Spare_Master` | `excluded-by-design` | source columns not loaded: ['ABC_Class', 'FMR_Class', 'Preferred_Vendor'] |
| `Checklist_Master` | `excluded-by-design` | source columns not loaded: ['Checklist_Name', 'Tool_Required', 'Frequency'] |
| `Machine_Master` | `excluded-by-design` | source columns not loaded: ['Cell_Name', 'Make', 'Model', 'Year_Installed', 'Checklist_Form_URL', 'Breakdown_Form_URL', 'Spare_Request_Form_URL', 'Abnormality_Form_URL'] |
| `StdHours_Monthly` | `excluded-by-design` | source columns not loaded: ['Cell_Name', 'Uploaded_By'] |
| `PM_WorkOrder` | `excluded-by-design` | source columns not loaded: ['Cell_Name', 'Planned_Start_Date', 'Lead_Tech_ID', 'Actual_Start_Date', 'Actual_End_Date', 'PM_Duration_Min', 'Reset_Date'] |
| `PM_Machine_Task` | `excluded-by-design` | source columns not loaded: ['Assigned_Tech_ID', 'Duration_Min', 'Checklist_Response_ID', 'NOT_OK_Count', 'Abnormality_Raised', 'Spare_Used_Flag', 'Completion_Date'] |
| `Checklist_Response` | `excluded-by-design` | source columns not loaded: ['Cell_ID', 'Action_Taken', 'Follow_Up_WO'] |
| `Breakdown_Log` | `excluded-by-design` | source columns not loaded: ['Response_Time_Min', 'MTTR_Min', 'Spare_Used', 'Linked_PM_WO', 'Remarks'] |
| `Spare_Replaced` | `excluded-by-design` | source columns not loaded: ['Spare_Description', 'Total_Cost_INR', 'Old_Part_Condition', 'Expected_Life_Hours', 'Remarks'] |
| `Abnormality_Log` | `excluded-by-design` | source columns not loaded: ['Immediate_Action', 'Closure_Remarks', 'Converted_To_WO'] |
| `PM_Plan_Calendar` | `excluded-by-design` | source columns not loaded: ['Cell_Name', 'Planned_Shift', 'Estimated_Duration_Hrs', 'Frozen_Date'] |

## Rules that were checked

| Rule | What it protects |
|---|---|
| `R0-duplicate-pk` / `R0-blank-pk` | Primary keys unique and present. A repeated key silently merges two machines' history. |
| `FK-unmatched` | Every foreign key resolves to a master row. An unmatched `Cell_ID` is the single most common monthly-upload failure. |
| `R1-task-count` | Task rows per work order equal `Machines_In_Scope`. A short work order closes early and resets the counter it should not have. |
| `R2-premature-close` | No work order is Completed while a task is Pending or In Progress. |
| `R3-completed-no-reset` | A completed work order whose counter was never zeroed. |
| `R4-orphan-response` | Every checklist response has a parent machine task. |
| `R6-active-blank` | No master row has a blank `Active` - blank is neither in nor out of scope. |
| `duplicate-month-cell` | One std-hours row per cell per month. Two rows double-count into the counter. |
| `machine-count-mismatch` | `Cell_Master.Machine_Count` equals the active machines in that cell. |
| `trigger-not-fired` | A cell over its trigger with no open work order. |
| `bad-date` / `bad-datetime` / `bad-number` / `bad-boolean` | Type coercion succeeded on every cell. |
| `month-as-date` | `YYYY-MM` columns did not get converted to dates by Excel. |
