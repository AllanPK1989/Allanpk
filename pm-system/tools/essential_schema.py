"""
essential_schema.py
-------------------
The reduced column set, and the reason for every cut.

Three rules decide what stays. Applied in this order, they are not judgement calls
and can be re-derived by anyone:

  RULE 1 - DERIVABLE goes.
      If a flow computes and stores it, and the report could compute it at read
      time, the stored copy is a liability: a flow step that can fail, and a number
      that goes stale without saying so. Exception: a column a SharePoint VIEW
      FILTER needs, because CAML cannot do arithmetic or compare two columns.

  RULE 2 - DENORMALISED goes.
      A copy of master data held on a fact row (Cell_Name on four lists) is a
      second place the same fact can be wrong. The model joins on the ID.
      Exception: a value that must stay readable after the master is edited.

  RULE 3 - SPECULATIVE goes.
      Nothing reads it, no rule needs it, and no one has asked for it. Reserved
      fields and asset-register detail that belongs in an asset register.

Everything that survives earns its place against one of these:
  * one of the ten business rules cannot work without it
  * it is the only record of something (attribution, evidence, a commitment)
  * a flow's own logic branches on it
  * a shop-floor view filters or displays it
"""

# KEEP = the essential set. CUT = column -> why, so the decision stays auditable.
KEEP = {
 "Cell_Master": [
   "Cell_ID","Cell_Name","Process_Area","Machine_Count","PM_Trigger_Hours",
   "Calendar_Backstop_Months","Cum_Std_Hours_Since_PM","Last_PM_Date",
   "Next_PM_Due_Date_Calendar","Owner_Supervisor","Criticality","Active"],

 "Machine_Master": [
   "Machine_ID","Machine_Name","Cell_ID","Machine_Family","Serial_No",
   "Location_Tag","Checklist_ID","QR_Payload_URL","Criticality","Active"],

 "Checklist_Master": [
   "Checklist_ID","Item_No","Check_Point","Check_Type","Acceptance_Standard",
   "Safety_Critical","Expected_Time_Min","Active"],

 "Technician_Master": ["Tech_ID","Tech_Name","Skill_Level","Trade","Active"],

 "Spare_Master": [
   "Spare_Code","Spare_Description","Category","UOM","Unit_Cost_INR",
   "Min_Stock","Current_Stock","Lead_Time_Days","Bin_Location","Active"],

 "Plant_Calendar": ["Calendar_Date","Is_Working_Day","Day_Type"],

 "StdHours_Monthly": [
   "Upload_Month","Cell_ID","Actual_Std_Hours","Production_Qty","Upload_Date","Remarks"],

 "PM_WorkOrder": [
   "WO_No","Cell_ID","Trigger_Type","Trigger_Hours_At_Creation","WO_Created_Date",
   "Planned_Month","Planned_End_Date","Priority","Machines_In_Scope",
   "Machines_Completed","WO_Status","Reset_Applied","Remarks"],

 "PM_Machine_Task": [
   "Task_ID","WO_No","Machine_ID","Cell_ID","Task_Status","Scan_Start_Time",
   "Scan_End_Time","Completed_By","Skip_Reason"],

 "Checklist_Response": [
   "Response_ID","Submitted_DateTime","WO_No","Machine_ID","Checklist_ID","Item_No",
   "Check_Point","Result","Measured_Value","Observation","Photo_Link","Tech_ID",
   "Follow_Up_Required"],

 "Breakdown_Log": [
   "BD_ID","Reported_DateTime","Machine_ID","Cell_ID","Reported_By_Tech_ID","Shift",
   "Breakdown_Type","Symptom","Root_Cause","Action_Taken","Response_DateTime",
   "Repair_Start","Repair_End","Production_Loss_Min","Status","Recurrence_Flag"],

 "Spare_Replaced": [
   "Repl_ID","Replaced_DateTime","Source_Type","Source_Ref","Machine_ID","Cell_ID",
   "Spare_Code","Qty_Used","Unit_Cost_INR","Failure_Mode","Replaced_By","Warranty_Claim"],

 "Abnormality_Log": [
   "Abn_ID","Logged_DateTime","Machine_ID","Cell_ID","Logged_By","Category",
   "Description","Severity","Photo_Link","Responsibility","Target_Date","Status",
   "Closed_Date"],

 "PM_Plan_Calendar": [
   "Plan_ID","Plan_Month","Cell_ID","Planned_Date","Planned_Tech_ID",
   "Plan_Version","WO_No","Adherence_Status"],
}

