# Bill of Materials

**Status: budgetary scope list, not a purchasing BOM.**

No part numbers and no prices appear here. Nothing in this project has been quoted, no
supplier has been approached, and the eleven open items in `01-process-flow.md` §5 change
what gets bought. A BOM carrying invented manufacturer part numbers would look
procurement-ready while being fiction — the same reasoning `animation/README.md` gives
for keeping invented cycle times out of the customer video.

What this **is**: every item the process needs, with the specification fields a supplier
will ask you to fill in.

**Configuration assumed:** option 2 from `01-process-flow.md` §3.1 — large barrel kept,
cobot replaced by a fixed drum tipper — and sidewall belt for CV-01 per §3.2. Change
either decision and the affected lines are marked.

---

## 1. Process equipment

| Item | Tag | Qty | Specification | Spec status |
|---|---|---|---|---|
| Pan mixer | MX-01 | 1 | Ø1.24 m pan, 0.56 m working depth, charge rim +1.52 m, bottom discharge +0.55 m | drive kW, mix time **[VERIFY]** |
| Vacuum transfer unit | VT-01 | 1 | Opening station → mixer, lift 1.52 m, cartridge filter with reverse-jet clean | throughput, run length **[VERIFY]**; viability depends on moisture |
| Bag opening station | MT-01 | 1 | Slitting table with integral LEV hood, bag compactor | capture velocity **[VERIFY]** |
| Sidewall belt conveyor | CV-01 | 1 | 4.845 m at 43.75°, 0.50 m belt, corrugated sidewall + cleats, fully covered | capacity t/h **[VERIFY]**. *Deleted if bucket elevator chosen* |
| Storage hopper | HP-01 | 1 | Ø1.70 × 1.15 m body + 0.75 m cone to Ø0.40, 3.343 m³, 4 legs to +1.95 m | material/finish, cone angle review **[VERIFY]** |
| Slide gate valve | HP-01-V1 | 1 | Ø0.40 outlet, pneumatic, at +1.83 m spout | fail position **[VERIFY]** |
| Drum tipper | TP-01 | 1 | Floor mounted at FL-01, lift and invert to +1.95 m, 1000 kg rated | *Only if §3.1 option 2. Replaced by cobot if barrel shrunk* |
| Filling machine | FL-01 | — | **Existing** — infeed rim +1.95 m | acceptance rate **[VERIFY]** |
| Goods lift | LI-01 | — | **Existing** — 4.20 m travel, car 1.90 × 1.90 × 2.10 m | rated load, goods duty **[VERIFY]** |

## 2. Mobile robotics

| Item | Tag | Qty | Specification | Spec status |
|---|---|---|---|---|
| AMR | AMR-01 | **[VERIFY]** | Deck +0.57 m, 2.60 m aisle, lift-capable, fleet manager | **payload blocked on §3.1** |
| Barrel | BR-01… | **[VERIFY]** | Ø0.84 × 1.05 m, 0.582 m³ | **size blocked on §3.1** |
| Cobot | RB-01 | 0 or 1 | 1.70 m reach, deck mounted | **Deleted in the assumed configuration.** 25–30 kg payload if barrel is shrunk |
| Barrel gripper | RB-01-EOAT | 0 or 1 | Rim or body clamp | Only with cobot |

Fleet size cannot be calculated: it needs throughput and travel times, neither of which
is known.

## 3. Instrumentation

| Item | Tag | Qty | Specification |
|---|---|---|---|
| Level switch, high | LSH-01 | 1 | HP-01 at +3.62 m, rotary paddle or vibrating fork |
| Level switch, low | LSL-01 | 1 | HP-01 at +2.85 m, same type |
| Load cells | WI-01 | 3 or 4 | Barrel fill by weight — **[VERIFY]** weight vs level control first |
| Mixer door proximity | ZS-01 | 2 | Open / closed proving on MX-01 discharge |
| Conveyor speed / underspeed | SI-01 | 1 | Belt slip detection on CV-01 |
| Belt misalignment switch | ZS-02 | 2 | CV-01, one per side |
| Blocked chute detector | LSH-02 | 1 | MX-01 → CV-01 transfer |
| RCS air monitoring | — | **[VERIFY]** | Personal sampling at MT-01 — occupational hygiene scope |

## 4. Controls

| Item | Tag | Qty | Specification |
|---|---|---|---|
| Cell PLC | PLC-01 | 1 | Safety-rated CPU, I/O per `04-io-list.md` |
| HMI | HMI-01 | 1 | Local at mixing area |
| Safety relay / safety PLC | SR-01 | 1 | E-stop, guard and interlock circuits |
| VFD | VFD-01 | 1 | CV-01 drive |
| VFD | VFD-02 | 1 | MX-01 drive — **[VERIFY]** if mixer is fixed-speed |
| Network switch | NS-01 | 1 | Industrial, cell network |
| AMR fleet manager interface | — | 1 | PLC ↔ fleet manager |
| MES interface | — | 1 | MO release — **[VERIFY]** protocol |
| Field cabling and containment | — | lot | Scope after I/O count is fixed |

## 5. Safety

| Item | Tag | Qty | Specification |
|---|---|---|---|
| E-stop stations | ES-01… | **[VERIFY]** | One per station minimum |
| Perimeter guarding, tipper | GD-01 | 1 lot | Around TP-01 — a 873 kg drum inversion is a crush and ejection hazard |
| Safety interlock switches | GS-01… | **[VERIFY]** | Guard doors |
| Area scanner / light curtain | SS-01 | **[VERIFY]** | Tipper approach |
| AMR aisle marking and signage | — | 1 lot | ISO 3691-4 |
| Lift landing interlocks | — | 2 | Existing — **[VERIFY]** compatibility with AMR calls |

## 6. Ventilation and environment

| Item | Tag | Qty | Specification |
|---|---|---|---|
| LEV system | LEV-01 | 1 | Serving MT-01 slitting hood; **mandatory**, RCS control |
| Ducting and dampers | — | 1 lot | Routing **[VERIFY]** |
| Filter unit | — | 1 | Cartridge, HEPA-grade final on RCS duty |
| Conveyor covers | — | 1 lot | CV-01 full length |
| Transfer point seals | — | 4 | MX-01→CV-01, CV-01→HP-01, HP-01→barrel, barrel→FL-01 |

LEV sizing needs capture velocity at the slitting point and duct routing, neither known.
This is a specialist LEV design, not a catalogue purchase.

## 7. Civil and structural

| Item | Qty | Specification |
|---|---|---|
| HP-01 foundation / slab check | 1 | ~11 kN per leg × 4 — **structural engineer required** |
| CV-01 support steel | 1 lot | 3 legs per model, heights 1.56 / 2.63 / 3.57 m |
| Floor levelling on AMR route | **[VERIFY]** | AMRs are sensitive to slope and joints |
| Aisle floor marking | 1 lot | 2.60 m route |

---

## Not included

Installation labour · commissioning · FAT/SAT · spares · training · software licences ·
decommissioning of superseded manual equipment · dust survey · structural design fees.

## Before this becomes a purchasing BOM

1. Resolve `01-process-flow.md` §5 — all eleven items.
2. Take the two blocking decisions in §3.1 and §3.2.
3. Measure the sand: bulk density, moisture, angle of repose, particle size.
4. Survey the building. Every dimension here is model geometry, not a site survey.
5. Get a structural verdict on the HP-01 slab loading.
6. Then approach suppliers — with the specification fields above filled in.
