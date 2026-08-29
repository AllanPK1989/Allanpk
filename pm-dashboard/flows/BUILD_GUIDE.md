# Power Automate — Build Guide

Six flows. Flow 2 owns the scheduling rule; the other five keep the system honest.

> Generated from `flows/definitions/*.json` by `scripts/build_flow_guide.py`, so the guide and the definitions cannot drift. `scripts/validate_flows.py` checks both.

## Before you start

1. Create the flows in a **solution**, not in *My flows*. Solutions are what make the flows movable between environments later; retrofitting that is painful.
2. Add connection references for **SharePoint**, **Office 365 Outlook**, **Microsoft Teams**, **Excel Online (Business)** and **Approvals**.
3. Every flow reads the site URL from an environment variable rather than a hard-coded string. Create `SharePointSiteUrl` first.
4. Turn on failure notifications on all six (⋯ ▸ Settings ▸ Notify on failure). A flow that fails silently is worse than no flow.

## Reading this guide

Each action is listed with the name to give it. **Names matter** — the expressions reference other actions by name, so a renamed action breaks everything downstream. Indented bullets are actions nested inside a condition or a loop.

---

## Flow 1 — Validate Standard Hours Upload

> Rejects a bad file before it can reach the ledger.
>
> The implausibility check (a value more than 3x the cell baseline) is worth adding once you have a few months of real data to set the multiplier from.
>

### Trigger

- `When_a_file_is_created` — **When a file is created (properties only)** (sharepointonline)
  - `folderId`: `@parameters('StdHoursFolderId')`
  - `inferContentType`: `True`

### Actions

- `Compose_file_name` — **Compose**
  <br>*The uploaded file name, which carries the month.*
  - Inputs: `@triggerOutputs()?['body/{FilenameWithExtension}']`
- `Compose_month_key` — **Compose**
  <br>*Cell_Standard_Hours_2026_09.xlsx -> 2026-09*
  - Inputs: `@replace(replace(replace(outputs('Compose_file_name'), 'Cell_Standard_Hours_', ''), '.xlsx', ''), '_', '-')`
- `Check_file_name` — **Condition**
  <br>*Reject anything that is not the agreed file name before it touches the ledger.*
  - Condition: `{"and": [{"startsWith": ["@outputs('Compose_file_name')", "Cell_Standard_Hours_"]}, {"endsWith": ["@toLower(outputs('Compose_file_name'))", ".xlsx"]}, {"equals": ["@length(outputs('Compose_month_key'))", 7]}, {"not": {"contains": ["@toUpper(outputs('Compose_file_name'))", "TEMPLATE"]}}]}`
  - *then:*
    - `Placeholder_name_ok` — **Compose**
      - Inputs: `Name accepted: @{outputs('Compose_month_key')}`
  - *else:*
    - `Mail_bad_name` — **Send an email (V2)** (office365)
      - `emailMessage/To`: `@parameters('UploaderEmail')`
      - `emailMessage/Subject`: `PM system: standard hours file rejected`
      - `emailMessage/Body`: `<p>The file <b>@{outputs('Compose_file_name')}</b> was not processed. The name must be exactly Cell_Standard_Hours_YYYY_MM.xlsx (for example Cell_Standard_Hours_2026_09.xlsx). Rename it and upload again.</p>`
      - `emailMessage/Importance`: `Normal`
    - `Stop_bad_name` — **Terminate**
      - Status: `Failed`, message: *File name does not match Cell_Standard_Hours_YYYY_MM.xlsx*
- `List_uploaded_rows` — **Get items** (excelonlinebusiness)
  <br>*Reads the named table tblStdHours. A renamed sheet or table fails here.*
  - `source`: `me`
  - `drive`: `@parameters('DocumentLibraryDriveId')`
  - `file`: `@triggerOutputs()?['body/{Identifier}']`
  - `table`: `tblStdHours`
- `Get_active_cells` — **Get items** (sharepointonline)
  - `table`: `Cell_Master`
  - `$filter`: `Active eq 'Yes'`
  - `$top`: `500`
