# Canvas app — screen-by-screen build sheet

Build order below is deliberate: each screen only depends on ones already built,
so the app is testable on a phone at the end of every screen rather than only at
the end of the week.

Every formula referenced is written in full in `power_fx_formulas.md`.

**Before you start:** confirm Power Apps licensing (see `README_PowerApps.md`) and
have `provision_lists.ps1` and `load_data.ps1` already run — the app is built
against real lists with real data, not against empty ones. An app built against
empty lists looks finished and falls over on the first real record.

---

## Step 0 — create the app

1. **make.powerapps.com** → **Create** → **Blank app** → **Blank canvas app**
2. Name `EPQPL PM Technician`, format **Phone**
3. **Settings → Display** → Orientation **Portrait**, Lock aspect ratio **On**
4. **Settings → Advanced → Data row limit → 500**

   > Not a performance setting — a diagnostic one. A non-delegable query then
   > breaks visibly during the build instead of hiding behind a 2,000-row cushion
   > and silently returning wrong numbers in production.

5. **Settings → General → Auto start / Auto pause** → off
6. **Data → Add data → SharePoint** → your site → select all 13 lists and the two
   photo libraries listed in `app_manifest.json`

### Theme

**Settings → Theme** does not go far enough; set these on each control as you go.

| Role | Hex |
|---|---|
| Primary (headers, primary buttons) | `#0C3549` |
| Accent (secondary buttons) | `#2E86AB` |
| Positive | `#44C088` |
| Warning | `#F0A202` |
| Negative | `#ED7373` |
| Screen background | `#F5F7F8` |
| Card | `#FFFFFF` |
| Text | `#1F2933` |
| Muted | `#7B8794` |
| Font | Segoe UI (`Font.'Segoe UI'`) |

These are the same values as the Power BI theme and the SharePoint column
formatting, so the shop floor, the list and the dashboard agree on what amber means.

### Sizing rules — these are not stylistic

| Element | Minimum |
|---|---|
| Any tappable button | **48 px** high |
| Body text | **16 px** |
| Machine_ID display | **28 px** bold |
| Gap between adjacent buttons | **12 px** |

44 px is the published accessibility floor. This app is used with gloves on, one
handed, standing next to a running machine, often in poor light. 48 with a 12 px gap
is what stops a mis-tap on "Report Breakdown" when the intent was "Complete
Checklist".

Set `App.OnStart` and `App.OnError` now — both are in `power_fx_formulas.md`.

---

## Step 1 — `scrHome`

The technician picks their name. Nothing else happens until they do.

| Control | Name | Notes |
|---|---|---|
| Rectangle | `recHeader` | Height 88, Fill `#0C3549` |
| Label | `lblTitle` | "EPQPL Preventive Maintenance", 20 px, white, bold |
| Label | `lblPrompt` | "Who are you?", 18 px |
| Dropdown | `drpTech` | `Items`, `OnChange` per formulas |
| Label | `lblSharedLogin` | The shared-login explanation, 13 px muted |
| Button | `btnContinue` | "Continue", 48 px, `DisplayMode` and `OnSelect` per formulas |
| Label | `lblOfflineBanner` | `Visible` and `Text` per formulas, Fill `#FDF0D2` |

**Why the name is mandatory and picked every session.** Every technician signs in
with the same M365 account, so `User().Email` identifies nobody. This dropdown is
the entire audit trail the system will ever have. It is never free text — free text
produces "Murugan", "murugan s" and "MURUGAN S", and three months later nothing can
be counted.

Do not "remember" the last technician across sessions. A shared handset would then
attribute the next person's work to whoever used it last, which is worse than no
attribution because it looks authoritative.

**Test:** open on a phone, confirm Continue is dead until a name is picked.

---

## Step 2 — `scrMyList`

The allotted PM list. This is the screen technicians live in.

