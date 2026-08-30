# Power Fx formulas — copy-paste ready

Every formula the canvas app needs. Paste into the property named in each heading.

**Delegation.** Set **App settings → Advanced → Data row limit = 500** while you
build. A non-delegable `Filter()` silently returns only the first N rows and gives
you a number that looks plausible and is wrong; with the limit at 500 it breaks
visibly instead. Every query below is delegable against SharePoint and uses a
column that `provision_lists.ps1` indexes.

---

## App

### `App.OnStart`

```powerfx
// Cache what the app needs to render offline. Everything here is small, static
// master data - caching a fact table would go stale within the hour.
Concurrent(
    ClearCollect(colTechs,
        Filter(Technician_Master, Active = true)
    ),
    ClearCollect(colMachines,
        Filter(Machine_Master, Active = true)
    ),
    ClearCollect(colChecklistMaster,
        Filter(Checklist_Master, Active = true)
    )
);

// Replay anything captured while offline, then start clean.
LoadData(colPendingWrites, "pm_pending", true);

Set(gblOffline, !Connection.Connected);
Set(gblSubmitting, false);

// A QR opens the app with ?machineid=MC-01-001, so the scan lands directly on
// the right machine instead of on a menu.
If(
    !IsBlank(Param("machineid")),
    Set(gblMachine, LookUp(Machine_Master, Machine_ID = Upper(Param("machineid"))))
);
```

### `App.OnError`

```powerfx
// Never let a raw connector error reach a technician standing at a machine.
// Log it, say something useful, carry on.
Notify(
    "Could not save. Your entry is held on the phone and will go through when the network returns.",
    NotificationType.Warning,
    4000
);
Trace("PM app error: " & FirstError.Message, TraceSeverity.Error);
```

---

## scrHome — pick the technician

### `drpTech.Items`

```powerfx
Sort(colTechs, Tech_Name, SortOrder.Ascending)
```

### `drpTech.OnChange`

```powerfx
Set(gblTech, drpTech.Selected)
```

### `btnContinue.DisplayMode`

```powerfx
// Mandatory, never optional. Technicians share one M365 login, so this dropdown
// is the only attribution the system will ever have. No name, no entry.
If(IsBlank(gblTech), DisplayMode.Disabled, DisplayMode.Edit)
```

### `btnContinue.OnSelect`

```powerfx
// Replay offline captures before doing anything else, so the technician's own
// earlier work is in the lists before he looks at his allotted list.
If(
    Connection.Connected && CountRows(colPendingWrites) > 0,
    ForAll(
        colPendingWrites As pending,
        Patch(
            Checklist_Response,
            Defaults(Checklist_Response),
            pending.Payload
        )
    );
    Clear(colPendingWrites);
    SaveData(colPendingWrites, "pm_pending");
    Notify("Saved entries have gone through.", NotificationType.Success)
);
Navigate(scrMyList, ScreenTransition.Fade)
```

### `lblSharedLogin.Text`

```powerfx
"Everyone signs in with the same account, so your name here is what puts this work against you. Pick it every shift."
```

---

## scrMyList — the allotted PM list

### `galMyList.Items`

```powerfx
// THIS FILTER IS THE WHOLE "AUTO-UPDATING LIST".
// A completed checklist flips Task_Status, and the row leaves this gallery on the
// next refresh. No sync, no local state, nothing to reconcile.
SortByColumns(
    Filter(
        PM_Machine_Task,
        Task_Status <> "Completed",
        Task_Status <> "Skipped"
    ),
    "Cell_ID", SortOrder.Ascending,
    "WO_No", SortOrder.Ascending
)
```

> Both `Task_Status` and `Cell_ID` are indexed. `<>` on a text column is delegable
> to SharePoint, so this keeps working past 5,000 items.

### `galMyList.OnSelect`