- `Filter_rows_wrong_month` — **Filter array**
  <br>*Any row whose MonthKey disagrees with the file name.*
  - From: `@body('List_uploaded_rows')?['value']`
  - Where: `@not(equals(item()?['MonthKey'], outputs('Compose_month_key')))`
- `Filter_rows_bad_value` — **Filter array**
  <br>*Blank or negative standard hours.*
  - From: `@body('List_uploaded_rows')?['value']`
  - Where: `@or(equals(item()?['StdHours'], null), less(float(coalesce(item()?['StdHours'], -1)), 0))`
- `Select_uploaded_cell_ids` — **Select**
  <br>*Flatten to a plain array of CellIDs so the next step is a simple contains().*
  - From: `@body('List_uploaded_rows')?['value']` → `@item()?['CellID']`
- `Filter_missing_cells` — **Filter array**
  <br>*Active cells with no row in the upload. A missing cell never accrues hours and would silently never be scheduled.*
  - From: `@body('Get_active_cells')?['value']`
  - Where: `@not(contains(body('Select_uploaded_cell_ids'), item()?['CellID']))`
- `Check_content` — **Condition**
  <br>*All three checks must pass. A half-processed file is worse than a rejected one.*
  - Condition: `{"and": [{"equals": ["@length(body('Filter_rows_wrong_month'))", 0]}, {"equals": ["@length(body('Filter_rows_bad_value'))", 0]}, {"equals": ["@length(body('Filter_missing_cells'))", 0]}]}`
  - *then:*
    - `Compose_std_hours_payload` — **Compose**
      <br>*Handed to the scheduler so it never has to touch Excel.*
      - Inputs: `@body('List_uploaded_rows')?['value']`
    - `Run_scheduler` — **Run a child flow**
      <br>*Calls Flow 2. Keeping the rule in one flow means it can be re-run for back-load and restatement without duplicating it.*
      - Child flow: `@parameters('SchedulerFlowId')`
      - `MonthKey`: `@outputs('Compose_month_key')`
      - `Mode`: `Normal`
      - `StdHoursJson`: `@string(outputs('Compose_std_hours_payload'))`
  - *else:*
    - `Mail_validation_failed` — **Send an email (V2)** (office365)
      - `emailMessage/To`: `@parameters('UploaderEmail')`
      - `emailMessage/Subject`: `PM system: standard hours file rejected - @{outputs('Compose_month_key')}`
      - `emailMessage/Body`: `<p>The upload was not processed.<br><br>Rows with the wrong MonthKey: <b>@{length(body('Filter_rows_wrong_month'))}</b><br>Rows with blank or negative StdHours: <b>@{length(body('Filter_rows_bad_value'))}</b><br>Active cells missing from the file: <b>@{length(body('Filter_missing_cells'))}</b><br><br>Correct the file and upload it again with the same name.</p>`
      - `emailMessage/Importance`: `Normal`
    - `Stop_validation_failed` — **Terminate**
      - Status: `Failed`, message: *Upload content failed validation - see the email for the counts*

### Environment variables this flow needs

| Name | Default | What it is |
|------|---------|------------|
| `SharePointSiteUrl` | `https://contoso.sharepoint.com/sites/PMSystem` | Root URL of the PMSystem site |
| `StdHoursFolderId` | `/Shared Documents/02 Standard Hours` | Folder the monthly upload lands in |
| `DocumentLibraryDriveId` | `` | Drive id of Shared Documents, for the Excel action |
| `UploaderEmail` | `production.planning@example.com` | Who to chase when an upload is missing or wrong |
| `SchedulerFlowId` | `` | The child flow id of Flow 2 |

---

## Flow 2 — Monthly PM Scheduler

> THE scheduling rule lives here. Change it here and in nowhere else.
>
> Runs as a child flow so Flow 1 can call it for a normal month and a person can call it directly for Backload and Restate.
>
> Concurrency on both loops must be 1. The machine index is shared state.
>
> Backload: call once per historical month, oldest first, and skip work order creation - historical PMs were done on paper.
>
> Restate: delete ledger rows from that month forward, then replay month by month.
>

### Trigger

- `manual` — **Manually trigger / PowerApps**

### Actions