# Lists removed entirely, with the trade-off stated rather than buried.
DROP_LISTS = {
 "Scan_Log":
   "Every column duplicates a timestamp PM_Machine_Task already holds. Its one "
   "unique contribution was the scan that led nowhere - a useful adoption signal, "
   "and the first thing to reinstate if take-up is ever in doubt. Costs a list, a "
   "flow branch and 336 rows a year to keep something nobody has asked for yet.",
 "Spare_Request":
   "A requisition-and-approval loop that the stores process already runs. The PM "
   "system needs to know what was FITTED - cost, failure mode, which machine - and "
   "that is Spare_Replaced. Asking it to also run approvals duplicates a process "
   "that exists, and it is the only list here with no PM rule behind it. "
   "TRADE-OFF: loses approval lead time and the Stock_At_Request snapshot.",
}

CUT = {
 # ---- RULE 1: derivable ----
 "Cell_Master.Avg_Monthly_Std_Hours_L3M": "R1 derivable - the report averages StdHours_Monthly directly, and does it over the last month WITH data rather than a stale snapshot",
 "Cell_Master.Last_PM_WO_No":             "R3 - SharePoint version history already answers 'why did this counter go to zero'",
 "Cell_Master.Plant":                     "R3 - one plant. Reinstate when there is a second",
 "PM_WorkOrder.Actual_Start_Date":        "R1 derivable - MIN of task Scan_Start_Time",
 "PM_WorkOrder.Actual_End_Date":          "R1 derivable - MAX of task Scan_End_Time",
 "PM_WorkOrder.PM_Duration_Min":          "R1 derivable - SUM of task durations",
 "PM_WorkOrder.Planned_Start_Date":       "R3 - on-time is measured against Planned_End_Date only",
 "PM_WorkOrder.Lead_Tech_ID":             "R3 - never populated by any flow; the plan carries the allocation",
 "PM_WorkOrder.Reset_Date":               "R1 derivable - equals Last_PM_Date on the cell, set in the same action",
 "PM_WorkOrder.Cell_Name":                "R2 denormalised - lookup from Cell_Master",
 "PM_Machine_Task.Duration_Min":          "R1 derivable - Scan_End_Time minus Scan_Start_Time, computed in the model",
 "PM_Machine_Task.NOT_OK_Count":          "R1 derivable - count of NOT OK responses. The allotted list shows only unfinished tasks, which have no findings yet",
 "PM_Machine_Task.Abnormality_Raised":    "R1 derivable - EXISTS against Abnormality_Log",
 "PM_Machine_Task.Spare_Used_Flag":       "R1 derivable - EXISTS against Spare_Replaced",
 "PM_Machine_Task.Completion_Date":       "R1 derivable - the date part of Scan_End_Time",
 "PM_Machine_Task.Checklist_Response_ID": "R3 - responses already carry WO_No and Machine_ID; the link is the pair",
 "PM_Machine_Task.Assigned_Tech_ID":      "R3 - allocation lives on the plan; Completed_By is the record that matters",
 "Checklist_Response.Cell_ID":            "R2 denormalised - reachable through Machine_ID",
 "Checklist_Response.Action_Taken":       "R3 - Observation carries what was seen and done; two boxes got one answer",
 "Checklist_Response.Follow_Up_WO":       "R3 - follow-up is now a decision made from a view, not an auto-raised work order",
 "Breakdown_Log.Response_Time_Min":       "R1 derivable - Response_DateTime minus Reported_DateTime",
 "Breakdown_Log.MTTR_Min":                "R1 derivable - Repair_End minus Repair_Start",
 "Breakdown_Log.Linked_PM_WO":            "R1 derivable - the after-PM measure works from dates, by design",
 "Breakdown_Log.Spare_Used":              "R1 derivable - EXISTS against Spare_Replaced",
 "Breakdown_Log.Remarks":                 "R3 - Symptom, Root_Cause and Action_Taken are three boxes already",
 "Spare_Replaced.Total_Cost_INR":         "R1 derivable - Qty_Used x Unit_Cost_INR. Removes integrity rule 5 with it",
 "Spare_Replaced.Spare_Description":      "R2 denormalised - lookup from Spare_Master",
 "Spare_Replaced.Old_Part_Condition":     "R3 - Failure_Mode is the column that changes decisions; condition restates it",
 "Spare_Replaced.Expected_Life_Hours":    "R3 - never read by any measure or view",
 "Spare_Replaced.Remarks":                "R3 - free text nobody queries",
 "Abnormality_Log.Immediate_Action":      "R3 - Description carries it; two boxes got one answer",
 "Abnormality_Log.Closure_Remarks":       "R3 - Closed_Date is the fact that matters",
 "Abnormality_Log.Converted_To_WO":       "R3 - follow-up is a view-driven decision now",
 "PM_Plan_Calendar.Cell_Name":            "R2 denormalised",
 "PM_Plan_Calendar.Planned_Shift":        "R3 - never read",
 "PM_Plan_Calendar.Estimated_Duration_Hrs":"R1 derivable - summed Expected_Time_Min across the cell",
 "PM_Plan_Calendar.Frozen_Date":          "R3 - Plan_Version already distinguishes V1 from V2",
 "StdHours_Monthly.Cell_Name":            "R2 denormalised",
 "StdHours_Monthly.Uploaded_By":          "R3 - SharePoint records Created By automatically",
 "Machine_Master.Cell_Name":              "R2 denormalised",
 "Machine_Master.Make":                   "R3 - asset-register detail, not PM data",
 "Machine_Master.Model":                  "R3 - asset-register detail",
 "Machine_Master.Year_Installed":         "R3 - asset-register detail",
 "Machine_Master.Checklist_Form_URL":     "R1 derivable - built from the machine ID in the Machine Hub formatting, so 30 rows of URLs stop being maintained by hand",
 "Machine_Master.Breakdown_Form_URL":     "R1 derivable - same",
 "Machine_Master.Spare_Request_Form_URL": "R1 derivable - same",
 "Machine_Master.Abnormality_Form_URL":   "R1 derivable - same",
 "Checklist_Master.Checklist_Name":       "R2 denormalised - it was always '<Checklist_ID> Standard PM Checklist'",
 "Checklist_Master.Tool_Required":        "R3 - belongs on the printed checklist, not in the database",
 "Checklist_Master.Frequency":            "R3 - reserved for a future split that has not happened. One value in every row",
 "Technician_Master.Default_Shift":       "R3 - never read",
 "Technician_Master.Contact_No":          "R3 - never read; the directory has it",
 "Technician_Master.Role_Scope":          "R3 - never read. One value in every row",
 "Spare_Master.ABC_Class":                "R3 - the spend analysis can classify from cost and usage at read time",
 "Spare_Master.FMR_Class":                "R3 - same",
 "Spare_Master.Preferred_Vendor":         "R3 - purchasing data, not maintenance data",
 "Plant_Calendar.Shift_Count":            "R3 - proration counts working DAYS, not shifts",
 "Plant_Calendar.Remarks":                "R3 - Day_Type says what kind of day it is",
}

