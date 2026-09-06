# Implementation guide — OVN-2026-01 oven control

How to turn the files in this folder into a running panel: the GX Works3
project, the GT Designer3 project, and the order to commission them in.

Written for someone who knows MELSOFT but has not seen this project before.
Follow it top to bottom. The steps marked **CRITICAL** are the ones that cause
silent, hard-to-diagnose faults if skipped.

---

# Part A — Before you start

## A.1 Software

| Tool | Version | For |
|------|---------|-----|
| **GX Works3** | 1.065T or later | FX5U-32MT/ES program |
| **GT Designer3 (GOT2000)**, part of GT Works3 | Version 1.170C or later | GT2107-WTBD screens |

Older GX Works3 releases do not carry the full FX5U parameter set. If your
release predates the versions above, check that `FX5U` appears in the New
Project dialogue before going further.

## A.2 What you have been given

```
oven-control-system/
├── 01-electrical-schematic/
│   └── OVN-2026-01_...Electrical-Schematic.pdf   13 A3 sheets, Rev 3
├── 02-plc-program/
│   ├── st/P00_Common.st … P07_Indication.st      the program, 8 blocks
│   ├── labels/global_labels.xlsx                 158 labels, paste into GX Works3
│   ├── labels/global_labels_PASTE.txt            same, tab-separated, no header
│   ├── labels/global_labels_GXW3.txt             same, UTF-16 for the importer
│   ├── labels/global_labels.csv                  same, for reading only
│   ├── labels/device_comments_xy.csv             X/Y comments
│   ├── docs/cpu-parameters.md                    every parameter to set
│   ├── docs/functional-description.md            what the program does and why
│   ├── docs/device-map.md                        full device allocation
│   ├── docs/event-codes.md                       SD log event codes
│   └── docs/commissioning-test-plan.md           site test sheet
└── 03-hmi-program/
    ├── OVN-2026-01_HMI-Screen-Design.pdf         10 screens at 800 × 480
    ├── screens/out/*.png                         the same, as images
    ├── docs/object-schedule.csv                  every object and its device
    ├── docs/alarm-list.csv                       14 alarms + operator actions
    ├── docs/device-crossref.csv                  64 devices, and where used
    ├── docs/got-configuration.md                 project settings
    └── docs/hmi-test-plan.md                     site test sheet
```

## A.3 Hardware to have on the bench

- FX5U-32MT/ES with an **SD memory card** fitted (NZ1MEM-2GBSD or similar)
- GT2107-WTBD with the **GT11-50BAT** battery fitted
- Ethernet switch or a crossover lead, and a USB lead for the GOT
- Laptop set to **192.168.3.10 / 255.255.255.0**

---

# Part B — GX Works3: building the PLC project

## B.1 Create the project

1. `Project → New`
2. Series **FX5CPU**, Type **FX5U**, Program Language **ST**
3. `OK`. GX Works3 creates a scan program called `MAIN`.
4. `Project → Save As` → `OVN-2026-01_PLC.gx3`

## B.2 Get the 158 global labels into the project

Four files are supplied for this. **Method 1 works everywhere — use it first.**

| File | For |
|------|-----|
| `global_labels.xlsx` | **Method 1**, clipboard paste. Excel workbook. |
| `global_labels_PASTE.txt` | **Method 1** without Excel. Tab-separated, no header. |
| `global_labels_GXW3.txt` | **Method 2**, the file importer. UTF-16 tab-delimited. |
| `global_labels.csv` | Reading and diffing only. **Do not import this one.** |

> If you import the plain `.csv` GX Works3 answers *"No imported information
> found in the file."* It is not a corrupt file and the columns are not wrong.
> MELSOFT's label importer only reads **UTF-16, tab-delimited** — the format
> its own export writes. A comma-delimited ASCII file parses to zero rows.

### Method 1 — paste into the grid (recommended)

Bypasses the importer completely. Under two minutes.

1. Navigation window → `Label → Global Label → Global1`
2. Open **`global_labels.xlsx`** (or `global_labels_PASTE.txt` in Notepad)
3. Select the **data rows only — not the header** — and copy
   - In Excel: click row 2, `Ctrl+Shift+End`, `Ctrl+C`
   - In Notepad: `Ctrl+A`, `Ctrl+C` (that file has no header)
4. In GX Works3, click the **Label Name cell of row 1** — the first editable
   cell, not the grey row-number column
