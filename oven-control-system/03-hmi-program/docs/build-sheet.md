# Copy-and-replace build sheet — GT Designer3

The ten screens contain 151 objects, but most of them are the same handful of
objects repeated six times. Build **one** of each, copy it, then change only
the device numbers. That turns the job into roughly 40 operations.

## The technique

1. Build the first instance completely — style, text, colours, trigger, everything.
2. Select the whole group and **copy-paste** it five times, positioning by the
   design PDF.
3. Retarget the copies. Two ways, both far faster than opening each dialogue:
   - **Data Browser** (`View → Docking Window → Data Browser`) lists every object
     on the screen with its device in a grid. Edit the device cells directly.
   - **Device replace** (`Search/Replace → Device Replace`), scoped to the
     selected objects, one substitution at a time.
4. Work down the substitution table for that screen. Tick each row.

> Do the copy **before** you set the triggers and gating, not after — a wrong
> trigger copied six times is six things to fix.

---

# Screen 1100 — cure slot tiles

Build the **SLOT 1** tile in full, then copy it five times.

One tile contains six objects:

| Object | Recipe | Device on slot 1 |
|--------|--------|------------------|
| State chip | R2 Word Lamp | `D70` |
| Elapsed hours | R7/R11 | `D40` |
| Elapsed minutes | R7/R11 | `D46` |
| Elapsed seconds | R7/R11 | `D52` |
| Progress bar | R10 Level | `D64` |
| Remaining minutes | R7 | `D58` |
| START switch | R3 Set | `M800` |
| RESET switch | R3 Set | `M810` |
| RESET enable condition | Operation Condition | `M4008` |

Then replace, per copy:

| Copy | State | Hours | Mins | Secs | Bar | Remain | START | RESET | RESET enable |
|---|---|---|---|---|---|---|---|---|---|
| **SLOT 2** | `D71` | `D41` | `D47` | `D53` | `D65` | `D59` | `M801` | `M811` | `M4009` |
| **SLOT 3** | `D72` | `D42` | `D48` | `D54` | `D66` | `D60` | `M802` | `M812` | `M4010` |
| **SLOT 4** | `D73` | `D43` | `D49` | `D55` | `D67` | `D61` | `M803` | `M813` | `M4011` |
| **SLOT 5** | `D74` | `D44` | `D50` | `D56` | `D68` | `D62` | `M804` | `M814` | `M4012` |
| **SLOT 6** | `D75` | `D45` | `D51` | `D57` | `D69` | `D63` | `M805` | `M815` | `M4013` |

Every device steps by exactly one per slot, so if a copy is out by one it will
be out by one on all six columns — easy to spot in the Data Browser grid.

---

# Screen 1000 — the six mini-tiles

Smaller: state chip, three-part time, progress bar. No switches.

| Copy | State | Hours | Mins | Secs | Bar |
|---|---|---|---|---|---|
| **SLOT 1** (build this one) | `D70` | `D40` | `D46` | `D52` | `D64` |
| **SLOT 2** | `D71` | `D41` | `D47` | `D53` | `D65` |
| **SLOT 3** | `D72` | `D42` | `D48` | `D54` | `D66` |
| **SLOT 4** | `D73` | `D43` | `D49` | `D55` | `D67` |
| **SLOT 5** | `D74` | `D44` | `D50` | `D56` | `D68` |
| **SLOT 6** | `D75` | `D45` | `D51` | `D57` | `D69` |

The rest of 1000 is built once each: four status lamps (`M32`, `M33`, `M35`,
`M10`), four switches (`M820`–`M823`), the PID lamp (`M11`), the door timer
(`D18`), and three summary cells (`D24` 32-bit, `D11`, and the alarm count).

---

# Screen 1700 — the six early-reset rows

One row: slot label, three-part elapsed time, remaining minutes, and an
EARLY RESET switch with a confirmation dialogue.

