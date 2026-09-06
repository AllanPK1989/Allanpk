# GT Designer3 build guide — OVN-2026-01

Screen-by-screen, object-by-object. Build alongside
`OVN-2026-01_HMI-Screen-Design.pdf`, which is drawn at the panel's true
800 × 480 so every position can be read straight off it.

Menu names move slightly between GT Works3 releases. Where that happens the
intent is stated as well as the name, so you can find the equivalent.

---

# Part 1 — Project creation

## 1.1 New project

`Project → New`

| Field | Value |
|-------|-------|
| Series | **GOT2000** |
| GOT Type | the **800 × 480 wide** GT21 group |
| Model | **GT2107-WTBD** |
| Colour Setting | **65536 Colors** |

Then the controller wizard:

| Field | Value |
|-------|-------|
| Manufacturer | **MITSUBISHI ELECTRIC** |
| Controller Type | **MELSEC iQ-F** |
| I/F | **Ethernet: Multiple** (or the single Ethernet driver, if offered) |
| Driver | **Ethernet(MITSUBISHI ELECTRIC), Q17nNC/CRnD-700** |

`Project → Save As` → `OVN-2026-01_HMI.gtx`

## 1.2 Ethernet

`Common → Controller Setting → CH1`

| Field | Value |
|-------|-------|
| GOT IP Address | `192.168.3.18` |
| Subnet Mask | `255.255.255.0` |
| GOT Port No. (Communication) | leave default |
| **Controller** — Net No. | `1` |
| Station No. | `1` |
| IP Address | `192.168.3.250` |
| Port No. | leave the driver default |

On the FX5U side there must be a **MELSOFT Connection** in
`Module Parameter → Ethernet Port → External Device Configuration`, or the GOT
will never connect no matter what is set here.

---

# Part 2 — Settings to make BEFORE you draw anything

Four settings that are painful to retrofit. Do them now.

## 2.1 Base screen switching device — **without this no navigation works**

`Common → GOT Environmental Setting → Screen Switching / Window`

| Field | Value |
|-------|-------|
| Base Screen | **`GD100`** |
| Overlap Window 1 | `GD101` |

Every "Go To Screen" switch writes the screen number into `GD100`. Leave it
blank and the switches appear to do nothing at all — the single most common
"my HMI is dead" call.

## 2.2 Startup screen

Same dialogue, or `Common → GOT Environmental Setting → Startup / Screen`:
set the startup base screen to **1000**.

## 2.3 Clock — take it from the PLC

`Common → GOT Environmental Setting → Time Setting`

Set the GOT to **adjust** its clock from the controller (CH1). The PLC stamps
every entry in the 7-day event log; if the two clocks disagree, the HMI alarm
history and the PLC log cannot be reconciled — which defeats the traceability.

## 2.4 Leave GOT security OFF

`Common → GOT Environmental Setting → Security`

Do **not** set up operator authentication or security levels. The two roles are
enforced by PLC bits — see Part 6. Turning on GOT security as well gives you two
competing mechanisms and a hierarchy you do not want.

## 2.5 Drawing aids

`View → Grid` on, 8 px, snap on. Every position in the design PDF is a multiple
of 2, most of 4.

---

# Part 3 — Object recipes

Build each object once, get it right, then copy-paste it. These recipes cover
all 151 objects in `object-schedule.csv`.

## R1 — Bit Lamp (status indicator)

`Object → Lamp → Bit Lamp`

| Tab | Field | Value |
|-----|-------|-------|
| Style | Lamp Type | Bit |
| | Device | e.g. `M32` |
| | Shape | Circle, or Rectangle for a chip |
| | OFF colour | `#AEB5BD` |
| | ON colour | `#1B7A4B` running, `#B25A16` heater, `#B5342A` alarm |
| Text | OFF text / ON text | e.g. `STOPPED` / `RUNNING` |

Two-state text on one object — you do not need two lamps.

## R2 — Word Lamp (three or more states)

`Object → Lamp → Word Lamp`

Used for the role chip and the slot state chip.