| Control | Name | Notes |
|---|---|---|
| Rectangle + Label | `recHeader`, `lblTitle` | "My PM list" |
| Label | `lblCount` | "n machines still to do" |
| Gallery (blank, vertical) | `galMyList` | `Items` per formulas — **this filter is the whole feature** |
| Inside gallery | `lblMachine` | `ThisItem.Machine_ID`, 18 px bold |
| Inside gallery | `lblCell` | `ThisItem.Cell_ID & " · " & ThisItem.WO_No`, 13 px muted |
| Inside gallery | `lblStatus` | Status pill, `Fill` / `Color` per formulas |
| Inside gallery | `btnRow` | Transparent, full width, height ≥ 64, `OnSelect` per formulas |
| Label | `lblEmpty` | Shown when nothing is allotted |
| Button | `btnScan` | "Scan a machine" → `Navigate(scrScan)` |

Gallery `TemplateSize` **72**. A 44 px row is a mis-tap on a moving shop floor.

**The auto-updating list.** `galMyList.Items` filters `Task_Status <> "Completed"`.
When a checklist submission flips that field, the row leaves the gallery on the
next refresh. There is no sync, no cached list, nothing to reconcile — the same
mechanism as the `My Allotted PM List` SharePoint view in Path A. A technician's
list emptying as he works is the single strongest adoption signal the system has.

**Test:** complete a task in SharePoint directly, pull to refresh, watch the row go.

---

## Step 3 — `scrScan`

| Control | Name | Notes |
|---|---|---|
| Barcode reader | `bcScanner` | `BarcodeType` **QR Code**, `OnScan` per formulas |
| Label | `lblHint` | "Point at the sticker on the machine" |
| Button | `btnManual` | Fallback: type the Machine_ID |

Always ship the manual fallback. Cameras fail, stickers get destroyed, and a
technician who cannot record a breakdown because a sticker is unreadable will go
back to paper and stay there.

The `OnScan` formula parses the `Machine_ID` out of the full URL the sticker
encodes, so the same sticker works whether it is scanned by this app or by the
phone's own camera app opening the SharePoint hub.

**Every scan is logged, including the ones that lead nowhere.** A scan against a
machine with no open work order is not an error — it is the earliest visible sign
of an adoption problem, and it only shows up if you record it.

**Test:** scan a printed label from `qr/labels/`. Then scan something that is not a
machine and confirm the message is clear and blames nothing on the technician.

---

## Step 4 — `scrMachineHub`

The screen a QR scan lands on. Identity first, then state, then actions.

| Control | Name | Notes |
|---|---|---|
| Label | `lblMachineId` | 28 px bold `#0C3549` |
| Label | `lblMachineName` | Name · cell · bay, 14 px |
| Label | `lblCriticality` | Pill: A red, B amber, C grey |
| Rectangle | `barCounterTrack` | Height 14, Fill `#E8EDEF`, radius 7 |
| Rectangle | `barCounter` | `Width` / `Fill` per formulas |
| Label | `lblCounter` | Both clocks — hours and calendar |
| Label | `lblOpenWO` | Work order, status, machines done |
| Button ×5 | `btnStartPM`, `btnChecklist`, `btnBreakdown`, `btnSpare`, `btnAbnormality` | 48 px, 12 px apart |

Button order is by **frequency of use**, not importance: Start PM and Checklist are
the daily path and sit at the top where a thumb reaches without shifting grip.

| Button | Fill | Text |
|---|---|---|
| Start PM | `#0C3549` | white |
| Complete Checklist | `#2E86AB` | white |
| Report Breakdown | `#ED7373` | white |
| Request Spare | white, 2 px `#0C3549` border | `#0C3549` |
| Log Abnormality | white, 2 px `#0C3549` border | `#0C3549` |

Machine_ID is shown largest so the technician confirms he scanned the sticker he
meant to. A wrong sticker discovered later is a field problem that takes a month to
find, and by then it has been scanned two hundred times against the wrong machine.

