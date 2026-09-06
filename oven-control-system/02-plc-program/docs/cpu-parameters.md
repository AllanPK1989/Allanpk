# CPU parameter settings — FX5U-32MT/ES

Set these in GX Works3 before downloading. The program will not behave correctly
without the latch ranges.

## 1. Latch ranges  — **mandatory**

`Navigation → Parameter → FX5UCPU → CPU Parameter → Memory/Device Setting →
Device/Label Memory Area Setting → Device Setting`

| Device | Latch (1) start | Latch (1) end | What lives there |
|--------|-----------------|---------------|------------------|
| M | **M4000** | **M4095** | slot running/complete flags, config options |
| D | **D4000** | **D4499** | slot elapsed seconds, all counters, all settings |

Everything else stays volatile on purpose. In particular the blower run
requests are **not** latched, so the supply being restored can never restart a
blower on its own (IEC 60204-1, unexpected start-up).

## 2. Digital input filter

`CPU Parameter → Input Response Time` — leave at the **10 ms** default.

Do not raise it. The door chatter detector needs to see the real transitions on
X5; the program does its own filtering in software, differently for each of the
three uses (interlock, counting, chatter). See `functional-description.md`.

## 3. Real-time clock

`Online → Set Clock` — set to local time at commissioning. The clock stamps
every event in the SD log. Check it at each planned maintenance; the CPU has no
battery for the RTC on all builds, so confirm on the actual unit supplied.

## 4. Ethernet

`Module Parameter → Ethernet Port`

| Item | Value |
|------|-------|
| IP address | 192.168.3.250 |
| Subnet mask | 255.255.255.0 |
| Communication data code | Binary |
| External device configuration | add one **MELSOFT Connection** for the GOT |

The GOT sits at 192.168.3.18. See schematic sheet 10.

## 5. Data logging to the SD card

`Tool → Logging Function → Logging Setting` (or the CPU's data-logging
configuration on your GX Works3 version).

| Item | Value |
|------|-------|
| Logging type | Trigger logging |
| Trigger condition | device `M59` (`gEventPulse`) rising edge |
| Sampled devices | `D12`, `D13`, `D14` (event code, param, value) |
| Time stamp | enabled |
| File format | CSV |
| Storage | SD card, `/LOGGING/` |
| File switching | by date, 1 file per day |
| Number of saved files | **8** (7 days plus today) |

Fit the SD card (NZ1MEM-2GBSD, BOM item 30) before the first RUN. With one file
per day and a few hundred events a day the card will never fill.

## 6. Program execution order

`Navigation → Program → Scan` — the eight program blocks must run in this
order. Order matters: P02 produces `gDoorOK` for P03, and P06 compares the
outputs P03/P04 have already resolved.

```
1  P00_Common
2  P01_Security
3  P02_Door
4  P03_Blowers
5  P04_Heater
6  P05_SlotTimers
7  P06_Alarms
8  P07_Indication
```

## 7. Local labels

Three POUs use a loop counter. Declare in each POU's **local label** list:

| POU | Label | Type |
|-----|-------|------|
| P05_SlotTimers | `i` | Word [Signed] |
| P06_Alarms | `i` | Word [Signed] |
| P07_Indication | `i` | Word [Signed] |

No other POU has local labels.