| Field | Value |
|-------|-------|
| Device | `D28` (role) or `D70`–`D75` (slot state) |
| Case count | 3 |
| Range 1 | `$W == 0` → text `OPERATOR` / `EMPTY`, grey |
| Range 2 | `$W == 1` → text `MAINTENANCE` / `CURING`, amber / green |
| Range 3 | `$W == 2` → text `QUALITY` / `COMPLETE`, blue |

`gSlotState` (D70–D75) exists purely so each slot tile is **one** object
instead of three overlapping bit lamps.

## R3 — Bit Switch, **Set** action — use for all command bits

`Object → Switch → Bit Switch`

| Tab | Field | Value |
|-----|-------|-------|
| Basic → Action | Device | e.g. `M800` |
| | Action | **Set** |
| Style | Shape / colours | per the design |
| Text | | e.g. `START` |

**Set, not Momentary.** The PLC clears every command bit after acting on it —
that handshake is written into the ST. A Set action cannot be missed by a short
tap; a momentary press shorter than one PLC scan could be.

Applies to: `M800`–`M815`, `M820`–`M830`, `M835`.

## R4 — Bit Switch, **Momentary** — manual test only

Identical to R3 but Action = **Momentary**.

Applies to `M832`, `M833`, `M834` only. Here the output must follow the finger:
release the button, the blower stops.

## R5 — Go To Screen Switch

`Object → Switch → Go To Screen Switch`

| Field | Value |
|-------|-------|
| Screen Type | Base |
| Screen No. | e.g. `1100` |

Requires 2.1 to be set.

## R6 — Two actions on one touch — the login buttons

This is the one non-obvious object in the project.

`Object → Switch → Bit Switch`, then in the **Action** list add **two** actions,
in this order:

| # | Action type | Settings |
|---|-------------|----------|
| 1 | **Word** | Device `D27`, Word Set, **Indirect** from the keypad input value |
| 2 | **Bit** | Device `M829` (maintenance) or `M835` (quality), **Set** |

Both fire on the same touch, so the passcode reaches `D27` and the request bit
goes on in the same instant. The PLC compares them and clears `D27` in that
scan. If you split these across two buttons the code sits in a register between
presses, which is exactly what we are avoiding.

If your release will not do an indirect word write from the numeric input,
use the simpler arrangement: a Numerical Input writing straight to `D27`
(recipe R9), and the login button doing action 2 only. Same result — the code
just lives in `D27` from the moment it is typed until the button is pressed.

## R7 — Numerical Display, 16-bit

`Object → Numerical Display / Input → Numerical Display`

| Field | Value |
|-------|-------|
| Device | e.g. `D19` |
| Data Type | **Signed BIN** |
| Data Size | **16 bit** |
| Display Format | Signed Decimal |
| Digits | as needed |

## R8 — Numerical Display, 32-bit — **get this right**

Same, but:

| Field | Value |
|-------|-------|
| Data Size | **32 bit** |
| Device | `D4020`, `D4022`, `D4024`, `D4026`, `D4028`, `D24` |

All the counters and `gLotsUnaccounted` are 32-bit. Set 16 bit by mistake and
they read correctly up to 32767, then go negative — which will not show up in
a short factory test.

**The 32-bit devices are:** `D24`, `D4000`–`D4011`, `D4020`, `D4022`, `D4024`,
`D4026`, `D4028`, `D4030`, `D4032`, `D4034`, `D4108`.
Everything else in the schedule is 16-bit.

## R9 — Numerical Input with range checking

`Object → Numerical Display / Input → Numerical Input`

| Tab | Field | Value |
|-----|-------|-------|
| Style | Device, Data Type, Size | as R7 |
| Extended | **Input Range** | tick, then enter the lower and upper limit |
| Extended | Operation Condition | ON, device `M58` (see Part 6) |

Ranges are printed on screen 1500 and repeat here:

| Setting | Device | Range |
|---------|--------|-------|
| Heat-up watchdog, min | `D4100` | 10 – 240 |
| Door watchdog, s | `D4101` | 60 – 1800 |
| Chatter transitions | `D4102` | 4 – 50 |
| Chatter window, s | `D4103` | 5 – 60 |
| Heater minimum ON, s | `D4104` | 5 – 120 |
| Heater minimum OFF, s | `D4105` | 5 – 120 |
| Manual test timeout, s | `D4106` | 60 – 900 |
| Auto-logout, s | `D4107` | 60 – 900 |