- `Compose_prev_month_key` — **Compose**
  - Inputs: `@{formatDateTime(subtractFromTime(concat(triggerBody()?['MonthKey'], '-01'), 1, 'Month'), 'yyyy-MM')}`
- `Compose_std_hours` — **Compose**
  <br>*Flow 1 already read and validated the Excel, so the scheduler never touches it.*
  - Inputs: `@json(triggerBody()?['StdHoursJson'])`
- `Init_machine_index` — **Initialize variable**
  - `MachineIndex` (integer) = `0`
- `Init_created` — **Initialize variable**
  - `WorkOrdersCreated` (integer) = `0`
- `Get_default_interval` — **Get items** (sharepointonline)
  - `table`: `PM_Config`
  - `$filter`: `ConfigKey eq 'DefaultPMIntervalStdHrs'`
  - `$top`: `1`
- `Compose_default_interval` — **Compose**
  <br>*The 4000 lives in PM_Config so the rule can be retuned without editing a flow.*
  - Inputs: `@if(empty(body('Get_default_interval')?['value']), 4000, int(first(body('Get_default_interval')?['value'])?['ConfigValue']))`
- `Check_already_processed` — **Get items** (sharepointonline)
  <br>*Idempotency guard: a retried run must not double-schedule a cell.*
  - `table`: `PM_Hour_Ledger`
  - `$filter`: `MonthKey eq '@{triggerBody()?['MonthKey']}'`
  - `$top`: `1`
- `Stop_if_duplicate` — **Condition**
  - Condition: `{"and": [{"greater": ["@length(body('Check_already_processed')?['value'])", 0]}, {"not": {"equals": ["@triggerBody()?['Mode']", "Restate"]}}]}`
  - *then:*
    - `Stop_duplicate` — **Terminate**
      - Status: `Cancelled`, message: *Ledger rows already exist for this month. Re-run with Mode = Restate to reprocess.*
- `Get_active_cells` — **Get items** (sharepointonline)
  - `table`: `Cell_Master`
  - `$filter`: `Active eq 'Yes'`
  - `$orderby`: `CellID asc`
  - `$top`: `500`
- `Get_previous_ledger` — **Get items** (sharepointonline)
  - `table`: `PM_Hour_Ledger`
  - `$filter`: `MonthKey eq '@{outputs('Compose_prev_month_key')}' and Scenario eq 'Actual'`
  - `$top`: `500`
