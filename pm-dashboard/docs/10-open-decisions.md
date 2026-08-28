# 10 · Open Decisions and Suggestions

Assumptions I made to keep building, and things worth deciding before you go live.

## Assumptions I made

| # | Assumption | Change it here |
|---|-----------|----------------|
| 1 | Standard hours means the production standard hours you already use for efficiency reporting — earned hours, not manned hours, not machine running hours | `docs/02` upload rules; the value itself is just a number in the upload |
| 2 | The whole cell is PM'd together in one window when the counter trips | `pm_core.run_pm_engine()`, Flow 2 step 4 |
| 3 | Carry-over rolls forward; hours past the threshold are never lost | `carry_over = MAX(0, closing - threshold)` |
| 4 | 4000 h and 12 months are per-cell overridable, defaulting from `PM_Config` | `Cell_Master.PMIntervalStdHrs`, `.CalendarBackstopMonths` |
| 5 | One PM type (`PM-4000`), one checklist per machine family | `PM_Checklist_Master` |
| 6 | Due date = last calendar day of the plan month | Flow 2 step 4 |
| 7 | A work order closes only through the app, after a machine QR scan | Power Apps; SharePoint item-level permissions |
| 8 | Currency is INR, financial year starts April | `pbi_measures.py` format strings; `Dim_Date` FY logic |
| 9 | Machine-level MTBF uses cell hours divided equally across the cell's machines | `Operating Hours Allocated` measure |
| 10 | Photos live in a SharePoint library, not in the list items | `04 Photos/` |

Numbers 1, 2 and 9 are the ones most likely to need changing. None is hard to change
now; all three are expensive to change after six months of history.

## Suggestions worth adding

### Strongly recommended

**Tiered PM.** You chose a single 4000-hour PM. In practice most plants end up with
1000 h light / 2000 h medium / 4000 h major, because a full major service every
cycle is expensive and a full year between any inspection is a long time on an A-class
machine. The model already supports it: add `PMType` and a threshold column per tier
to `Cell_Master`, one checklist per tier, and let Flow 2 evaluate all three thresholds
each month. Roughly a day of work now; a rebuild later.

**A shutdown / opportunity flag.** When a cell goes down unplanned for four hours, that
is the cheapest PM window you will ever get. A "PM is due within 30 days — do it now"
flag on the machine hub turns unplanned downtime into planned maintenance. One measure
and one label.

**Lock the checklist to the scan window.** Right now a technician can scan at 08:00 and
submit at 17:00. Stamping scan time and submit time and flagging anything under, say,
40% of `PMStdMinutes` catches the fastest form of fake compliance. The data is already
being captured — it just is not being compared.

**Spare parts consumption against the PM cycle.** You are recording what was replaced.
One step further — expected life per part per machine type — turns that into
"this bearing is being replaced every 2 cycles when it should last 6". That is where
the money is, and you already have the raw data.

### Worth considering

**Meter readings on the checklist.** Add one numeric task per machine capturing the
machine's own hour meter. Over a year this tells you how well cell standard hours
proxy for actual machine running hours — and if the correlation is poor for a
particular machine, that is an argument for the per-machine weighting variant below.

**Per-machine weighting.** If one machine in a cell is a bottleneck running 1.3× the
cell rate and another is a standby at 0.4×, a single cell counter over-services one
and under-services the other. Add a `HourWeightFactor` column to `Machine_Master` and
give each machine its own counter. More accurate; more master data to maintain; loses
the single-window advantage. Only do this if the meter readings show you need it.

**Technician skill matrix.** Assignment is currently by area. A `Skill_Matrix` list
(TechID × MachineType × certified) would stop a hydraulics technician being assigned a
furnace PM. Worth it above roughly 20 technicians.

**Cost per work order.** Labour rate × wrench hours, plus spares consumed, gives real
maintenance cost per machine per year. Two columns and one measure, and it changes the
conversation with Finance entirely.

**Predictive flags.** Once you have 18–24 months of history: machines whose checklist
fail rate is rising, or whose MTBF is falling cycle on cycle, ranked. Not machine
learning — just a trend on data you will already have.

### Deliberately left out

**Live machine hour meters / IoT.** You specified monthly standard hours. Retrofitting
hour meters is a separate capital project. If it ever happens, only Flow 2 changes.

**ERP integration.** If spares already live in an ERP, two-way sync is a project of its
own. Start with the manual monthly stock upload and see whether the pain justifies it.

**Native mobile app.** Power Apps on a phone is good enough and costs nothing extra.

## Questions to settle before go-live

1. **Is "standard hours" the same figure Production reports for efficiency?** If
   Maintenance and Production are using two different definitions, every scheduling
   argument for the next two years starts here.
2. **Who owns the upload, by name?** Not a department — a person, with a named backup.
   The whole system stops without it.
3. **What happens when a cell is due and Production will not release it?** Deferred
   with approval, or overdue? Decide the policy now, because the dashboard will make
   this visible from week one and somebody will be uncomfortable.
4. **Are the 4000-hour thresholds actually right?** They should come from the OEM
   manual per machine family, rolled up to a cell figure. If 4000 is a round number
   someone picked, say so out loud — it is a fine starting point but it should be
   reviewed at the first quarterly.
5. **Retention on `QR_Scan_Log` and `PM_ChecklistResults`?** Quality systems commonly
   want seven years of PM evidence. Check before setting any deletion policy.
6. **Who sees what?** Should a technician see other technicians' compliance? There is a
   defensible answer either way, but decide it before the first person notices.
7. **Power BI licensing for viewers.** Pro per viewer, or a Fabric capacity? This is
   usually the largest recurring cost in the whole solution and it is worth pricing
   before the pilot, not after.
