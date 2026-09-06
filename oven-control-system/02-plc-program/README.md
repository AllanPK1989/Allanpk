# FX5U PLC program — OVN-2026-01 oven control

MELSEC iQ-F **FX5U-32MT/ES**, programmed in Structured Text, eight program
blocks. Written against schematic **OVN-2026-01 Rev 2** — the I/O allocation
here and on sheet 13 come from the same source file.

## Status

**97 of 97 behavioural tests pass.** `python3 test/test_logic.py`

Every specified behaviour is covered: the door interlock and its auto-restart,
the no-restart-after-stop rule, the heater anti-chatter and permissive
override, the heat-up watchdog (including that normal PID cycling never trips
it), both door-signal watchdogs, chatter not inflating the counters, the six
slot timers, the early-reset password rule and the malpractice figure, resume
after a power failure, manual test guards, alarm handling and welded-contactor
detection.

## What is here

| Path | What it is |
|------|-----------|
| `st/*.st` | **The program.** Eight ST program blocks, P00–P07. |
| `labels/global_labels.csv` | Global label list for GX Works3 import (143 labels). |
| `labels/make_labels.py` | Generates the CSV **and checks it** — see below. |
| `labels/device_comments_xy.csv` | X/Y device comments. |
| `test/sim.py` | Behavioural model of the program (a test harness, not the deliverable). |
| `test/test_logic.py` | The 97 tests. |
| `docs/functional-description.md` | What it does and why, section by section. |
| `docs/device-map.md` | Full device allocation, generated. |
| `docs/cpu-parameters.md` | Latch ranges, Ethernet, SD logging, execution order. |
| `docs/event-codes.md` | SD log event codes, including the traceability record. |
| `docs/commissioning-test-plan.md` | Signed-off site test sheet. |

### The label checker

`make_labels.py` is not just a generator. It fails the build if:

- a label used in the ST is not declared,
- two labels collide on one device (bar the documented alarm-block overlay),
- latched data sits outside the latch range, or non-latched data sits inside it.

Run it after any change:

```bash
cd labels && python3 make_labels.py     # exit 0 = clean
```

## Building the project in GX Works3

1. New project → Series **FX5CPU**, Type **FX5U**, Language **ST**.
2. `Navigation → Label → Global Label` → import `labels/global_labels.csv`.
   *If the column order is rejected, export the empty template from your
   GX Works3 first and match its columns — the layout varies by version.*
3. Create eight ST program blocks named `P00_Common` … `P07_Indication` and
   paste each `.st` file in.
4. Declare the local label `i` (Word [Signed]) in P05, P06 and P07.
5. Register the blocks to the **Scan** program **in numerical order** — the
   order is load-bearing, see `docs/cpu-parameters.md` §6.
6. Set the latch ranges, Ethernet and logging per `docs/cpu-parameters.md`.
7. Import `labels/device_comments_xy.csv` as device comments.
8. Build, download, run the commissioning plan.

## Why ST and not ladder

The arithmetic here — six 32-bit retentive timers, five counters, the
reconciliation expression, the event log — is genuinely worse in ladder. ST
keeps it readable and reviewable, and GX Works3 compiles it natively.

If your maintenance standard requires ladder for the binary interlock logic,
say so: P02 (door), P03 (blowers) and P04 (heater output) convert to roughly
30 rungs cleanly, and GX Works3 happily mixes languages in one project. I did
not produce both by default because two implementations of the same logic is
two things to keep in step.

## Decisions worth knowing

- **Run requests are not latched.** The supply being restored never restarts a
  blower on its own — IEC 60204-1 on unexpected start-up. Slot timers *are*
  latched, so a cure resumes.
- **X5 is filtered three different ways** for its three different jobs. See
  the functional description; without it, a bouncing switch would hammer the
  contactors and inflate the counters.
- **Early reset does not count as an unload.** That asymmetry is what makes
  `gLotsUnaccounted` a real number rather than an accounting identity.
- **Two safety options are built but disabled** so the delivered behaviour is
  exactly as specified — `gSetHtrNeedsAir` (M4020) and `gSetSlotGated` (M4021).
  Both are tested. See the functional description §7.