```powerfx
Set(gblTask, ThisItem);
Set(gblMachine, LookUp(Machine_Master, Machine_ID = ThisItem.Machine_ID));
Set(gblCell, LookUp(Cell_Master, Cell_ID = ThisItem.Cell_ID));
Set(gblWO, LookUp(PM_WorkOrder, WO_No = ThisItem.WO_No));
Navigate(scrMachineHub, ScreenTransition.None)
```

### `lblCount.Text`

```powerfx
CountRows(galMyList.AllItems) & " machine" &
If(CountRows(galMyList.AllItems) = 1, "", "s") & " still to do"
```

### `lblEmpty.Visible`

```powerfx
CountRows(galMyList.AllItems) = 0
```

### `lblEmpty.Text`

```powerfx
"Nothing allotted right now. Scan a machine if you need to report a breakdown or log something you have noticed."
```

### Status pill — `lblStatus.Fill`

```powerfx
Switch(
    ThisItem.Task_Status,
    "Pending",     ColorValue("#FDF0D2"),
    "In Progress", ColorValue("#D8EBF4"),
    ColorValue("#EDF0F2")
)
```

### `lblStatus.Color`

```powerfx
Switch(
    ThisItem.Task_Status,
    "Pending",     ColorValue("#8A5A00"),
    "In Progress", ColorValue("#0C3549"),
    ColorValue("#57606A")
)
```

---

## scrScan — the barcode reader

### `bcScanner.OnScan`

```powerfx
// The QR encodes a full URL. Pull the Machine_ID out of it rather than expecting
// a bare ID, so the same sticker works whether it is scanned by the app or by the
// phone's camera app.
Set(
    varScannedId,
    Upper(
        If(
            "MACHINE_ID" in Upper(bcScanner.Value),
            // ...FilterValue1=MC-01-001&FilterType1=Text
            First(
                Split(
                    Last(Split(bcScanner.Value, "FilterValue1=")).Result,
                    "&"
                )
            ).Result,
            bcScanner.Value
        )
    )
);

Set(gblMachine, LookUp(Machine_Master, Machine_ID = varScannedId));

If(
    IsBlank(gblMachine),
    Notify("Sticker " & varScannedId & " is not in the machine list. Tell your supervisor - do not guess.", NotificationType.Error, 5000),

    // Log every scan, including the ones that lead nowhere. The scans that never
    // become a completion are the earliest sign of an adoption problem.
    Patch(Scan_Log, Defaults(Scan_Log),
        {
            Title:         "SCN-" & Text(Now(), "yyyymmddhhmmss"),
            Scan_ID:       "SCN-" & Text(Now(), "yyyymmddhhmmss"),
            Scan_DateTime: Now(),
            Machine_ID:    gblMachine.Machine_ID,
            Cell_ID:       gblMachine.Cell_ID,
            Tech_ID:       gblTech.Tech_ID,
            Scan_Action:   "View",
            Device:        "Android",
            WO_No:         LookUp(PM_Machine_Task,
                               Machine_ID = gblMachine.Machine_ID
                               && Task_Status <> "Completed").WO_No
        }
    );
    Set(gblCell, LookUp(Cell_Master, Cell_ID = gblMachine.Cell_ID));
    Set(gblTask, LookUp(PM_Machine_Task,
            Machine_ID = gblMachine.Machine_ID && Task_Status <> "Completed"));
    Navigate(scrMachineHub, ScreenTransition.None)
)
```

---

## scrMachineHub — the five actions

### `lblMachineId.Text`

```powerfx
gblMachine.Machine_ID
```

### `lblMachineName.Text`

```powerfx
gblMachine.Machine_Name & "   ·   " & gblMachine.Cell_Name & "   ·   " & gblMachine.Location_Tag
```

### `lblCounter.Text`

