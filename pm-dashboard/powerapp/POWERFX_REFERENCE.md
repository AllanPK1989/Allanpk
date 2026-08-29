# Power Fx Reference

Every control and formula in the PM Field App, in build order. Create the screen, add the control with exactly the name given, and paste the formula into the named property.

> Generated from `scripts/powerfx_reference.py`. The working prototype shows these same formulas next to the screen they implement, so what you demo and what you build cannot drift apart.

## Before you start

1. Power Apps ▸ Create ▸ Blank app ▸ Canvas ▸ **Phone** (640 × 1136).
2. Name it `PM Field App`.
3. Add the SharePoint connector and all eight lists, plus the six master workbooks as data sources.
4. Create the screens in this order: `scrHome`, `scrMachineHub`, `scrMyPMList`, `scrChecklist`, `scrBreakdown`, `scrSpareRequest`, `scrSpareReplaced`, `scrAbnormality`, `scrMachineHistory`.

## App

### `App.OnStart`

The QR code is a deep link. Param() reads type and id out of it and jumps straight to the right screen. Identity comes from User(), never from the QR.

```powerfx
Set(gUser, User());
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
Navigate(Switch(gScanType, "machine", scrMachineHub, "tech", scrMyPMList, scrHome));
```

### `App.OnError`

A technician on a shop floor cannot act on a raw error. Log the detail, show them something useful.

```powerfx
Notify("Something went wrong. Your entry has not been lost - "
    & "try again, or tell your supervisor.", NotificationType.Error);
Trace("PMFieldApp error: " & FirstError.Message, TraceSeverity.Error);
```

## `scrMachineHub` — Machine hub

*What a machine QR opens*

### `scrMachineHub.OnVisible`

Two lookups drive the whole screen: the last completed PM, and whether this person has an open job on this machine.

```powerfx
Set(gLastPM,
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
);
```

### `lblLastPM.Text`

This is the question people scan to ask. It goes at the top, in large type, before any button.

```powerfx
If(IsBlank(gLastPM),
   "No PM recorded yet",
   Text(gLastPM.ActualEndDate, "dd mmm yyyy")
     & "   (" & DateDiff(gLastPM.ActualEndDate, Today(), Days) & " days ago)"
     & Char(10) & "by " & gLastPM.AssignedTechName & " · " & gLastPM.PMResult
)
```

### `btnStartPM.Visible`

Hidden unless this machine has an open job assigned to the person scanning. A button that errors when pressed is worse than no button.

```powerfx
!IsBlank(gOpenWO)
```

### `btnStartPM.OnSelect`

Every action on this screen writes a scan record first. That is what makes attendance provable rather than asserted.

```powerfx
Patch(QR_Scan_Log, Defaults(QR_Scan_Log), {
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
Navigate(scrChecklist);
```

### `lblNextPM.Text`

Shows the counter the same way the dashboard does, so the floor and the office are reading one number.

```powerfx
With({
    ledger: LookUp(Sort(Filter(PM_Hour_Ledger, CellID = gMachine.CellID,
                               Scenario = "Actual"), MonthKey, SortOrder.Descending), true)
},
  "Next PM at " & Text(ledger.PMIntervalStdHrs, "[$-en-GB]#,##0") & " h · "
  & Text(Max(0, ledger.PMIntervalStdHrs - ledger.ClosingStdHrs), "[$-en-GB]#,##0")
  & " h to go"
)
```

## `scrMyPMList` — My PM list

*What a technician QR opens*

### `galMyPM.Items`

The list maintains itself. A job leaves it when the machine QR is scanned and the checklist submitted - there is no 'mark as done' control anywhere.

```powerfx
SortByColumns(
    Filter(PM_WorkOrders,
        AssignedTechID = gTech.TechID,
        Status in ["Scheduled", "In Progress", "Overdue"]
    ),
    "DueDate", SortOrder.Ascending
)
```

### `lblProgress.Text`

One line of progress at the top. People check this more than any report.

```powerfx
CountRows(Filter(PM_WorkOrders, AssignedTechID = gTech.TechID,
        PlanMonth = Text(Today(), "yyyy-mm"), Status = "Completed"))
& " of " &
CountRows(Filter(PM_WorkOrders, AssignedTechID = gTech.TechID,
        PlanMonth = Text(Today(), "yyyy-mm")))
& " done this month"
```

### `galMyPM.OnSelect`

Tapping a row opens the machine hub, NOT the checklist. The technician still has to scan the machine. That is the whole point.

