"""
powerfx_reference.py - the Power Fx behind every screen.

Each entry is (Control, Property, Formula, Why). The prototype shows these
in-app next to the screen they implement, and build_power_app.py writes them
out as the build reference, so the demo and the specification cannot drift.
"""

APP = [
    ("App", "OnStart", """Set(gUser, User());
Set(gTech,
    LookUp(Technician_Master, Lower(Email) = Lower(gUser.Email) && Active = "Yes")
);
Set(gScanType, Lower(Coalesce(Param("type"), "")));
Set(gScanId,   Upper(Coalesce(Param("id"), "")));
Set(gMachine,
    If(gScanType = "machine", LookUp(Machine_Master, MachineID = gScanId), Blank())
);
Set(gCell, If(!IsBlank(gMachine), LookUp(Cell_Master, CellID = gMachine.CellID), Blank()));
Set(gScannedThisSession, false);
Navigate(Switch(gScanType, "machine", scrMachineHub, "tech", scrMyPMList, scrHome));""",
     "The QR code is a deep link. Param() reads type and id out of it and jumps "
     "straight to the right screen. Identity comes from User(), never from the QR."),

    ("App", "OnError", """Notify("Something went wrong. Your entry has not been lost - "
    & "try again, or tell your supervisor.", NotificationType.Error);
Trace("PMFieldApp error: " & FirstError.Message, TraceSeverity.Error);""",
     "A technician on a shop floor cannot act on a raw error. Log the detail, "
     "show them something useful."),
]

