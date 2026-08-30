# UAT test cases

35 cases. Work through them in order — later ones depend on state the earlier ones
create. Record a name and a date against each; an unrecorded test is an untested
system.

**Test in a separate SharePoint site**, not production. Several cases deliberately
corrupt data to prove a guard works.

| Priority | Meaning |
|---|---|
| **CRITICAL** | Go-live blocker. If this fails, stop |
| **HIGH** | Fix before go-live |
| **MEDIUM** | Fix in the first month |

---

## A. Provisioning and data load

### UAT-01 — Lists are created with correct types · **CRITICAL**
1. Run `provision_lists.ps1 -WhatIf`, then for real.
2. Open each of the 16 lists → **List settings**.

**Expected:** 16 lists, 224 columns. Every Choice column shows its real values from
the dictionary, not free text. Dates are Date-only or Date-and-Time as specified.
Yes/No columns are Boolean, not text.

### UAT-02 — Column internal names are not mangled · **CRITICAL**
1. `Cell_Master` → List settings → click `Cell_ID`.
2. Read the browser URL.

**Expected:** ends `Field=Cell_ID`. **Fail** if it shows `Cell%5Fx005f%5FID`.

*Why it matters:* a mangled name breaks every Power Query step, every flow
expression and every model reference, and the breakage is silent.

### UAT-03 — Row counts reconcile · **CRITICAL**
1. Run `load_data.ps1`.
2. Compare every list's item count against `sharepoint/data/_ROW_COUNTS.csv`.

**Expected:** exact match. 2,822 rows total, of which 730 are the plant calendar.

### UAT-04 — Validator rejects a bad row · **HIGH**
1. In a copy of the source workbook, change one `Spare_Replaced.Total_Cost_INR` to a
   wrong figure and duplicate one `Task_ID`.
2. Run `prepare_sharepoint_data.py --strict`.

**Expected:** non-zero exit. Report names `R5-cost-mismatch` and
`R0-duplicate-pk` with the offending IDs.

### UAT-05 — Views render on a phone · **HIGH**
1. Open `My Allotted PM List` on an actual handset.
2. Open `Machine Hub` filtered to `MC-01-001`.

**Expected:** the allotted list groups by cell and shows status pills. The hub shows
the machine identity and **five buttons, each at least 48 px tall**, tappable with a
gloved finger.

---

## B. The PM trigger

### UAT-06 — A cell crossing 4,000 raises exactly one work order · **CRITICAL**
1. Set `CELL-03` `Cum_Std_Hours_Since_PM` to `3,950`.
2. Upload a month giving it 200 h.
3. Run Flow 2 manually.

**Expected:** counter is 4,150. **One** work order, `Trigger_Type = Std Hours`,
`Trigger_Hours_At_Creation = 4150`, one `PM_Machine_Task` per active machine in the
cell (4 for CELL-03).

### UAT-07 — The 6-month backstop fires · **CRITICAL**
1. Set `CELL-07` `Cum_Std_Hours_Since_PM` to `800` and `Last_PM_Date` to 200 days ago.
2. Run Flow 2.

**Expected:** work order raised with `Trigger_Type = Calendar Backstop`.

*Why it matters:* this is the rule that protects a low-utilisation cell that would
otherwise never reach 4,000 hours and never be maintained.

### UAT-08 — No duplicate work order on a second run · **CRITICAL**
1. With UAT-06's work order still open, run Flow 2 again.

**Expected:** no second work order. Run history shows the open-WO condition
short-circuiting.

*Why it matters:* without this the flow raises a duplicate every morning until
someone closes the first.

### UAT-09 — A retuned trigger is respected · **HIGH**
1. Set `CELL-04` `PM_Trigger_Hours` to `3,000` and its counter to `3,100`.
2. Run Flow 2.

**Expected:** work order raised. The per-cell re-check used 3,000, not a hard-coded
4,000.

### UAT-10 — An inactive machine is excluded · **HIGH**
1. Set one `CELL-01` machine to `Active = No`.
2. Trigger a PM on CELL-01.

**Expected:** 3 task rows, `Machines_In_Scope = 3`. A mismatch alert fires because
`Cell_Master.Machine_Count` still says 4.

### UAT-11 — An inactive cell never triggers · **MEDIUM**
1. Set `CELL-08` `Active = No`, counter to `5,000`.
2. Run Flow 2.

**Expected:** no work order.

---

## C. Execution and the reset

### UAT-12 — Scan-in stamps the start time · **CRITICAL**
1. Scan `MC-01-001`, submit the PM Start form.

**Expected:** `Scan_Log` row with `Scan_Action = Start PM`. Task moves to
`In Progress` with `Scan_Start_Time` stamped. Work order moves to `In Progress` with
`Actual_Start_Date` set.

### UAT-13 — A duplicate scan does not double-count · **CRITICAL**
1. Submit the PM Start form for the same machine a second time.

**Expected:** a **second** `Scan_Log` row (the raw log records everything), but
`Scan_Start_Time` on the task is **unchanged**.

