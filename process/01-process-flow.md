# Sand Mixing Line — Process Flow

**Scope.** Ground-floor sand mixing cell, from bag pick in the mezzanine warehouse to
discharge into the filling machine infeed hopper. Covers the AFTER (automated) state.

**Source of the process.** The step sequence is the AFTER scenario documented in
`animation/README.md`. All dimensions come from `process/layout.json`, which was read
out of `animation/lib/plant.js`. **This was not extracted from the YouTube video** —
that video could not be reached from the build environment (see `README.md`).

---

## 1. Flow summary

| # | Step | Equipment | Material state | Transfer |
|---|------|-----------|----------------|----------|
| 1 | MO released to warehouse | MES → PLC | — | data |
| 2 | Bag picked and loaded to AMR deck | ST-01, AMR-01 | bagged | manual, waist height |
| 3 | AMR descends to ground floor | LI-01 | bagged | powered, 4.20 m |
| 4 | AMR transits to mixing area, parks | AMR-01 | bagged | powered, 2.60 m aisle |
| 5 | Operator slits bag | MT-01 | bagged → loose | **manual — only touch in loop** |
| 6 | Vacuum transfer into mixer | VT-01 | loose | pneumatic, to +1.52 m |
| 7 | Mix cycle | MX-01 | mixed | — |
| 8 | Discharge to storage hopper | CV-01 | mixed | inclined conveyor, +3.35 m lift |
| 9 | Barrel filled in place on AMR | HP-01 | mixed | gravity, spout at +1.83 m |
| 10 | AMR transits to filler | AMR-01 | mixed | powered |
| 11 | Barrel lifted and discharged to infeed | RB-01 | mixed | robot, to +1.95 m |

Step 5 is the only manual material contact. Steps 2 and 5 are the only human touches.

---

## 2. Step detail

### Step 1 — MO release
MES issues the manufacturing order to the cell PLC. PLC checks HP-01 level (LSH not
made) and mixer empty before accepting. **[VERIFY]** MES protocol and message schema.

### Step 2 — Bag pick to AMR
Operator picks one bag from ST-01 racking and places it on the AMR deck at +0.57 m.
Deck height chosen to keep the lift within a safe manual handling window.
**[VERIFY]** bag mass. At 25 kg this is a two-handed lift within normal guidance; above
that a lift assist is required at the racking.

### Step 3 — Vertical transport
AMR enters LI-01, descends 4.20 m, exits at ground level. Lift call and door interlocks
are exchanged with the AMR fleet manager. Car internal 1.90 × 1.90 m, 2.10 m high.
**[VERIFY]** existing lift's rated load and whether it is certified for unaccompanied
goods movement — an AMR plus load may exceed a passenger-lift duty rating.

### Step 4 — Transit to mixing area
AMR follows the marked route along the 2.60 m aisle and parks at the MX-01 station.
Parking repeatability governs whether VT-01's suction lance needs compliance or a
vision correction. **[VERIFY]** AMR docking repeatability, typically ±10 mm.

### Step 5 — Bag opening (manual)
Operator slits the bag at the opening station. This is the dust-generating step and the
one place a person is in contact with loose sand.
**Control:** local exhaust ventilation at the slitting point is mandatory — see §4.

### Step 6 — Vacuum transfer to mixer
Vacuum conveyor lifts sand from the opening station into MX-01 over the charge rim at
+1.52 m. Sized on batch mass and an acceptable charge time.
**[VERIFY]** moisture content. Damp sand will not vacuum-convey reliably and bridges in
the receiver; above roughly 1–2 % free moisture this method needs rethinking.

### Step 7 — Mix cycle
Pan mixer, Ø1.24 m pan, working depth 0.56 m.
Geometric pan volume **0.676 m³**; at 60 % working fill and 1500 kg/m³ that is a batch of
about **608 kg**. **[VERIFY]** actual batch recipe and mix time — neither was available.

