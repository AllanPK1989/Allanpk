# Step-by-step build guide

**Plain English, in order, start to finish.**

This is the friendly walkthrough. `IMPLEMENTATION_RUNBOOK.md` is the same journey
with every technical detail — come here first, go there when you need the fine print.

You do **not** need to be a SharePoint or Power BI expert. Everything you type is
written out. Where you need to click something, it says where.

---

## How the pieces fit together

Before you build anything, understand what you are building. There are five parts
and they connect in one direction:

```
        ┌──────────────────────────────────────────────────┐
        │  1. SHAREPOINT  — the filing cabinet             │
        │     16 lists holding every PM record             │
        └───────────────┬──────────────────────────────────┘
                        │  everything reads and writes here
        ┌───────────────┴──────────────┬───────────────────┐
        │                              │                   │
┌───────▼─────────┐        ┌───────────▼──────┐   ┌────────▼────────┐
│ 2. QR STICKERS  │        │ 3. FORMS         │   │ 5. POWER BI     │
│ on each machine │───────▶│ what the         │   │ the dashboard   │
│ opens the       │        │ technician fills │   │ managers read   │
│ machine's page  │        │ in on his phone  │   │                 │
└─────────────────┘        └───────────┬──────┘   └────────▲────────┘
                                       │                   │
                           ┌───────────▼───────────────────┴───┐
                           │ 4. POWER AUTOMATE — 11 flows      │
                           │    the rules that run by          │
                           │    themselves: counters, triggers,│
                           │    resets, alerts                 │
                           └───────────────────────────────────┘
```

**In one sentence:** a technician scans a sticker, fills in a form, a flow updates
the filing cabinet, and the dashboard shows what it all means.

**Build them in this order.** Each part needs the one before it to exist.

---

## Before you start — what you need

### People and access

| You need | Why |
|---|---|
| A SharePoint site you own | The system creates 16 lists — do not use an existing site |
| **Site Owner** permission on it | You cannot create lists without it |
| One M365 account to own everything | All 11 flows and 5 forms are built under it. **Decide who, now** — see §"The one thing to get right" at the end |
| Two colleagues as co-owners | So you are not the only person who can fix a flow |
| A shared mailbox for alerts | So failure emails do not go to one person's inbox |
| One Android phone | To test the QR stickers |

### Software on your laptop

Three things. Install them once.

**1. PowerShell 7** — this is the tool that creates the SharePoint lists for you, so
you do not have to click through 224 columns by hand.

Download from Microsoft's PowerShell releases page and install. Then open it (search
"PowerShell 7" in the Start menu) and paste this:

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
```

Press Y if it asks. PnP is a free Microsoft toolkit for talking to SharePoint.

**2. Python** — this prepares your data and generates the QR stickers. Install from
python.org, **ticking "Add Python to PATH"** during setup. Then open a Command
Prompt in the project folder and run:

```
pip install -r tools/requirements.txt
pip install -r qr/requirements.txt
```

**3. Power BI Desktop** — free from the Microsoft Store.

### The project folder

Everything lives in the `pm-system` folder. Put it somewhere sensible on your
laptop, like `C:\EPQPL_PM\`. All the commands below assume you have a Command
Prompt or PowerShell window **open inside that folder**.

> **Tip:** open the folder in File Explorer, click in the address bar, type `cmd`
> and press Enter. That opens a Command Prompt already in the right place.

---

# Stage 1 — Check the data  ·  30 minutes

**What you are doing:** turning the three Excel workbooks into clean files that
SharePoint will accept, and checking nothing in them is broken.

### Do this

1. Make sure the three workbooks and the data dictionary are in the `input` folder.
2. Run:

```
python tools/prepare_sharepoint_data.py --strict
```

### How you know it worked

The last line says:

```
0 error(s), 0 warning(s).
```

You will also find new files in `sharepoint\data\` — one `.csv` per list, plus a
report.

### If it goes wrong

If it says anything other than 0 errors, **stop and fix the workbook**. Open
`sharepoint\data\_VALIDATION_REPORT.md` — it names the exact row and what is wrong
with it.

> **Why not just skip it?** Because a bad `Cell_ID` that reaches SharePoint becomes
> a record that belongs to no cell. Nothing will tell you. It just quietly makes a
> number wrong forever.

### Before you move on

Open `sharepoint\data\_ROW_COUNTS.csv` and note the total: **2,822**. You will check
against this in Stage 3.

---

# Stage 2 — Build the SharePoint site  ·  45 minutes

**What you are doing:** creating the 16 lists, all 224 columns, and the views the
technicians will actually use. The script does it; you just run it.

### Do this

**1. Create an empty site.** SharePoint → **Create site** → **Team site** → name it
`Maintenance`. Copy the address — it looks like
`https://yourcompany.sharepoint.com/sites/Maintenance`.

