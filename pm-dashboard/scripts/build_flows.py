#!/usr/bin/env python3
"""
build_flows.py - generates the six Power Automate workflow definitions.

Output is Logic Apps workflow-definition JSON, the same shape Power Automate
shows under Peek code. It is the authoritative statement of what each flow does;
flows/BUILD_GUIDE.md turns it into click-by-click build steps.

Run:  python3 scripts/build_flows.py
Out:  flows/definitions/*.json
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "flows", "definitions")
os.makedirs(OUT, exist_ok=True)

SP = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
XL = "/providers/Microsoft.PowerApps/apis/shared_excelonlinebusiness"
O365 = "/providers/Microsoft.PowerApps/apis/shared_office365"
APPR = "/providers/Microsoft.PowerApps/apis/shared_approvals"

SCHEMA = ("https://schema.management.azure.com/providers/Microsoft.Logic/"
          "schemas/2016-06-01/workflowdefinition.json#")


# ---------------------------------------------------------------------------
# action helpers
# ---------------------------------------------------------------------------

def act(kind, inputs, after=None, desc=None, metadata=None):
    a = {"type": kind, "inputs": inputs, "runAfter": after or {}}
    if desc:
        a["description"] = desc
    if metadata:
        a["metadata"] = metadata
    return a


def sp(op, params, after=None, desc=None, api=SP, conn="shared_sharepointonline"):
    return act("OpenApiConnection", {
        "host": {"connectionName": conn, "operationId": op, "apiId": api},
        "parameters": params,
        "authentication": "@parameters('$authentication')",
    }, after, desc)


def compose(value, after=None, desc=None):
    return act("Compose", value, after, desc)


def init_var(name, vtype, value, after=None, desc=None):
    return act("InitializeVariable",
               {"variables": [{"name": name, "type": vtype, "value": value}]},
               after, desc)


def set_var(name, value, after=None, desc=None):
    return act("SetVariable", {"name": name, "value": value}, after, desc)


def cond(expression, if_true, if_false=None, after=None, desc=None):
    a = {"type": "If", "expression": expression, "actions": if_true,
         "runAfter": after or {}}
    if if_false:
        a["else"] = {"actions": if_false}
    if desc:
        a["description"] = desc
    return a


def foreach(over, actions, after=None, desc=None, concurrency=None):
    a = {"type": "Foreach", "foreach": over, "actions": actions,
         "runAfter": after or {}}
    if concurrency is not None:
        a["runtimeConfiguration"] = {"concurrency": {"repetitions": concurrency}}
    if desc:
        a["description"] = desc
    return a


def terminate(status, code=None, message=None, after=None):
    inp = {"runStatus": status}
    if message:
        inp["runError"] = {"code": code or "ValidationFailed", "message": message}
    return act("Terminate", inp, after)


def mail(to, subject, body, after=None, desc=None):
    return act("OpenApiConnection", {
        "host": {"connectionName": "shared_office365",
                 "operationId": "SendEmailV2", "apiId": O365},
        "parameters": {"emailMessage/To": to, "emailMessage/Subject": subject,
                       "emailMessage/Body": "<p>" + body + "</p>",
                       "emailMessage/Importance": "Normal"},
        "authentication": "@parameters('$authentication')",
    }, after, desc)


def wf(triggers, actions, params=None):
    p = {"$connections": {"defaultValue": {}, "type": "Object"},
         "$authentication": {"defaultValue": {}, "type": "SecureObject"}}
    p.update(params or {})
    return {"definition": {
        "$schema": SCHEMA,
        "contentVersion": "1.0.0.0",
        "parameters": p,
        "triggers": triggers,
        "actions": actions,
        "outputs": {},
    }}


def save(n, name, obj, notes):
    obj["_name"] = name
    obj["_notes"] = notes
    path = os.path.join(OUT, f"Flow_{n}_{name.replace(' ', '_')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    n_actions = len(obj["definition"]["actions"])
    print(f"  Flow {n}  {name:<34} {n_actions} top-level actions")


SITE = "@parameters('SharePointSiteUrl')"


# ===========================================================================
# Shared expressions
# ===========================================================================
MONTH_START = "concat(triggerBody()?['MonthKey'], '-01')"
MONTH_END = (f"formatDateTime(subtractFromTime(addToTime({MONTH_START}, 1, 'Month'), "
             "1, 'Day'), 'yyyy-MM-dd')")
DAYS_IN_MONTH = (f"int(formatDateTime(subtractFromTime(addToTime({MONTH_START}, 1, 'Month'), "
                 "1, 'Day'), 'dd'))")

# whole months between two dates, computed as year*12 + month so it is exact
def months_between(a, b):
    def ym(x):
        return f"add(mul(int(formatDateTime({x}, 'yyyy')), 12), int(formatDateTime({x}, 'MM')))"
    return f"sub({ym(b)}, {ym(a)})"


# ===========================================================================
# FLOW 1 - Validate Standard Hours Upload
# ===========================================================================
f1_actions = {
    "Compose_file_name": compose("@triggerOutputs()?['body/{FilenameWithExtension}']", None,
                                 "The uploaded file name, which carries the month."),
    "Compose_month_key": compose(
        "@replace(replace(replace(outputs('Compose_file_name'), "
        "'Cell_Standard_Hours_', ''), '.xlsx', ''), '_', '-')",
        {"Compose_file_name": ["Succeeded"]},
        "Cell_Standard_Hours_2026_09.xlsx -> 2026-09"),
    "Check_file_name": cond(
        {"and": [
            {"startsWith": ["@outputs('Compose_file_name')", "Cell_Standard_Hours_"]},
            {"endsWith": ["@toLower(outputs('Compose_file_name'))", ".xlsx"]},
            {"equals": ["@length(outputs('Compose_month_key'))", 7]},
            {"not": {"contains": ["@toUpper(outputs('Compose_file_name'))", "TEMPLATE"]}},
        ]},
        {"Placeholder_name_ok": compose("Name accepted: @{outputs('Compose_month_key')}")},
        {
            "Mail_bad_name": mail(
                "@parameters('UploaderEmail')",
                "PM system: standard hours file rejected",
                "The file <b>@{outputs('Compose_file_name')}</b> was not processed. "
                "The name must be exactly Cell_Standard_Hours_YYYY_MM.xlsx "
                "(for example Cell_Standard_Hours_2026_09.xlsx). "
                "Rename it and upload again."),
            "Stop_bad_name": terminate(
                "Failed", "BadFileName",
                "File name does not match Cell_Standard_Hours_YYYY_MM.xlsx",
                {"Mail_bad_name": ["Succeeded"]}),
        },
        {"Compose_month_key": ["Succeeded"]},
        "Reject anything that is not the agreed file name before it touches the ledger."),

    "List_uploaded_rows": act("OpenApiConnection", {
        "host": {"connectionName": "shared_excelonlinebusiness",
                 "operationId": "GetItems", "apiId": XL},
        "parameters": {"source": "me", "drive": "@parameters('DocumentLibraryDriveId')",
                       "file": "@triggerOutputs()?['body/{Identifier}']",
                       "table": "tblStdHours"},
        "authentication": "@parameters('$authentication')",
    }, {"Check_file_name": ["Succeeded"]},
        "Reads the named table tblStdHours. A renamed sheet or table fails here."),

    "Get_active_cells": sp("GetItems", {
        "dataset": SITE, "table": "Cell_Master",
        "$filter": "Active eq 'Yes'", "$top": 500,
    }, {"List_uploaded_rows": ["Succeeded"]}),

    "Filter_rows_wrong_month": act("Query", {
        "from": "@body('List_uploaded_rows')?['value']",
        "where": "@not(equals(item()?['MonthKey'], outputs('Compose_month_key')))",
    }, {"Get_active_cells": ["Succeeded"]},
        "Any row whose MonthKey disagrees with the file name."),

    "Filter_rows_bad_value": act("Query", {
        "from": "@body('List_uploaded_rows')?['value']",
        "where": "@or(equals(item()?['StdHours'], null), less(float(coalesce(item()?['StdHours'], -1)), 0))",
    }, {"Filter_rows_wrong_month": ["Succeeded"]},
        "Blank or negative standard hours."),

    "Select_uploaded_cell_ids": act("Select", {
        "from": "@body('List_uploaded_rows')?['value']",
        "select": "@item()?['CellID']",
    }, {"Filter_rows_bad_value": ["Succeeded"]},
        "Flatten to a plain array of CellIDs so the next step is a simple contains()."),

    "Filter_missing_cells": act("Query", {
        "from": "@body('Get_active_cells')?['value']",
        "where": "@not(contains(body('Select_uploaded_cell_ids'), item()?['CellID']))",
    }, {"Select_uploaded_cell_ids": ["Succeeded"]},
        "Active cells with no row in the upload. A missing cell never accrues hours "
        "and would silently never be scheduled."),

    "Check_content": cond(
        {"and": [
            {"equals": ["@length(body('Filter_rows_wrong_month'))", 0]},
            {"equals": ["@length(body('Filter_rows_bad_value'))", 0]},
            {"equals": ["@length(body('Filter_missing_cells'))", 0]},
        ]},
        {
            "Compose_std_hours_payload": compose(
                "@body('List_uploaded_rows')?['value']",
                None, "Handed to the scheduler so it never has to touch Excel."),
            "Run_scheduler": act("Workflow", {
                "host": {"workflowReferenceName": "@parameters('SchedulerFlowId')"},
                "body": {
                    "MonthKey": "@outputs('Compose_month_key')",
                    "Mode": "Normal",
                    "StdHoursJson": "@string(outputs('Compose_std_hours_payload'))",
                },
            }, {"Compose_std_hours_payload": ["Succeeded"]},
                "Calls Flow 2. Keeping the rule in one flow means it can be re-run "
                "for back-load and restatement without duplicating it."),
        },
        {
            "Mail_validation_failed": mail(
                "@parameters('UploaderEmail')",
                "PM system: standard hours file rejected - @{outputs('Compose_month_key')}",
                "The upload was not processed.<br><br>"
                "Rows with the wrong MonthKey: <b>@{length(body('Filter_rows_wrong_month'))}</b><br>"
                "Rows with blank or negative StdHours: <b>@{length(body('Filter_rows_bad_value'))}</b><br>"
                "Active cells missing from the file: <b>@{length(body('Filter_missing_cells'))}</b><br><br>"
                "Correct the file and upload it again with the same name."),
            "Stop_validation_failed": terminate(
                "Failed", "ValidationFailed",
                "Upload content failed validation - see the email for the counts",
                {"Mail_validation_failed": ["Succeeded"]}),
        },
        {"Filter_missing_cells": ["Succeeded"]},
        "All three checks must pass. A half-processed file is worse than a rejected one."),
}

save(1, "Validate Standard Hours Upload", wf(
    {"When_a_file_is_created": act("OpenApiConnection", {
        "host": {"connectionName": "shared_sharepointonline",
                 "operationId": "OnNewFileV2", "apiId": SP},
        "parameters": {"dataset": SITE, "folderId": "@parameters('StdHoursFolderId')",
                       "inferContentType": True},
        "authentication": "@parameters('$authentication')",
    })},
    f1_actions,
    {"SharePointSiteUrl": {"defaultValue": "https://contoso.sharepoint.com/sites/PMSystem", "type": "String"},
     "StdHoursFolderId": {"defaultValue": "/Shared Documents/02 Standard Hours", "type": "String"},
     "DocumentLibraryDriveId": {"defaultValue": "", "type": "String"},
     "UploaderEmail": {"defaultValue": "production.planning@example.com", "type": "String"},
     "SchedulerFlowId": {"defaultValue": "", "type": "String"}}),
    ["Rejects a bad file before it can reach the ledger.",
     "The implausibility check (a value more than 3x the cell baseline) is worth adding "
     "once you have a few months of real data to set the multiplier from."])


# ===========================================================================
# FLOW 2 - Monthly PM Scheduler   (this is the one that owns the rule)
# ===========================================================================
CELL = "items('For_each_cell')"
PREV = "first(body('Filter_previous_ledger_row'))"
STD = "first(body('Filter_std_hours_row'))"
LAST_PM = "first(body('Get_last_completed_PM')?['value'])"

OPENING = (f"if(empty(body('Filter_previous_ledger_row')), 0, "
           f"float(coalesce({PREV}?['CarryOverAfterPM'], {PREV}?['ClosingStdHrs'], 0)))")
ADDED = f"if(empty(body('Filter_std_hours_row')), 0, float(coalesce({STD}?['StdHours'], 0)))"
CLOSING = "add(float(outputs('Compose_opening')), float(outputs('Compose_added')))"
THRESHOLD = (f"if(equals(coalesce({CELL}?['PMIntervalStdHrs'], 0), 0), "
             "int(outputs('Compose_default_interval')), "
             f"int({CELL}?['PMIntervalStdHrs']))")
BACKSTOP = f"if(equals(coalesce({CELL}?['CalendarBackstopMonths'], 0), 0), 12, int({CELL}?['CalendarBackstopMonths']))"
MONTHS_SINCE = (f"if(empty(body('Get_last_completed_PM')?['value']), 999, "
                + months_between(f"{LAST_PM}?['ActualEndDate']", MONTH_START) + ")")

machine_actions = {
    "Increment_machine_index": act(
        "IncrementVariable", {"name": "MachineIndex", "value": 1}, None,
        "There is no loop index in Power Automate, so keep one. This is why the "
        "loop must run with concurrency 1."),
    "Compose_planned_date": compose(
        "@{formatDateTime(addDays(concat(triggerBody()?['MonthKey'], '-01'), "
        "sub(int(div(mul(" + DAYS_IN_MONTH + ", variables('MachineIndex')), "
        "add(length(body('Get_machines_in_cell')?['value']), 1))), 1)), 'yyyy-MM-dd')}",
        {"Increment_machine_index": ["Succeeded"]},
        "Spread the cell's machines across the month instead of dumping them all on the 1st."),
    "Compose_assigned_tech": compose(
        "@if(empty(body('Get_area_technicians')?['value']), null, "
        "body('Get_area_technicians')?['value']"
        "[mod(variables('MachineIndex'), length(body('Get_area_technicians')?['value']))])",
        {"Compose_planned_date": ["Succeeded"]},
        "Round-robin across technicians whose PrimaryArea matches the cell."),
    "Create_work_order": sp("PostItem", {
        "dataset": SITE, "table": "PM_WorkOrders",
        "item/Title": "@{items('For_each_machine')?['MachineID']}",
        "item/WOID": "@{concat('WO-', substring(guid(), 0, 8))}",
        "item/CycleID": "@{outputs('Compose_cycle_id')}",
        "item/CellID": "@{items('For_each_cell')?['CellID']}",
        "item/MachineID": "@{items('For_each_machine')?['MachineID']}",
        "item/MachineName": "@{items('For_each_machine')?['MachineName']}",
        "item/PMType": "PM-4000",
        "item/TriggerType": "@{outputs('Compose_trigger_type')}",
        "item/TriggerStdHrs": "@{outputs('Compose_closing')}",
        "item/PlanMonth": "@{triggerBody()?['MonthKey']}",
        "item/PlannedDate": "@{outputs('Compose_planned_date')}",
        "item/DueDate": "@{" + MONTH_END + "}",
        "item/AssignedTechID": "@{outputs('Compose_assigned_tech')?['TechID']}",
        "item/AssignedTechName": "@{outputs('Compose_assigned_tech')?['TechName']}",
        "item/Shift": "@{outputs('Compose_assigned_tech')?['Shift']}",
        "item/Status": "Scheduled",
        "item/ChecklistTotalTasks": "@{length(body('Get_checklist_tasks')?['value'])}",
        "item/StdMinutes": "@{items('For_each_machine')?['PMStdMinutes']}",
        "item/MachineQRScanned": "No",
    }, {"Compose_assigned_tech": ["Succeeded"]},
        "One work order per machine. TriggerType and TriggerStdHrs are stamped on so "
        "months later anyone can see why this job existed."),
}

triggered_actions = {
    "Get_machines_in_cell": sp("GetItems", {
        "dataset": SITE, "table": "Machine_Master",
        "$filter": "CellID eq '@{items('For_each_cell')?['CellID']}' and Active eq 'Yes'",
        "$orderby": "MachineID asc", "$top": 200,
    }),
    "Get_previous_cycles": sp("GetItems", {
        "dataset": SITE, "table": "PM_Hour_Ledger",
        "$filter": "CellID eq '@{items('For_each_cell')?['CellID']}' and PMTriggered eq 'Yes'",
        "$top": 500,
    }, {"Get_machines_in_cell": ["Succeeded"]},
        "Cycle number = how many times this cell has tripped before, plus this one."),
    "Compose_cycle_id": compose(
        "@{concat(items('For_each_cell')?['CellID'], '-C', "
        "formatNumber(add(length(body('Get_previous_cycles')?['value']), 1), '00'))}",
        {"Get_previous_cycles": ["Succeeded"]}),
    "Get_area_technicians": sp("GetItems", {
        "dataset": SITE, "table": "Technician_Master",
        "$filter": "PrimaryArea eq '@{items('For_each_cell')?['Area']}' and Active eq 'Yes'",
        "$orderby": "TechID asc", "$top": 100,
    }, {"Compose_cycle_id": ["Succeeded"]}),
    "Get_checklist_tasks": sp("GetItems", {
        "dataset": SITE, "table": "PM_Checklist_Master", "$top": 500,
    }, {"Get_area_technicians": ["Succeeded"]},
        "Only used for the task count stamped on the work order."),
    "Reset_machine_index": set_var("MachineIndex", 0,
                                   {"Get_checklist_tasks": ["Succeeded"]}),
    "For_each_machine": foreach(
        "@body('Get_machines_in_cell')?['value']", machine_actions,
        {"Reset_machine_index": ["Succeeded"]},
        "One work order per active machine in the cell.", concurrency=1),
    "Increment_created": act("IncrementVariable", {
        "name": "WorkOrdersCreated",
        "value": "@length(body('Get_machines_in_cell')?['value'])",
    }, {"For_each_machine": ["Succeeded"]}),
}

cell_actions = {
    "Filter_previous_ledger_row": act("Query", {
        "from": "@body('Get_previous_ledger')?['value']",
        "where": "@equals(item()?['CellID'], items('For_each_cell')?['CellID'])",
    }, None, "Last month's row for this cell - the carry-over lives here."),
    "Filter_std_hours_row": act("Query", {
        "from": "@outputs('Compose_std_hours')",
        "where": "@equals(item()?['CellID'], items('For_each_cell')?['CellID'])",
    }, {"Filter_previous_ledger_row": ["Succeeded"]}),
    "Compose_opening": compose("@" + OPENING, {"Filter_std_hours_row": ["Succeeded"]},
                               "Carry-over from the previous cycle, else last month's closing, else zero."),
    "Compose_added": compose("@" + ADDED, {"Compose_opening": ["Succeeded"]}),
    "Compose_closing": compose("@" + CLOSING, {"Compose_added": ["Succeeded"]}),
    "Get_last_completed_PM": sp("GetItems", {
        "dataset": SITE, "table": "PM_WorkOrders",
        "$filter": "CellID eq '@{items('For_each_cell')?['CellID']}' and Status eq 'Completed'",
        "$orderby": "ActualEndDate desc", "$top": 1,
    }, {"Compose_closing": ["Succeeded"]}),
    "Compose_months_since": compose("@" + MONTHS_SINCE,
                                    {"Get_last_completed_PM": ["Succeeded"]},
                                    "999 when the cell has never had a PM, so the backstop fires."),
    "Compose_threshold": compose("@" + THRESHOLD, {"Compose_months_since": ["Succeeded"]}),
    "Compose_backstop": compose("@" + BACKSTOP, {"Compose_threshold": ["Succeeded"]}),
    "Compose_hours_due": compose(
        "@greaterOrEquals(float(outputs('Compose_closing')), float(outputs('Compose_threshold')))",
        {"Compose_backstop": ["Succeeded"]}),
    "Compose_calendar_due": compose(
        "@greaterOrEquals(int(outputs('Compose_months_since')), int(outputs('Compose_backstop')))",
        {"Compose_hours_due": ["Succeeded"]}),
    "Compose_triggered": compose(
        "@or(bool(outputs('Compose_hours_due')), bool(outputs('Compose_calendar_due')))",
        {"Compose_calendar_due": ["Succeeded"]}),
    "Compose_trigger_type": compose(
        "@if(bool(outputs('Compose_hours_due')), 'Std Hours', "
        "if(bool(outputs('Compose_calendar_due')), 'Calendar Backstop', ''))",
        {"Compose_triggered": ["Succeeded"]},
        "Hours wins the label when both fire in the same month."),
    "Compose_carry_over": compose(
        "@if(bool(outputs('Compose_triggered')), "
        "max(0, sub(float(outputs('Compose_closing')), float(outputs('Compose_threshold')))), "
        "float(outputs('Compose_closing')))",
        {"Compose_trigger_type": ["Succeeded"]},
        "Hours past the threshold are never lost - they open the next cycle."),
    "Create_ledger_row": sp("PostItem", {
        "dataset": SITE, "table": "PM_Hour_Ledger",
        "item/Title": "@{concat(items('For_each_cell')?['CellID'], ' ', triggerBody()?['MonthKey'])}",
        "item/MonthKey": "@{triggerBody()?['MonthKey']}",
        "item/CellID": "@{items('For_each_cell')?['CellID']}",
        "item/CellName": "@{items('For_each_cell')?['CellName']}",
        "item/OpeningStdHrs": "@{outputs('Compose_opening')}",
        "item/StdHoursAdded": "@{outputs('Compose_added')}",
        "item/ClosingStdHrs": "@{outputs('Compose_closing')}",
        "item/PMIntervalStdHrs": "@{outputs('Compose_threshold')}",
        "item/PMTriggered": "@{if(bool(outputs('Compose_triggered')), 'Yes', 'No')}",
        "item/TriggerType": "@{outputs('Compose_trigger_type')}",
        "item/CarryOverAfterPM": "@{outputs('Compose_carry_over')}",
        "item/MonthsSinceLastPM": "@{outputs('Compose_months_since')}",
        "item/Scenario": "Actual",
    }, {"Compose_carry_over": ["Succeeded"]},
        "A row every month, triggered or not. A gap in the ledger is a gap nobody "
        "can explain later."),
    "If_triggered": cond(
        {"equals": ["@bool(outputs('Compose_triggered'))", True]},
        triggered_actions, None,
        {"Create_ledger_row": ["Succeeded"]},
        "The whole cell goes together: one work order per active machine."),
}

f2_actions = {
    "Compose_prev_month_key": compose(
        "@{formatDateTime(subtractFromTime(concat(triggerBody()?['MonthKey'], '-01'), "
        "1, 'Month'), 'yyyy-MM')}", None),
    "Compose_std_hours": compose(
        "@json(triggerBody()?['StdHoursJson'])", {"Compose_prev_month_key": ["Succeeded"]},
        "Flow 1 already read and validated the Excel, so the scheduler never touches it."),
    "Init_machine_index": init_var("MachineIndex", "integer", 0,
                                   {"Compose_std_hours": ["Succeeded"]}),
    "Init_created": init_var("WorkOrdersCreated", "integer", 0,
                             {"Init_machine_index": ["Succeeded"]}),
    "Get_default_interval": sp("GetItems", {
        "dataset": SITE, "table": "PM_Config",
        "$filter": "ConfigKey eq 'DefaultPMIntervalStdHrs'", "$top": 1,
    }, {"Init_created": ["Succeeded"]}),
    "Compose_default_interval": compose(
        "@if(empty(body('Get_default_interval')?['value']), 4000, "
        "int(first(body('Get_default_interval')?['value'])?['ConfigValue']))",
        {"Get_default_interval": ["Succeeded"]},
        "The 4000 lives in PM_Config so the rule can be retuned without editing a flow."),
    "Check_already_processed": sp("GetItems", {
        "dataset": SITE, "table": "PM_Hour_Ledger",
        "$filter": "MonthKey eq '@{triggerBody()?['MonthKey']}'", "$top": 1,
    }, {"Compose_default_interval": ["Succeeded"]},
        "Idempotency guard: a retried run must not double-schedule a cell."),
    "Stop_if_duplicate": cond(
        {"and": [
            {"greater": ["@length(body('Check_already_processed')?['value'])", 0]},
            {"not": {"equals": ["@triggerBody()?['Mode']", "Restate"]}},
        ]},
        {"Stop_duplicate": terminate(
            "Cancelled", "AlreadyProcessed",
            "Ledger rows already exist for this month. Re-run with Mode = Restate to reprocess.")},
        None, {"Check_already_processed": ["Succeeded"]}),
    "Get_active_cells": sp("GetItems", {
        "dataset": SITE, "table": "Cell_Master",
        "$filter": "Active eq 'Yes'", "$orderby": "CellID asc", "$top": 500,
    }, {"Stop_if_duplicate": ["Succeeded"]}),
    "Get_previous_ledger": sp("GetItems", {
        "dataset": SITE, "table": "PM_Hour_Ledger",
        "$filter": "MonthKey eq '@{outputs('Compose_prev_month_key')}' and Scenario eq 'Actual'",
        "$top": 500,
    }, {"Get_active_cells": ["Succeeded"]}),
    "For_each_cell": foreach(
        "@body('Get_active_cells')?['value']", cell_actions,
        {"Get_previous_ledger": ["Succeeded"]},
        "Concurrency must stay at 1 - the machine index variable is shared state.",
        concurrency=1),
    "Respond_summary": act("Response", {
        "statusCode": 200,
        "body": {
            "MonthKey": "@triggerBody()?['MonthKey']",
            "Mode": "@triggerBody()?['Mode']",
            "CellsProcessed": "@length(body('Get_active_cells')?['value'])",
            "WorkOrdersCreated": "@variables('WorkOrdersCreated')",
        },
    }, {"For_each_cell": ["Succeeded"]}),
}

save(2, "Monthly PM Scheduler", wf(
    {"manual": {"type": "Request", "kind": "Button", "inputs": {"schema": {
        "type": "object",
        "properties": {
            "MonthKey": {"type": "string", "title": "Month (YYYY-MM)", "x-ms-content-hint": "TEXT"},
            "Mode": {"type": "string", "title": "Normal | Backload | Restate", "x-ms-content-hint": "TEXT"},
            "StdHoursJson": {"type": "string", "title": "Standard hours rows as JSON", "x-ms-content-hint": "TEXT"},
        },
        "required": ["MonthKey", "Mode", "StdHoursJson"],
    }}}},
    f2_actions,
    {"SharePointSiteUrl": {"defaultValue": "https://contoso.sharepoint.com/sites/PMSystem", "type": "String"}}),
    ["THE scheduling rule lives here. Change it here and in nowhere else.",
     "Runs as a child flow so Flow 1 can call it for a normal month and a person can "
     "call it directly for Backload and Restate.",
     "Concurrency on both loops must be 1. The machine index is shared state.",
     "Backload: call once per historical month, oldest first, and skip work order "
     "creation - historical PMs were done on paper.",
     "Restate: delete ledger rows from that month forward, then replay month by month."])


# ===========================================================================
# FLOW 3 - Overdue Sweep
# ===========================================================================
save(3, "Overdue Sweep", wf(
    {"Every_night": {"type": "Recurrence", "recurrence": {
        "frequency": "Day", "interval": 1, "schedule": {"hours": ["23"], "minutes": [30]},
        "timeZone": "India Standard Time"}}},
    {
        "Get_grace_days": sp("GetItems", {
            "dataset": SITE, "table": "PM_Config",
            "$filter": "ConfigKey eq 'OverdueGraceDays'", "$top": 1}),
        "Compose_cutoff": compose(
            "@{formatDateTime(subtractFromTime(utcNow(), "
            "if(empty(body('Get_grace_days')?['value']), 0, "
            "int(first(body('Get_grace_days')?['value'])?['ConfigValue'])), 'Day'), 'yyyy-MM-dd')}",
            {"Get_grace_days": ["Succeeded"]}),
        "Get_lapsed_work_orders": sp("GetItems", {
            "dataset": SITE, "table": "PM_WorkOrders",
            "$filter": "(Status eq 'Scheduled' or Status eq 'In Progress') "
                       "and DueDate lt '@{outputs('Compose_cutoff')}'",
            "$top": 2000,
        }, {"Compose_cutoff": ["Succeeded"]}),
        "For_each_lapsed": foreach(
            "@body('Get_lapsed_work_orders')?['value']",
            {"Mark_overdue": sp("PatchItem", {
                "dataset": SITE, "table": "PM_WorkOrders",
                "id": "@{items('For_each_lapsed')?['ID']}",
                "item/Status": "Overdue"})},
            {"Get_lapsed_work_orders": ["Succeeded"]},
            "Status is set by this sweep, never by a person. Overdue is a fact, not an opinion."),
        "Check_any_overdue": cond(
            {"greater": ["@length(body('Get_lapsed_work_orders')?['value'])", 0]},
            {"Post_digest": act("OpenApiConnection", {
                "host": {"connectionName": "shared_teams",
                         "operationId": "PostMessageToConversation",
                         "apiId": "/providers/Microsoft.PowerApps/apis/shared_teams"},
                "parameters": {
                    "poster": "Flow bot", "location": "Channel",
                    "body/recipient/groupId": "@parameters('TeamsGroupId')",
                    "body/recipient/channelId": "@parameters('TeamsChannelId')",
                    "body/messageBody": "<p><b>@{length(body('Get_lapsed_work_orders')?['value'])} "
                                        "PM work order(s) are now overdue.</b><br>"
                                        "Oldest first on the Execution page of the dashboard.</p>",
                },
                "authentication": "@parameters('$authentication')",
            })}, None, {"For_each_lapsed": ["Succeeded"]},
            "One digest a day, not one message per work order. A channel nobody reads "
            "is worse than no channel."),
    },
    {"SharePointSiteUrl": {"defaultValue": "https://contoso.sharepoint.com/sites/PMSystem", "type": "String"},
     "TeamsGroupId": {"defaultValue": "", "type": "String"},
     "TeamsChannelId": {"defaultValue": "", "type": "String"}}),
    ["Runs nightly. Deferred is a decision with an approver; Overdue is a failure. "
     "Keeping them apart is what makes the compliance number arguable-with rather than "
     "argued-about."])


# ===========================================================================
# FLOW 4 - Abnormality Escalation
# ===========================================================================
save(4, "Abnormality Escalation", wf(
    {"When_an_abnormality_is_logged": act("OpenApiConnection", {
        "host": {"connectionName": "shared_sharepointonline",
                 "operationId": "OnNewItems", "apiId": SP},
        "parameters": {"dataset": SITE, "table": "Abnormality_Log"},
        "authentication": "@parameters('$authentication')",
    }, None, None, {"operationMetadataId": "abn-created"})},
    {
        "Check_high_severity": cond(
            {"equals": ["@triggerOutputs()?['body/Severity/Value']", "High"]},
            {
                "Mail_head": mail(
                    "@parameters('MaintenanceHeadEmail')",
                    "HIGH severity abnormality - @{triggerOutputs()?['body/MachineName']}",
                    "<b>@{triggerOutputs()?['body/MachineName']}</b> "
                    "(@{triggerOutputs()?['body/CellName']})<br>"
                    "Category: @{triggerOutputs()?['body/Category/Value']}<br>"
                    "Reported by: @{triggerOutputs()?['body/ReportedByName']}<br>"
                    "@{triggerOutputs()?['body/Description']}<br><br>"
                    "Photo is attached to the item in the Abnormality Log."),
                "Post_teams": act("OpenApiConnection", {
                    "host": {"connectionName": "shared_teams",
                             "operationId": "PostMessageToConversation",
                             "apiId": "/providers/Microsoft.PowerApps/apis/shared_teams"},
                    "parameters": {
                        "poster": "Flow bot", "location": "Channel",
                        "body/recipient/groupId": "@parameters('TeamsGroupId')",
                        "body/recipient/channelId": "@parameters('TeamsChannelId')",
                        "body/messageBody": "<p><b>HIGH severity abnormality</b><br>"
                                            "@{triggerOutputs()?['body/MachineName']} - "
                                            "@{triggerOutputs()?['body/Description']}</p>",
                    },
                    "authentication": "@parameters('$authentication')",
                }, {"Mail_head": ["Succeeded"]}),
            }, None, None,
            "High severity goes to a person immediately. Everything else waits for "
            "the Monday digest."),
    },
    {"SharePointSiteUrl": {"defaultValue": "https://contoso.sharepoint.com/sites/PMSystem", "type": "String"},
     "MaintenanceHeadEmail": {"defaultValue": "maintenance.head@example.com", "type": "String"},
     "TeamsGroupId": {"defaultValue": "", "type": "String"},
     "TeamsChannelId": {"defaultValue": "", "type": "String"}}),
    ["A separate weekly digest flow for items open past 30 days is worth adding once "
     "the log has volume. The ageing measure is already on the dashboard."])


# ===========================================================================
# FLOW 5 - Spare Approval
# ===========================================================================
save(5, "Spare Approval", wf(
    {"When_a_spare_is_requested": act("OpenApiConnection", {
        "host": {"connectionName": "shared_sharepointonline",
                 "operationId": "OnNewItems", "apiId": SP},
        "parameters": {"dataset": SITE, "table": "SparePart_Requests"},
        "authentication": "@parameters('$authentication')",
    })},
    {
        "Get_approval_limit": sp("GetItems", {
            "dataset": SITE, "table": "PM_Config",
            "$filter": "ConfigKey eq 'SpareApprovalLimitINR'", "$top": 1}),
        "Compose_limit": compose(
            "@if(empty(body('Get_approval_limit')?['value']), 25000, "
            "float(first(body('Get_approval_limit')?['value'])?['ConfigValue']))",
            {"Get_approval_limit": ["Succeeded"]}),
        "Compose_approver": compose(
            "@if(greater(float(coalesce(triggerOutputs()?['body/TotalCostINR'], 0)), "
            "float(outputs('Compose_limit'))), parameters('PlantHeadEmail'), "
            "parameters('MaintenanceHeadEmail'))",
            {"Compose_limit": ["Succeeded"]},
            "Above the limit it goes to the Plant Head. The app warns the technician "
            "before submit so the delay is not a surprise."),
        "Start_and_wait_for_approval": act("OpenApiConnection", {
            "host": {"connectionName": "shared_approvals",
                     "operationId": "StartAndWaitForAnApproval", "apiId": APPR},
            "parameters": {
                "approvalType": "Basic",
                "ApprovalCreationInput/title":
                    "Spare request @{triggerOutputs()?['body/RequestID']} - "
                    "@{triggerOutputs()?['body/PartName']}",
                "ApprovalCreationInput/assignedTo": "@outputs('Compose_approver')",
                "ApprovalCreationInput/details":
                    "Machine: @{triggerOutputs()?['body/MachineName']}\n"
                    "Part: @{triggerOutputs()?['body/PartNo']} @{triggerOutputs()?['body/PartName']}\n"
                    "Quantity: @{triggerOutputs()?['body/QtyRequested']}\n"
                    "Value: INR @{triggerOutputs()?['body/TotalCostINR']}\n"
                    "Urgency: @{triggerOutputs()?['body/Urgency/Value']}\n"
                    "Raised from: @{triggerOutputs()?['body/SourceType']} "
                    "@{triggerOutputs()?['body/SourceID']}",
            },
            "authentication": "@parameters('$authentication')",
        }, {"Compose_approver": ["Succeeded"]},
            "The Approvals connector keeps the decision auditable, which a mailed "
            "yes/no does not."),
        "Record_outcome": cond(
            {"equals": ["@outputs('Start_and_wait_for_approval')?['body/outcome']", "Approve"]},
            {"Set_approved": sp("PatchItem", {
                "dataset": SITE, "table": "SparePart_Requests",
                "id": "@{triggerOutputs()?['body/ID']}",
                "item/Status": "Approved",
                "item/ApprovedDate": "@{formatDateTime(utcNow(), 'yyyy-MM-dd')}",
                "item/ApprovedBy": "@{outputs('Compose_approver')}"})},
            {"Set_rejected": sp("PatchItem", {
                "dataset": SITE, "table": "SparePart_Requests",
                "id": "@{triggerOutputs()?['body/ID']}",
                "item/Status": "Rejected",
                "item/RejectionReason":
                    "@{outputs('Start_and_wait_for_approval')?['body/responses'][0]['comments']}"})},
            {"Start_and_wait_for_approval": ["Succeeded"]},
            "Stores sets Issued when the part physically leaves the counter. "
            "A flow must not claim that a part was handed over."),
    },
    {"SharePointSiteUrl": {"defaultValue": "https://contoso.sharepoint.com/sites/PMSystem", "type": "String"},
     "MaintenanceHeadEmail": {"defaultValue": "maintenance.head@example.com", "type": "String"},
     "PlantHeadEmail": {"defaultValue": "plant.head@example.com", "type": "String"}}),
    ["Issued is deliberately not set by this flow. Requested, approved and consumed "
     "are three different facts and the dashboard shows the gaps between them."])


# ===========================================================================
# FLOW 6 - Upload Reminder
# ===========================================================================
save(6, "Upload Reminder", wf(
    {"On_the_5th_and_8th": {"type": "Recurrence", "recurrence": {
        "frequency": "Month", "interval": 1,
        "schedule": {"monthDays": [5, 8], "hours": ["9"], "minutes": [0]},
        "timeZone": "India Standard Time"}}},
    {
        "Compose_target_month": compose(
            "@{formatDateTime(subtractFromTime(utcNow(), 1, 'Month'), 'yyyy_MM')}", None,
            "Chasing last month's file."),
        "List_uploaded_files": sp("GetFileItems", {
            "dataset": SITE, "table": "@parameters('StdHoursLibraryId')", "$top": 500,
        }, {"Compose_target_month": ["Succeeded"]}),
        "Filter_this_month": act("Query", {
            "from": "@body('List_uploaded_files')?['value']",
            "where": "@contains(coalesce(item()?['{Name}'], ''), "
                     "concat('Cell_Standard_Hours_', outputs('Compose_target_month')))",
        }, {"List_uploaded_files": ["Succeeded"]}),
        "Chase_if_missing": cond(
            {"equals": ["@length(body('Filter_this_month'))", 0]},
            {"Mail_reminder": mail(
                "@parameters('UploaderEmail')",
                "Action needed: standard hours for @{outputs('Compose_target_month')} not uploaded",
                "The PM system has no standard-hours file for "
                "<b>@{outputs('Compose_target_month')}</b>.<br><br>"
                "Until it is uploaded, no cell accrues hours and no PM will be scheduled "
                "for any of them - while the dashboard still shows green.<br><br>"
                "Upload <b>Cell_Standard_Hours_@{outputs('Compose_target_month')}.xlsx</b> "
                "to the 02 Standard Hours folder.")},
            None, {"Filter_this_month": ["Succeeded"]}),
    },
    {"SharePointSiteUrl": {"defaultValue": "https://contoso.sharepoint.com/sites/PMSystem", "type": "String"},
     "StdHoursLibraryId": {"defaultValue": "Shared Documents", "type": "String"},
     "UploaderEmail": {"defaultValue": "production.planning@example.com", "type": "String"}}),
    ["Two lines of logic that protect the whole system. Without the upload, counters "
     "freeze and nothing is ever scheduled.",
     "Copy the Plant Head on the 8th-of-the-month run once you have seen how often "
     "the 5th is missed."])

print()
