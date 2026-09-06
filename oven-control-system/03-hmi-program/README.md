# GT2107 HMI project — OVN-2026-01 oven control

GOT2000 **GT2107-WTBD**, 7", 800 × 480, Ethernet to the FX5U.
Ten screens, 150 objects, 14 alarms.

## What is here

GT Designer3 projects are a binary format, so this is not a `.GTX` file. It is
everything needed to build one exactly, plus a rendered design you can approve
before anyone opens the software.

| Path | What it is |
|------|-----------|
| `OVN-2026-01_GT-Designer3-Build-Guide.pdf` | **How to build it** — 14 pages, a recipe per object type, exact dialogue fields, screen by screen |
| `OVN-2026-01_HMI-Screen-Design.pdf` | **All ten screens at true 800 × 480**, one per page |
| `screens/out/*.png` | The same screens as images, 2× for reviewing on a monitor |
| `screens/*.py` | The renderer. Every object registers itself as it is drawn, so the schedule below cannot drift from the design. |
| `docs/object-schedule.csv` | Every object: screen, type, device, action, role, notes |
| `docs/alarm-list.csv` | The 14 alarms, importable, with operator actions |
| `docs/device-crossref.csv` | Every PLC device the HMI touches, and where |
| `docs/got-configuration.md` | Project settings, comms, security, alarms, logging |
| `docs/hmi-test-plan.md` | Signed-off verification sheet |

Rebuild the design after any edit:

```bash
cd screens && python3 build.py
```

## The one thing to get right

**Do not implement the two roles with GOT security levels.** They are
hierarchical — a level-3 user inherits level 1 and 2. Maintenance and quality
must not inherit from each other, so the check lives in the PLC and the GOT
only collects the passcode.

The login switch does **two actions on one touch**: write the keypad value to
`D27`, then set `M829` (maintenance) or `M835` (quality). One touch means the
typed code exists for a single PLC scan and is cleared immediately after the
comparison. `docs/got-configuration.md` §3 has the detail.

Use the role bit (`M58` / `M60`) as the security condition on **every switch**
on a protected screen, not only on the screen call — a screen condition alone
can be bypassed by a direct screen-change command.

## Two records, not one

Worth being precise about, because it is easy to assume otherwise:

| Record | Lives on | Retrieved by |
|--------|----------|--------------|
| Alarm history | the GOT, battery-backed | EXPORT TO USB on B-1900 |
| 7-day event log — slot starts, **early resets**, logins, counter resets | the **SD card in the PLC** | removing the card, or GX Works3 |

The GOT does not read the PLC's SD card. B-1900 says so on the screen so that
nobody assumes the USB export is the traceability record. It is not.

## Design notes

The palette follows ISA-101: neutral grey for normal running, saturated colour
only for abnormal conditions. Green means "this motor is turning", not "good";
red is only ever an alarm. An operator glancing across from the oven should be
able to tell in about a second whether anything on screen is coloured.

Touch targets are 40 px minimum, mostly 54 px or more — comfortable with gloves.

`UNACCOUNTED LOTS` is given a red panel of its own on B-1200 and a tile on the
home screen. It is the number the whole traceability requirement exists to
produce, so it is not buried in a table.
