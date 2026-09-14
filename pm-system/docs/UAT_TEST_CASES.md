# UAT test cases

36 cases. Work through them in order — later ones depend on state the earlier ones
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
2. Open each of the 14 lists → **List settings**.

**Expected:** 14 lists, 138 columns. Every Choice column shows its real values from
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

**Expected:** exact match. 2,422 rows total, of which 730 are the plant calendar.

### UAT-03a — A completed work order that nothing can date is rejected · **HIGH**
1. In the source workbook, blank `Scan_End_Time` on every machine task belonging to
   one `Completed` work order.
2. Run `python tools/prepare_sharepoint_data.py --strict`.

**Expected:** an `R5b-completed-undated` **error** naming that work order, and **no
CSVs written**.

*Why it matters:* the work order no longer stores its own end date — the model takes
the latest scan across its tasks. A completed work order with nothing scanned out
therefore has no date at all, and drops silently out of `Breakdowns After PM (7d)`,
`PM On-Time %` and `Avg PM Delay (Days)`. Every one of those reads *better* for the missing
row, which is the wrong direction for a fault to fail in.

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

**Expected:** the task moves to `In Progress` with `Scan_Start_Time` stamped, and the
work order moves to `In Progress`.

3. Now scan a machine that has **no** open task.

**Expected:** an email back saying there is no open PM for that machine, and the run
finishes as **Succeeded** — nothing failed, somebody scanned a machine with no job on
it.

### UAT-13 — A duplicate scan does not double-count · **CRITICAL**
1. Submit the PM Start form for the same machine a second time.

**Expected:** `Scan_Start_Time` on the task is **unchanged**, and the flow run shows
green.

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

**Expected on `PM_WorkOrder`:**
- `WO_Status = Completed`, `Reset_Applied = Yes`
- `Machines_Completed = 4`

**Expected on `Cell_Master`, all three in the same item version:**
- `Cum_Std_Hours_Since_PM = 0`
- `Last_PM_Date` = today
- `Next_PM_Due_Date_Calendar` = today + 6 months

**Check the version history.** All three `Cell_Master` fields must change in **one**
version. Two versions means the update was split, and a failure between them would
leave a zeroed counter with no `Last_PM_Date` — which nothing downstream can tell
apart from a genuine reset.

3. In Power BI, refresh and open the work order.

**Expected:** its start, end and total duration read back correctly from the four task
rows, with nothing stored on the work order itself to disagree with them.

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

### UAT-18 — A too-fast checklist is caught · **MEDIUM**
1. Scan in, wait 5 minutes, submit a checklist whose items sum to 45 expected minutes.

**Expected:** `Scan_End_Time` stamped, and the supervisor receives the
**closed-implausibly-fast** email — 5 minutes is under 30% of 45.

2. Refresh Power BI.

**Expected:** the task's duration reads ≈ 5 minutes, computed as `Scan_End_Time`
minus `Scan_Start_Time`. Nothing stores it.

*Why it matters:* the number moved out of the list, but the check it existed for did
not. A 45-minute checklist closed in 4 minutes is a pencil-whipped PM whether or not
anybody wrote the duration down.

---

## D. Monthly hours and proration

### UAT-19 — Mid-month reset prorates by WORKING days · **CRITICAL**
1. Confirm `Plant_Calendar` has April 2026 loaded with Sundays marked as non-working.
2. Set `CELL-05` `Last_PM_Date` to `2026-04-02`, counter `0`.
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

### UAT-23 — The 3-month average is right without being stored · **MEDIUM**
1. Load three monthly uploads for a cell. Refresh Power BI.

**Expected:** `Avg Monthly Std Hours L3M` equals the mean of those three months.

2. Now skip a month for that cell — load a fourth upload with no row for it.

**Expected:** the average still uses the last three months **that have data**, not
three calendar months with a zero in the middle.

*Why it matters:* the average used to be written onto the cell by a flow at reset
time, which meant it went stale between resets and silently read zero for a cell
whose flow run had failed. Computed at refresh it cannot be stale, and this second
step is the case the stored version got wrong.

---

## E. Findings, breakdowns, spares

### UAT-24 — A NOT OK reaches the supervisor's queue · **HIGH**
1. Submit a checklist answering one item **NOT OK — needs follow-up** and another
   **NOT OK — fixed on the spot**.
2. Open the **NOT OK Findings** view on `Checklist_Response`.

**Expected:** both rows carry `Result = NOT OK`; only the first has
`Follow_Up_Required = Yes`, and only the first appears on the view. The view shows
machine, check point, observation and who raised it, newest first.

### UAT-25 — Nothing raises a work order behind the supervisor's back · **HIGH**
1. Leave the finding from UAT-24 open overnight.
2. Next morning, list `PM_WorkOrder` for that cell.

**Expected:** **no** new work order. Then run Flow 2 and confirm the cell's normal
4,000-hour trigger still evaluates — it is not being suppressed by anything.

*Why it matters:* corrective work orders used to be raised automatically into
`PM_WorkOrder`, where Flow 2's open-work-order check could not tell them apart from
a live PM. One unclosed corrective job would have blocked that cell's next real PM
trigger indefinitely, and nothing would have reported it.

### UAT-26 — A criticality-A breakdown alerts immediately · **HIGH**
1. Report a breakdown on a criticality-A machine.

**Expected:** Teams message and email within a minute. Repeat on a criticality-C
machine — **no** alert.

### UAT-27 — Breakdown-after-PM is derived, not stamped · **MEDIUM**
1. Complete a cell PM. Report a breakdown on that cell 3 days later.
2. Report another on the same cell 10 days after the PM.

**Expected:** `Breakdowns After PM (7d)` counts the first and not the second — and
counts historic breakdowns loaded before any flow existed, because the measure works
from dates rather than from a column a flow had to remember to write.

### UAT-28 — Stock cannot go negative · **HIGH**
1. Submit Spare Replaced with `Qty_Used` greater than `Current_Stock`.

**Expected:** `Current_Stock` clamps at **0**, never below — and the below-minimum
alert is sent anyway.

*Why it matters:* a negative stock figure means the physical count was already wrong.
Clamping the number quietly would hide that; clamping it **and still alerting** shows
it.

### UAT-29 — Replacing a part decrements stock and alerts · **HIGH**
1. Submit Spare Replaced for a part with `Current_Stock` one above `Min_Stock`.

**Expected:** stock decremented, below-minimum alert sent **including the lead time**.
In Power BI, `Spare Cost MTD` rises by `Qty_Used × Unit_Cost_INR` — computed at
refresh, with no stored line total to disagree with it.

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
2. Run Flow 9 manually on a **Monday**.
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
2. Run Flow 9 on a **Tuesday** (so the Monday heartbeat is not what sends it).

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
- `Breakdowns After PM (7d)` = **7** of 88 (8.0%) — see `ASSUMPTIONS.md` §9.1 if you were expecting 9
- `PM Compliance %` = **89.6%** (43 of 48)
- `Reset Not Applied Count` = **0**
- `Schedule Adherence %` = **54.9%** (28 of 51 committed rows, 4 forecast excluded)

### UAT-32 — All nine pages open with no visual errors · **CRITICAL**
1. Open each page in Desktop.

**Expected:** no error triangles, no "can't display this visual". Drillthrough from a
machine on any page reaches Machine 360 filtered to that machine. Slicers filter
across the page.

> There is no longer a Gantt offset series to set transparent. The five measures that
> faked a Gantt out of a stacked bar went with the reduction, and with them the manual
> "set two series to no fill" step in Desktop that had to be redone on every rebuild.

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
