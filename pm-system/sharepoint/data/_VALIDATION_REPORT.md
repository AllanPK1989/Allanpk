# Data Validation Report

Generated: 2026-08-30 13:53
Source: `input`  ->  Output: `sharepoint/data`

**0 error(s), 0 warning(s).**

An ERROR means the row would break a documented integrity rule once it is in
SharePoint. Fix it in the source workbook and re-run - do not load past it.
A WARN is something worth knowing that does not block the load.

## Row counts

| # | List | Rows | Columns |
|---|---|---:|---:|
| 1 | `Cell_Master` | 8 | 15 |
| 2 | `Technician_Master` | 6 | 8 |
| 3 | `Spare_Master` | 15 | 13 |
| 4 | `Checklist_Master` | 51 | 11 |
| 5 | `Machine_Master` | 30 | 18 |
| 6 | `Plant_Calendar` | 730 | 5 |
| 7 | `StdHours_Monthly` | 96 | 8 |
| 8 | `PM_WorkOrder` | 51 | 20 |
| 9 | `PM_Machine_Task` | 193 | 16 |
| 10 | `Checklist_Response` | 997 | 16 |
| 11 | `Scan_Log` | 336 | 9 |
| 12 | `Breakdown_Log` | 88 | 21 |
| 13 | `Spare_Request` | 64 | 19 |
| 14 | `Spare_Replaced` | 58 | 17 |
| 15 | `Abnormality_Log` | 44 | 16 |
| 16 | `PM_Plan_Calendar` | 55 | 12 |

**Total rows: 2,822**

## Errors

None. All error checks passed.

## Warnings

None. All warning checks passed.

## Rules that were checked

| Rule | What it protects |
|---|---|
| `R0-duplicate-pk` / `R0-blank-pk` | Primary keys unique and present. A repeated key silently merges two machines' history. |
| `FK-unmatched` | Every foreign key resolves to a master row. An unmatched `Cell_ID` is the single most common monthly-upload failure. |
| `R1-task-count` | Task rows per work order equal `Machines_In_Scope`. A short work order closes early and resets the counter it should not have. |
| `R2-premature-close` | No work order is Completed while a task is Pending or In Progress. |
| `R3-reset-incomplete` / `R3-completed-no-reset` | The reset quartet moves together: counter, date, work order number, flag. |
| `R4-orphan-response` | Every checklist response has a parent machine task. |
| `R5-cost-mismatch` | `Total_Cost_INR` = `Qty_Used` x `Unit_Cost_INR` on every row. |
| `R6-active-blank` | No master row has a blank `Active` - blank is neither in nor out of scope. |
| `duplicate-month-cell` | One std-hours row per cell per month. Two rows double-count into the counter. |
| `machine-count-mismatch` | `Cell_Master.Machine_Count` equals the active machines in that cell. |
| `trigger-not-fired` | A cell over its trigger with no open work order. |
| `bad-date` / `bad-datetime` / `bad-number` / `bad-boolean` | Type coercion succeeded on every cell. |
| `month-as-date` | `YYYY-MM` columns did not get converted to dates by Excel. |