5. `Ctrl+V`
6. Confirm **158 rows**, and that no cell is flagged red

The columns arrive in the grid's own order:
`Label Name`, `Data Type`, `Class`, `Assign (Device/Label)`, `Constant`, `Comment`

### Method 2 — the file importer

Only if you would rather not paste.

1. In the Global Label editor choose the import command
2. Select **`global_labels_GXW3.txt`** — the UTF-16 file, **not the .csv**
3. At *"Import the content of specified file"* click **Yes**
4. Confirm 158 rows

If this still reports nothing imported, your GX Works3 release wants a
slightly different column set. Export a blank template from the same dialogue,
send it over, and the file will be regenerated to match it exactly. Do not
spend time hand-editing — Method 1 is faster than diagnosing it.

### Check the paste landed properly

Spot-check three rows that exercise the awkward data types:

| Label | Data Type | Assign |
|-------|-----------|--------|
| `gTick100ms` | `Bit` | `M0` |
| `gSlotElapsed` | `Double Word [Signed](1..6)` | `D4000` |
| `gAlmBits` | `Bit(0..15)` | `M700` |

`gAlmBits` and `gAlmMem` are **arrays that deliberately overlay** the named
alarm labels at M700 and M720. Two names for one device is intended — the
array lets the summary loop in `P06_Alarms` stay short, and lets the GOT watch
the block as one alarm range. GX Works3 will not object.

## B.3 Create the eight program blocks

1. Navigation → `Program → Scan` → right-click → `Add New Data`
2. Type **Program Block**, Language **ST**, name it `P00_Common`
3. Repeat for all eight, using these names exactly:

   ```
   P00_Common      P01_Security    P02_Door        P03_Blowers
   P04_Heater      P05_SlotTimers  P06_Alarms      P07_Indication
   ```
4. Open each block and paste in the matching `.st` file, whole.
5. Delete the default `MAIN` block if your project created one — the eight
   blocks above replace it.

## B.4 Local labels — **CRITICAL**

Three blocks use a loop counter. Without it they will not compile.

| Program block | Label | Class | Data Type | Lines that need it |
|---------------|-------|-------|-----------|--------------------|
| `P05_SlotTimers` | `i` | VAR | Word [Signed] | 30 |
| `P06_Alarms` | `i` | VAR | Word [Signed] | 4 |
| `P07_Indication` | `i` | VAR | Word [Signed] | 11 |

Pick **Word [Signed]** from the Data Type dropdown — do not type `INT`.

A POU's local variables live in the label editor pane, not in the code, so
there is no `VAR ... END_VAR` block in the program body to paste. These three
rows are the only hand-typed labels in the whole project. Miss one and the
build reports *"Undefined label is used"* once for every line in that block
that touches the loop counter — 25 to 30 errors from a single missing row.

Open each block's **local label** editor (the pane above the ST code) and add
the row. No other block has local labels.

## B.5 Execution order — **CRITICAL**

Navigation → `Program → Scan`. Drag the blocks until the order reads:

```
1  P00_Common        5  P04_Heater
2  P01_Security      6  P05_SlotTimers
3  P02_Door          7  P06_Alarms
4  P03_Blowers       8  P07_Indication
```

This is not cosmetic. `P02_Door` produces the door interlock signal that
`P03_Blowers` consumes, and `P06_Alarms` compares outputs that `P03`/`P04`
have already resolved. Out of order, the blowers act on a stale door state and
the contactor feedback alarms chatter.

## B.6 Latch ranges — **CRITICAL**

`Parameter → FX5UCPU → CPU Parameter → Memory/Device Setting →
Device/Label Memory Area Setting → Device Setting`

| Device | Latch (1) start | Latch (1) end |
|--------|-----------------|---------------|
| **M** | **M4000** | **M4095** |
| **D** | **D4000** | **D4499** |

Skip this and everything appears to work on the bench — then the first power
cut wipes every cure timer, every counter and both passcodes, and the defaults
silently rewrite themselves. It is the worst failure mode in the project
because nothing announces it.

Everything outside those ranges is volatile **on purpose**: the blower run
requests must not survive a power cut, or a restored supply would restart a
motor on its own (IEC 60204-1).

## B.7 Ethernet

`Parameter → FX5UCPU → Module Parameter → Ethernet Port`