The PLC does **not** police these. If the GOT lets someone type 2 into the
heater minimum-ON, the contactor will chatter.

For the passcode fields on 1500, additionally set Display Format so the value
is masked, and set the Operation Condition to the role that owns it — `M58`
for the maintenance code, `M60` for the quality code.

## R10 — Level (progress bar)

`Object → Graph → Level`

| Field | Value |
|-------|-------|
| Device | `D64`–`D69` (`gSlotPct`) |
| Data Type | Signed BIN, 16 bit |
| Lower Limit | `0` |
| Upper Limit | `100` |
| Direction | Right |
| Fill colour | green curing, blue complete |

## R11 — Elapsed time as HH:MM:SS

There is no single time device — the PLC splits it for you:

| Part | Device |
|------|--------|
| Hours | `D40`–`D45` |
| Minutes | `D46`–`D51` |
| Seconds | `D52`–`D57` |

Place **three Numerical Displays** side by side with fixed `:` text between
them. Set each to **2 digits** with **leading zero fill** so it reads `01:14:22`
and not `1:14:22`.

## R12 — Date and time

`Object → Date/Time Display`. One date object, one time object, top right of
the header. Format `dd-mm-yyyy` and `hh:mm`.

## R13 — Advanced User Alarm display

First the observation, then the object.

**Common → Alarm → Advanced User Alarm Observation → new, No. 1**

| Field | Value |
|-------|-------|
| Alarm Points | **14** |
| Device | **`M700`**, consecutive |
| Detection | Rise (OFF → ON) |
| Comment Group | 1 |
| History | store to GOT internal memory |
| Number of stored | 512 |

**Comments — Common → Comment → Comment Group 1**, 14 comments, in this order:

| No. | Comment |
|-----|---------|
| 1 | EMERGENCY STOP OPERATED |
| 2 | BLOWER 1 OVERLOAD TRIPPED |
| 3 | BLOWER 2 OVERLOAD TRIPPED |
| 4 | HEATER OVERLOAD TRIPPED |
| 5 | HIGH-LIMIT THERMOSTAT TRIPPED |
| 6 | TEMPERATURE CONTROLLER ALARM / SENSOR BREAK |
| 7 | FAILURE TO REACH SETPOINT |
| 8 | DOOR SIGNAL PULSATING |
| 9 | NO DOOR CLOSED SIGNAL |
| 10 | BLOWER 1 CONTACTOR FEEDBACK FAULT |
| 11 | BLOWER 2 CONTACTOR FEEDBACK FAULT |
| 12 | HEATER CONTACTOR FEEDBACK FAULT |
| 13 | LOTS LOADED / UNLOADED MISMATCH |
| 14 | CURE TIMERS PAUSED - OVEN NOT FIT TO CURE |

Comment 1 is `M700`, comment 14 is `M713` — the order is the device order and
must not be rearranged. Use the *Operator action* column of `alarm-list.csv`
as the detail text.

> Comment import has the same encoding trap as the PLC labels. If the CSV
> import gives you nothing, open `alarm-list.csv` in Excel and paste the
> message column straight into the comment list instead.

**Then** `Object → Alarm Display → Advanced User Alarm Display` on screen 1300,
pointed at observation 1. Columns: occurrence time, comment, status.

## R14 — Alarm history on screen 1900

Same object type, set to show the **history** rather than the current list, with
date, time and comment columns.

## R15 — Role gating

See Part 6. It is two fields on every protected object.

## R16 — Confirmation dialogue

On any destructive switch, `Extended` tab → enable the confirmation /
simple dialog option, message:

> This is recorded against your login. Continue?

Apply to: all six early-reset switches on 1700, and both counter-reset switches
on 1800.

---

# Part 4 — The common header and footer

Build these **first**, on one screen, then reuse. Retrofitting them across ten
screens is an afternoon you do not need to spend.

Use a **base screen template**, or draw them on a screen and copy-paste the
group onto each new screen. If your release supports set overlay windows for
this, better still.