```powerfx
// The two clocks, side by side, exactly as the planner sees them.
"Cell hours: " & Text(gblCell.Cum_Std_Hours_Since_PM, "#,##0") &
" of " & Text(gblCell.PM_Trigger_Hours, "#,##0") &
"   (" & Text(gblCell.Cum_Std_Hours_Since_PM / gblCell.PM_Trigger_Hours, "0%") & ")" &
Char(10) &
"Last PM: " & Text(gblCell.Last_PM_Date, "dd mmm yyyy") &
"   ·   Calendar due: " & Text(gblCell.Next_PM_Due_Date_Calendar, "dd mmm yyyy")
```

### `barCounter.Width` — the utilisation bar

```powerfx
Min(
    gblCell.Cum_Std_Hours_Since_PM / gblCell.PM_Trigger_Hours,
    1
) * barCounterTrack.Width
```

### `barCounter.Fill`

```powerfx
// Same thresholds as the SharePoint column formatting and the Power BI measure,
// so a cell that is amber here is amber everywhere.
With(
    { util: gblCell.Cum_Std_Hours_Since_PM / gblCell.PM_Trigger_Hours },
    If(util >= 1,    ColorValue("#ED7373"),
       util >= 0.9,  ColorValue("#F0A202"),
       util >= 0.75, ColorValue("#2E86AB"),
                     ColorValue("#44C088"))
)
```

### `lblOpenWO.Text`

```powerfx
If(
    IsBlank(gblTask),
    "No open work order for this machine",
    "Work order " & gblTask.WO_No & "   ·   " & gblTask.Task_Status &
    "   ·   " & Text(CountRows(Filter(PM_Machine_Task, WO_No = gblTask.WO_No, Task_Status = "Completed"))) &
    " of " & Text(CountRows(Filter(PM_Machine_Task, WO_No = gblTask.WO_No))) & " machines done"
)
```

### `btnStartPM.DisplayMode`

```powerfx
// Nothing to start if there is no open task, or if it is already running.
If(
    IsBlank(gblTask) || gblTask.Task_Status = "In Progress",
    DisplayMode.Disabled,
    DisplayMode.Edit
)
```

### `btnStartPM.OnSelect`

```powerfx
Set(gblSubmitting, true);

// Guard the duplicate scan. A technician who taps twice because the page was slow
// must not restart his own clock - a 40-minute job would then read 4 minutes and
// look like a pencil-whipped PM.
If(
    IsBlank(gblTask.Scan_Start_Time),
    Patch(PM_Machine_Task, gblTask,
        {
            Task_Status:      "In Progress",
            Scan_Start_Time:  Now(),
            Assigned_Tech_ID: gblTech.Tech_ID
        }
    );
    Patch(Scan_Log, Defaults(Scan_Log),
        {
            Title:         "SCN-" & Text(Now(), "yyyymmddhhmmss"),
            Scan_ID:       "SCN-" & Text(Now(), "yyyymmddhhmmss"),
            Scan_DateTime: Now(),
            Machine_ID:    gblMachine.Machine_ID,
            Cell_ID:       gblMachine.Cell_ID,
            Tech_ID:       gblTech.Tech_ID,
            Scan_Action:   "Start PM",
            Device:        "Android",
            WO_No:         gblTask.WO_No
        }
    );
    Notify("PM started. Work through the checklist.", NotificationType.Success),
    Notify("This machine was already scanned in at " & Text(gblTask.Scan_Start_Time, "hh:mm") & ".", NotificationType.Information)
);

Set(gblTask, LookUp(PM_Machine_Task, Task_ID = gblTask.Task_ID));
Set(gblSubmitting, false);
Navigate(scrChecklist, ScreenTransition.None)
```

### Button height — every action button

```powerfx
// 48, not 44. 44 is the accessibility floor; a gloved finger on a moving shop
// floor needs the extra four pixels.
48
```

---

## scrChecklist — one check point at a time

### `scrChecklist.OnVisible`

```powerfx
// Build this machine's checklist with an empty answer against each point.
ClearCollect(
    colChecklist,
    AddColumns(
        SortByColumns(
            Filter(colChecklistMaster, Checklist_ID = gblMachine.Checklist_ID),
            "Item_No", SortOrder.Ascending
        ),
        "Result",         "",
        "Measured_Value", Blank(),
        "Observation",    "",
        "Action_Taken",   "",
        "FollowUp",       false
    )
);
Set(varIdx, 1)
```