**2. Practice run first.** In PowerShell 7, in the project folder:

```powershell
cd sharepoint
.\provision_lists.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance" -WhatIf
```

`-WhatIf` means **"show me what you would do, but do not actually do it."** Nothing
is created. It prints every list and column it *would* make.

Read it. You should see **16 lists, 224 columns, 5 libraries** and `Failed : 0`.

**3. Now do it for real.** Same command, without `-WhatIf`:

```powershell
.\provision_lists.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance"
```

It will ask you to sign in. Takes a few minutes.

**4. Add the views and the shop-floor buttons:**

```powershell
.\apply_views.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance" -WhatIf
.\apply_views.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance"
```

### How you know it worked

`Failed : 0` at the end, and you can see 16 lists on the site.

### ⚠ One check you must not skip

Open the `Cell_Master` list → **Settings** (gear icon) → **List settings** → click
the column **`Cell_ID`**. Look at the web address in your browser.

- ✅ It ends `Field=Cell_ID` — **correct, carry on**
- ❌ It ends `Field=Cell%5Fx005f%5FID` — **stop**

The second one means the column was created by hand rather than by the script.
SharePoint mangles names containing underscores. Everything downstream — the
dashboard, the flows, the app — refers to `Cell_ID`, and none of it would find
`Cell_x005f_ID`. Delete that column and re-run the script.

---

# Stage 3 — Load the data  ·  20 minutes

**What you are doing:** putting the 2,822 rows into the lists you just made.

### Do this

```powershell
.\load_data.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance" -WhatIf
.\load_data.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance"
```

Practice run first, as before. The real run takes a few minutes.

### How you know it worked

`Rows loaded : 2822` and `Conversion problems : 0`.

### ⚠ Then count them yourself

Open each list and compare its item count against `sharepoint\data\_ROW_COUNTS.csv`.

```
Cell_Master              8      PM_WorkOrder            51
Technician_Master        6      PM_Machine_Task        193
Spare_Master            15      Checklist_Response     997
Checklist_Master        51      Scan_Log               336
Machine_Master          30      Breakdown_Log           88
Plant_Calendar         730      Spare_Request           64
StdHours_Monthly        96      Spare_Replaced          58
                                Abnormality_Log         44
                                PM_Plan_Calendar        55
```

A list that is short by even one row means a row was dropped silently. Find it now,
not in six months.

### ⚠ Now mark your holidays

Open the **`Plant_Calendar`** list. It has one row per day for two years, with
Sundays already marked as non-working.

**It does not know about your festival holidays or the annual shutdown.** Nobody
could guess those, so they were left for you.

Filter to the next 12 months, and for every holiday, Pongal day, and shutdown day:
- set `Day_Type` to `Holiday` or `Shutdown`
- set `Is_Working_Day` to **No**

> **Why this matters:** when a cell's PM happens mid-month, the system splits that
> month's hours between the old cycle and the new one — based on **working days**.
> Every holiday you do not mark is a day the system thinks you were producing. The
> counter then creeps, and the next PM comes slightly early. Every cycle. Forever.

---

# Stage 4 — Build the forms  ·  half a day

**What you are doing:** making the five forms the technicians fill in. This is the
fiddliest stage. Take your time.

The five forms: **PM Start**, **PM Checklist**, **Breakdown Report**, **Spare
Request**, **Abnormality Log**.

### ⚠ The rule that will catch you out

A pre-filled link fills in answers **by position** — question 1 gets the first
value, question 2 the second, and so on. It does not use question names.

So: **`Machine ID` must always be question 1. `Cell ID` must always be question 2.**

If you ever add a question above them, every sticker on the shop floor will start
filling the wrong boxes — silently, with no error. Add new questions at the bottom.

### Do this, for each of the five forms

