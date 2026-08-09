# Control I/O List

Signals implied by the process flow and interlocks. Counts are indicative — the final
list follows equipment selection, and two items are still blocked (see
`01-process-flow.md` §3).

Types: DI digital in · DO digital out · AI analogue in · AO analogue out · SAFE safety-rated

---

## MX-01 — Pan mixer

| Tag | Type | Signal | Notes |
|---|---|---|---|
| MX01-RUN | DO | Mixer run | Via VFD-02 if variable speed |
| MX01-RUNNING | DI | Running feedback | |
| MX01-FAULT | DI | Drive fault | |
| MX01-DOOR-OPEN | DO | Discharge door open | Pneumatic |
| MX01-ZSO | DI | Door proved open | Interlock with CV-01 running |
| MX01-ZSC | DI | Door proved closed | Permissive for charge |
| MX01-ESTOP | SAFE | E-stop | |

## VT-01 — Vacuum transfer

| Tag | Type | Signal | Notes |
|---|---|---|---|
| VT01-RUN | DO | Vacuum pump run | |
| VT01-RUNNING | DI | Running feedback | |
| VT01-VAC | AI | Vacuum level | Blockage / bridging detection |
| VT01-FILTER-DP | AI | Filter differential pressure | Clean-cycle trigger |
| VT01-JET | DO | Reverse-jet clean | |

## CV-01 — Inclined conveyor

| Tag | Type | Signal | Notes |
|---|---|---|---|
| CV01-RUN | DO | Run command | Via VFD-01 |
| CV01-SPEED-REF | AO | Speed reference | |
| CV01-RUNNING | DI | Running feedback | |
| CV01-FAULT | DI | Drive fault | |
| CV01-UNDERSPEED | DI | Belt slip / underspeed | **Critical at 43.75°** |
| CV01-MISALIGN-L | DI | Belt misalignment, left | |
| CV01-MISALIGN-R | DI | Belt misalignment, right | |
| CV01-PULLCORD | SAFE | Emergency pull cord | Full length |
| CV01-CHUTE-BLOCK | DI | Blocked chute at infeed | |

## HP-01 — Storage hopper

| Tag | Type | Signal | Notes |
|---|---|---|---|
| HP01-LSH | DI | Level high, +3.62 m | **Stops CV-01** |
| HP01-LSL | DI | Level low, +2.85 m | **Permits CV-01 start** |
| HP01-V1-OPEN | DO | Slide gate open | |
| HP01-V1-ZSO | DI | Gate proved open | |
| HP01-V1-ZSC | DI | Gate proved closed | |
| HP01-WI | AI | Barrel fill weight | **[VERIFY]** — only if weight control chosen |

## TP-01 — Drum tipper *(assumed configuration; deleted if cobot retained)*

| Tag | Type | Signal | Notes |
|---|---|---|---|
| TP01-RAISE | DO | Raise / invert | |
| TP01-LOWER | DO | Lower | |
| TP01-ZS-HOME | DI | At home position | |
| TP01-ZS-TIP | DI | At tip position | |
| TP01-CLAMP | DO | Drum clamp | |
| TP01-CLAMP-ZS | DI | Clamp proved | Interlock — must prove before raise |
| TP01-GUARD | SAFE | Guard door interlock | |
| TP01-SCANNER | SAFE | Area scanner | |
| TP01-ESTOP | SAFE | E-stop | |

## AMR-01 — via fleet manager, not hardwired

| Tag | Type | Signal | Notes |
|---|---|---|---|
| AMR-CALL-MIX | — | Call to mixing station | Fleet manager message |
| AMR-CALL-HOPPER | — | Call to hopper station | |
| AMR-CALL-FILL | — | Call to filler station | |
| AMR-ARRIVED | — | Docked and stationary | Permissive for fill / tip |
| AMR-RELEASE | — | Release to move | Only when gate closed and clamp released |
| AMR-BATTERY | — | State of charge | |
| LI01-CALL | — | Lift call | **[VERIFY]** interface to existing lift |
| LI01-READY | — | Lift at level, doors open | |

## LEV-01 — Ventilation

| Tag | Type | Signal | Notes |
|---|---|---|---|
| LEV01-RUN | DO | Fan run | |
| LEV01-RUNNING | DI | Running feedback | |
| LEV01-DP | AI | Hood differential pressure | Proves capture |
| LEV01-FAIL | DI | Airflow failure alarm | **Should inhibit MT-01 bag opening** |

## Cell-wide safety

| Tag | Type | Signal |
|---|---|---|
| CELL-ESTOP | SAFE | E-stop loop, all stations |
| CELL-RESET | DI | Safety reset |
| CELL-SAFE-OK | SAFE | Safety circuit healthy |
| CELL-BEACON | DO | Status beacon |
| CELL-HORN | DO | AMR movement warning |

---

## Indicative counts

| Type | Count |
|---|---|
| DI | ~26 |
| DO | ~15 |
| AI | ~5 |
| AO | ~1 |
| SAFE | ~7 |

Add 20 % spare capacity per type when sizing PLC-01. Counts exclude the cobot
configuration and anything downstream of an unresolved decision.

---

## Key interlocks

1. **CV-01 stops on HP01-LSH.** Non-negotiable — overfilling a 3.9 m hopper from a 43.75°
   conveyor backs material into the transfer chute.
2. **CV-01 must be running and proved before MX-01 discharge door opens.** Otherwise a
   full batch dumps onto a stationary belt.
3. **HP-01 gate cannot open unless AMR-ARRIVED is true** and, if weight control is used,
   the weigh system is zeroed.
4. **TP-01 cannot raise unless TP01-CLAMP-ZS is proved** and the guard is closed.
5. **AMR cannot be released while HP01-V1 is open or TP-01 is off home.**
6. **LEV01-FAIL inhibits bag opening at MT-01.** This is an occupational-health interlock,
   not a process one, and should not be defeatable from the HMI.