- `For_each_cell` — **Apply to each**
  <br>*Concurrency must stay at 1 - the machine index variable is shared state.*
  - Over: `@body('Get_active_cells')?['value']`
  - **Concurrency must be set to 1** (Settings ▸ Concurrency Control)
  - *then:*
    - `Filter_previous_ledger_row` — **Filter array**
      <br>*Last month's row for this cell - the carry-over lives here.*
      - From: `@body('Get_previous_ledger')?['value']`
      - Where: `@equals(item()?['CellID'], items('For_each_cell')?['CellID'])`
    - `Filter_std_hours_row` — **Filter array**
      - From: `@outputs('Compose_std_hours')`
      - Where: `@equals(item()?['CellID'], items('For_each_cell')?['CellID'])`
    - `Compose_opening` — **Compose**
      <br>*Carry-over from the previous cycle, else last month's closing, else zero.*
      - Inputs: `@if(empty(body('Filter_previous_ledger_row')), 0, float(coalesce(first(body('Filter_previous_ledger_row'))?['CarryOverAfterPM'], first(body('Filter_previous_ledger_row'))?['ClosingStdHrs'], 0)))`
    - `Compose_added` — **Compose**
      - Inputs: `@if(empty(body('Filter_std_hours_row')), 0, float(coalesce(first(body('Filter_std_hours_row'))?['StdHours'], 0)))`
    - `Compose_closing` — **Compose**
      - Inputs: `@add(float(outputs('Compose_opening')), float(outputs('Compose_added')))`
    - `Get_last_completed_PM` — **Get items** (sharepointonline)
      - `table`: `PM_WorkOrders`
      - `$filter`: `CellID eq '@{items('For_each_cell')?['CellID']}' and Status eq 'Completed'`
      - `$orderby`: `ActualEndDate desc`
      - `$top`: `1`
    - `Compose_months_since` — **Compose**
      <br>*999 when the cell has never had a PM, so the backstop fires.*
      - Inputs: `@if(empty(body('Get_last_completed_PM')?['value']), 999, sub(add(mul(int(formatDateTime(concat(triggerBody()?['MonthKey'], '-01'), 'yyyy')), 12), int(formatDateTime(concat(triggerBody()?['MonthKey'], '-01'), 'MM'))), add(mul(int(formatDateTime(first(body('Get_last_completed_PM')?['value'])?['ActualEndDate'], 'yyyy')), 12), int(formatDateTime(first(body('Get_last_completed_PM')?['value'])?['ActualEndDate'], 'MM')))))`
    - `Compose_threshold` — **Compose**
      - Inputs: `@if(equals(coalesce(items('For_each_cell')?['PMIntervalStdHrs'], 0), 0), int(outputs('Compose_default_interval')), int(items('For_each_cell')?['PMIntervalStdHrs']))`
    - `Compose_backstop` — **Compose**
      - Inputs: `@if(equals(coalesce(items('For_each_cell')?['CalendarBackstopMonths'], 0), 0), 12, int(items('For_each_cell')?['CalendarBackstopMonths']))`
    - `Compose_hours_due` — **Compose**
      - Inputs: `@greaterOrEquals(float(outputs('Compose_closing')), float(outputs('Compose_threshold')))`
    - `Compose_calendar_due` — **Compose**
      - Inputs: `@greaterOrEquals(int(outputs('Compose_months_since')), int(outputs('Compose_backstop')))`
    - `Compose_triggered` — **Compose**
      - Inputs: `@or(bool(outputs('Compose_hours_due')), bool(outputs('Compose_calendar_due')))`
    - `Compose_trigger_type` — **Compose**
      <br>*Hours wins the label when both fire in the same month.*
      - Inputs: `@if(bool(outputs('Compose_hours_due')), 'Std Hours', if(bool(outputs('Compose_calendar_due')), 'Calendar Backstop', ''))`
    - `Compose_carry_over` — **Compose**
      <br>*Hours past the threshold are never lost - they open the next cycle.*
      - Inputs: `@if(bool(outputs('Compose_triggered')), max(0, sub(float(outputs('Compose_closing')), float(outputs('Compose_threshold')))), float(outputs('Compose_closing')))`
    - `Create_ledger_row` — **Create item** (sharepointonline)
      <br>*A row every month, triggered or not. A gap in the ledger is a gap nobody can explain later.*
      - `table`: `PM_Hour_Ledger`
      - `item/Title`: `@{concat(items('For_each_cell')?['CellID'], ' ', triggerBody()?['MonthKey'])}`
      - `item/MonthKey`: `@{triggerBody()?['MonthKey']}`
      - `item/CellID`: `@{items('For_each_cell')?['CellID']}`
      - `item/CellName`: `@{items('For_each_cell')?['CellName']}`
      - `item/OpeningStdHrs`: `@{outputs('Compose_opening')}`
      - `item/StdHoursAdded`: `@{outputs('Compose_added')}`
      - `item/ClosingStdHrs`: `@{outputs('Compose_closing')}`
      - `item/PMIntervalStdHrs`: `@{outputs('Compose_threshold')}`
      - `item/PMTriggered`: `@{if(bool(outputs('Compose_triggered')), 'Yes', 'No')}`
      - `item/TriggerType`: `@{outputs('Compose_trigger_type')}`
      - `item/CarryOverAfterPM`: `@{outputs('Compose_carry_over')}`
      - `item/MonthsSinceLastPM`: `@{outputs('Compose_months_since')}`
      - `item/Scenario`: `Actual`
    - `If_triggered` — **Condition**
      <br>*The whole cell goes together: one work order per active machine.*
      - Condition: `{"equals": ["@bool(outputs('Compose_triggered'))", true]}`
      - *then:*
        - `Get_machines_in_cell` — **Get items** (sharepointonline)
          - `table`: `Machine_Master`
          - `$filter`: `CellID eq '@{items('For_each_cell')?['CellID']}' and Active eq 'Yes'`
          - `$orderby`: `MachineID asc`
          - `$top`: `200`
        - `Get_previous_cycles` — **Get items** (sharepointonline)
          <br>*Cycle number = how many times this cell has tripped before, plus this one.*
          - `table`: `PM_Hour_Ledger`
          - `$filter`: `CellID eq '@{items('For_each_cell')?['CellID']}' and PMTriggered eq 'Yes'`
          - `$top`: `500`
        - `Compose_cycle_id` — **Compose**
          - Inputs: `@{concat(items('For_each_cell')?['CellID'], '-C', formatNumber(add(length(body('Get_previous_cycles')?['value']), 1), '00'))}`
        - `Get_area_technicians` — **Get items** (sharepointonline)
          - `table`: `Technician_Master`
          - `$filter`: `PrimaryArea eq '@{items('For_each_cell')?['Area']}' and Active eq 'Yes'`
          - `$orderby`: `TechID asc`
          - `$top`: `100`
        - `Get_checklist_tasks` — **Get items** (sharepointonline)
          <br>*Only used for the task count stamped on the work order.*
          - `table`: `PM_Checklist_Master`
          - `$top`: `500`
        - `Reset_machine_index` — **Set variable**
          - `MachineIndex` = `0`
        - `For_each_machine` — **Apply to each**
          <br>*One work order per active machine in the cell.*
          - Over: `@body('Get_machines_in_cell')?['value']`
          - **Concurrency must be set to 1** (Settings ▸ Concurrency Control)
          - *then:*
            - `Increment_machine_index` — **Increment variable**
              <br>*There is no loop index in Power Automate, so keep one. This is why the loop must run with concurrency 1.*
              - `MachineIndex` = `1`
            - `Compose_planned_date` — **Compose**
              <br>*Spread the cell's machines across the month instead of dumping them all on the 1st.*
              - Inputs: `@{formatDateTime(addDays(concat(triggerBody()?['MonthKey'], '-01'), sub(int(div(mul(int(formatDateTime(subtractFromTime(addToTime(concat(triggerBody()?['MonthKey'], '-01'), 1, 'Month'), 1, 'Day'), 'dd')), variables('MachineIndex')), add(length(body('Get_machines_in_cell')?['value']), 1))), 1)), 'yyyy-MM-dd')}`
            - `Compose_assigned_tech` — **Compose**
              <br>*Round-robin across technicians whose PrimaryArea matches the cell.*
              - Inputs: `@if(empty(body('Get_area_technicians')?['value']), null, body('Get_area_technicians')?['value'][mod(variables('MachineIndex'), length(body('Get_area_technicians')?['value']))])`
            - `Create_work_order` — **Create item** (sharepointonline)
              <br>*One work order per machine. TriggerType and TriggerStdHrs are stamped on so months later anyone can see why this job existed.*
              - `table`: `PM_WorkOrders`
              - `item/Title`: `@{items('For_each_machine')?['MachineID']}`
              - `item/WOID`: `@{concat('WO-', substring(guid(), 0, 8))}`
              - `item/CycleID`: `@{outputs('Compose_cycle_id')}`
              - `item/CellID`: `@{items('For_each_cell')?['CellID']}`
              - `item/MachineID`: `@{items('For_each_machine')?['MachineID']}`
              - `item/MachineName`: `@{items('For_each_machine')?['MachineName']}`
              - `item/PMType`: `PM-4000`
              - `item/TriggerType`: `@{outputs('Compose_trigger_type')}`
              - `item/TriggerStdHrs`: `@{outputs('Compose_closing')}`
              - `item/PlanMonth`: `@{triggerBody()?['MonthKey']}`
              - `item/PlannedDate`: `@{outputs('Compose_planned_date')}`
              - `item/DueDate`: `@{formatDateTime(subtractFromTime(addToTime(concat(triggerBody()?['MonthKey'], '-01'), 1, 'Month'), 1, 'Day'), 'yyyy-MM-dd')}`
              - `item/AssignedTechID`: `@{outputs('Compose_assigned_tech')?['TechID']}`
              - `item/AssignedTechName`: `@{outputs('Compose_assigned_tech')?['TechName']}`
              - `item/Shift`: `@{outputs('Compose_assigned_tech')?['Shift']}`
              - `item/Status`: `Scheduled`
              - `item/ChecklistTotalTasks`: `@{length(body('Get_checklist_tasks')?['value'])}`
              - `item/StdMinutes`: `@{items('For_each_machine')?['PMStdMinutes']}`
              - `item/MachineQRScanned`: `No`
        - `Increment_created` — **Increment variable**
          - `WorkOrdersCreated` = `@length(body('Get_machines_in_cell')?['value'])`