## Header, y 0 – 56

| Object | Type | Detail |
|--------|------|--------|
| Background | Rectangle | 0,0 → 800,56, fill `#2B323B`, no border |
| Project line | Text | `OVN-2026-01  OVEN CONTROL`, 13 px, `#9FB0C0` |
| Screen title | Text | per screen, 19 px bold, `#F3F5F7` |
| Role chip | **Word Lamp (R2)** | `D28`, 560,12 → 688,34 |
| "logged in" | Text | 10 px, under the chip |
| Time | **Date/Time (R12)** | right aligned at x 786 |

## Footer, y 424 – 480

Background rectangle `#2B323B`, then six **Go To Screen** switches (R5),
each about 130 px wide:

| Label | Screen |
|-------|--------|
| HOME | 1000 |
| SLOTS | 1100 |
| COUNTERS | 1200 |
| ALARMS | 1300 |
| HISTORY | 1900 |
| LOGIN | 1600 |

Highlight the active tab by giving that screen's copy a lighter fill.

---

# Part 5 — Screen by screen

Object counts are from `object-schedule.csv`. Positions from the design PDF.

## 1000 Overview — 24 objects

- Alarm banner: rectangle + **Bit Lamp (R1)** on `M49` (`gAnyAlarm`) as the
  display trigger; comment or text inside naming the top alarm
- Four status tiles: Bit Lamps (R1) on `M32`, `M33`, `M35`, `M10`
- Four switches (R3): `M820` `M821` `M822` `M823`
- PID demand: Bit Lamp on `M11`
- Door open elapsed: Numerical Display 16-bit (R7) on `D18`
- Six slot mini-tiles: Word Lamp (R2) on `D70`–`D75`, three-part time (R11),
  Level (R10) on `D64`–`D69`
- Three summary cells: 32-bit Numerical Display (R8) on `D24`, 16-bit on `D11`

## 1100 Cure slot timers — 14 objects

Six tiles, each: Word Lamp state chip, HH:MM:SS (R11), Level (R10), remaining
minutes (`D58`–`D63`), and one switch.

The **same switch device** serves start and reset per slot:

| Slot | Start | Reset |
|------|-------|-------|
| 1–6 | `M800`–`M805` | `M810`–`M815` |

Show the START switch when `gSlotState = 0` and the RESET switch when
`gSlotState = 2`, using the Trigger tab against `D70`+n. A curing slot shows a
greyed RESET — set its Operation Condition to `M4008`+n so it cannot be pressed.

Paused banner: Bit Lamp on `M62` (`gSlotTimersPaused`).

EARLY RESET button: Go To Screen 1700, gated on `M58` (Part 6).

## 1200 Counters — 20 objects

All six counters are **32-bit (R8)**: `D4020`, `D4022`, `D4024`, `D4026`,
`D4028`, and `D24` for unaccounted.

Run hours are 16-bit: `D19`, `D20`, `D21`.

The UNACCOUNTED panel: give the rectangle a Bit Lamp behaviour on `M712` so it
turns red only when non-zero. RESET COUNTERS button gated on `M60`.

## 1300 Alarms — 10 objects

Advanced User Alarm Display (R13), ACCEPT switch (R3) on `M824`, a Go To Screen
to 1900, and a count.

## 1400 Manual test — 17 objects

Three **Momentary** switches (R4) on `M832`–`M834`, three feedback Bit Lamps on
`M15`, `M16`, `M17`, five condition lamps, the timeout numeric on `D9`, and an
EXIT switch (R3) on `M828`.

Every object on this screen is gated on `M58`.

## 1500 Settings — 21 objects

Nine Numerical Inputs with ranges (R9), two option toggles — Bit Switches with
**Alternate** action on `M4021` and `M4020` — and the two passcode fields.

All gated on `M58`, except the quality passcode field which is gated on `M60`.

## 1600 Login — 15 objects

Numeric keypad, the masked entry on `D27`, the two login buttons (R6), the
lockout panel (Bit Lamp on `M61`, countdown on `D26`), and LOG OUT (R3) on
`M830`.

This screen is **not** gated — anyone must be able to reach it.

