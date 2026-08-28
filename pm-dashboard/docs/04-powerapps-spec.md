# 04 · Power Apps — "PM Field App"

One canvas app, phone layout, opened by every QR code. This is the only thing that
writes data.

## App-level setup

**Create:** Power Apps ▸ Create ▸ Blank app ▸ Canvas ▸ **Phone** (640 × 1136).
**Name:** `PM Field App`.

**Data sources** — SharePoint connector, site `PMSystem`, all eight lists, plus
the six master workbooks via the same site (Excel tables) or as additional lists
if you prefer to keep masters as lists.

**App.OnStart** — this is what makes a QR code work. The QR encodes a deep link
with `type` and `id` in the query string; the app reads them and jumps straight to
the right screen:

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
Set(gCell,
    If(!IsBlank(gMachine), LookUp(Cell_Master, CellID = gMachine.CellID), Blank())
);

// A technician QR overrides the signed-in identity only for supervisors;
// for everyone else the signed-in account wins. Never trust the QR alone.
If(gScanType = "tech" && gTech.TechID <> gScanId && !gIsSupervisor,
   Notify("This badge is not yours. Showing your own list.", NotificationType.Warning)
);

Set(gConfig, PM_Config);

Navigate(
    Switch(gScanType,
        "machine", scrMachineHub,
        "tech",    scrMyPMList,
        scrHome
    )
);
```

**Offline:** in `App.OnStart` also run `LoadData`/`SaveData` for the technician's
open work orders and the checklist master, so a lost signal in a bay does not stop
a job. `Connection.Connected` gates the submit; queued items flush on reconnect.

## Screens

### `scrMachineHub` — what a machine QR opens

The moment of truth for the whole system. Big type, six buttons, nothing else.

```
┌────────────────────────────────┐
│  CNC Lathe TL-01               │   MachineName, 22pt
│  MC-001 · CNC Turning Line A   │   MachineID · CellName
├────────────────────────────────┤
│  LAST PM DONE                  │
│  14 Jun 2026        (75 days)  │   ← the question everyone scans to ask
│  by Arun Kumar · Pass          │
│  NEXT PM DUE                   │
│  Sep 2026 · 640 h to go        │
├────────────────────────────────┤
│  ▶  Start PM checklist      ①  │   visible only if an open WO exists
│  ⚠  Report breakdown           │
│  ⚙  Request spare part         │
│  ⟳  Record spare replaced      │
│  ◎  Log abnormality            │
│  ⌕  View full history          │
└────────────────────────────────┘
```

Last PM block:

```powerfx
// gLastPM
Set(gLastPM,
    First(
        Sort(
            Filter(PM_WorkOrders, MachineID = gMachine.MachineID, Status = "Completed"),
            ActualEndDate, SortOrder.Descending
        )
    )
);
```

Label text:

```powerfx
If(IsBlank(gLastPM),
   "No PM recorded yet",
   Text(gLastPM.ActualEndDate, "dd mmm yyyy")
     & "   (" & DateDiff(gLastPM.ActualEndDate, Today(), Days) & " days ago)"
     & Char(10) & "by " & gLastPM.AssignedTechName & " · " & gLastPM.PMResult
)
```

**Every button on this screen writes a scan record first.** That is what makes
attendance provable:

```powerfx
Patch(QR_Scan_Log, Defaults(QR_Scan_Log), {
    ScanID:   "SC-" & Text(Now(), "yyyymmddhhmmss") & "-" & gTech.TechID,
    QRType:   "Machine QR",
    MachineID: gMachine.MachineID,
    MachineName: gMachine.MachineName,
    TechID:   gTech.TechID,
    TechName: gTech.TechName,
    ScanDateTime: Now(),
    Action:   "Start PM Checklist",
    CellID:   gMachine.CellID
});
```

### `scrMyPMList` — what a technician QR opens

The personal work list. **This is the list that updates itself**: an item leaves it
the moment the machine QR is scanned and the checklist submitted — there is no
"mark as done" button anywhere, because a job you can tick off without being at the
machine is a job that gets ticked off without being at the machine.

```powerfx
// Items
SortByColumns(
    Filter(PM_WorkOrders,
        AssignedTechID = gTech.TechID,
        Status in ["Scheduled", "In Progress", "Overdue"]
    ),
    "DueDate", SortOrder.Ascending
)
```

Gallery row: machine name, cell, due date, a status pill, and a red left border
when `DueDate < Today()`. Header shows the count and the month's progress:

```powerfx
CountRows(Filter(PM_WorkOrders, AssignedTechID = gTech.TechID,
                 PlanMonth = Text(Today(), "yyyy-mm"), Status = "Completed"))
& " of " &
CountRows(Filter(PM_WorkOrders, AssignedTechID = gTech.TechID,
                 PlanMonth = Text(Today(), "yyyy-mm")))