- `Respond_summary` — **Respond to a PowerApp or flow**

### Environment variables this flow needs

| Name | Default | What it is |
|------|---------|------------|
| `SharePointSiteUrl` | `https://contoso.sharepoint.com/sites/PMSystem` | Root URL of the PMSystem site |

---

## Flow 3 — Overdue Sweep

> Runs nightly. Deferred is a decision with an approver; Overdue is a failure. Keeping them apart is what makes the compliance number arguable-with rather than argued-about.
>

### Trigger

- `Every_night` — **Recurrence**

### Actions

- `Get_grace_days` — **Get items** (sharepointonline)
  - `table`: `PM_Config`
  - `$filter`: `ConfigKey eq 'OverdueGraceDays'`
  - `$top`: `1`
- `Compose_cutoff` — **Compose**
  - Inputs: `@{formatDateTime(subtractFromTime(utcNow(), if(empty(body('Get_grace_days')?['value']), 0, int(first(body('Get_grace_days')?['value'])?['ConfigValue'])), 'Day'), 'yyyy-MM-dd')}`
- `Get_lapsed_work_orders` — **Get items** (sharepointonline)
  - `table`: `PM_WorkOrders`
  - `$filter`: `(Status eq 'Scheduled' or Status eq 'In Progress') and DueDate lt '@{outputs('Compose_cutoff')}'`
  - `$top`: `2000`