## 1700 Early reset — 10 objects

Six rows, each with elapsed time and an EARLY RESET switch (R3) on `M810`–`M815`
with a confirmation dialogue (R16). Whole screen gated on `M58`.

The same device as the normal reset: the PLC decides which rule applies from
whether the slot is complete. You do not need separate bits.

## 1800 Counter reset — 10 objects

Two switches (R3) on `M825` and `M826`, both with confirmation dialogues.
Whole screen gated on `M60`.

## 1900 Event history — 10 objects

Alarm history display (R14) and the USB export switch.

For the export, use `Object → Switch → Special Function Switch` set to the
alarm-history output / utility function that writes the history to the USB
drive. It touches no PLC device.

---

# Part 6 — Security, in detail

Two roles that must not inherit from each other. GOT security levels are
hierarchical, so they cannot express this. The PLC holds the truth:

| Bit | Meaning |
|-----|---------|
| `M58` | maintenance logged in |
| `M60` | quality logged in |

## On every object of a protected screen — two fields

| Tab | Field | Value |
|-----|-------|-------|
| Trigger | Trigger Type | **ON** |
| | Trigger Device | `M58` or `M60` |
| Extended | Operation Condition | **ON**, same device |

Trigger controls whether it is *drawn*. Operation Condition controls whether it
*responds*. Set both.

**Do this on every switch, not just on the screen-change button.** A screen
condition alone can be walked past by a direct screen-change command, and then
the buttons on that screen still work.

| Screen | Gate |
|--------|------|
| 1400, 1500, 1700 | `M58` |
| 1800 | `M60` |
| quality passcode field on 1500 | `M60` |

## The activity ping

`M831` (`gHmiActivity`) resets the PLC's 5-minute auto-logout. Add a second
action to each switch on 1400, 1500, 1700 and 1800:

| Action | Device | Type |
|--------|--------|------|
| Bit | `M831` | Set |

About fifteen switches. Without it, a technician part-way through a settings
change gets logged out under them.

---

# Part 7 — Test before you download

`Tools → Simulator → Activate`, with the GX Works3 simulator running.

You can walk the entire project with no hardware:

| Check | How |
|-------|-----|
| Navigation | every footer tab reaches the right screen |
| Login | type `2468`, press MAINTENANCE — role chip changes |
| `D27` cleared | watch `D27` in GX Works3: back to 0 immediately |
| Role separation | as QUALITY, 1400 / 1500 / 1700 must be unreachable |
| Lockout | three wrong codes → LOCKED OUT panel, `D26` counting down |
| 32-bit displays | force `D4024` to 40000; it must read 40000, not a negative |
| Slot tiles | force `D70` to 0, 1, 2 — chip text and colour must follow |
| Alarms | force `M700`–`M713` one at a time; check text and order |

The 32-bit check is worth the minute it takes. It is invisible until a counter
passes 32767, by which time the panel is in service.

## Download

`Communication → Write to GOT`, USB for the first transfer.

Then on the panel itself: fit the **GT11-50BAT**, and confirm the clock has
picked up from the PLC (Part 2.3).

---

# Part 8 — Mistakes that cost an afternoon

| Symptom | Cause |
|---------|-------|
| Navigation switches do nothing | Base screen switching device not set (2.1) |
| Counters go negative past 32767 | Numerical Display left at 16 bit (R8) |
| Quality can open the maintenance screens | GOT security levels used instead of `M58` / `M60` (Part 6) |
| Protected buttons still work after a direct screen change | Gate applied to the screen, not to each object (Part 6) |
| A command repeats itself | Command bit set to Alternate instead of Set (R3) |
| Manual test blower will not stop | `M832`–`M834` set to Set instead of Momentary (R4) |
| Passcode sits in `D27` after login | The two actions were split across two buttons (R6) |
| Alarm text on the wrong alarm | Comment group reordered — comment 1 is `M700` (R13) |
| Times read `1:4:2` | Leading-zero fill not set on the three numerics (R11) |
| Logged out mid-edit | `M831` activity ping not added (Part 6) |
| Time on the log does not match the HMI | GOT clock not adjusting from the PLC (2.3) |