**The duplicate-scan guard is on this screen.** `btnStartPM.OnSelect` only stamps
`Scan_Start_Time` when it is currently blank. A technician who taps twice because
the page was slow must not restart his own clock — a 40-minute job would then read
4 minutes and look like a pencil-whipped PM in every report.

**Test:** tap Start PM twice. The second tap must say "already scanned in at HH:MM"
and change nothing.

---

## Step 5 — `scrChecklist`

One check point at a time, with its acceptance standard on screen.

| Control | Name | Notes |
|---|---|---|
| Label | `lblProgress` | "Check 3 of 6" |
| Label | `lblCheckPoint` | 18 px, the instruction |
| Label | `lblStandard` | The acceptance standard and the tool |
| Label | `lblSafety` | Red banner, `Visible` per formulas |
| Button | `btnOK` | Green, 48 px |
| Button | `btnNotOK` | Red, 48 px |
| Text input | `inpMeasured` | `Visible` per formulas, `Format` Number |
| Text input | `inpObservation` | Multiline, required on NOT OK |
| Camera | `camPhoto` | Shown on NOT OK |
| Toggle | `tglFollowUp` | "Needs a follow-up job" |
| Button | `btnPrev` / `btnNext` | `varIdx` navigation |
| Button | `btnSubmit` | `Visible` / `OnSelect` / `DisplayMode` per formulas |

**One at a time, not a long scrolling form.** A six-item list on one screen gets
tapped down the OK column in eleven seconds. One at a time, with the standard
visible, is slower — and slower is the point.

**The acceptance standard on screen is what makes the checklist real.** "Check the
pressure" with no limit means every technician invents his own. "5.0–6.0 bar" means
they all use the same one.

**`btnNext` is disabled until the item is properly answered**: a measurement check
must have a number, a NOT OK must have an observation. A bearing reading of 48, 52,
57 °C across three PMs is a failure you can see coming — but only if somebody typed
the number.

**`btnNotOK` deliberately does not advance.** A NOT OK needs detail, and
auto-advancing past it is how findings end up with no observation and no photo.

**`btnSubmit` is disabled while a write is in flight.** Without it a double tap
writes the whole checklist twice and nothing downstream can tell which copy is real.

**Test:** try to advance past a Measurement item without a reading. Submit a
checklist with a safety-critical NOT OK and confirm `Task_Status` stays
`In Progress`, so the cell cannot close.

---

## Step 6 — `scrBreakdown`

| Control | Notes |
|---|---|
| `drpShift`, `drpType` | From the choice columns |
| `inpSymptom` | "What did the operator see?" |
| `inpRootCause` | "What was actually wrong?" |
| `inpAction` | The fix |
| `dtpResponse` / `dtpRepairStart` / `dtpRepairEnd` + hour/minute dropdowns | |
| `inpLoss` | Production loss in minutes, with `lblLossHelp` beneath it |
| `tglSpare`, `tglRepeat` | |

**Symptom and root cause are separate fields and must stay separate.** Merging them
is what makes repeat-failure analysis impossible — you end up with a free-text
column that cannot be grouped.

**`lblLossHelp` matters more than it looks.** Production loss is not repair time: it
includes waiting for a technician, waiting for a part, and restarting the line, and
it is almost always the bigger number. If people record repair time here,
`Availability %` comes out flattering and wrong, and nobody notices because it looks
good.

---

## Step 7 — `scrSpare`

| Control | Notes |
|---|---|
| `drpSpare` | Active parts only |
| `lblStock` | Current stock, minimum, bin, and a lead-time warning if below minimum |
| `inpQty` | Number |
| `drpUrgency`, `drpReason` | |
| `inpRemarks` | |
| `btnSubmitSpare` | `DisplayMode` blocks submission **offline** |

Showing stock before the request stops the request that was never needed, and warns
about the one that cannot be filled this week.