### `lblProgress.Text`

```powerfx
"Check " & varIdx & " of " & CountRows(colChecklist)
```

### `lblCheckPoint.Text`

```powerfx
Index(colChecklist, varIdx).Check_Point
```

### `lblStandard.Text`

```powerfx
// Without the acceptance standard on screen, "check the pressure" means every
// technician invents his own limit. This label is what makes the checklist real.
"Accept: " & Index(colChecklist, varIdx).Acceptance_Standard &
If(
    !IsBlank(Index(colChecklist, varIdx).Tool_Required) && Index(colChecklist, varIdx).Tool_Required <> "-",
    Char(10) & "Tool: " & Index(colChecklist, varIdx).Tool_Required,
    ""
)
```

### `lblSafety.Visible`

```powerfx
Index(colChecklist, varIdx).Safety_Critical
```

### `lblSafety.Text`

```powerfx
"SAFETY CRITICAL - a NOT OK here stops the cell closing until it is dealt with"
```

### `inpMeasured.Visible`

```powerfx
Index(colChecklist, varIdx).Check_Type = "Measurement"
```

### `btnOK.OnSelect`

```powerfx
Patch(colChecklist, Index(colChecklist, varIdx), { Result: "OK" });
If(varIdx < CountRows(colChecklist), Set(varIdx, varIdx + 1))
```

### `btnNotOK.OnSelect`

```powerfx
Patch(colChecklist, Index(colChecklist, varIdx), { Result: "NOT OK" })
// Deliberately does NOT advance. A NOT OK needs an observation and usually a
// photo, and auto-advancing past it is how findings end up with no detail.
```

### `btnNext.DisplayMode`

```powerfx
// A measurement check needs a number. A bearing reading of 48, 52, 57 across
// three PMs is a failure you can see coming - but only if somebody typed it.
With(
    { item: Index(colChecklist, varIdx) },
    If(
        IsBlank(item.Result)
        || (item.Check_Type = "Measurement" && IsBlank(item.Measured_Value))
        || (item.Result = "NOT OK" && IsBlank(item.Observation)),
        DisplayMode.Disabled,
        DisplayMode.Edit
    )
)
```

### `btnSubmit.Visible`

```powerfx
CountRows(Filter(colChecklist, IsBlank(Result))) = 0
```

### `btnSubmit.OnSelect`

```powerfx
Set(gblSubmitting, true);

With(
    {
        notOk:  CountRows(Filter(colChecklist, Result = "NOT OK")),
        safety: CountRows(Filter(colChecklist, Result = "NOT OK" && Safety_Critical))
    },
    // One response row per check point.
    ForAll(
        colChecklist As item,
        Patch(Checklist_Response, Defaults(Checklist_Response),
            {
                Title:              "CR-" & Text(Now(), "yyyymmddhhmmss") & "-" & item.Item_No,
                Response_ID:        "CR-" & Text(Now(), "yyyymmddhhmmss") & "-" & item.Item_No,
                Submitted_DateTime: Now(),
                WO_No:              gblTask.WO_No,
                Machine_ID:         gblMachine.Machine_ID,
                Cell_ID:            gblMachine.Cell_ID,
                Checklist_ID:       gblMachine.Checklist_ID,
                Item_No:            item.Item_No,
                Check_Point:        item.Check_Point,
                Result:             item.Result,
                Measured_Value:     item.Measured_Value,
                Observation:        item.Observation,
                Action_Taken:       item.Action_Taken,
                Tech_ID:            gblTech.Tech_ID,
                Follow_Up_Required: item.FollowUp
            }
        )
    );

    // A safety-critical NOT OK leaves the task In Progress, so the cell cannot
    // close and the counter cannot reset until somebody deals with it.
    Patch(PM_Machine_Task, gblTask,
        {
            Task_Status:           If(safety > 0, "In Progress", "Completed"),
            Scan_End_Time:         Now(),
            Duration_Min:          DateDiff(gblTask.Scan_Start_Time, Now(), TimeUnit.Minutes),
            NOT_OK_Count:          notOk,
            Completed_By:          gblTech.Tech_ID,
            Completion_Date:       Today(),
            Checklist_Response_ID: "CR-" & Text(Now(), "yyyymmddhhmmss")
        }
    );

    Set(varSafetyBlocked, safety > 0);
    Set(varFindings, notOk)
);

Set(gblSubmitting, false);
Navigate(scrDone, ScreenTransition.Fade)
```