### Step 8 — Discharge to storage hopper
Mixer discharges at +0.55 m onto CV-01, which lifts 3.35 m over a 3.50 m run to enter
HP-01 at +3.90 m. **See the critical finding in §3 — this geometry does not work with a
plain belt.**

### Step 9 — Barrel filling
Barrel stands on the AMR deck under the HP-01 spout at +1.83 m. Spout height was set to
clear a barrel top at 0.57 + 1.05 = 1.62 m. Slide valve opens on a weight or time
signal. **[VERIFY]** whether fill is by weight (needs load cells under the AMR deck or a
weigh frame) or by level.

### Step 10 — Transit to filler
AMR carries the filled barrel to FL-01.
**See §3 — the filled-barrel mass drives both AMR and robot selection.**

### Step 11 — Discharge to filling machine
Robot lifts the barrel and tips it into the FL-01 infeed hopper at +1.95 m.

---

## 3. Critical findings

These came out of checking the model geometry against real equipment capability. Both
are blocking — the concept as drawn cannot be built as drawn.

### 3.1 The barrel is far too heavy for a cobot — **blocking**

Barrel in the model: Ø0.84 m × 1.05 m → **0.582 m³** geometric.

| Fill | Volume | Mass at 1500 kg/m³ |
|---|---|---|
| 100 % | 0.582 m³ | **873 kg** |
| 50 % | 0.291 m³ | **437 kg** |
| 20 % | 0.116 m³ | **175 kg** |

The heaviest collaborative robots on the market are around **30 kg** payload (UR30,
FANUC CRX-30iA, Doosan H-series ~25 kg). The barrel exceeds that by a factor of roughly
6 even at 20 % fill. No deck-mounted cobot performs this lift, and the two-link
kinematics in `plant.js` (0.82 m + 0.88 m, 1.70 m reach) describe a light arm.

There is a second problem behind it: an 873 kg payload plus barrel tare plus the arm
itself is at or beyond the capacity of common AMRs (MiR1350, OTTO 1500 class).

**Options, in order of preference:**

1. **Shrink the barrel** to match a real cobot. A 25 kg payload at 1500 kg/m³ is about
   **16 litres** of sand — a Ø0.30 × 0.25 m keg, not a Ø0.84 × 1.05 m drum. This changes
   the whole material-handling concept: more trips, or several small containers per AMR.
2. **Keep the large barrel and drop the cobot.** Use a floor-mounted drum tipper or post
   hoist at FL-01. The AMR delivers, a fixed tipper does the lift. Cheaper and far more
   robust than any robot for a lift this size, but it is no longer a cobot cell.
3. **Eliminate the barrel entirely.** Run a second vacuum or screw transfer from HP-01
   directly to the FL-01 infeed. HP-01 and FL-01 are only 5.00 m apart. This removes the
   AMR from the second half of the loop and is likely the lowest-cost automation of the
   three — but it also removes most of the flexibility the AMR was bought for.

**This decision must be made before any equipment is quoted.** The BOM in
`03-bom.md` is written against option 2, as the least disruptive to the documented
layout, and flags the alternatives.

### 3.2 The conveyor incline is too steep for a plain belt — **blocking**

CV-01 runs from (−0.70, 0.55) to (2.80, 3.90): **4.845 m** long at **43.75°**.

Dry sand on a smooth belt begins slipping back at roughly **18–20°**. 43.75° is more
than double that. Practical ceilings by type:

| Conveyor type | Max incline, dry sand | Fits here? |
|---|---|---|
| Plain troughed belt | ~18–20° | No |
| Cleated belt | ~35° | No |
| Sidewall / corrugated-wall belt | up to 90° | Yes |
| Enclosed screw | ~30–40° (capacity falls off sharply) | Marginal |
| Bucket elevator | vertical | Yes |
| Vacuum / pneumatic | any | Yes |

**Options:**

1. **Sidewall belt conveyor** — keeps the drawn geometry exactly, contains the dust.
   Recommended.