1. Go to **forms.office.com**, signed in as the **owning account** (the one you
   chose at the start). → **New Form**
2. **Question 1:** type of question **Text**, title `Machine ID`, mark **Required**
3. **Question 2:** **Text**, `Cell ID`, **Required**
4. **Question 3:** **Choice**, `Technician Name`, **Required** — type in all six
   names from the `Technician_Master` list

   > This one is not optional and never becomes a text box. Everyone signs in with
   > the same account, so this dropdown is the *only* record of who did the work.
   > Free text gives you "Murugan", "murugan s" and "MURUGAN S", and then nothing
   > can be counted.

5. Add the rest of the questions for that form — listed in
   `automate\FLOW_SPECS.md`
6. **Settings** (…) → **Anyone can respond** ✅ , **Record name** ❌

### Then make the pre-filled links

1. Open a form → **Collect responses** → **Get a link to prefill answers**
2. Type `MC-01-001` into Machine ID and `CELL-01` into Cell ID, leave the rest blank
3. Click **Get link**. You get something like:

```
https://forms.office.com/r/AbCdEf?id=xxxxx&r1a2b3c4=MC-01-001&r5d6e7f8=CELL-01
```

Those `r1a2b3c4` codes are that form's question IDs. They never change.

4. Now make one for each of the 30 machines by swapping the machine and cell IDs.
   Easiest way: paste that link into a spreadsheet column next to your machine list
   and use a formula to substitute, then paste the results into the four URL columns
   in `Machine_Master`.

**Test one on a real phone before you make all 30.** Open it and check the machine
and cell are already filled in, and the first thing you have to touch is the name
dropdown — not the keyboard.

---

# Stage 5 — Print and fit the QR stickers  ·  half a day

**What you are doing:** making the stickers that go on the machines.

### Do this

1. Generate them against your real site address:

```
python qr/generate_qr_labels.py --base-url https://yourcompany.sharepoint.com/sites/Maintenance --test
```

2. **It must say `passed: 30    failed: 0`.** If it does not, do not print.

> `--test` reads every sticker back with a scanner and checks it points at its own
> machine. A wrong sticker takes about a month to notice, and by then it has been
> scanned two hundred times against the wrong machine — every one of those a record
> you cannot easily unpick.

3. Print `qr\labels\PM_QR_Labels.pdf`:

| Setting | Value |
|---|---|
| Paper | A4 **polyester or vinyl** sticker sheets, 3 × 8 pre-cut at 50 × 30 mm |
| Scale | **100% / Actual size** — never "Fit to page" |
| Printer | **Laser**, not inkjet |

> Paper labels do not survive a fuse plant — oil soaks in and the code is gone in
> weeks. "Fit to page" shrinks the code below the size a phone can read reliably.
> Inkjet runs the moment someone wipes the machine with solvent.

4. Stick them at **chest height**, on a flat surface, away from the coolant spray.

5. **Walk the floor and scan every single one.** Two people, one hour. Check each
   opens the page for the machine it is stuck to. This removes an entire class of
   problem permanently.

---

# Stage 6 — Build the flows  ·  2 days

**What you are doing:** building the 11 automations that make the system run by
itself. This is the biggest stage.

Open `automate\FLOW_SPECS.md`. It lists every flow, every action in order, and every
setting. `automate\expressions.md` has every formula written out to copy and paste.

### Build them in this order

**Do 5, 2 and 1 first.** They are the heart of the system — the reset, the trigger
and the monthly counter. Get those working before anything else.

| Order | Flow | What it does | Time |
|---|---|---|---|
| 1st | **5 — Cell Closure & Reset** | Zeroes the counter when the last machine in a cell is done | 3 h |
| 2nd | **2 — PM Trigger** | Raises the work order when a cell hits 4,000 hours or 6 months | 3 h |
| 3rd | **1 — Monthly Hours Import** | Adds each month's hours to the counters | 4 h |
| then | 3, 4 | Scan in, checklist submission | 4 h |
| then | 6, 7, 8, 9 | Breakdown, spare request, spare used, abnormality | 5 h |
| last | 10, 11 | Follow-up jobs, daily digest | 3 h |

### Three rules while building

**1. Name your actions before you write formulas.** Formulas refer to actions by
name. Rename an action afterwards and the formula breaks — the flow still saves, and
then fails later with a confusing error.