*Why it matters:* a technician who taps twice because the page was slow must not
restart his own clock. Otherwise a 40-minute job reads 4 minutes and looks like a
pencil-whipped PM in every report.

### UAT-14 — A partially completed cell does NOT reset · **CRITICAL**
1. On a 4-machine cell, complete checklists for **three** machines.

**Expected:**
- 3 tasks `Completed`, 1 `Pending`
- `Machines_Completed = 3`, `WO_Status` still `In Progress`
- **`Cum_Std_Hours_Since_PM` UNCHANGED**
- `Last_PM_Date` unchanged, `Reset_Applied = No`

*This and UAT-15 are the whole system.* If the counter resets at three of four, every
PM interval is wrong from that day on, and nothing on any dashboard will show it.

### UAT-15 — The final machine triggers the reset · **CRITICAL**
1. Complete the fourth machine's checklist.

**Expected, all in the same item version:**
- `WO_Status = Completed`, `Actual_End_Date` stamped
- `Machines_Completed = 4`
- `Cum_Std_Hours_Since_PM = 0`
- `Last_PM_Date` = today
- `Last_PM_WO_No` = this work order
- `Reset_Applied = Yes`, `Reset_Date` = today
- `Next_PM_Due_Date_Calendar` = today + 6 months

**Check the version history.** All five `Cell_Master` fields must change in **one**
version. Two versions means the update was split, and a failure between them would
leave a zeroed counter with no `Last_PM_Date`.

### UAT-16 — A skipped machine still lets the cell close · **HIGH**
1. Set one task to `Skipped` with a `Skip_Reason`; complete the rest.

**Expected:** work order completes, counter resets, and the skip is visible for the
monthly review.

*Confirm this is what you want.* "Machine running, will do next time" repeated four
times is how a PM system quietly dies.

### UAT-17 — A safety-critical NOT OK blocks closure · **CRITICAL**
1. Submit a checklist with a NOT OK on a `Safety_Critical = Yes` item.

**Expected:** task stays `In Progress`, **not** `Completed`. Teams and email
escalation fire. The cell cannot close and the counter cannot reset.

### UAT-18 — Duration is calculated · **MEDIUM**
1. Scan in, wait 5 minutes, submit the checklist.

**Expected:** `Duration_Min` ≈ 5, `Scan_End_Time` stamped.

---

## D. Monthly hours and proration

### UAT-19 — Mid-month reset prorates by WORKING days · **CRITICAL**
1. Confirm `Plant_Calendar` has April 2026 loaded with Sundays marked as non-working.
2. Set `CELL-05` `Reset_Date` to `2026-04-02`, counter `0`.
3. Upload April 2026 with `Actual_Std_Hours = 780`.

**Expected:**
```
April 2026: 30 calendar days, 4 Sundays  ->  26 working days
working days strictly after 02 Apr       ->  24
posted  = 780 × 24/26 = 720.00
counter = 720.00      (NOT 780, and NOT 728)
```

`720`, not `728`. If you get 728 the flow is still prorating by calendar days and
`Actual_Std_Hours` is a **capacity** figure — capacity does not accrue on a Sunday.

`StdHours_Monthly.Actual_Std_Hours` stores **780** — the raw figure. Only the counter
increment is prorated.

*Why it matters:* without proration at all, every cell resetting mid-month runs its
next PM early, permanently, getting worse each cycle.

### UAT-19a — An unmaintained plant calendar fails loudly · **HIGH**
1. Delete or unmark every working day for one month in `Plant_Calendar`.
2. Upload that month.

**Expected:** flow **terminates as Failed** with an email naming the month. It must
**not** divide by zero, and must **not** silently post the full month's hours.

*Why it matters:* the divisor comes from a list a human maintains. "Somebody will
remember to add the holidays" is not a control.

### UAT-20 — No reset in the month means no proration · **HIGH**
1. Upload a month for a cell whose last reset was two months ago.

**Expected:** the full month's hours are added. `varDayOfReset = 0`, so the formula
gives `hours × 30/30`.

### UAT-21 — Duplicate month upload is rejected · **CRITICAL**
1. Upload the same month's file twice.

**Expected:** second run **terminates as Failed**, file moves to `Rejected/`, email
sent. No `StdHours_Monthly` rows created, no counter changed.

*Check it terminates as Failed, not Succeeded.* A rejected upload showing green in
the run history looks identical to a good one.

### UAT-22 — An unmatched Cell_ID stops the whole file · **CRITICAL**
1. Upload a file with `CELL-99` on row 4 of 8.

**Expected:** **nothing** imported — not rows 1–3, not rows 5–8. Email names the bad
row. Flow terminates as Failed.

*Why it matters:* a half-imported month is far harder to unpick than a rejected one,
because nothing on the surface says which half landed.

### UAT-23 — The 3-month average recalculates · **MEDIUM**
1. After three monthly uploads, complete a cell PM.

**Expected:** `Avg_Monthly_Std_Hours_L3M` = mean of the last three months.