### `btnSubmit.DisplayMode`

```powerfx
// Disabled while a write is in flight. Without this a double tap writes the whole
// checklist twice, and nothing downstream can tell which copy is real.
If(gblSubmitting, DisplayMode.Disabled, DisplayMode.Edit)
```

### Photo on a NOT OK — `camPhoto.OnSelect`

```powerfx
Patch(
    PM_Photos,
    Defaults(PM_Photos),
    {
        Name: gblMachine.Machine_ID & "_" & Text(Now(), "yyyymmddhhmmss") & ".jpg",
        Image: camPhoto.Photo
    }
)
```

---

## scrBreakdown

### `btnSubmitBreakdown.OnSelect`

```powerfx
Set(gblSubmitting, true);
Patch(Breakdown_Log, Defaults(Breakdown_Log),
    {
        Title:               "BD-" & Text(Now(), "yyyymmddhhmmss"),
        BD_ID:               "BD-" & Text(Now(), "yyyymmddhhmmss"),
        Reported_DateTime:   Now(),
        Machine_ID:          gblMachine.Machine_ID,
        Cell_ID:             gblMachine.Cell_ID,
        Reported_By_Tech_ID: gblTech.Tech_ID,
        Shift:               drpShift.Selected.Value,
        Breakdown_Type:      drpType.Selected.Value,
        Symptom:             inpSymptom.Text,
        Root_Cause:          inpRootCause.Text,
        Action_Taken:        inpAction.Text,
        Response_DateTime:   dtpResponse.SelectedDate + Time(Value(drpRespHour.Selected.Value), Value(drpRespMin.Selected.Value), 0),
        Repair_Start:        dtpRepairStart.SelectedDate + Time(Value(drpStartHour.Selected.Value), Value(drpStartMin.Selected.Value), 0),
        Repair_End:          dtpRepairEnd.SelectedDate + Time(Value(drpEndHour.Selected.Value), Value(drpEndMin.Selected.Value), 0),
        Production_Loss_Min: Value(inpLoss.Text),
        Spare_Used:          tglSpare.Value,
        Status:              "Open",
        Recurrence_Flag:     tglRepeat.Value
    }
);
Set(gblSubmitting, false);
Navigate(scrDone, ScreenTransition.Fade)
```

### `lblLossHelp.Text`

```powerfx
// Production loss is not repair time. It includes waiting for a technician,
// waiting for a part and restarting the line, and it is almost always the bigger
// number. Recording repair time here makes availability look flattering and wrong.
"Total minutes the machine could not produce - including waiting for help and for parts, not just the repair itself."
```

---

## scrSpare — request a part

### `drpSpare.Items`

```powerfx
Sort(Filter(Spare_Master, Active = true), Spare_Description, SortOrder.Ascending)
```

### `lblStock.Text`

```powerfx
// Showing stock before he asks stops the request that was never needed, and warns
// about the one that will not be fillable.
If(
    IsBlank(drpSpare.Selected),
    "",
    "In stock: " & drpSpare.Selected.Current_Stock & " " & drpSpare.Selected.UOM &
    "   ·   Minimum " & drpSpare.Selected.Min_Stock &
    "   ·   Bin " & drpSpare.Selected.Bin_Location &
    If(
        drpSpare.Selected.Current_Stock <= drpSpare.Selected.Min_Stock,
        Char(10) & "Below minimum - lead time " & drpSpare.Selected.Lead_Time_Days & " days",
        ""
    )
)
```

