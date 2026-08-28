# 07 · Dashboard Design

Ten pages, 1600 × 900, one visual language.

## Design rules

**Palette.** Deep slate ink `#0F2A3D`, teal accent `#1B6E8C`, paper `#F2F5F7`,
white cards, hairline borders `#D5DEE4`. Status colours are reserved and mean only
one thing: green `#2F9E7E` good, amber `#D08B2C` watch, red `#C4553B` act. Nothing
decorative is ever green, amber or red — if a colour appears, it carries meaning.

**Layout.** Every page: a 76 px ink header band with title and one line of context,
a row of six KPI cards, then two content rows. Margin 24, gap 14, card radius 8.
The grid is identical on all ten pages so the eye lands in the same place every
time.

**Typography.** Segoe UI throughout. Callout values 30 pt semibold, titles 11 pt,
labels and axes 9 pt in muted grey. Axis titles are off — the visual title already
says what it is; repeating it twice wastes the space the chart needs.

**Chart choices.** Categories with more than five members go horizontal
(`clusteredBarChart`), so labels read left-to-right instead of being turned on
their side. Time goes across the x-axis, always. Donuts appear exactly twice, both
times for a part-to-whole split of fewer than eight slices. No 3-D, no gauges, no
gradients, no drop shadows.

**Density.** Six KPIs is the ceiling. Beyond that nobody reads any of them.

## The pages

### 1 · Overview
The control tower. PM compliance, overdue count, availability, breakdowns, open
abnormalities, cells due in the next three months. A combo chart of completed and
overdue work orders with a compliance line, a bar chart of every cell's counter
against 4000 hours, the full cell plan table, and downtime by area.

If somebody looks at exactly one page a month, this is it.

### 2 · PM Planning
The 4000-hour counter, in detail. Run rate, rolling 12-month hours, cells tripped,
cells due next quarter, hours remaining, counter percentage. The forward-plan table
carries the answer to the only question planning actually asks: *when is each cell
next due, and is it hours or the calendar driving it?* Below, standard hours by
month and cell, and a matrix of the closing counter cell-by-month.

### 3 · Monthly Schedule
What has been raised. A cell-by-month matrix of work order counts, a status
breakdown by month, and the full work order list with machine, technician, shift,
planned date, due date, checklist completion and whether the machine was scanned.

This is the page a planner works from on the first Monday of the month.

### 4 · Execution & Quality
Compliance, completion, checklist completion, checklist fail rate, QR verification,
actual-vs-standard duration. Compliance and fail rate on one line chart, because the
relationship between them is the story: compliance rising while fail rate falls to
zero usually means the checklist is being clicked through, not worked through.

Safety-critical failures by cell get their own chart. That number goes to a person,
every week.

### 5 · Machine 360
The QR landing page, in dashboard form. Pick a machine and get: last PM date,
months since, breakdown count, downtime hours, MTBF — then four tables, PM history,
breakdown history, spares fitted, and abnormalities.

Built with a machine slicer rather than as a drillthrough page, so it also works
as a filtered report URL from the app. Converting it to a proper drillthrough is
two clicks in Desktop if you want both — see the note in `09-deployment-checklist.md`.

### 6 · Reliability
Breakdowns, downtime, MTTR, MTBF, availability, and **failures within 15 days of a
PM**. That last one is the sharpest measure of PM quality available: a high number
means PMs are being signed off rather than done, and no amount of compliance
percentage will tell you that.

Downtime by failure mode as a Pareto, breakdowns and MTTR by month, and a bad-actor
table sorted by loss.

### 7 · Spare Parts
Requested value, consumed value, pending approvals, emergency request share, parts
below minimum, spend per standard hour. Requested and consumed are shown side by
side deliberately — the gap between them is where money leaks.

Emergency request share is the leading indicator: when it climbs, planning is losing
to firefighting, and the PM programme is about to slip whatever the compliance
number says.

### 8 · Abnormalities
Logged, open, high-severity open, open beyond 30 days, closure rate, average days
to close. By category, by month and severity, and the open list in full.

Every row here is a breakdown that has not happened yet. Ageing matters more than
volume — a large log that closes quickly is a healthy system; a small one that
never closes is not.

### 9 · Technician
Headcount, work orders per person, wrench hours, capacity hours, utilisation, scans.
Wrench hours against capacity per technician, on-time compliance per technician, and
a full scorecard.

Load balance is deliberately shown before performance. An overloaded technician is
a planning problem, and reading their compliance number without their utilisation
number next to it produces the wrong conversation.

### 10 · Data Quality
Total issues, missing upload rows, work orders closed without a scan, work orders
with no checklist evidence, latest upload month, data as of. A cell-by-month upload
matrix where any blank is a missing file, and the list of desk-closed work orders.

Every number on this page should read zero. Put this page second in the review, not
last — a dashboard built on a month of missing uploads is worse than no dashboard,
because it looks authoritative.

## Filters

Each page carries what it needs and nothing more: Financial Year and Area on
planning-oriented pages, Machine on Machine 360. There is no report-level slicer
panel — cross-page filter state that people cannot see is the fastest way to have
two managers reading different numbers off the same screen.

## Accessibility

- Every status colour is paired with a number or a word, never colour alone.
- Green/amber/red at the chosen values pass 3:1 against white for graphical objects.
- Tab order runs left to right, top to bottom, set explicitly on every visual.
- Alt text on every chart: fill it in Desktop before publishing — the generator
  cannot write something meaningful for you.