**2. Turn concurrency OFF on flows 1 and 5.** In the flow: the "Apply to each" step →
**Settings** → **Concurrency Control** → **Off**.

> Both flows read a number, change it, and write it back. If two run at the same
> time they both read the same starting number and one of the two updates is lost.
> This will happen the first month two cells finish on the same afternoon.

**3. Add your two co-owners to every flow as you finish it.** Flow → **Share** → add
both. Doing this later across 11 flows is an hour nobody ever schedules.

Also: point every failure alert at the **shared mailbox**, not your own inbox.

---

# Stage 7 — Set up the dashboard  ·  half a day

**What you are doing:** opening the Power BI report and pointing it at your live
SharePoint site.

### Do this

1. Double-click `powerbi\PM_Dashboard.pbip`. Power BI Desktop opens.
2. It asks for settings. Set `pSourceFolder` to your `input` folder. Click
   **Refresh**.
3. Check all nine pages open without red error triangles.

### Two small jobs Power BI will not do for you

Both take under a minute. They cannot be saved in the file.

**a) The machine drill-through.** Click the `Machine 360` page. In the
**Visualizations** panel on the right, find the **Drill through** box, and drag
`Dim_Machine → Machine_ID` into it. Now you can right-click any machine anywhere and
jump to its full history.

**b) The planned-vs-actual bars on page 3.** Click the bar chart. Format → **Bars**
→ **Colors** → set `Gantt Planned Offset (Days)` and `Gantt Actual Offset (Days)` to
**no fill**. Those two are invisible spacers that push the visible bars into the
right position — a trick, because Power BI has no real timeline chart.

### Now point it at SharePoint

**Home → Transform data → Manage parameters:**

| Setting | Change it to |
|---|---|
| `pSourceMode` | `SharePoint` |
| `pSharePointSite` | your site address |

Click **Refresh**. That is the whole switch — one setting.

4. **Publish** to your workspace. Then in the browser: **Settings → Scheduled
   refresh** → twice a day, **06:00** and **14:00**.

---

# Stage 8 — Test everything  ·  1 day

**What you are doing:** proving it works before real people depend on it.

Open `docs\UAT_TEST_CASES.md`. There are 35 tests. Write a name and a date against
each one as you do it.

**Do not shorten this.** These five matter most:

| Test | What you are proving |
|---|---|
| **UAT-14** | Finish 3 of 4 machines in a cell → the counter does **not** reset |
| **UAT-15** | Finish the 4th → the counter resets and all five fields change together |
| **UAT-19** | A mid-month PM splits the hours correctly → **720.00** hours, not 780 or 728 |
| **UAT-21** | Uploading the same month twice → rejected |
| **UAT-30a** | The Monday "system healthy" email arrives |

> **UAT-14 and UAT-15 together are the whole system.** If the counter resets when
> three of four machines are done, every PM interval is wrong from that day on — and
> nothing on any screen will tell you.

---

# Stage 9 — Train and go live  ·  1 day

### Print the SOP

`docs\TECHNICIAN_SOP_1PAGE.md` — one page, English and Tamil. Print it, laminate it,
put one at every cell.

### Train the technicians — 30 minutes, standing at a machine

Not in a meeting room. At a machine.

1. Scan a sticker. Look at the screen. Read the hours counter.
2. Start a PM. Work through the checklist. Submit it.
3. Report a breakdown.
4. **Explain the name dropdown.** Say it plainly: *this is the only record of who
   did the work. Pick the wrong name and someone else gets asked about your job.*

### Train the supervisors — 1 hour

- The `My Allotted PM List` view, and how rows disappear as work gets done
- The daily digest, and what to act on first
- The planning page in Power BI, and the monthly plan
- Approving spare requests

### Go live

**On a Monday.** Not a Friday. The first week produces questions and you want a full
week to answer them.

**Run the first monthly upload with someone watching.** It has the most moving parts
and it is the step nobody will remember in a year.

---

# After go-live — the routine

| When | What | Who |
|---|---|---|
| **Every Monday** | **Check the "system healthy" email arrived.** No email = the flows have stopped | Supervisor |
| Every day | Act on the digest. Deal with **reset failures** first | Supervisor |
| 1st–3rd | Upload the hours file. Check the summary email | Planner |
| 5th | Review cells at 90%+. Agree PM dates with production | Supervisor |
| **25th** | **Freeze next month's plan** | Supervisor |
| Monthly | Review every skipped machine and why | Manager |
| Monthly | Check `Breakdowns After PM` — **is the PM actually working?** | Manager |
| Each December | Mark next year's holidays in `Plant_Calendar` | Planner |