| Item | Value |
|------|-------|
| IP address | `192.168.3.250` |
| Subnet mask | `255.255.255.0` |
| Communication data code | Binary |

Then `External Device Configuration` → drag in a **MELSOFT Connection** and
leave its default port. That is what the GOT will connect to.

## B.8 Input response time

`CPU Parameter → Input Response Time` — leave every point at the **10 ms**
default.

Do not raise it. The door chatter detector has to see the real transitions on
X5; the program filters that input three different ways in software, one per
job. Raising the hardware filter masks the very fault the alarm exists to find.

## B.9 Data logging to the SD card

`Tool → Logging Function` (the exact menu name varies slightly by release).

| Item | Value |
|------|-------|
| Logging type | Trigger logging |
| Trigger | device `M59` (`gEventPulse`), rising edge |
| Sampled devices | `D12`, `D13`, `D14` |
| Time stamp | enabled |
| Format | CSV |
| Storage | SD card |
| File switching | by date, one file per day |
| Saved files | **8** (7 days plus today) |

This is the traceability record — every slot start, every early reset with the
minutes it was cut short, every login, every counter reset. See
`02-plc-program/docs/event-codes.md`.

## B.10 Device comments

`Navigation → Device → Device Comment → Global Comment`, then import
`labels/device_comments_xy.csv`. Optional, but it makes monitoring the I/O
readable.

## B.11 Build

`Convert → Rebuild All`.

Expect **0 errors**. If you get type errors on arithmetic lines, your GX
Works3 release wants typed literals — the code already uses `DINT#1`,
`DINT#60` and so on for exactly this reason, so a failure here means something
was pasted incompletely. Re-paste the whole file.

## B.12 Download and first run

1. Connect over Ethernet, `Online → Write to PLC`
2. Select **Program**, **Parameter**, **Global Label** and **Device Comment**
3. Write, then power-cycle the CPU
4. `Online → Set Clock` — the clock stamps every log entry
5. Put the CPU in **RUN**

## B.13 Prove the first run — **CRITICAL**

On the very first RUN the program writes its defaults into the latched area,
then sets `M4022` so it never does so again. Check it took:

| Device | Should read | Meaning |
|--------|-------------|---------|
| `M4022` | ON | defaults written |
| `D4100` | 60 | heat-up watchdog, min |
| `D4101` | 600 | door watchdog, s |
| `D4108` | 7200 | cure time, s |
| `D4110` | **2468** | maintenance passcode |
| `D4111` | **1357** | quality passcode |
| `M4021` | ON | cure timers pause on a fault |
| `M4020` | OFF | heater airflow interlock, disabled |

Then power-cycle once more and check `D4110` still reads 2468. If it has gone
to 0, your latch range from B.6 did not take — go back and fix it before doing
anything else.

**Change both passcodes before handover** and issue them to the two teams
separately, in writing. Also set a project password:
`Project → Security → User Authentication`.

---

# Part C — GT Designer3: building the HMI project

## C.1 Create the project

1. `Project → New`
2. GOT Type: the **800 × 480 wide** GT21 group, Model **GT2107-WTBD**
3. Colour setting **65536 colours**
4. Controller: Manufacturer **MITSUBISHI ELECTRIC**, Controller Type
   **MELSEC iQ-F**, I/F **Ethernet**
5. Save as `OVN-2026-01_HMI.gtx`

## C.2 Communications

`Common → Controller Setting → CH1`

| Item | Value |
|------|-------|
| GOT IP | `192.168.3.18` |
| Subnet | `255.255.255.0` |
| PLC IP | `192.168.3.250` |
| Port | leave the driver default (usually 5562) unless it disagrees with the FX5U |

Leave the default port. Change it only if the GOT reports a connection error
and the FX5U's MELSOFT Connection entry shows something different.

## C.3 Build the common header and footer first

Every screen shares them, so build them once as a **template base screen** or a
**set overlay window** and reuse it. Doing this after the ten screens means
ten edits every time the navigation changes.

Header (y 0–56) and footer (y 424–480) are drawn on every page of
`OVN-2026-01_HMI-Screen-Design.pdf`. The footer's six tabs are HOME, SLOTS,
COUNTERS, ALARMS, HISTORY, LOGIN.

## C.4 Create the ten base screens

`Screen → New → Base Screen`, numbered exactly:

| No. | Title | Role |
|-----|-------|------|
| 1000 | Overview | – |
| 1100 | Cure slot timers | – |
| 1200 | Counters | – |
| 1300 | Alarms | – |
| 1400 | Manual test | MAINTENANCE |
| 1500 | Settings | MAINTENANCE |
| 1600 | Login | – |
| 1700 | Early reset | MAINTENANCE |
| 1800 | Counter reset | QUALITY |
| 1900 | Event history | – |

Startup screen: **1000**.

## C.5 Place the objects

Work from **`03-hmi-program/docs/object-schedule.csv`** with the matching page
of the screen-design PDF open beside it. The CSV has one row per object:

`Screen, Object type, Name, Device, Action, Role required, Notes`

151 objects across the ten screens. The PDF is drawn at the panel's true
800 × 480, so positions can be read straight off it.

Conventions that apply throughout:

- Every command bit (`M800`–`M835`) is **momentary**. The PLC clears each one
  after acting on it, so a latched bit would repeat the command.
- Manual-test buttons on 1400 are **momentary while touched** — never latched.
- Numeric inputs on 1500 get **range checking** per the range column shown on
  the screen. The PLC does not police these.
- **Confirm dialogue** on every destructive switch: all six early resets and
  both counter resets. Suggested text: *"This is recorded against your login.
  Continue?"*

## C.6 Security — **CRITICAL, and not the obvious way**

**Do not use GOT security levels for the two roles.** GOT levels are
hierarchical: a level-3 user automatically holds level-1 and level-2 rights.
Maintenance and quality must not inherit from each other — that inheritance is
exactly what the separation of duties exists to prevent — so the check lives in
the PLC and the GOT only collects the passcode.

**On screen 1600:**

1. A numeric input writes the typed code to `D27`, display format masked (`*`).
2. The **MAINTENANCE** button is one switch with **two actions on one touch**:
   - Word write: `D27` ← the keypad value
   - Bit set: `M829`
3. The **QUALITY** button is the same, setting `M835` instead.

One touch matters: the code then exists in `D27` for a single PLC scan, and the
PLC clears it the moment it has compared it.

**On the protected screens:** use `M58` (maintenance) or `M60` (quality) as the
security/display condition on **every switch on the screen**, not only on the
screen-change button. A screen condition on its own can be walked past with a
direct screen-change command.

Set an inactivity **screen return to 1000** of 5 minutes, to match the PLC's
auto-logout.

## C.7 Alarms

`Common → Alarm → Advanced User Alarm`

| Item | Value |
|------|-------|
| Observation | bit device block, **M700 – M713**, 14 points |
| Alarm text | import `docs/alarm-list.csv` |
| Detail text | the *Operator action* column |
| History | GOT internal memory, battery backed |
| History size | 512 records |

The ACCEPT switch on screen 1300 sets `M824`.

## C.8 History and USB export

The **EXPORT TO USB** button on screen 1900 exports **the GOT's own alarm
history**, using the standard alarm-history CSV output to the USB drive.

It does **not** export the PLC's 7-day event log. That log lives on the SD card
in the FX5U and comes out by pulling the card or reading it with GX Works3.
Screen 1900 says so on the face of it, deliberately, so nobody hands over a USB
stick believing it holds the traceability record.

## C.9 Panel settings

`Common → GOT Environmental Setting`

| Item | Value |
|------|-------|
| Backlight off | 30 min, wake on touch |
| Screen saver | none |
| Buzzer | on, touch feedback only |
| Utility call | **two-point** touch, top corners |
| Language | English |

Two-point utility call matters: a single-point call gets opened by accident by
someone leaning on the panel.

## C.10 Test offline, then download

1. `Tools → Simulator → Activate` with the GX Works3 simulator running. You can
   walk the whole navigation, the login flow and the alarm list without any
   hardware.
2. `Communication → Write to GOT`, over USB for the first download.
3. Fit the **GT11-50BAT** battery and set the GOT clock. Without the battery
   the alarm history and clock are lost at every power-down.

---

# Part D — Commissioning order

Do it in this sequence. Each stage depends on the one before.