```powerfx
Set(gMachine, LookUp(Machine_Master, MachineID = ThisItem.MachineID));
Set(gCell, LookUp(Cell_Master, CellID = gMachine.CellID));
Set(gScannedThisSession, false);
Navigate(scrMachineHub);
```

### `recOverdueStripe.Fill`

Encode state in form as well as text, so what needs attention reads at a glance.

```powerfx
If(ThisItem.DueDate < Today(), ColorValue("#C4553B"),
   ThisItem.DueDate <= DateAdd(Today(), 3, Days), ColorValue("#D08B2C"),
   ColorValue("#CBD7DD"))
```

## `scrChecklist` — PM checklist

*The evidence trail*

### `scrChecklist.OnVisible`

The guard on the first line is the anti-desk-closure rule, in code. Then one result row per task, and the work order flips to In Progress.

```powerfx
If(!gScannedThisSession,
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
});
```

### `galTasks.Items`

One row per task, rendered by TaskType: Measurement gets a numeric box, everything else gets OK / Not OK / N-A.

```powerfx
Filter(PM_ChecklistResults, WOID = gWO.WOID)
```

### `btnSubmit.DisplayMode`

Mandatory tasks block submit. This is what stops a partial PM being signed off as complete.

```powerfx
If(
    CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID,
                     Mandatory = "Yes", IsBlank(Result))) = 0,
    DisplayMode.Edit, DisplayMode.Disabled
)
```

### `tglNotOK.OnChange`

A failed task raises an abnormality automatically. Nobody has to remember to.

```powerfx
If(Self.Value,
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
)
```

### `btnSubmit.OnSelect`

OnTimeFlag is calculated here, not typed. That is what keeps the compliance number honest.

```powerfx
Patch(PM_WorkOrders, gWO, {
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
Navigate(scrMyPMList);
```

## `scrBreakdown` — Report breakdown

*Unplanned stoppage*

### `btnSubmitBreakdown.OnSelect`

ReportedDateTime is Now() and is not editable by the reporter. A back-datable breakdown time makes MTTR worthless.

```powerfx
Patch(Breakdown_Reports, Defaults(Breakdown_Reports), {
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
Navigate(scrMachineHub);
```

### `cmbFailureMode.Items`

A curated list, not free text. Free text makes the Pareto chart useless.

```powerfx
["Bearing failure", "Hydraulic leak", "Sensor / proximity fault",
 "Drive / VFD trip", "Coolant pump failure", "Spindle overheating",
 "Belt / chain breakage", "PLC communication loss", "Pneumatic pressure drop",
 "Thermocouple drift", "Seal / gasket leak", "Limit switch damage",
 "Tool clamp malfunction", "Motor winding failure", "Software / parameter loss"]
```

## `scrSpareRequest` — Request spare

*Parts*

### `cmbPart.Items`

Filtered to what actually fits this machine.

```powerfx
Filter(SparePart_Master,
    AppliesToMachineType = gMachine.MachineType || AppliesToMachineType = "All")
```

### `lblApprovalWarning.Visible`

Warn before submit that this needs Plant Head approval, so the delay is not a surprise three days later.

```powerfx
cmbPart.Selected.UnitCostINR * Value(txtQty.Text)
  > Value(LookUp(PM_Config, ConfigKey = "SpareApprovalLimitINR").ConfigValue)
```

### `btnSubmitRequest.OnSelect`

Status starts at Pending Approval. Flow 5 takes it from there.

```powerfx
Patch(SparePart_Requests, Defaults(SparePart_Requests), {
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
});
```

## `scrAbnormality` — Log abnormality

*Early warning*

### `btnSubmitAbn.DisplayMode`

Photo mandatory, no exceptions. An abnormality without a photo does not get fixed.

```powerfx
If(IsBlank(imgPhoto.Image), DisplayMode.Disabled, DisplayMode.Edit)
```

### `btnSubmitAbn.OnSelect`

EscalationRequired is set here; Flow 4 watches for it.

```powerfx
Patch(Abnormality_Log, Defaults(Abnormality_Log), {
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
});
```

## Rules the app enforces, and why

| Rule | Reason |
|------|--------|
| A checklist can only start from a machine QR scan in the same session | Stops desk closure |
| Every screen entry writes to `QR_Scan_Log` | Attendance is provable, not asserted |
| Photo mandatory on any Not OK and on every abnormality | An abnormality without a photo does not get fixed |
| Mandatory tasks block submit | Partial PMs stop being signed off as complete |
| `ReportedDateTime` is `Now()`, never editable | MTTR stays honest |
| The technician QR shows the signed-in user's list, not the badge's | A borrowed badge cannot close someone else's work |
