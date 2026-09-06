# Oven Control System — Heater + 2 Blowers, FX5U PLC & GT2107 HMI

Retrofit of an electric batch oven: an 18 kW heater bank and two recirculation
blowers, previously switched by hardwired push-buttons and a stand-alone
temperature controller, are brought under a Mitsubishi MELSEC iQ-F FX5U PLC with
a GOT2000 GT2107 HMI.

## Deliverables

| # | Deliverable | Status | Location |
|---|-------------|--------|----------|
| 1 | Electrical schematic diagram (13 A3 sheets) | **Delivered** | `01-electrical-schematic/` |
| 2 | FX5U PLC program (GX Works3) | Not started | `02-plc-program/` |
| 3 | GT2107 HMI project (GT Designer3) | Not started | `03-hmi-program/` |

## 1. Electrical schematic

* `OVN-2026-01_Oven-Control-Panel_Electrical-Schematic.pdf` — the drawing set, 13 A3 sheets.
* `svg/sheet-NN.svg` — one editable SVG per sheet.
* `eplan.py` — IEC 60617 symbol/drawing library (mm units, A3 frame, title block).
* `data.py` — single source of truth for the I/O allocation, terminal schedule and BOM.
  Sheets 06, 07, 12 and 13 are all generated from it, so they cannot drift apart.
* `sheets_a.py` / `sheets_b.py` / `sheets_c.py` — sheet definitions.
* `build.py` — regenerates every SVG. `make_pdf.py` — assembles the PDF.

Regenerate after any edit:

```bash
cd 01-electrical-schematic
python3 build.py && python3 make_pdf.py
```

Requires `cairosvg` and `pypdf`.

### Sheet index

| Sheet | Title |
|-------|-------|
| 01 | Cover sheet, drawing index & legend |
| 02 | Single line diagram — power distribution |
| 03 | Power circuit — blower motors -M1 / -M2 |
| 04 | Power circuit — heater bank -E1/-E2/-E3 |
| 05 | Control supply, E-stop & 24 V DC distribution |
| 06 | PLC -A1: CPU supply & digital inputs X0–X17 |
| 07 | PLC -A1: digital outputs Y0–Y17 |
| 08 | Contactor coil circuits & door-interlock provision |
| 09 | Temperature controller & over-temperature protection |
| 10 | HMI -A3, Ethernet network & panel door arrangement |
| 11 | Panel general arrangement & gland plate |
| 12 | Terminal strip schedule -X1 / -X2 |
| 13 | I/O schedule & bill of materials |

## 2. Design basis (as agreed)

| Item | Decision |
|------|----------|
| Supply | 415 V AC, 3-ph + N + PE, 50 Hz, TN-S, 10 kA |
| Heater | 3 × 6 kW = 18 kW, star, 25 A/ph, switched by **contactor -K3 only** (no SSR) |
| Blowers | 2 × 1.5 kW, 415 V 3-ph, DOL, 3.5 A FLC |
| Heater command | PID controller -A2 relay output → volt-free contact → PLC X6 → Y2 → -KA3 → -K3 |
| Door interlock | Position switch -B1 → PLC input X5 **only** (software stop of blowers) |
| Over-temperature | Independent high-limit thermostat -B3, **hardwired** in the -K3 coil circuit |
| PLC | FX5U-32MT/ES — 16 DI (all used), 16 DO (10 used, 6 spare), transistor sink |
| HMI | GT2107-WTBD, 7", 24 V DC, Ethernet to the FX5U built-in port |
| Control supply | 230 V AC ex 500 VA transformer -T1; 24 V DC ex 5 A SMPS -G1 |

### Points worth knowing about the chosen door interlock

The door switch was specified to go to a PLC input only, so the blowers are
stopped by the program rather than by hardware. Two consequences are designed
around rather than argued about:

* A PLC fault could leave the blowers running with the door open. Terminals
  **-X1:60 / -X1:61** carry a wire link **-LK1** in the blower coil circuit
  (sheet 08). Removing the link and landing the NC contact of a second,
  safety-rated door switch converts the design to a hardwired interlock with no
  other panel change.
* The heater deliberately stays energised with the door open, as required by the
  process. The only protection limiting oven temperature in that condition is
  the high-limit thermostat -B3, which is hardwired and manual-reset. It must be
  function-tested at every planned maintenance, and a "HOT SURFACES — HEATER
  LIVE" label fitted at the door.

## 3. Control functions to be implemented in the PLC

1. Blower 1 / Blower 2 start–stop from panel push-buttons and from the HMI.
2. Door interlock: blowers stop while the door is open, heater stays ON, blowers
   restart automatically when the door closes.
3. Heater contactor follows the PID demand contact, gated by permissives
   (E-stop, overloads, high-limit, no contactor fault), with anti-chatter
   minimum-on/minimum-off timers to protect -K3.
4. Heat-up watchdog: demand ON continuously beyond a preset time without
   reaching set point → "FAILURE TO REACH SETPOINT" alarm (warning only; -B3 is
   the real protection).
5. Six retentive 2-hour slot timers. A started timer runs to 02:00:00 and can
   only then be reset; an earlier reset requires the maintenance password.
6. Separate, resettable door-open and door-close counters.
7. Lots loaded / lots unloaded counters derived from slot-timer start and reset
   events, with a mismatch indication to expose malpractice.
8. Password-protected manual test of blowers and heater.

## 4. Open items before the PLC and HMI programs are built

These do not block the schematic but do change the program:

1. **Slot-timer semantics.** Does "start" mean an operator presses a Start button
   for that slot on the HMI, or is loading detected by a sensor? Current
   assumption: HMI button per slot.
2. **Retentive behaviour across power failure.** Assumption: a running slot timer
   keeps its accumulated value and resumes on power-up (latched devices), rather
   than restarting from zero or being abandoned.
3. **Lot counting rule.** Assumption: lots loaded increments on every timer start;
   lots unloaded increments only on a *normal* reset at 2 h. A password reset
   before 2 h increments a separate "early reset" counter and does **not** count
   as an unload — this is what makes the malpractice visible.
4. **Passwords.** How many levels and who holds them. Current design: level 1
   supervisor, level 2 maintenance technician.
5. **Heat-up watchdog default.** Assumed 60 min, adjustable 10–240 min on the HMI.
6. **Manual test limits.** Assumption: manual test is inhibited unless the oven
   door is closed and no overload is tripped, and it self-cancels after 5 min.
7. **Data logging.** Whether the timer/counter history has to be exportable to
   USB, and for how long it must be retained.