SCREENS = {
    "scrMachineHub": ("Machine hub", "What a machine QR opens", [
        ("scrMachineHub", "OnVisible", """Set(gLastPM,
    First(Sort(
        Filter(PM_WorkOrders, MachineID = gMachine.MachineID, Status = "Completed"),
        ActualEndDate, SortOrder.Descending
    ))
);
Set(gOpenWO,
    LookUp(PM_WorkOrders,
        MachineID = gMachine.MachineID
        && AssignedTechID = gTech.TechID
        && Status in ["Scheduled", "In Progress", "Overdue"]
    )
);""",
         "Two lookups drive the whole screen: the last completed PM, and whether "
         "this person has an open job on this machine."),

        ("lblLastPM", "Text", """If(IsBlank(gLastPM),
   "No PM recorded yet",
   Text(gLastPM.ActualEndDate, "dd mmm yyyy")
     & "   (" & DateDiff(gLastPM.ActualEndDate, Today(), Days) & " days ago)"
     & Char(10) & "by " & gLastPM.AssignedTechName & " · " & gLastPM.PMResult
)""",
         "This is the question people scan to ask. It goes at the top, in large type, "
         "before any button."),

        ("btnStartPM", "Visible", "!IsBlank(gOpenWO)",
         "Hidden unless this machine has an open job assigned to the person scanning. "
         "A button that errors when pressed is worse than no button."),

        ("btnStartPM", "OnSelect", """Patch(QR_Scan_Log, Defaults(QR_Scan_Log), {
    ScanID: "SC-" & Text(Now(), "yyyymmddhhmmss") & "-" & gTech.TechID,
    QRType: "Machine QR",
    MachineID: gMachine.MachineID,
    MachineName: gMachine.MachineName,
    TechID: gTech.TechID,
    TechName: gTech.TechName,
    ScanDateTime: Now(),
    Action: "Start PM Checklist",
    CellID: gMachine.CellID
});
Set(gScannedThisSession, true);
Set(gWO, gOpenWO);
Set(gStartTime, Now());
Navigate(scrChecklist);""",
         "Every action on this screen writes a scan record first. That is what makes "
         "attendance provable rather than asserted."),

        ("lblNextPM", "Text", """With({
    ledger: LookUp(Sort(Filter(PM_Hour_Ledger, CellID = gMachine.CellID,
                               Scenario = "Actual"), MonthKey, SortOrder.Descending), true)
},
  "Next PM at " & Text(ledger.PMIntervalStdHrs, "[$-en-GB]#,##0") & " h · "
  & Text(Max(0, ledger.PMIntervalStdHrs - ledger.ClosingStdHrs), "[$-en-GB]#,##0")
  & " h to go"
)""",
         "Shows the counter the same way the dashboard does, so the floor and the "
         "office are reading one number."),
    ]),

    "scrMyPMList": ("My PM list", "What a technician QR opens", [
        ("galMyPM", "Items", """SortByColumns(
    Filter(PM_WorkOrders,
        AssignedTechID = gTech.TechID,
        Status in ["Scheduled", "In Progress", "Overdue"]
    ),
    "DueDate", SortOrder.Ascending
)""",
         "The list maintains itself. A job leaves it when the machine QR is scanned "
         "and the checklist submitted - there is no 'mark as done' control anywhere."),

        ("lblProgress", "Text", """CountRows(Filter(PM_WorkOrders, AssignedTechID = gTech.TechID,
        PlanMonth = Text(Today(), "yyyy-mm"), Status = "Completed"))
& " of " &
CountRows(Filter(PM_WorkOrders, AssignedTechID = gTech.TechID,
        PlanMonth = Text(Today(), "yyyy-mm")))
& " done this month" """,
         "One line of progress at the top. People check this more than any report."),

        ("galMyPM", "OnSelect", """Set(gMachine, LookUp(Machine_Master, MachineID = ThisItem.MachineID));
Set(gCell, LookUp(Cell_Master, CellID = gMachine.CellID));
Set(gScannedThisSession, false);
Navigate(scrMachineHub);""",
         "Tapping a row opens the machine hub, NOT the checklist. The technician still "
         "has to scan the machine. That is the whole point."),

        ("recOverdueStripe", "Fill", """If(ThisItem.DueDate < Today(), ColorValue("#C4553B"),
   ThisItem.DueDate <= DateAdd(Today(), 3, Days), ColorValue("#D08B2C"),
   ColorValue("#CBD7DD"))""",
         "Encode state in form as well as text, so what needs attention reads at a glance."),
    ]),

    "scrChecklist": ("PM checklist", "The evidence trail", [
        ("scrChecklist", "OnVisible", """If(!gScannedThisSession,
    Notify("Scan the machine QR code to start this checklist.", NotificationType.Warning);
    Back()
);
If(CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID)) = 0,
    ForAll(Filter(PM_Checklist_Master, ChecklistID = gMachine.ChecklistID) As Task,
        Patch(PM_ChecklistResults, Defaults(PM_ChecklistResults), {
            ResultID: gWO.WOID & "-T" & Text(Task.TaskNo, "00"),
            WOID: gWO.WOID,
            MachineID: gMachine.MachineID,
            MachineName: gMachine.MachineName,
            ChecklistID: Task.ChecklistID,
            TaskNo: Task.TaskNo,
            TaskDescription: Task.TaskDescription,
            TaskType: Task.TaskType,
            AcceptanceStandard: Task.AcceptanceStandard,
            Mandatory: Task.Mandatory,
            SafetyCritical: Task.SafetyCritical,
            TechID: gTech.TechID
        })
    )
);
Patch(PM_WorkOrders, gWO, {
    Status: "In Progress",
    ActualStartDate: Today(),
    MachineQRScanned: "Yes"
});""",
         "The guard on the first line is the anti-desk-closure rule, in code. "
         "Then one result row per task, and the work order flips to In Progress."),

        ("galTasks", "Items", "Filter(PM_ChecklistResults, WOID = gWO.WOID)",
         "One row per task, rendered by TaskType: Measurement gets a numeric box, "
         "everything else gets OK / Not OK / N-A."),

        ("btnSubmit", "DisplayMode", """If(
    CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID,
                     Mandatory = "Yes", IsBlank(Result))) = 0,
    DisplayMode.Edit, DisplayMode.Disabled
)""",
         "Mandatory tasks block submit. This is what stops a partial PM being signed "
         "off as complete."),

        ("tglNotOK", "OnChange", """If(Self.Value,
    Patch(Abnormality_Log, Defaults(Abnormality_Log), {
        AbnormalityID: "ABN-" & Text(Now(), "yyyymmddhhmmss"),
        Source: "PM Checklist",
        SourceRefID: gWO.WOID,
        MachineID: gMachine.MachineID,
        CellID: gMachine.CellID,
        Category: cmbCategory.Selected.Value,
        Severity: cmbSeverity.Selected.Value,
        Description: "Task " & ThisItem.TaskNo & ": " & ThisItem.TaskDescription
                     & " - outside standard (" & ThisItem.AcceptanceStandard & ")",
        ReportedByTechID: gTech.TechID,
        ReportedDate: Today(),
        Status: "Open",
        EscalationRequired: If(cmbSeverity.Selected.Value = "High", "Yes", "No")
    })
)""",
         "A failed task raises an abnormality automatically. Nobody has to remember to."),

        ("btnSubmit", "OnSelect", """Patch(PM_WorkOrders, gWO, {
    Status: "Completed",
    ActualEndDate: Today(),
    DurationMin: DateDiff(gStartTime, Now(), Minutes),
    ChecklistDoneTasks: CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID, !IsBlank(Result))),
    ChecklistFailTasks: CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID, Result = "Not OK")),
    PMResult: With({fails: CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID,
                                            Result = "Not OK"))},
        Switch(true, fails = 0, "Pass", fails <= 2, "Pass with observation",
               "Fail - follow-up raised")),
    OnTimeFlag: If(Today() <= gWO.DueDate, "Yes", "No")
});
Notify("PM closed for " & gMachine.MachineName, NotificationType.Success);
Navigate(scrMyPMList);""",
         "OnTimeFlag is calculated here, not typed. That is what keeps the compliance "
         "number honest."),
    ]),

    "scrBreakdown": ("Report breakdown", "Unplanned stoppage", [
        ("btnSubmitBreakdown", "OnSelect", """Patch(Breakdown_Reports, Defaults(Breakdown_Reports), {
    BreakdownID: "BD-" & Text(Now(), "yyyymmddhhmmss"),
    MachineID: gMachine.MachineID,
    MachineName: gMachine.MachineName,
    CellID: gMachine.CellID,
    ReportedDateTime: Now(),
    FailureMode: cmbFailureMode.Selected.Value,
    FailureCategory: cmbFailureMode.Selected.Category,
    Severity: cmbSeverity.Selected.Value,
    ActionTaken: "",
    ReportedBy: If(IsBlank(gTech), "Operator", "Technician"),
    AttendedTechID: gTech.TechID,
    AttendedTechName: gTech.TechName,
    Status: "Open"
});
Navigate(scrMachineHub);""",
         "ReportedDateTime is Now() and is not editable by the reporter. A back-datable "
         "breakdown time makes MTTR worthless."),

        ("cmbFailureMode", "Items", """["Bearing failure", "Hydraulic leak", "Sensor / proximity fault",
 "Drive / VFD trip", "Coolant pump failure", "Spindle overheating",
 "Belt / chain breakage", "PLC communication loss", "Pneumatic pressure drop",
 "Thermocouple drift", "Seal / gasket leak", "Limit switch damage",
 "Tool clamp malfunction", "Motor winding failure", "Software / parameter loss"]""",
         "A curated list, not free text. Free text makes the Pareto chart useless."),
    ]),

    "scrSpareRequest": ("Request spare", "Parts", [
        ("cmbPart", "Items", """Filter(SparePart_Master,
    AppliesToMachineType = gMachine.MachineType || AppliesToMachineType = "All")""",
         "Filtered to what actually fits this machine."),

        ("lblApprovalWarning", "Visible", """cmbPart.Selected.UnitCostINR * Value(txtQty.Text)
  > Value(LookUp(PM_Config, ConfigKey = "SpareApprovalLimitINR").ConfigValue)""",
         "Warn before submit that this needs Plant Head approval, so the delay is not "
         "a surprise three days later."),

        ("btnSubmitRequest", "OnSelect", """Patch(SparePart_Requests, Defaults(SparePart_Requests), {
    RequestID: "REQ-" & Text(Now(), "yyyymmddhhmmss"),
    SourceType: If(IsBlank(gWO), "Breakdown", "PM"),
    SourceID: Coalesce(gWO.WOID, gBreakdownID),
    MachineID: gMachine.MachineID,
    MachineName: gMachine.MachineName,
    CellID: gMachine.CellID,
    PartNo: cmbPart.Selected.PartNo,
    PartName: cmbPart.Selected.PartName,
    QtyRequested: Value(txtQty.Text),
    UnitCostINR: cmbPart.Selected.UnitCostINR,
    TotalCostINR: cmbPart.Selected.UnitCostINR * Value(txtQty.Text),
    RequestedByTechID: gTech.TechID,
    RequestDate: Today(),
    Urgency: cmbUrgency.Selected.Value,
    Status: "Pending Approval"
});""",
         "Status starts at Pending Approval. Flow 5 takes it from there."),
    ]),

    "scrAbnormality": ("Log abnormality", "Early warning", [
        ("btnSubmitAbn", "DisplayMode",
         "If(IsBlank(imgPhoto.Image), DisplayMode.Disabled, DisplayMode.Edit)",
         "Photo mandatory, no exceptions. An abnormality without a photo does not get fixed."),

        ("btnSubmitAbn", "OnSelect", """Patch(Abnormality_Log, Defaults(Abnormality_Log), {
    AbnormalityID: "ABN-" & Text(Now(), "yyyymmddhhmmss"),
    Source: "QR Walk-by",
    MachineID: gMachine.MachineID,
    MachineName: gMachine.MachineName,
    CellID: gMachine.CellID,
    Category: cmbCategory.Selected.Value,
    Severity: cmbSeverity.Selected.Value,
    Description: txtDescription.Text,
    ReportedByTechID: gTech.TechID,
    ReportedByName: gTech.TechName,
    ReportedDate: Today(),
    Status: "Open",
    EscalationRequired: If(cmbSeverity.Selected.Value = "High", "Yes", "No")
});""",
         "EscalationRequired is set here; Flow 4 watches for it."),
    ]),
}
