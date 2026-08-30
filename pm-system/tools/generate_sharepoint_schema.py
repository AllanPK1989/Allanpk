"""
generate_sharepoint_schema.py
-----------------------------
Emits one schema JSON per SharePoint list into sharepoint/schema/.
provision_lists.ps1 reads these files - it contains no column definitions of
its own, so the schema and the script can never drift apart.

Run this only when the data dictionary changes.
    python tools/generate_sharepoint_schema.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare_sharepoint_data import TYPES, LOAD_ORDER  # noqa: E402

# --------------------------------------------------------------------------
# Choice domains. Taken from the data dictionary, widened where the dummy data
# carries a value the dictionary abbreviates (noted in docs/ASSUMPTIONS.md).
# A Choice column with the wrong values is worse than a text column: the form
# silently drops the value and the technician never sees an error.
# --------------------------------------------------------------------------
CHOICES = {
    "Cell_Master": {
        "Process_Area": ["Element", "Assembly", "Filling", "Curing", "Testing", "Packing"],
        "Criticality": ["A", "B", "C"],
    },
    "Machine_Master": {
        "Criticality": ["A", "B", "C"],
    },
    "Checklist_Master": {
        "Check_Type": ["Visual", "Measurement", "Functional"],
        "Frequency": ["Monthly (per PM cycle)", "Quarterly", "Annual"],
    },
    "Technician_Master": {
        "Skill_Level": ["Senior", "Junior", "Trainee"],
        "Trade": ["Mechanical", "Electrical"],
        "Default_Shift": ["A (06:00-14:00)", "B (14:00-22:00)", "C (22:00-06:00)"],
    },
    "Spare_Master": {
        "Category": ["Mechanical", "Electrical", "Pneumatic", "Instrument",
                     "Utility", "Consumable", "Sensor"],
        "ABC_Class": ["A", "B", "C"],
        "FMR_Class": ["F", "M", "R"],
    },
    "PM_WorkOrder": {
        "Trigger_Type": ["Std Hours", "Calendar Backstop", "Manual"],
        "Priority": ["High", "Medium", "Low"],
        "WO_Status": ["Planned", "In Progress", "Completed", "Overdue", "Cancelled"],
    },
    "PM_Machine_Task": {
        "Task_Status": ["Pending", "In Progress", "Completed", "Skipped"],
    },
    "Checklist_Response": {
        "Result": ["OK", "NOT OK", "NA"],
    },
    "Scan_Log": {
        "Scan_Action": ["Start PM", "Complete PM", "Breakdown", "Spare Request",
                        "Abnormality", "View"],
        "Device": ["Android", "iOS", "Kiosk"],
    },
    "Breakdown_Log": {
        "Shift": ["A (06:00-14:00)", "B (14:00-22:00)", "C (22:00-06:00)"],
        "Breakdown_Type": ["Mechanical", "Electrical", "Pneumatic", "Hydraulic",
                           "Instrumentation", "Utility"],
        "Status": ["Open", "Closed"],
    },
    "Spare_Request": {
        "Urgency": ["Normal", "Urgent", "Breakdown"],
        "Reason": ["PM replacement", "Breakdown repair", "Predictive finding",
                   "Stock top-up"],
        "Approval_Status": ["Pending", "Approved", "Rejected"],
        "Issue_Status": ["Not Issued", "Partially Issued", "Issued"],
    },
    "Spare_Replaced": {
        "Source_Type": ["PM", "Breakdown"],
        "Old_Part_Condition": ["Worn", "Damaged", "Burnt", "Leaking", "End of life"],
        "Failure_Mode": ["Wear", "Fatigue", "Electrical burnout", "Contamination",
                         "Corrosion", "Overload", "End of rated life",
                         "Improper handling"],
    },
    "Abnormality_Log": {
        "Category": ["Safety", "Quality", "Air Leak", "Oil Leak", "Abnormal Noise",
                     "Vibration", "Overheating", "Contamination", "5S / Housekeeping"],
        "Severity": ["High", "Medium", "Low"],
        "Status": ["Open", "In Progress", "Closed"],
    },
    "PM_Plan_Calendar": {
        "Planned_Shift": ["A (06:00-14:00)", "B (14:00-22:00)", "C (22:00-06:00)"],
        "Plan_Version": ["V1", "V1 Forecast", "V2"],
        "Adherence_Status": ["On Time", "Delayed", "Overdue", "Cancelled", "Forecast",
                             "Planned", "In Progress"],
    },
}

# Columns that need a multi-line box rather than a 255-character single line.
MULTILINE = {
    "Acceptance_Standard", "Remarks", "Skip_Reason", "Observation", "Action_Taken",
    "Comments", "Symptom", "Root_Cause", "Description", "Immediate_Action",
    "Closure_Remarks", "Role_Scope",
}

# Primary keys - required, indexed, and used as the list Title on load.
PRIMARY_KEY = {
    "Cell_Master": "Cell_ID", "Machine_Master": "Machine_ID",
    "Checklist_Master": None, "Technician_Master": "Tech_ID",
    "Spare_Master": "Spare_Code", "StdHours_Monthly": None,
    "PM_WorkOrder": "WO_No", "PM_Machine_Task": "Task_ID",
    "Checklist_Response": "Response_ID", "Scan_Log": "Scan_ID",
    "Breakdown_Log": "BD_ID", "Spare_Request": "Req_ID",
    "Spare_Replaced": "Repl_ID", "Abnormality_Log": "Abn_ID",
    "PM_Plan_Calendar": "Plan_ID",
}

# Mandatory everywhere. Business rule 8: technicians share one M365 login, so
# the technician dropdown is the only audit trail that exists.
TECHNICIAN_FIELDS = {
    "Completed_By", "Tech_ID", "Logged_By", "Requested_By", "Replaced_By",
    "Reported_By_Tech_ID",
}

# Extra required columns beyond the primary key and technician fields.
ALSO_REQUIRED = {
    "Cell_Master": ["Cell_Name", "PM_Trigger_Hours", "Calendar_Backstop_Months", "Active"],
    "Machine_Master": ["Machine_Name", "Cell_ID", "Checklist_ID", "Active"],
    "Checklist_Master": ["Checklist_ID", "Item_No", "Check_Point", "Check_Type",
                         "Acceptance_Standard", "Active"],
    "Technician_Master": ["Tech_Name", "Active"],
    "Spare_Master": ["Spare_Description", "Unit_Cost_INR", "Active"],
    "StdHours_Monthly": ["Upload_Month", "Cell_ID", "Actual_Std_Hours"],
    "PM_WorkOrder": ["Cell_ID", "WO_Status", "Machines_In_Scope"],
    "PM_Machine_Task": ["WO_No", "Machine_ID", "Cell_ID", "Task_Status"],
    "Checklist_Response": ["WO_No", "Machine_ID", "Item_No", "Result"],
    "Scan_Log": ["Machine_ID", "Scan_Action"],
    "Breakdown_Log": ["Machine_ID", "Breakdown_Type", "Status"],
    "Spare_Request": ["Spare_Code", "Qty_Requested", "Urgency", "Reason"],
    "Spare_Replaced": ["Spare_Code", "Qty_Used"],
    "Abnormality_Log": ["Machine_ID", "Category", "Severity", "Status"],
    "PM_Plan_Calendar": ["Plan_Month", "Cell_ID", "Planned_Date"],
}

# Indexed columns. SharePoint allows 20 indexes per list; every column used in a
# view filter or a Power Automate "Get items" filter query needs one, or the
# 5,000-item list view threshold will stop the flow dead one day without warning.
INDEXES = {
    "Cell_Master": ["Cell_ID", "Active", "Cum_Std_Hours_Since_PM", "Last_PM_Date"],
    "Machine_Master": ["Machine_ID", "Cell_ID", "Active", "Checklist_ID"],
    "Checklist_Master": ["Checklist_ID", "Active"],
    "Technician_Master": ["Tech_ID", "Active"],
    "Spare_Master": ["Spare_Code", "Active"],
    "StdHours_Monthly": ["Upload_Month", "Cell_ID"],
    "PM_WorkOrder": ["WO_No", "Cell_ID", "WO_Status", "Planned_Month",
                     "WO_Created_Date", "Planned_End_Date", "Actual_End_Date"],
    "PM_Machine_Task": ["Task_ID", "WO_No", "Machine_ID", "Cell_ID", "Task_Status",
                        "Completion_Date"],
    "Checklist_Response": ["Response_ID", "WO_No", "Machine_ID", "Result",
                           "Submitted_DateTime", "Follow_Up_Required"],
    "Scan_Log": ["Machine_ID", "Scan_DateTime", "WO_No"],
    "Breakdown_Log": ["Machine_ID", "Cell_ID", "Status", "Reported_DateTime"],
    "Spare_Request": ["WO_No", "Spare_Code", "Approval_Status", "Request_DateTime"],
    "Spare_Replaced": ["Source_Ref", "Machine_ID", "Spare_Code", "Replaced_DateTime"],
    "Abnormality_Log": ["Machine_ID", "Cell_ID", "Status", "Severity", "Target_Date"],
    "PM_Plan_Calendar": ["Plan_Month", "Cell_ID", "Adherence_Status", "Planned_Date"],
}

DESCRIPTIONS = {
    "Cell_Master": "One row per production cell. Holds the running standard-hours counter that triggers PM.",
    "Machine_Master": "One row per machine. Carries the QR payload and the pre-filled form links behind the Machine Hub buttons.",
    "Checklist_Master": "The check points that make up each of the nine checklist sets.",
    "Technician_Master": "The values behind the mandatory Technician Name dropdown on every form.",
    "Spare_Master": "Spare parts catalogue with cost, stock and reorder data.",
    "StdHours_Monthly": "Monthly actual standard hours per cell. One row per cell per month.",
    "PM_WorkOrder": "One row per cell PM. Closes only when every machine task in the cell is complete.",
    "PM_Machine_Task": "One row per machine per work order. This is the technician-facing allotted list.",
    "Checklist_Response": "One row per check point per machine per PM.",
    "Scan_Log": "Raw QR scan events, including the scans that never led to a completion.",
    "Breakdown_Log": "Unplanned stoppages, with response and repair timings.",
    "Spare_Request": "Spare part requests and their approval trail.",
    "Spare_Replaced": "Parts actually fitted, with failure mode and cost.",
    "Abnormality_Log": "Conditions found that are not yet failures.",
    "PM_Plan_Calendar": "The frozen monthly plan. Adherence is measured against this, not against the work order.",
}

LIBRARIES = [
    {"Title": "StdHours_Inbox",
     "Description": "Drop the monthly standard-hours workbook here. Flow 1 picks it up, validates it and moves it out."},
    {"Title": "StdHours_Archive",
     "Description": "Processed monthly workbooks. Power BI's folder query points here."},
    {"Title": "PM_Photos",
     "Description": "Photos attached to checklist findings."},
    {"Title": "Abnormality_Photos",
     "Description": "Evidence photos for abnormality records."},
    {"Title": "Checklist_PDFs",
     "Description": "Printable checklist sheets, one per checklist set, for the paper fallback."},
]

SP_TYPE = {
    "id": "Text", "text": "Text", "month": "Text", "url": "URL",
    "int": "Number", "dec": "Number", "date": "DateTime", "dttm": "DateTime",
    "bool": "Boolean",
}


def build(table):
    typemap = TYPES[table]
    choices = CHOICES.get(table, {})
    required = set(ALSO_REQUIRED.get(table, []))
    pk = PRIMARY_KEY.get(table)
    if pk:
        required.add(pk)
    required |= {c for c in typemap if c in TECHNICIAN_FIELDS}

    fields = []
    for name, kind in typemap.items():
        f = {
            "InternalName": name,      # must equal DisplayName, character for character
            "DisplayName": name,
            "Required": name in required,
            "Indexed": name in INDEXES.get(table, []),
        }
        if name in choices:
            f["Type"] = "Choice"
            f["Choices"] = choices[name]
            f["Format"] = "Dropdown"
            f["FillInChoice"] = False
        elif name in MULTILINE:
            f["Type"] = "Note"
            f["NumberOfLines"] = 4
            f["RichText"] = False
            f["AppendOnly"] = False
        else:
            f["Type"] = SP_TYPE[kind]
            if kind == "int":
                f["Decimals"] = 0
            elif kind == "dec":
                f["Decimals"] = 2
            elif kind == "date":
                f["DisplayFormat"] = "DateOnly"
            elif kind == "dttm":
                f["DisplayFormat"] = "DateTime"
            elif kind == "bool":
                f["DefaultValue"] = "0"
            elif kind in ("id", "text", "month"):
                f["MaxLength"] = 255
        fields.append(f)

    return {
        "ListTitle": table,
        "ListUrl": f"Lists/{table}",
        "Description": DESCRIPTIONS[table],
        "Template": "GenericList",
        "EnableVersioning": True,
        "MajorVersionLimit": 50,
        "EnableAttachments": table in ("Checklist_Response", "Abnormality_Log",
                                       "Breakdown_Log"),
        "TitleColumn": {
            "Required": False,
            "Hidden": False,
            "SetFrom": pk,
            "Note": ("Title is populated from the primary key on load so the item "
                     "has a readable display name and shows up in search. Matching "
                     "is always done on the explicit key column, never on Title."),
        },
        "PrimaryKey": pk,
        "IndexedColumns": INDEXES.get(table, []),
        "Fields": fields,
    }


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "sharepoint", "schema")
    out = os.path.normpath(out)
    os.makedirs(out, exist_ok=True)

    manifest = {
        "SiteDescription": "EPQPL Pondicherry - cell-based preventive maintenance system",
        "ProvisioningOrder": LOAD_ORDER,
        "DocumentLibraries": LIBRARIES,
        "Lists": [],
    }

    for table in LOAD_ORDER:
        schema = build(table)
        path = os.path.join(out, f"{table}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(schema, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        manifest["Lists"].append({
            "Title": table,
            "SchemaFile": f"{table}.json",
            "FieldCount": len(schema["Fields"]),
            "IndexCount": len(schema["IndexedColumns"]),
        })
        print(f"  wrote {path}  ({len(schema['Fields'])} fields, "
              f"{len(schema['IndexedColumns'])} indexes)")

    path = os.path.join(out, "_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"  wrote {path}")

    total_fields = sum(x["FieldCount"] for x in manifest["Lists"])
    over = [x for x in manifest["Lists"] if x["IndexCount"] > 20]
    print(f"\n{len(manifest['Lists'])} lists, {total_fields} columns, "
          f"{len(LIBRARIES)} document libraries.")
    if over:
        print(f"WARNING: over the 20-index SharePoint limit: {over}")


if __name__ == "__main__":
    main()