**This screen is blocked offline on purpose.** `Stock_At_Request` has to be the real
number at the moment of asking — it is the evidence for a min-stock revision six
months later. Capturing it against a cached figure from this morning would make
that evidence worthless, so the app says "you need a network for this" instead.

---

## Step 8 — `scrAbnormality`

| Control | Notes |
|---|---|
| `drpCategory` | Safety, Quality, Air Leak, Oil Leak, Abnormal Noise, Vibration, Overheating, Contamination, 5S |
| `inpDescription` | Multiline |
| `drpSeverity` | High / Medium / Low |
| `camPhoto` | → `Abnormality_Photos` |
| `inpImmediate` | Containment done on the spot |
| `drpOwner` | From `Technician_Master` |
| `dtpTarget` | `DefaultDate` varies by severity |

`dtpTarget.DefaultDate` is **Today + 1** for High, +7 for Medium, +30 for Low. The
default is the commitment most people accept without thinking about it, so it needs
to be the right one rather than a convenient one.

Air-leak entries feed straight into compressed-air reduction work. Make the category
easy to pick and people will log them; bury it and they will not.

---

## Step 9 — `scrDone`

One label, `lblDone`, that says what actually happens next — including whether this
machine was the one that closed the cell.

Telling the technician "that was the last machine in the cell — the cell PM is
complete and the hour counter resets" is what makes the 4,000-hour rule feel like a
real thing he just did, rather than an administrative rule he complied with.

---

## Step 10 — offline

1. `App.OnStart` — `LoadData(colPendingWrites, "pm_pending", true)`
2. Checklist submit — the offline branch in `power_fx_formulas.md`
3. `scrHome` continue — replay on reconnect
4. `lblOfflineBanner` on every screen

**What works offline:** the allotted list (from cache), the machine hub, the
checklist, the abnormality log.

**What does not, deliberately:** spare requests, because `Stock_At_Request` must be
live. Better to block the action with a clear reason than to capture a number that
is quietly wrong.

**Test:** turn on flight mode, complete a checklist, confirm the banner shows a
count. Turn the network back on, reopen, confirm the rows land in SharePoint and the
count clears.

---

## Step 11 — publish

1. **File → Save → Publish**
2. **Share** with the maintenance security group. **Co-owner** only for the two
   people who maintain it.
3. On each handset: install Power Apps, sign in with the shared account, open the
   app, **pin to home screen**.
4. **Settings → Advanced → Enable deep linking**, then update `QR_Payload_URL`:

   ```
   https://apps.powerapps.com/play/<AppID>?tenantId=<TenantID>&machineid=MC-01-001
   ```

   Regenerate the stickers against the new pattern and **test before printing**:

   ```bash
   python qr/generate_qr_labels.py --test
   ```

   > Changing `QR_Payload_URL` means reprinting every sticker. Decide between Path A
   > and Path B **before** the first print run, not after.

---

## What the app must never do

| Never | Why |
|---|---|
| Set `Cum_Std_Hours_Since_PM` to 0 | Only Flow 5 resets the counter, and only together with `Last_PM_Date`, `Last_PM_WO_No`, `Reset_Applied` and `Reset_Date`. All five move together or none do |
| Create a `PM_WorkOrder` | Flow 2 owns the trigger rule, so it lives in exactly one place |
| Compute `Total_Cost_INR` | Flow 8 copies the master price at the time of use, so a later price rise does not rewrite last year's cost |
| Delete any master row | Set `Active = No`. Deleting orphans every fact that references it |
| Hard-code 4000 | Read `PM_Trigger_Hours` from the cell. A hard-coded trigger anywhere is a defect |

The app captures what a person observed. Everything derived from that is decided by
a flow, in one place, where it can be tested. Duplicating a rule into the app is how
the app and the flow start disagreeing, and the disagreement is always found months
later by someone trying to explain a number to a manager.
