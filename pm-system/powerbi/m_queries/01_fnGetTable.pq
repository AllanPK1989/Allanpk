// ===========================================================================
// Function: fnGetTable
// ---------------------------------------------------------------------------
// The single source-swap point for the whole model.
//
//   fnGetTable("Cell_Master", "01_PM_Master_Data.xlsx", "Cell_Master")
//
// In Excel mode it opens the named sheet in the named workbook under
// pSourceFolder. In SharePoint mode it opens the list of the same name on
// pSharePointSite. Because the data dictionary made every sheet name and every
// column name identical to its SharePoint list and column name, the two paths
// return the same shape and every downstream step is unchanged.
//
// Arguments:
//   ListName   - SharePoint list title (production)
//   WorkbookFile - workbook file name (development)
//   SheetName  - sheet name inside that workbook (development)
//
// Note on SharePoint.Tables vs SharePoint.Contents:
//   SharePoint.Tables uses the OData v1.0 list endpoint. It returns friendly
//   column names and folds filters back to the server, which is what keeps a
//   1,000-row list from being pulled in full on every refresh. That is why the
//   implementation below uses ApiVersion 15 rather than the newer default.
// ===========================================================================
let
    fnGetTable = (ListName as text, WorkbookFile as text, SheetName as text) as table =>
        let
            // Normalise the folder so it works with or without a trailing slash.
            FolderRaw  = Text.Trim(pSourceFolder),
            Folder     = if Text.EndsWith(FolderRaw, "\") or Text.EndsWith(FolderRaw, "/")
                         then Text.Start(FolderRaw, Text.Length(FolderRaw) - 1)
                         else FolderRaw,
            Separator  = if Text.Contains(Folder, "/") then "/" else "\",
            FullPath   = Folder & Separator & WorkbookFile,

            FromExcel =
                let
                    Source = Excel.Workbook(File.Contents(FullPath), null, true),
                    Sheet  = Source{[Item = SheetName, Kind = "Sheet"]}[Data],
                    Header = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
                    // Drop the fully blank rows Excel leaves behind under a table.
                    Clean  = Table.SelectRows(
                                 Header,
                                 each not List.IsEmpty(
                                     List.RemoveMatchingItems(Record.FieldValues(_), {"", null})))
                in
                    Clean,

            FromSharePoint =
                let
                    Site    = Text.TrimEnd(Text.Trim(pSharePointSite), "/"),
                    Source  = SharePoint.Tables(Site, [ApiVersion = 15]),
                    Rows    = Source{[Title = ListName]}[Items],
                    // SharePoint hands back dozens of system columns (Created,
                    // Modified, ContentType, every *_x003a_* lookup expansion).
                    // Keeping only the dictionary columns is what stops the model
                    // doubling in size the day someone enables a new site column.
                    Wanted  = List.Intersect({Table.ColumnNames(Rows), ExpectedColumns(ListName)}),
                    Trimmed = Table.SelectColumns(Rows, Wanted)
                in
                    Trimmed
        in
            if pSourceMode = "SharePoint" then FromSharePoint else FromExcel,

    // The column list per table, so SharePoint mode returns exactly the
    // dictionary columns and nothing else. Kept here rather than in each query
    // so there is one place to edit when the dictionary changes.
    ExpectedColumns = (ListName as text) as list =>
        let
            m = [
                Cell_Master        = {"Cell_ID","Cell_Name","Plant","Process_Area","Machine_Count","PM_Trigger_Hours","Calendar_Backstop_Months","Cum_Std_Hours_Since_PM","Last_PM_Date","Last_PM_WO_No","Next_PM_Due_Date_Calendar","Avg_Monthly_Std_Hours_L3M","Owner_Supervisor","Criticality","Active"},
                Machine_Master     = {"Machine_ID","Machine_Name","Cell_ID","Cell_Name","Machine_Family","Make","Model","Serial_No","Year_Installed","Location_Tag","Checklist_ID","Checklist_Form_URL","Breakdown_Form_URL","Spare_Request_Form_URL","Abnormality_Form_URL","QR_Payload_URL","Criticality","Active"},
                Checklist_Master   = {"Checklist_ID","Checklist_Name","Item_No","Check_Point","Check_Type","Acceptance_Standard","Tool_Required","Frequency","Safety_Critical","Expected_Time_Min","Active"},
                Technician_Master  = {"Tech_ID","Tech_Name","Skill_Level","Trade","Default_Shift","Contact_No","Role_Scope","Active"},
                Spare_Master       = {"Spare_Code","Spare_Description","Category","UOM","ABC_Class","FMR_Class","Unit_Cost_INR","Min_Stock","Current_Stock","Lead_Time_Days","Bin_Location","Preferred_Vendor","Active"},
                StdHours_Monthly   = {"Upload_Month","Cell_ID","Cell_Name","Actual_Std_Hours","Production_Qty","Uploaded_By","Upload_Date","Remarks"},
                PM_WorkOrder       = {"WO_No","Cell_ID","Cell_Name","Trigger_Type","Trigger_Hours_At_Creation","WO_Created_Date","Planned_Month","Planned_Start_Date","Planned_End_Date","Lead_Tech_ID","Priority","Machines_In_Scope","Machines_Completed","WO_Status","Actual_Start_Date","Actual_End_Date","PM_Duration_Min","Reset_Applied","Reset_Date","Remarks"},
                PM_Machine_Task    = {"Task_ID","WO_No","Machine_ID","Cell_ID","Assigned_Tech_ID","Task_Status","Scan_Start_Time","Scan_End_Time","Duration_Min","Checklist_Response_ID","NOT_OK_Count","Abnormality_Raised","Spare_Used_Flag","Completed_By","Completion_Date","Skip_Reason"},
                Checklist_Response = {"Response_ID","Submitted_DateTime","WO_No","Machine_ID","Cell_ID","Checklist_ID","Item_No","Check_Point","Result","Measured_Value","Observation","Photo_Link","Action_Taken","Tech_ID","Follow_Up_Required","Follow_Up_WO"},
                Scan_Log           = {"Scan_ID","Scan_DateTime","Machine_ID","Cell_ID","Tech_ID","Scan_Action","Device","WO_No","Comments"},
                Breakdown_Log      = {"BD_ID","Reported_DateTime","Machine_ID","Cell_ID","Reported_By_Tech_ID","Shift","Breakdown_Type","Symptom","Root_Cause","Action_Taken","Response_DateTime","Repair_Start","Repair_End","Response_Time_Min","MTTR_Min","Production_Loss_Min","Spare_Used","Status","Recurrence_Flag","Linked_PM_WO","Remarks"},
                Spare_Request      = {"Req_ID","Request_DateTime","WO_No","Machine_ID","Cell_ID","Spare_Code","Spare_Description","Qty_Requested","Requested_By","Urgency","Reason","Approval_Status","Approved_By","Approved_Date","Issue_Status","Issued_Qty","Issue_Date","Stock_At_Request","Remarks"},
                Spare_Replaced     = {"Repl_ID","Replaced_DateTime","Source_Type","Source_Ref","Machine_ID","Cell_ID","Spare_Code","Spare_Description","Qty_Used","Unit_Cost_INR","Total_Cost_INR","Old_Part_Condition","Failure_Mode","Replaced_By","Expected_Life_Hours","Warranty_Claim","Remarks"},
                Abnormality_Log    = {"Abn_ID","Logged_DateTime","Machine_ID","Cell_ID","Logged_By","Category","Description","Severity","Photo_Link","Immediate_Action","Responsibility","Target_Date","Status","Closed_Date","Closure_Remarks","Converted_To_WO"},
                PM_Plan_Calendar   = {"Plan_ID","Plan_Month","Cell_ID","Cell_Name","Planned_Date","Planned_Shift","Planned_Tech_ID","Estimated_Duration_Hrs","Plan_Version","Frozen_Date","WO_No","Adherence_Status"}
            ]
        in
            Record.FieldOrDefault(m, ListName, {})
in
    fnGetTable
