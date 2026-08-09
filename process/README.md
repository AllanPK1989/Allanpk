# Sand Mixing Line — Automation Package

Process flow, general arrangement drawings, equipment specification, bill of materials
and control I/O list for the automated (AFTER) sand mixing cell.

## Provenance — read this first

**This package was not extracted from the YouTube video.** That video
(`youtube.com/watch?v=vYhS1O6gHCk`) could not be reached: the build environment's
network policy refuses `CONNECT` to `youtube.com` and `googlevideo.com` with HTTP 403.
Both the `watch` and `video-frame-analysis` skills were run and both failed at the
network layer, not the tooling layer.

The process here is instead anchored on **the AFTER scenario already documented in
`animation/README.md`**, and every dimension was read out of `animation/lib/plant.js`.
When the video becomes available — upload the file and the frame analysis can run
locally — this package should be reconciled against it.

**Nothing here is a site survey.** The geometry is the 3D model's, which
`animation/README.md` already labels "representative, not your actual plant".

## Contents

| File | What it is |
|---|---|
| `01-process-flow.md` | 11-step flow, step detail, **critical findings**, HSE, open items |
| `02-equipment-spec.md` | Functional spec per machine |
| `03-bom.md` | Scope-level bill of materials |
| `04-io-list.md` | Control I/O and interlocks |
| `layout.json` | Single dimensional source of truth |
| `drawings/ga-plan.svg` | General arrangement, plan |
| `drawings/ga-elevation.svg` | General arrangement, front elevation |
| `drawings/pfd.svg` | Process flow diagram |
| `drawings/ga-plan.dxf` | Plan as R12 DXF, for CAD |
| `scripts/drawings.py` | Generates all four drawings from `layout.json` |

## Two blocking findings

Checking the model geometry against real equipment capability turned up two problems
that stop the concept being built as drawn. Both are detailed in `01-process-flow.md` §3.

**1. The barrel is far too heavy for a cobot.** The barrel in the model is Ø0.84 × 1.05 m
— 0.582 m³, which is **873 kg** of sand at 1500 kg/m³, and still 175 kg at only 20 % full.
The largest collaborative robots on the market carry about **30 kg**. The AFTER animation
shows a deck-mounted cobot lifting this barrel into the filler; no such robot exists.
Three ways out are set out in §3.1 — shrink the barrel to roughly 16 litres, keep the
barrel and use a fixed drum tipper instead of a cobot, or delete the barrel and convey
HP-01 → FL-01 directly across the 5 m between them.

**2. The conveyor is far too steep for a plain belt.** CV-01 runs 4.845 m at **43.75°**.
Dry sand slips on a smooth belt above roughly 18–20°. A sidewall belt holds the drawn
geometry; a bucket elevator or a re-pitch to ≤18° both move the hopper. See §3.2.

A third item worth a look, not blocking: HP-01 holds about **7 mixer batches** (4262 kg),
which is roughly **11 kN per leg** into the ground-floor slab, and a cross-contamination
problem if recipes change between batches (§3.3).

Also: `animation/README.md` states the mixer charge port is at 2.54 m on a 0.55 m
platform. `plant.js` has it at **1.52 m with no platform**. The code is newer; this
package uses 1.52 m, and the animation README needs correcting (§3.4).

## Regenerating the drawings

All four drawings are generated — there are no dimensions hard-coded in the drawing
script. Edit `layout.json`, then:

```bash
python3 process/scripts/drawings.py
```

Derived quantities (volumes, masses, conveyor length and angle) are recomputed on every
run and written back into `layout.json`, so they cannot go stale against the geometry.

## What is deliberately absent

No part numbers, no prices, no cycle times, no headcount, no throughput figures. None
were available, nothing has been quoted, and no supplier has been approached. The
standard is the one `animation/README.md` already sets: invented numbers that look
authoritative are worse than an acknowledged gap. Every such gap is marked `[VERIFY]`
and collected in `01-process-flow.md` §5.