- `For_each_lapsed` — **Apply to each**
  <br>*Status is set by this sweep, never by a person. Overdue is a fact, not an opinion.*
  - Over: `@body('Get_lapsed_work_orders')?['value']`
  - *then:*
    - `Mark_overdue` — **Update item** (sharepointonline)
      - `table`: `PM_WorkOrders`
      - `id`: `@{items('For_each_lapsed')?['ID']}`
      - `item/Status`: `Overdue`
- `Check_any_overdue` — **Condition**
  <br>*One digest a day, not one message per work order. A channel nobody reads is worse than no channel.*
  - Condition: `{"greater": ["@length(body('Get_lapsed_work_orders')?['value'])", 0]}`
  - *then:*
    - `Post_digest` — **Post message in a chat or channel** (teams)
      - `poster`: `Flow bot`
      - `location`: `Channel`
      - `body/recipient/groupId`: `@parameters('TeamsGroupId')`
      - `body/recipient/channelId`: `@parameters('TeamsChannelId')`
      - `body/messageBody`: `<p><b>@{length(body('Get_lapsed_work_orders')?['value'])} PM work order(s) are now overdue.</b><br>Oldest first on the Execution page of the dashboard.</p>`

### Environment variables this flow needs

| Name | Default | What it is |
|------|---------|------------|
| `SharePointSiteUrl` | `https://contoso.sharepoint.com/sites/PMSystem` | Root URL of the PMSystem site |
| `TeamsGroupId` | `` | Team the digest is posted to |
| `TeamsChannelId` | `` | Channel the digest is posted to |

---

## Flow 4 — Abnormality Escalation

> A separate weekly digest flow for items open past 30 days is worth adding once the log has volume. The ageing measure is already on the dashboard.
>

### Trigger

- `When_an_abnormality_is_logged` — **When an item is created** (sharepointonline)
  - `table`: `Abnormality_Log`

### Actions