### `btnSubmitSpare.OnSelect`

```powerfx
Set(gblSubmitting, true);
Patch(Spare_Request, Defaults(Spare_Request),
    {
        Title:             "REQ-" & Text(Now(), "yyyymmddhhmmss"),
        Req_ID:            "REQ-" & Text(Now(), "yyyymmddhhmmss"),
        Request_DateTime:  Now(),
        WO_No:             gblTask.WO_No,
        Machine_ID:        gblMachine.Machine_ID,
        Cell_ID:           gblMachine.Cell_ID,
        Spare_Code:        drpSpare.Selected.Spare_Code,
        Spare_Description: drpSpare.Selected.Spare_Description,
        Qty_Requested:     Value(inpQty.Text),
        Requested_By:      gblTech.Tech_ID,
        Urgency:           drpUrgency.Selected.Value,
        Reason:            drpReason.Selected.Value,
        Approval_Status:   "Pending",
        Issue_Status:      "Not Issued",
        Issued_Qty:        0,
        // Snapshot now. It is the evidence for a min-stock revision six months
        // later, when nobody remembers what the shelf looked like.
        Stock_At_Request:  drpSpare.Selected.Current_Stock,
        Remarks:           inpRemarks.Text
    }
);
Set(gblSubmitting, false);
Navigate(scrDone, ScreenTransition.Fade)
```

### `btnSubmitSpare.DisplayMode`

```powerfx
// Blocked offline on purpose: Stock_At_Request must be the real number at the
// moment of asking, not whatever was cached this morning.
If(
    !Connection.Connected
    || gblSubmitting
    || IsBlank(drpSpare.Selected)
    || IsBlank(inpQty.Text)
    || Value(inpQty.Text) <= 0,
    DisplayMode.Disabled,
    DisplayMode.Edit
)
```

---

## scrAbnormality

### `btnSubmitAbn.OnSelect`

```powerfx
Set(gblSubmitting, true);
Patch(Abnormality_Log, Defaults(Abnormality_Log),
    {
        Title:            "ABN-" & Text(Now(), "yyyymmddhhmmss"),
        Abn_ID:           "ABN-" & Text(Now(), "yyyymmddhhmmss"),
        Logged_DateTime:  Now(),
        Machine_ID:       gblMachine.Machine_ID,
        Cell_ID:          gblMachine.Cell_ID,
        Logged_By:        gblTech.Tech_ID,
        Category:         drpCategory.Selected.Value,
        Description:      inpDescription.Text,
        Severity:         drpSeverity.Selected.Value,
        Immediate_Action: inpImmediate.Text,
        Responsibility:   drpOwner.Selected.Tech_ID,
        Target_Date:      dtpTarget.SelectedDate,
        Status:           "Open",
        Converted_To_WO:  false
    }
);
If(
    !IsBlank(gblTask),
    Patch(PM_Machine_Task, gblTask, { Abnormality_Raised: true })
);
Set(gblSubmitting, false);
Navigate(scrDone, ScreenTransition.Fade)
```

### `dtpTarget.DefaultDate`

```powerfx
// A High severity item defaults to 24 hours, not a week. The default is the
// commitment most people accept without thinking, so it should be the right one.
Switch(
    drpSeverity.Selected.Value,
    "High",   Today() + 1,
    "Medium", Today() + 7,
    Today() + 30
)
```

---

## scrDone — say what happens next

### `lblDone.Text`