---

## E. Findings, breakdowns, spares

### UAT-24 — A NOT OK raises a follow-up work order · **HIGH**
1. Submit a checklist with `Follow_Up_Required = Yes`. Run Flow 10.

**Expected:** corrective work order `CWO-…` created, `Trigger_Type = Manual`, and
`Follow_Up_WO` written **back** onto the checklist response row.

### UAT-25 — The follow-up does not repeat · **HIGH**
1. Run Flow 10 again the next day.

**Expected:** no second corrective work order — the filter excludes rows where
`Follow_Up_WO` is already set.

*Why it matters:* without the write-back the same finding raises a fresh corrective
job every morning, and within a week nobody trusts the corrective queue.

### UAT-26 — A criticality-A breakdown alerts immediately · **HIGH**
1. Report a breakdown on a criticality-A machine.

**Expected:** Teams message and email within a minute. Repeat on a criticality-C
machine — **no** alert.

### UAT-27 — Breakdown-after-PM linkage · **MEDIUM**
1. Complete a cell PM. Report a breakdown on that cell 3 days later.

**Expected:** `Linked_PM_WO` populated. In Power BI, `Breakdowns After PM (7d)`
includes it — **and also includes historic ones where `Linked_PM_WO` is blank**,
because the measure derives the link from dates.

### UAT-28 — A rejected spare request is recorded · **HIGH**
1. Submit a spare request, reject the approval.

**Expected:** `Approval_Status = Rejected`, `Approved_By` and `Approved_Date` set,
requester emailed with the comment. Stock **unchanged**.

### UAT-29 — Replacing a part decrements stock and alerts · **HIGH**
1. Submit Spare Replaced for a part with `Current_Stock` one above `Min_Stock`.

**Expected:** `Total_Cost_INR = Qty_Used × Unit_Cost_INR`, stock decremented,
below-minimum alert sent **including the lead time**.

### UAT-30 — A high-severity abnormality escalates and follows up · **HIGH**
1. Log a High severity abnormality. Leave it open 24 hours.

**Expected:** immediate Teams + email. After 24 h, a follow-up reminder. Close it and
confirm a second reminder does **not** fire.

*Why it matters:* a reminder that fires whether or not the problem was fixed teaches
people to ignore reminders.

---

### UAT-30a — The Monday heartbeat arrives on a clean week · **CRITICAL**
1. Clear every outstanding item: no overdue cells, no open work orders, nothing
   unscanned, no overdue abnormalities, no reset failures.
2. Run Flow 11 manually on a **Monday**.
3. Run it again on a **Tuesday** with the same clean state.

**Expected:** Monday sends the one-line *"PM system healthy — nothing outstanding"*.
Tuesday sends **nothing** and the run history shows a skip.

*Why it matters:* the flows run on one individual's connections. Without a scheduled
all-clear, an empty inbox means either "nothing outstanding" or "the flows died three
weeks ago", and nobody can tell which until damage is done. **No Monday digest means
the flows have stopped** — that is the entire early-warning system, so prove it works
before go-live.

### UAT-30b — A reset failure alone triggers the digest · **HIGH**
1. Clear everything else, then set one completed work order to `Reset_Applied = No`.
2. Run Flow 11 on a **Tuesday** (so the Monday heartbeat is not what sends it).

**Expected:** the digest sends, with the reset-failure section populated.

*Why it matters:* a completed work order whose counter never zeroed is the most
expensive silent failure in the system, and the send-condition must count it. If the
digest stays quiet here, `Get_items_reset_failures` is missing from the condition —
see `expressions.md` §16.

---

## F. Reporting

### UAT-31 — Every measure returns a sensible value · **CRITICAL**
1. Run `python tools/verify_measures.py --asof 2026-08-30`.
2. Compare each figure against the same measure in Power BI Desktop.

**Expected:** they agree, and match `ASSUMPTIONS.md` §9. No measure errors; no measure
is unexpectedly blank.

Spot-check these four by hand:
- `Breakdowns After PM (7d)` = **9** of 88 (10.2%)
- `PM Compliance %` = **89.6%** (43 of 48)
- `Reset Not Applied Count` = **0**
- `Schedule Adherence %` = **54.9%** (28 of 51 committed rows, 4 forecast excluded)

### UAT-32 — All nine pages open with no visual errors · **CRITICAL**
1. Open each page in Desktop.

**Expected:** no error triangles, no "can't display this visual". Drillthrough from a
machine on any page reaches Machine 360 filtered to that machine. The Gantt offset
series is transparent. Slicers filter across the page.

---

## Sign-off

| | Name | Date | Signature |
|---|---|---|---|
| Tested by | | | |
| Maintenance Manager | | | |
| IT / M365 Administrator | | | |

**Go-live is blocked until every CRITICAL case passes.**

| Result | Count |
|---|---|
| Passed | |
| Failed | |
| Not tested | |

Record failures here, with the case number and what happened:

```
UAT-__  ................................................
UAT-__  ................................................
```