- `Check_high_severity` — **Condition**
  <br>*High severity goes to a person immediately. Everything else waits for the Monday digest.*
  - Condition: `{"equals": ["@triggerOutputs()?['body/Severity/Value']", "High"]}`
  - *then:*
    - `Mail_head` — **Send an email (V2)** (office365)
      - `emailMessage/To`: `@parameters('MaintenanceHeadEmail')`
      - `emailMessage/Subject`: `HIGH severity abnormality - @{triggerOutputs()?['body/MachineName']}`
      - `emailMessage/Body`: `<p><b>@{triggerOutputs()?['body/MachineName']}</b> (@{triggerOutputs()?['body/CellName']})<br>Category: @{triggerOutputs()?['body/Category/Value']}<br>Reported by: @{triggerOutputs()?['body/ReportedByName']}<br>@{triggerOutputs()?['body/Description']}<br><br>Photo is attached to the item in the Abnormality Log.</p>`
      - `emailMessage/Importance`: `Normal`
    - `Post_teams` — **Post message in a chat or channel** (teams)
      - `poster`: `Flow bot`
      - `location`: `Channel`
      - `body/recipient/groupId`: `@parameters('TeamsGroupId')`
      - `body/recipient/channelId`: `@parameters('TeamsChannelId')`
      - `body/messageBody`: `<p><b>HIGH severity abnormality</b><br>@{triggerOutputs()?['body/MachineName']} - @{triggerOutputs()?['body/Description']}</p>`

### Environment variables this flow needs

| Name | Default | What it is |
|------|---------|------------|
| `SharePointSiteUrl` | `https://contoso.sharepoint.com/sites/PMSystem` | Root URL of the PMSystem site |
| `MaintenanceHeadEmail` | `maintenance.head@example.com` | Approver below the spare limit; abnormality escalation |
| `TeamsGroupId` | `` | Team the digest is posted to |
| `TeamsChannelId` | `` | Channel the digest is posted to |

---

## Flow 5 — Spare Approval

> Issued is deliberately not set by this flow. Requested, approved and consumed are three different facts and the dashboard shows the gaps between them.
>

### Trigger

- `When_a_spare_is_requested` — **When an item is created** (sharepointonline)
  - `table`: `SparePart_Requests`

### Actions

- `Get_approval_limit` — **Get items** (sharepointonline)
  - `table`: `PM_Config`
  - `$filter`: `ConfigKey eq 'SpareApprovalLimitINR'`
  - `$top`: `1`
- `Compose_limit` — **Compose**
  - Inputs: `@if(empty(body('Get_approval_limit')?['value']), 25000, float(first(body('Get_approval_limit')?['value'])?['ConfigValue']))`
- `Compose_approver` — **Compose**
  <br>*Above the limit it goes to the Plant Head. The app warns the technician before submit so the delay is not a surprise.*
  - Inputs: `@if(greater(float(coalesce(triggerOutputs()?['body/TotalCostINR'], 0)), float(outputs('Compose_limit'))), parameters('PlantHeadEmail'), parameters('MaintenanceHeadEmail'))`
- `Start_and_wait_for_approval` — **Start and wait for an approval** (approvals)
  <br>*The Approvals connector keeps the decision auditable, which a mailed yes/no does not.*
  - `approvalType`: `Basic`
  - `ApprovalCreationInput/title`: `Spare request @{triggerOutputs()?['body/RequestID']} - @{triggerOutputs()?['body/PartName']}`
  - `ApprovalCreationInput/assignedTo`: `@outputs('Compose_approver')`
  - `ApprovalCreationInput/details`: `Machine: @{triggerOutputs()?['body/MachineName']}
Part: @{triggerOutputs()?['body/PartNo']} @{triggerOutputs()?['body/PartName']}
Quantity: @{triggerOutputs()?['body/QtyRequested']}
Value: INR @{triggerOutputs()?['body/TotalCostINR']}
Urgency: @{triggerOutputs()?['body/Urgency/Value']}
Raised from: @{triggerOutputs()?['body/SourceType']} @{triggerOutputs()?['body/SourceID']}`
- `Record_outcome` — **Condition**
  <br>*Stores sets Issued when the part physically leaves the counter. A flow must not claim that a part was handed over.*
  - Condition: `{"equals": ["@outputs('Start_and_wait_for_approval')?['body/outcome']", "Approve"]}`
  - *then:*
    - `Set_approved` — **Update item** (sharepointonline)
      - `table`: `SparePart_Requests`
      - `id`: `@{triggerOutputs()?['body/ID']}`
      - `item/Status`: `Approved`
      - `item/ApprovedDate`: `@{formatDateTime(utcNow(), 'yyyy-MM-dd')}`
      - `item/ApprovedBy`: `@{outputs('Compose_approver')}`
  - *else:*
    - `Set_rejected` — **Update item** (sharepointonline)
      - `table`: `SparePart_Requests`
      - `id`: `@{triggerOutputs()?['body/ID']}`
      - `item/Status`: `Rejected`
      - `item/RejectionReason`: `@{outputs('Start_and_wait_for_approval')?['body/responses'][0]['comments']}`