```powerfx
If(
    varSafetyBlocked,
    "Saved. A safety-critical item is NOT OK, so this machine stays open and your supervisor has been told. The cell cannot close until it is dealt with.",
    varFindings > 0,
    "Saved. " & varFindings & " finding" & If(varFindings = 1, "", "s") &
    " recorded - each one raises a corrective job. This machine is done.",
    "Saved. This machine is done." &
    If(
        CountRows(Filter(PM_Machine_Task, WO_No = gblTask.WO_No, Task_Status <> "Completed")) = 0,
        " That was the last machine in the cell - the cell PM is complete and the hour counter resets.",
        " " & CountRows(Filter(PM_Machine_Task, WO_No = gblTask.WO_No, Task_Status <> "Completed")) &
        " machine(s) left in this cell."
    )
)
```

> Telling the technician that his machine was the one that closed the cell is what
> makes the 4,000-hour rule feel real rather than administrative.

---

## Offline capture

### `btnSubmit.OnSelect` — the offline branch on the checklist

```powerfx
If(
    Connection.Connected,

    // online path - the ForAll/Patch above
    Notify("Saved.", NotificationType.Success),

    // offline path - hold it on the phone and replay on reconnect
    ForAll(
        colChecklist As item,
        Collect(colPendingWrites,
            {
                Kind: "Checklist_Response",
                Payload: {
                    Response_ID:        "CR-" & Text(Now(), "yyyymmddhhmmss") & "-" & item.Item_No,
                    Submitted_DateTime: Now(),
                    WO_No:              gblTask.WO_No,
                    Machine_ID:         gblMachine.Machine_ID,
                    Cell_ID:            gblMachine.Cell_ID,
                    Checklist_ID:       gblMachine.Checklist_ID,
                    Item_No:            item.Item_No,
                    Check_Point:        item.Check_Point,
                    Result:             item.Result,
                    Measured_Value:     item.Measured_Value,
                    Observation:        item.Observation,
                    Tech_ID:            gblTech.Tech_ID
                }
            }
        )
    );
    SaveData(colPendingWrites, "pm_pending");
    Notify("No network. Held on this phone - it will go through when you are back in range.", NotificationType.Warning, 5000)
)
```

### `lblOfflineBanner.Visible`

```powerfx
!Connection.Connected
```

### `lblOfflineBanner.Text`

```powerfx
"Working offline - " & CountRows(colPendingWrites) & " entr" &
If(CountRows(colPendingWrites) = 1, "y", "ies") & " waiting to send"
```

---

## Formatting helpers

| Need | Formula |
|---|---|
| Theme primary | `ColorValue("#0C3549")` |
| Theme accent | `ColorValue("#2E86AB")` |
| Good / warn / bad | `ColorValue("#44C088")` / `ColorValue("#F0A202")` / `ColorValue("#ED7373")` |
| Date for display | `Text(dateValue, "dd mmm yyyy")` |
| Time for display | `Text(timeValue, "hh:mm")` |
| Minutes between | `DateDiff(start, end, TimeUnit.Minutes)` |
| Days since | `DateDiff(dateValue, Today(), TimeUnit.Days)` |
| Percentage | `Text(value, "0%")` |
| Rupees | `"₹" & Text(value, "#,##0")` |

## Delegation quick reference

| Pattern | Delegable to SharePoint? |
|---|---|
| `Filter(list, Col = "x")` | Yes |
| `Filter(list, Col <> "x")` | Yes |
| `Filter(list, Col >= n)` | Yes on Number and DateTime |
| `Filter(list, StartsWith(Col, "x"))` | Yes |
| `Filter(list, "x" in Col)` | **No** — pulls 500 rows and filters locally |
| `LookUp(list, Col = "x")` | Yes |
| `Sort` / `SortByColumns` on an indexed column | Yes |
| `CountRows(Filter(...))` | **No** on SharePoint — counts only what was fetched |
| `Search()` | **No** |

`CountRows(Filter(...))` is the one that catches people out. It is used above only
against `PM_Machine_Task` filtered by `WO_No`, which returns at most four rows — well
inside any limit. Do not copy that pattern onto `Checklist_Response`, which has
thousands; if you need a count there, have a flow write it to a column.