| Stage | What | Sheet to sign |
|-------|------|---------------|
| 1 | Panel wiring against the schematic, **heater feeder isolated** | schematic Rev 3 |
| 2 | PLC I/O proving, blowers, door interlock, door watchdogs | PLC plan §1–3 |
| 3 | Counters and slot timers, with the cure time shortened | PLC plan §4 |
| 4 | **Restore the cure time to 7200 s** and the watchdog to 60 min | PLC plan §4.8, §5.8 |
| 5 | Heater, with the feeder now live, including the `-B3` trip | PLC plan §5 |
| 6 | Manual test and security | PLC plan §6–7 |
| 7 | HMI: comms, screens, roles, alarms, export | HMI plan §1–8 |
| 8 | Handover | both plans, final section |

Test plans:
`02-plc-program/docs/commissioning-test-plan.md`
`03-hmi-program/docs/hmi-test-plan.md`

The one test not to skip is **HMI plan §5**, the separation of duties: log in as
maintenance, cut a cure short, then try to clear the counter that recorded it.
It must be refused. That single sequence is the whole traceability requirement,
proved end to end.

---

# Part E — When it goes wrong

| Symptom | Cause | Fix |
|---------|-------|-----|
| *"No imported information found in the file"* | The plain `.csv` was imported. MELSOFT reads UTF-16 tab-delimited only | Paste from `global_labels.xlsx` instead, or import `global_labels_GXW3.txt` (B.2) |
| Import runs but cells are flagged red | Column set differs by GX Works3 release | Export a blank template and send it over; or just use the paste method (B.2) |
| Type errors on `+ DINT#1` lines | Block pasted incompletely | Re-paste the whole `.st` file |
| *"Undefined label is used"*, many errors, all in `P05_SlotTimers`, `P06_Alarms` or `P07_Indication` | The local label `i` is not declared in that POU. 30, 4 and 11 lines respectively use it, so one missing row makes dozens of errors | Add the one row per POU (B.4). Errors confined to these three blocks mean the global labels imported correctly |
| *"Undefined label is used"* in **every** POU including `P00_Common` | The global labels did not import | B.2 |
| Counters and timers zero after a power cut | Latch range not set | B.6, then re-prove with B.13 |
| Passcodes revert to 2468 / 1357 | Same cause — `M4022` is not latched | B.6 |
| Blowers hesitate or the feedback alarms chatter | Program blocks out of order | B.5 |
| Door chatter alarm never fires | Input response time raised above 10 ms | B.8 |
| GOT will not connect | IP, subnet, or no MELSOFT Connection in the FX5U | B.7, C.2 |
| A command repeats itself | An HMI switch is latched, not momentary | C.5 |
| Quality can reach the maintenance screens | GOT security levels used instead of the PLC bits | C.6 — rebuild that part |
| Cure timer not counting | Oven not fit to cure; `M62` is on | Expected. Clear the fault; see alarm 13 |

## Regenerating the drawings

Everything in this folder is generated. If a device rating changes, edit the
source and rebuild — do not edit the PDF.

```bash
cd 01-electrical-schematic && python3 build.py && python3 make_pdf.py
cd 02-plc-program/labels    && python3 make_labels.py     # also the checker
cd 02-plc-program           && python3 test/test_logic.py # 127 tests
cd 03-hmi-program/screens   && python3 build.py
```

`make_labels.py` is a checker as well as a generator: it fails if a label used
in the ST is undeclared, if two labels collide on a device, or if latched data
strays outside the latch range. Run it after any change to the program.

---

# Part F — Outstanding

Two items are still open and neither blocks the build.

1. **Motor and element nameplates.** The ratings on schematic sheets 02, 03 and
   04 assume 1.5 kW blowers at 3.5 A and 3 × 6 kW elements. Send the actual
   nameplates and the breaker, overload and cable sizes get corrected.
2. **`gSetHtrNeedsAir` (M4020)** is built, tested and **off**. Turning it on
   makes the heater require a blower running, or the door open. It is off
   because the specified door behaviour deliberately runs the heater with both
   blowers stopped. Running 18 kW of elements with no airflow and the door shut
   is the case it protects against. Decide before FAT — it is a one-bit change.

## Handover pack

- [ ] Both passcodes changed and issued separately, in writing
- [ ] `D4108` = 7200 and `D4100` = 60 confirmed after commissioning
- [ ] SD card fitted, one day's log read back
- [ ] GT11-50BAT fitted, both clocks set
- [ ] GX Works3 and GT Designer3 projects backed up and password-protected
- [ ] 'HOT SURFACES — HEATER LIVE' label fitted at the oven door
- [ ] `-B3` high-limit function test recorded and diarised for every PM