| Copy | Hours | Mins | Secs | Remain | EARLY RESET switch | Row visible when |
|---|---|---|---|---|---|---|
| **SLOT 1** (build this one) | `D40` | `D46` | `D52` | `D58` | `M810` | `D70` = 1 |
| **SLOT 2** | `D41` | `D47` | `D53` | `D59` | `M811` | `D71` = 1 |
| **SLOT 3** | `D42` | `D48` | `D54` | `D60` | `M812` | `D72` = 1 |
| **SLOT 4** | `D43` | `D49` | `D55` | `D61` | `M813` | `D73` = 1 |
| **SLOT 5** | `D44` | `D50` | `D56` | `D62` | `M814` | `D74` = 1 |
| **SLOT 6** | `D45` | `D51` | `D57` | `D63` | `M815` | `D75` = 1 |

The switch device is the **same** `M810`–`M815` used for the normal reset on
1100. The PLC decides which rule applies from whether the slot is complete, so
there is no second set of bits to wire.

Whole screen gated on `M58`. Confirmation dialogue on all six.

---

# Screen 1600 — the keypad

Twelve keys. Build **one** digit key, copy it eleven times, change only the
text and the value written.

All twelve write to the GOT's own numeric input buffer, not to a PLC device —
only the two login buttons touch the PLC. So the copies need no device change
at all, just the caption.

| Key | Caption |
|-----|---------|
| 1 | `1` |
| 2 | `2` |
| 3 | `3` |
| 4 | `4` |
| 5 | `5` |
| 6 | `6` |
| 7 | `7` |
| 8 | `8` |
| 9 | `9` |
| CLR | `CLR` |
| 0 | `0` |
| DEL | `DEL` |

---

# Screen 1500 — the nine settings rows

Build **one** row — label text, Numerical Input, unit text, range text — then
copy eight times and change the device, the range and the two texts.

| Row | Device | Range | Unit |
|---|---|---|---|
| Heat-up watchdog | `D4100` | 10 – 240 | min |
| Door watchdog | `D4101` | 60 – 1800 | s |
| Chatter transitions | `D4102` | 4 – 50 | — |
| Chatter window | `D4103` | 5 – 60 | s |
| Heater minimum ON | `D4104` | 5 – 120 | s |
| Heater minimum OFF | `D4105` | 5 – 120 | s |
| Manual test timeout | `D4106` | 60 – 900 | s |
| Auto-logout | `D4107` | 60 – 900 | s |
| Cure time | `D4108` | fixed 7200 | s |

`D4108` is **32-bit** (recipe R8). The other eight are 16-bit.

All nine gated on `M58`. Each also needs the `M831` activity ping as a second
action.

---

# Built once, not copied

Everything else is a one-off. Roughly forty objects in total:

| Screen | Objects |
|--------|---------|
| Header / footer template | 1 rectangle, 2 texts, 1 word lamp, date, time, 6 nav switches |
| 1200 Counters | 6 × 32-bit numerics, 3 × 16-bit, 1 alarm-driven panel, 1 gated switch, 3 recent-reset texts |
| 1300 Alarms | 1 alarm display, 1 accept switch, 1 nav switch, 1 count |
| 1400 Manual test | 3 momentary switches, 3 feedback lamps, 5 condition lamps, 1 numeric, 1 exit switch |
| 1600 Login | 1 masked input, 2 login buttons, 1 lockout lamp, 1 countdown, 1 logout switch |
| 1800 Counter reset | 5 numerics, 2 switches with dialogues |
| 1900 History | 1 history display, 1 USB export switch |

---

# Checking it afterwards

Open the **Data Browser** with all screens shown. It lists every object and its
device. Compare that against `device-crossref.csv`, which lists the same 64
devices and where each should appear.

The three things worth checking specifically, because they fail quietly:

| Check | Why |
|-------|-----|
| Every device in the 32-bit list is set to 32 bit | reads fine to 32767, then goes negative |
| `M800`–`M815` and `M820`–`M830` are **Set**, not Alternate or Momentary | a command could repeat or be missed |
| `M832`–`M834` are **Momentary** | otherwise a manual-test blower will not stop |

**32-bit devices:** `D24`, `D4000`–`D4011`, `D4020`, `D4022`, `D4024`, `D4026`,
`D4028`, `D4030`, `D4032`, `D4034`, `D4108`. Everything else is 16-bit.