# Columns that LOOK derivable but stay, because something would break.
KEPT_DESPITE = {
 "Cell_Master.Next_PM_Due_Date_Calendar": "the 'Cells Due This Month' view filters on it, and CAML cannot add months to another column",
 "Cell_Master.Machine_Count":             "Flow 2 cross-checks the tasks it created against it. Deriving both sides of a control from the same source is not a control",
 "PM_WorkOrder.Machines_In_Scope":        "the completion bar on the tracking view needs both numbers in the row; SharePoint formatting cannot count a related list",
 "PM_WorkOrder.Machines_Completed":       "same",
 "Checklist_Response.Check_Point":        "storing the text keeps an old record readable after the master is reworded. The response is evidence",
 "Spare_Replaced.Unit_Cost_INR":          "copied at the time of use, so a later price rise does not rewrite last year's maintenance cost",
}

if __name__ == "__main__":
    import json, glob
    old = {}
    for f in sorted(glob.glob('sharepoint/schema/*.json')):
        if '_manifest' in f: continue
        d = json.load(open(f))
        old[d['ListTitle']] = [x['InternalName'] for x in d['Fields']]

    print(f"{'List':<22} {'was':>4} {'now':>4} {'cut':>4}")
    print('-'*40)
    tw = tn = 0
    for l in old:
        if l in DROP_LISTS:
            print(f"{l:<22} {len(old[l]):>4} {'--':>4} {len(old[l]):>4}   LIST REMOVED")
            tw += len(old[l]); continue
        k = KEEP.get(l, old[l])
        print(f"{l:<22} {len(old[l]):>4} {len(k):>4} {len(old[l])-len(k):>4}")
        tw += len(old[l]); tn += len(k)
    print('-'*40)
    print(f"{'TOTAL':<22} {tw:>4} {tn:>4} {tw-tn:>4}   ({(tw-tn)/tw:.0%} fewer)")
    print(f"\nlists {len(old)} -> {len(old)-len(DROP_LISTS)}")

    # every KEEP column must exist in the current schema
    bad = [(l,c) for l,cs in KEEP.items() for c in cs if c not in old.get(l,[])]
    print(f"KEEP columns not present in the current schema: {bad if bad else 'none'}")
    # every CUT must name a real column
    badcut = [k for k in CUT if k.split('.')[1] not in old.get(k.split('.')[0],[])]
    print(f"CUT entries naming a non-existent column: {badcut if badcut else 'none'}")
    # accounting: kept + cut + dropped-lists must equal the original
    acct = tn + len(CUT) + sum(len(old[l]) for l in DROP_LISTS)
    print(f"accounting: {tn} kept + {len(CUT)} cut + {sum(len(old[l]) for l in DROP_LISTS)} in dropped lists = {acct} (original {tw})")