### Environment variables this flow needs

| Name | Default | What it is |
|------|---------|------------|
| `SharePointSiteUrl` | `https://contoso.sharepoint.com/sites/PMSystem` | Root URL of the PMSystem site |
| `MaintenanceHeadEmail` | `maintenance.head@example.com` | Approver below the spare limit; abnormality escalation |
| `PlantHeadEmail` | `plant.head@example.com` | Approver above the spare limit |

---

## Flow 6 — Upload Reminder

> Two lines of logic that protect the whole system. Without the upload, counters freeze and nothing is ever scheduled.
>
> Copy the Plant Head on the 8th-of-the-month run once you have seen how often the 5th is missed.
>

### Trigger

- `On_the_5th_and_8th` — **Recurrence**

### Actions

- `Compose_target_month` — **Compose**
  <br>*Chasing last month's file.*
  - Inputs: `@{formatDateTime(subtractFromTime(utcNow(), 1, 'Month'), 'yyyy_MM')}`
- `List_uploaded_files` — **Get files (properties only)** (sharepointonline)
  - `table`: `@parameters('StdHoursLibraryId')`
  - `$top`: `500`
- `Filter_this_month` — **Filter array**
  - From: `@body('List_uploaded_files')?['value']`
  - Where: `@contains(coalesce(item()?['{Name}'], ''), concat('Cell_Standard_Hours_', outputs('Compose_target_month')))`
- `Chase_if_missing` — **Condition**
  - Condition: `{"equals": ["@length(body('Filter_this_month'))", 0]}`
  - *then:*
    - `Mail_reminder` — **Send an email (V2)** (office365)
      - `emailMessage/To`: `@parameters('UploaderEmail')`
      - `emailMessage/Subject`: `Action needed: standard hours for @{outputs('Compose_target_month')} not uploaded`
      - `emailMessage/Body`: `<p>The PM system has no standard-hours file for <b>@{outputs('Compose_target_month')}</b>.<br><br>Until it is uploaded, no cell accrues hours and no PM will be scheduled for any of them - while the dashboard still shows green.<br><br>Upload <b>Cell_Standard_Hours_@{outputs('Compose_target_month')}.xlsx</b> to the 02 Standard Hours folder.</p>`
      - `emailMessage/Importance`: `Normal`

### Environment variables this flow needs

| Name | Default | What it is |
|------|---------|------------|
| `SharePointSiteUrl` | `https://contoso.sharepoint.com/sites/PMSystem` | Root URL of the PMSystem site |
| `StdHoursLibraryId` | `Shared Documents` | Library holding the monthly uploads |
| `UploaderEmail` | `production.planning@example.com` | Who to chase when an upload is missing or wrong |

---

## After you build them

1. Run **Flow 2** by hand with `Mode = Backload`, once per historical month, oldest first, using the history back-load workbook. Skip work order creation for those months — historical PMs were done on paper.
2. Reconcile: does the ledger's last-PM date per cell match the maintenance register? Fix that before going further, because every carry-over depends on it.
3. Upload one real monthly file and watch Flow 1 → Flow 2 run end to end.
4. Check the work orders that appear against what you expected. If a cell you expected did not trip, look at its ledger row: opening, added, closing, threshold. The row tells you which of the four is wrong.