2. **Bucket elevator** — better for a 3.35 m lift, smaller footprint, but changes the
   layout: it needs a vertical run, not a diagonal one.
3. **Re-pitch to ≤18°** — needs a 10.3 m run for the same lift. There is not 10.3 m
   between MX-01 and HP-01; the hopper would have to move.

The BOM specifies option 1.

### 3.3 Storage hopper capacity is worth a sanity check — **not blocking**

HP-01 geometric volume is **3.343 m³** (2.610 body + 0.732 cone). At 85 % working fill
and 1500 kg/m³ that is **4262 kg** — about **7 mixer batches**.

Two consequences:

- **Is a 7-batch buffer intended?** If the line runs one recipe continuously, yes. If it
  changes recipe between batches, a hopper holding seven batches of the previous recipe
  is a cross-contamination and cleandown problem.
- **Structural load.** 4262 kg of sand plus vessel and frame on four legs is roughly
  **11 kN per leg** before dynamic and seismic factors. **[VERIFY]** the ground-floor
  slab can take it — this needs a structural engineer, not a process one.

### 3.4 The README is out of date on the mixer charge height — minor

`animation/README.md` says the mixer charge port sits at **2.54 m with a 0.55 m access
platform**. `plant.js` actually has `RIM_TOP = 1.52` and `platformY = 0` — the port was
lowered and the platform removed at some point, and the README was not updated. The
drawings and this document use **1.52 m**, the value in the code.

---

## 4. Health, safety and environment

**Respirable crystalline silica is the controlling hazard, not dust explosion.** Silica
sand is chemically inert and non-combustible, so combustible-dust zoning (DSEAR/ATEX,
NFPA 652) does **not** normally apply. What does apply is occupational exposure: RCS
causes silicosis and is a recognised carcinogen.

- Exposure limits are jurisdiction-specific — UK WEL 0.1 mg/m³ (8 h TWA), US OSHA PEL
  0.05 mg/m³. **[VERIFY]** the limit that applies to your site.
- **LEV at the bag-slitting station (step 5) is mandatory.** This is the highest-exposure
  point in the process and the only one where a person handles loose material.
- Enclose the CV-01 transfer and both hopper connections. A sidewall belt with covers
  does this; an open belt does not.
- **[VERIFY]** whether health surveillance and air monitoring are already in place.

**Machinery safety.** Introducing an AMR and a lifting robot into an aisle shared with
people requires a risk assessment to ISO 12100, with ISO 3691-4 for the AMR and
ISO 10218 / ISO/TS 15066 for the robot cell. If option 2 in §3.1 is taken (fixed drum
tipper), the tipper needs its own guarding assessment — a 873 kg drum being inverted is
a serious crush and ejection hazard.

---

## 5. Open items

Everything below must be answered before this package can become a procurement
specification.

| # | Item | Blocks |
|---|------|--------|
| 1 | Barrel size / robot vs tipper decision (§3.1) | AMR, robot, barrel, gripper |
| 2 | Conveyor type decision (§3.2) | CV-01 |
| 3 | Sand bulk density and moisture (measured) | every mass and volume in this pack |
| 4 | Batch mass and mix time | MX-01, throughput, cycle time |
| 5 | Target throughput (batches/shift) | whole-line sizing |
| 6 | Bag mass at ST-01 | manual handling assessment |
| 7 | Existing lift rated load and certification | LI-01 reuse or replace |
| 8 | Ground-floor slab capacity under HP-01 | HP-01 structure |
| 9 | Fill control method — weight or level | instrumentation, load cells |
| 10 | Recipe changeover frequency | hopper sizing, cleandown |
| 11 | Applicable RCS exposure limit | LEV sizing |
| 12 | MES interface protocol | controls |

No cycle times or headcount figures appear anywhere in this package. None were supplied,
and the same reasoning given in `animation/README.md` applies: invented numbers that look
authoritative are worse than an acknowledged gap.
