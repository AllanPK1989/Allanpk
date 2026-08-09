# Equipment Specification

Functional specification per item. Dimensions are from `layout.json` (read out of
`animation/lib/plant.js`) and are **representative model geometry, not a site survey**.
Every `[VERIFY]` is a field a supplier will ask for and that nobody has answered yet.

Read `01-process-flow.md` §3 first — two items below are affected by blocking findings.

---

## MX-01 — Pan mixer

| Parameter | Value | Provenance |
|---|---|---|
| Pan inside diameter | 1.24 m | model |
| Pan floor / top | +0.86 / +1.42 m | model |
| Charge rim height | **+1.52 m** | model |
| Working depth | 0.56 m | derived |
| Geometric pan volume | 0.676 m³ | derived |
| Batch at 60 % fill | ~608 kg | derived, at assumed 1500 kg/m³ |
| Discharge height | +0.55 m | model |
| Base plate | 1.15 × 1.15 m | model |
| Drive rating | **[VERIFY]** | — |
| Mix time | **[VERIFY]** | — |

Charge is over the open rim, not through a hatch. Discharge is a bottom door onto CV-01.

---

## VT-01 — Vacuum transfer, opening station → mixer

| Parameter | Value | Provenance |
|---|---|---|
| Lift height | 0 → +1.52 m | derived |
| Horizontal run | **[VERIFY]** — depends on where the opening station sits | — |
| Throughput | **[VERIFY]** — set by acceptable charge time | — |
| Filter | Cartridge, reverse-jet | assumed |

**Viability depends on moisture.** Above roughly 1–2 % free moisture, dense-phase vacuum
conveying of sand becomes unreliable and the receiver bridges. **[VERIFY]** before this
item is quoted.

---

## CV-01 — Inclined conveyor, mixer → storage hopper

| Parameter | Value | Provenance |
|---|---|---|
| From / to | (−0.70, +0.55) → (2.80, +3.90) | model |
| Length along incline | **4.845 m** | derived |
| Incline | **43.75°** | derived |
| Vertical lift | 3.35 m | derived |
| Trough width | 0.50 m | model |
| Type | **Sidewall / corrugated-wall belt** | selected — see §3.2 |
| Capacity | **[VERIFY]** — must clear one batch inside the mix cycle | — |
| Enclosure | Covered, full length | required for RCS control |

**A plain troughed belt will not work at this angle** (~18–20° ceiling for dry sand).
See `01-process-flow.md` §3.2 for the alternatives and why sidewall was chosen.

Interlocks: stop on HP-01 LSH made; permissive requires MX-01 discharge door open and
CV-01 running before mixer discharge.

---

## HP-01 — Sand storage hopper

| Parameter | Value | Provenance |
|---|---|---|
| Body | Ø1.70 m × 1.15 m, +2.70 → +3.85 | model |
| Cone | Ø1.70 → Ø0.40, +1.95 → +2.70 | model |
| Cone half-angle | ~23° from vertical | derived |
| Overall height | 3.90 m | model |
| Geometric volume | **3.343 m³** (2.610 body + 0.732 cone) | derived |
| Working mass at 85 % | **~4262 kg** | derived |
| Equivalent batches held | ~7 | derived |
| Discharge spout | +1.83 m | model |
| Level switches | LSH +3.62, LSL +2.85 | model |
| Legs | 4 off, 0.12 × 0.12, to +1.95 | model |

**Cone angle check.** A ~23° half-angle against an assumed 34° angle of repose is on the
shallow side for reliable mass flow in sand. If the measured angle of repose comes back
higher, or the sand is damp, this cone will rathole and needs either steepening or a
discharge aid (vibrator or air pad). **[VERIFY]** by measurement.

**Structural.** ~11 kN per leg before dynamic factors. **[VERIFY]** slab capacity.

---

## FL-01 — Filling machine

| Parameter | Value | Provenance |
|---|---|---|
| Footprint | 1.50 × 0.78 m | model |
| Cabinet top | +0.80 m | model |
| Deck | +0.95 m | model |
| Infeed hopper | +1.70 → +1.95 m | model |
| Infeed rim | **+1.95 m** | model |
| Product | Fuse bodies | from `plant.js` comment |

Existing machine, assumed retained. **[VERIFY]** its infeed acceptance rate — it sets the
whole line's throughput ceiling and nobody has stated it.

---

## AMR-01 — Autonomous mobile robot

| Parameter | Value | Provenance |
|---|---|---|
| Deck height | +0.57 m | model |
| Aisle width available | 2.60 m | model |
| Lift travel required | 4.20 m | model |
| Payload | **[VERIFY] — see below** | — |
| Docking repeatability | **[VERIFY]**, typically ±10 mm | — |

**Payload is unresolved and blocking.** If the Ø0.84 × 1.05 m barrel is retained, a full
barrel is 873 kg, which puts this at the top of or beyond the common AMR range once
tare and any deck equipment are added. Resolve `01-process-flow.md` §3.1 first.

Must interface with LI-01 for lift calls, and with the cell PLC for station handshakes.

---

## RB-01 — Barrel discharge robot

**This item cannot be specified until §3.1 is resolved.** The model describes a two-link
arm of 0.82 + 0.88 m (1.70 m reach) mounted on the AMR deck at +0.57 m, lifting a barrel
to +1.95 m.

The reach and the geometry are fine. **The payload is not** — 873 kg full, against a
~30 kg ceiling for the largest collaborative robots.

| If the decision is… | RB-01 becomes |
|---|---|
| Shrink the barrel to ~16 L | A real cobot, 25–30 kg payload, 1.70 m reach, deck mounted |
| Keep the barrel, drop the cobot | Deleted — replaced by a **floor-mounted drum tipper** at FL-01 |
| Direct transfer HP-01 → FL-01 | Deleted — replaced by a second vacuum or screw conveyor |

The BOM assumes the middle option.

---

## LI-01 — Goods lift

| Parameter | Value | Provenance |
|---|---|---|
| Travel | 4.20 m | model |
| Car internal | 1.90 × 1.90 × 2.10 m | model |
| Rated load | **[VERIFY]** | — |
| Unaccompanied goods duty | **[VERIFY]** | — |

Existing lift, assumed reused. If it is a passenger lift, its rated load and its
certification may not permit an AMR plus a heavy load travelling unaccompanied.