& " done this month"
```

Tapping a row opens `scrMachineHub` for that machine — it does **not** open the
checklist directly. The technician still has to scan the machine. That is the
whole point.

### `scrChecklist` — the PM checklist

Entered only from `scrMachineHub` ▸ Start PM checklist, and only when
`gMachine.MachineID` came from a scan in this session.

On entry, materialise one result row per task:

```powerfx
If(
    CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID)) = 0,
    ForAll(
        Filter(PM_Checklist_Master, ChecklistID = gMachine.ChecklistID) As Task,
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

Each row renders by `TaskType`:

| TaskType | Control |
|----------|---------|
| `Measurement` | numeric text input + the acceptance standard shown underneath |
| `Safety`, `Visual`, `Functional`, `Electrical`, `Cleaning`, `Lubrication`, `Replacement` | OK / Not OK / N-A toggle |

**Not OK** expands the row: a mandatory comment, a mandatory photo, and a severity
picker. On submit it writes both the result and an abnormality:

```powerfx
Patch(Abnormality_Log, Defaults(Abnormality_Log), {
    AbnormalityID: "ABN-" & Text(Now(), "yyyymmddhhmmss"),
    Source: "PM Checklist",
    SourceRefID: gWO.WOID,
    MachineID: gMachine.MachineID,
    CellID: gMachine.CellID,
    Category: cmbCategory.Selected.Value,
    Severity: cmbSeverity.Selected.Value,
    Description: "Task " & ThisItem.TaskNo & ": " & ThisItem.TaskDescription
                 & " — outside standard (" & ThisItem.AcceptanceStandard & ")",
    ReportedByTechID: gTech.TechID,
    ReportedDate: Today(),
    Status: "Open",
    EscalationRequired: If(cmbSeverity.Selected.Value = "High", "Yes", "No")
});
```

**Submit is disabled** until every `Mandatory = Yes` task is answered:

```powerfx
// btnSubmit.DisplayMode
If(
    CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID,
                     Mandatory = "Yes", IsBlank(Result))) = 0,
    DisplayMode.Edit, DisplayMode.Disabled
)
```

On submit:

```powerfx
Patch(PM_WorkOrders, gWO, {
    Status: "Completed",
    ActualEndDate: Today(),
    DurationMin: DateDiff(gStartTime, Now(), Minutes),
    ChecklistDoneTasks: CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID,
                                         !IsBlank(Result))),
    ChecklistFailTasks: CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID,
                                         Result = "Not OK")),
    PMResult: Switch(true,
        CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID, Result = "Not OK")) = 0,
            "Pass",
        CountRows(Filter(PM_ChecklistResults, WOID = gWO.WOID, Result = "Not OK")) <= 2,
            "Pass with observation",
        "Fail - follow-up raised"),
    OnTimeFlag: If(Today() <= gWO.DueDate, "Yes", "No")
});
```

### `scrBreakdown`

Machine pre-filled from the scan. Fields: failure mode (choice from a curated
list, not free text), category, severity, description, photo. `ReportedDateTime`
is `Now()` and is not editable — a back-dateable breakdown time makes MTTR
worthless. Restoration and root cause are captured later from the same screen when
the record is reopened; `Status` cannot move to Closed with `RootCause` blank.

### `scrSpareRequest`

Part picker filtered by machine type:

```powerfx
// cmbPart.Items
Filter(SparePart_Master,
    AppliesToMachineType = gMachine.MachineType || AppliesToMachineType = "All")
```

Shows `CurrentStock` vs `MinStock` next to each part so the technician knows
whether they are about to trigger a purchase. Urgency: Planned / Urgent /
Emergency. Requests over `PM_Config.SpareApprovalLimitINR` are flagged in the app
before submit so nobody is surprised by the approval delay.

### `scrSpareReplaced`

Separate from the request on purpose — requested is not consumed. Links to an open
request if one exists, otherwise records a direct stock issue. Old part condition
is a required choice; it is the input to failure analysis.

### `scrAbnormality`

Free-standing abnormality from a walk-by scan. Photo mandatory, no exceptions:

```powerfx
// btnSubmit.DisplayMode
If(IsBlank(imgPhoto.Image), DisplayMode.Disabled, DisplayMode.Edit)
```

### `scrMachineHistory`

Read-only. Four collapsible sections: PM history, breakdowns, spares fitted, open
abnormalities. Same data the Machine 360 dashboard page shows, sized for a phone.

## Rules the app enforces, and why

| Rule | Reason |
|------|--------|
| A checklist can only be started from a machine QR scan in the same session | Stops desk closure |
| Every screen entry writes to `QR_Scan_Log` | Attendance is provable, not asserted |
| Photo mandatory on any Not OK and on every abnormality | An abnormality without a photo does not get fixed |
| Mandatory tasks block submit | Partial PMs stop being signed off as complete |
| `ReportedDateTime` is `Now()`, never editable | MTTR stays honest |
| Safety-critical Not OK forces a second-person verification field | It is a safety device |
| Technician QR shows the signed-in user's list, not the badge's | A borrowed badge cannot close someone else's work |

## Publishing and sharing

Publish, then share with the **Technicians** security group as *User*. Copy the
web link — that is what goes into the QR codes:

```
https://apps.powerapps.com/play/e/<ENV_ID>/a/<APP_ID>?tenantId=<TENANT_ID>
```

Feed those three IDs to `scripts/generate_qr_codes.py` and print the labels.
Republishing to the same environment keeps the IDs; moving environments changes
them, and every label has to be reprinted.
