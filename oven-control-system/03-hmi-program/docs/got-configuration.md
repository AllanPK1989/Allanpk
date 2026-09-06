# GT Designer3 project configuration — GT2107-WTBD

Reference: schematic OVN-2026-01 Rev 3 sheet 10, and the PLC device map in
`../../02-plc-program/docs/device-map.md`.

## 1. Project and controller

| Item | Value |
|------|-------|
| GOT type | **GT2107-WTBD**, 7", 800 × 480, 65536 colours |
| Colour setting | 65536 colours |
| Controller | MELSEC iQ-F, **FX5U** |
| Connection | **Ethernet**, MELSOFT connection |
| GOT IP | 192.168.3.18 |
| PLC IP | 192.168.3.250, port 5562 |
| Subnet | 255.255.255.0 |

The GOT is powered from `-F12` and is **not** interrupted by the emergency
stop, so alarms and cure timers stay readable during an E-stop.

## 2. Screens

| Screen | Title | Role required |
|--------|-------|---------------|
| B-1000 | Overview | – |
| B-1100 | Cure slot timers | – |
| B-1200 | Counters | – |
| B-1300 | Alarms | – |
| B-1400 | Manual test | MAINTENANCE |
| B-1500 | Settings | MAINTENANCE |
| B-1600 | Login | – |
| B-1700 | Early reset | MAINTENANCE |
| B-1800 | Counter reset | QUALITY |
| B-1900 | Event history | – |

Startup screen: **B-1000**. Header and footer are drawn on every screen — build
them once as a **set overlay window** or a template base screen so the
navigation stays identical everywhere.

## 3. Security — how the two roles are enforced

**Do not use GOT security levels for this.** GOT levels are hierarchical: a
level-3 user automatically gets level-1 and level-2 rights. Maintenance and
quality must *not* inherit from each other, so the check lives in the PLC.

The GOT's job is only to collect the passcode and show the right screens:

1. On **B-1600**, a numeric input writes the typed code to `D27`
   (`gHmiPasscodeEntry`), masked with `*`.
2. The **MAINTENANCE** and **QUALITY** buttons each use a switch with **two
   actions on one touch**: *word write* `D27` ← keypad value, then *bit set*
   `M829` or `M835`. One touch, so the code exists in `D27` for a single PLC
   scan.
3. The PLC compares, sets `M58` or `M60`, and **clears `D27` immediately**.
4. Screens B-1400/B-1500/B-1700 use `M58` as their display condition;
   B-1800 uses `M60`. Set the same bit as the *security* condition on every
   switch on those screens, not just on the screen call — a screen condition
   alone can be bypassed by a direct screen-change command.

Three wrong entries lock login out for `D4113` seconds; `M61` drives the
LOCKED OUT panel and `D26` counts it down.

Set an inactivity **screen return to B-1000** of 5 minutes to match the PLC's
auto-logout.

## 4. Alarms

Use **Advanced User Alarm**.

| Item | Value |
|------|-------|
| Observation | bit device block, **M700 – M713**, 14 points |
| Alarm text | import `alarm-list.csv` |
| History | store in GOT internal memory, battery backed |
| History size | 512 records (well over 7 days at this event rate) |
| Detail | show the *Operator action* column as the detail text |
| Accept | the ACCEPT switch on B-1300 sets `M824` (`gHmiAlarmAccept`) |

Fit the **GT11-50BAT** battery — without it the alarm history and the real-time
clock are lost on power-down.

## 5. Event history and USB export

Be clear about which record is which:

| Record | Where it lives | How to get it out |
|--------|----------------|-------------------|
| Alarm history | this GOT, battery-backed SRAM | **EXPORT TO USB** on B-1900 |
| 7-day event log — slot starts, early resets, logins, counter resets | **SD card in the FX5U** | remove the card, or read it with GX Works3 |

The GOT does **not** read the PLC's SD card. B-1900 says so on the screen, so
nobody assumes the USB export contains the traceability log — it does not.

## 6. Object conventions

- **Momentary** action on every command bit (`M800`–`M835`). The PLC clears
  each one after acting on it, so a stuck bit cannot repeat a command.
- **Confirm dialogue** on every destructive switch: all six early resets, both
  counter resets. Message: *"This is recorded against your login. Continue?"*
- **Numeric input range checking** on every settings field, per the range
  column on B-1500. Out-of-range entries must be rejected by the GOT — the PLC
  does not police them.
- Manual-test buttons on B-1400 are **momentary while touched**, never latched.

## 7. Panel behaviour

| Item | Value |
|------|-------|
| Backlight off | 30 min, wake on touch |
| Screen saver | none — the first touch after backlight-off must not press a button |
| Buzzer | on, for touch feedback only; the alarm hooter is `-B4`, driven by the PLC |
| Utility call | two-point touch on the top corners, so it is not reachable by accident |
| System language | English |

## 8. Design rationale

The palette follows **ISA-101**: a neutral grey field for normal operation,
with saturated colour reserved for things that are wrong. Green means "this
motor is turning", not "good"; red is only ever an alarm. That is why the home
screen is mostly grey — an operator glancing at it from the oven should be able
to tell in under a second whether anything is coloured.

Touch targets are 40 px minimum and mostly 54 px or more, which is comfortable
with gloves on a 7" panel.