---

# The one thing to get right

The 11 flows will be owned by **one person's account**. There is no service account
available, and that is fine — but you need to know what it means.

A flow has two things attached: who can **edit** it, and the **connections** it uses
to reach SharePoint, Outlook and Teams. Those connections belong to the single
account that created them.

**If that account is ever disabled or loses its licence, every connection breaks and
all 11 flows stop.** Adding co-owners lets someone else go in and repair them — it
does not stop them breaking.

So the real question is: *how long before anyone notices?*

### The answer is the Monday email

The daily digest only sends when there is something to act on — otherwise people
stop reading it. But that makes silence mean two things: "nothing wrong" or
"everything died three weeks ago".

So it also sends **every Monday, even when everything is fine**, saying
*"PM system healthy — nothing outstanding."*

> ## If no email arrives on a Monday, the flows have stopped.
>
> Tell whoever watches the system this one sentence. It is the entire early warning,
> and it costs one email a week.

### And do these three while building

1. **Two co-owners on every flow** — Flow → Share
2. **Failure alerts to a shared mailbox** — not one person's inbox
3. **Export a backup after testing** — Power Automate → Export → Package (.zip),
   keep it with the project folder

If the owning person is ever leaving, hand the flows over **before** their last day.
Once the licence is gone the connections are already broken.
`ASSUMPTIONS.md` §8.2 has the full procedure — about half a day.

---

# Quick reference — every command

```
# Stage 1 — check and prepare the data
python tools/prepare_sharepoint_data.py --strict

# Stage 2 — build the site  (practice run first, always)
cd sharepoint
.\provision_lists.ps1 -SiteUrl "<your site>" -WhatIf
.\provision_lists.ps1 -SiteUrl "<your site>"
.\apply_views.ps1     -SiteUrl "<your site>" -WhatIf
.\apply_views.ps1     -SiteUrl "<your site>"

# Stage 3 — load the data
.\load_data.ps1       -SiteUrl "<your site>" -WhatIf
.\load_data.ps1       -SiteUrl "<your site>"

# Stage 5 — QR stickers  (must say 30 passed, 0 failed)
python qr/generate_qr_labels.py --base-url "<your site>" --test

# Any time — check the whole system is still sound
python tools/validate_model.py
python tools/verify_measures.py
```

---

# If something breaks

| What you see | What it means | What to do |
|---|---|---|
| **No Monday email** | **The flows have stopped** | Power Automate → My flows → look for a switched-off flow or an "Invalid connection" warning |
| Counter did not reset after all machines done | Flow 5 failed, or one task is still `Pending` | Open Flow 5 → run history → read the error |
| Two work orders for the same cell | Flow 2 is missing its "is one already open?" check | Cancel one, fix the condition |
| Monthly upload rejected | That month is already loaded | Check `StdHours_Monthly` for existing rows |
| Counter jumped a whole month after a mid-month PM | The hours were not split | Check `Reset_Date` is filled in and falls inside the uploaded month |
| Import fails, naming a month | `Plant_Calendar` has no working days for it | Add the dates and mark working days |
| Sticker opens a blank page | The link points at a renamed view | Re-run `apply_views.ps1`, update `QR_Payload_URL`, reprint |
| Dashboard columns blank after switching to SharePoint | Mangled column names (see Stage 2) | Recreate those columns using the script |
| Flow fails "cannot convert null" | A blank number in a calculation | Wrap it: `float(coalesce(x, 0))` |

---

## Where to go for more detail

| Question | Read |
|---|---|
| Exact technical steps | `IMPLEMENTATION_RUNBOOK.md` |
| Why something was built that way | `ASSUMPTIONS.md` |
| How to build a specific flow | `automate/FLOW_SPECS.md` |
| A formula to paste into a flow | `automate/expressions.md` |
| Power BI: opening, refreshing, repointing | `powerbi/README_PowerBI.md` |
| QR stickers: printing, reprinting | `qr/README_QR.md` |
| The full picture for whoever takes over | `HANDOVER.md` |
