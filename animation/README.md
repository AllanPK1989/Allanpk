# Sand Mixing — BEFORE / AFTER 3D animations

Two 3D animations of the sand mixing process, walking the full flow in-to-out:

- **`before.html`** — the current manual process (10 steps, 74 s)
- **`after.html`** — the same process with an **AMR** and a **cobot** (11 steps, 79 s)

Rendered videos are in [`video/`](./video).

## Run the interactive scenes

No build step and no network — Three.js is vendored in `vendor/`. ES modules
need a server, so `file://` will not work:

```bash
python3 -m http.server 8000
# → http://localhost:8000/animation/before.html
# → http://localhost:8000/animation/after.html
```

**Controls:** click any step in the left-hand list to jump to it · scrub the
timeline · `◀ ▶` step between stations · <kbd>space</kbd> play/pause.

## The two scenarios

### BEFORE — every transfer is carried by an operator

| # | Step |
|---|------|
| 1 | Manufacturing Order released |
| 2 | Operator walks ground floor → stairs → 2nd floor warehouse |
| 3 | Collects sand bag from pallet racking |
| 4 | Carries the bag back down to the mixing area |
| 5 | Climbs the access platform and tips the bag into the charge port |
| 6 | Mixing process runs — operator waits |
| 7 | Discharges the bottom hopper into bins |
| 8 | Transfers bins into a storage barrel (double handling) |
| 9 | Trolleys the barrel to the filling machine |
| 10 | Manually lifts sand into the machine's top hopper |

### AFTER — material moves itself, the operator supervises

| # | Step |
|---|------|
| 1 | MES releases the MO directly to the warehouse |
| 2 | Warehouse operator loads the bag onto the AMR at waist height |
| 3 | AMR takes the goods lift down to the ground floor |
| 4 | AMR delivers to the mixing area and waits |
| 5 | Operator opens the bag — the only manual touch in the loop |
| 6 | Vacuum system transfers sand into the mixing vessel |
| 7 | Mixing process runs — operator free for other work |
| 8 | Inclined conveyor to the storage hopper, interlocked on high/low level |
| 9 | Barrel filled in place on the cobot-equipped AMR |
| 10 | AMR drives to the filling machine |
| 11 | Cobot lifts the barrel and discharges into the top hopper |

The manual carry, the stair trips, the bin-to-barrel double handling and the
trolley move all disappear; the repetitive lift at the filling machine is taken
over by the cobot.

## Layout

Both scenes share one plant model (`lib/plant.js`) so the before/after
comparison is like-for-like — same building, same machines, same distances:

```
mezzanine warehouse   x -15 … -4.5, floor at 4.2 m
goods lift shaft      x -6,   z -7      (AFTER: AMR route down)
stair flight          x -4.5, z 2 … 7   (BEFORE: operator route)
sand mixing machine   x -1,   z 0
sand storage hopper   x  3.5, z 0       (AFTER only)
sand filling machine  x  8.5, z 0
```

## Files

```
before.html        BEFORE scene + timeline
after.html         AFTER scene + timeline
lib/plant.js       shared plant geometry, materials, lighting, cobot IK
lib/story.js       deterministic timeline, camera rig, UI, caption overlay
vendor/            Three.js r160 (vendored — runs offline)
video/             rendered MP4s
```

## Notes on how this was built

**Everything is a pure function of story time.** No clock, no per-frame state
accumulation. Frame *N* rendered offline is identical to scrubbing to that
timestamp interactively — which is what makes correct video capture possible on
a machine with no GPU.

**Machine heights are constrained by what a human and a cobot can actually
reach.** The mixer charge port sits at 2.54 m with a 0.55 m access platform, and
the filling machine's top hopper at 1.95 m — chest height for a manual lift, and
inside a deck-mounted cobot's working envelope. An earlier draft had them at 5 m
and 4.3 m, which would have shown an operator and a cobot doing things neither
could physically do.

**The cobot arm is solved with two-link inverse kinematics** (`solveCobot`)
rather than hand-keyed joint angles. Hand-keyed angles put the gripper 2.8 m
away from the hopper it was supposed to be pouring into; solving from the target
position puts the barrel over the rim to within 1 cm, and stays correct if the
AMR parks slightly differently.

**Captions are rendered into the 3D canvas**, not the DOM. Frame capture reads
the WebGL framebuffer, so DOM overlays would never reach the video, and this
ffmpeg build has no `drawtext` filter to burn them in afterwards.

## Caveats

- Equipment geometry is **representative, not your actual plant** — no CAD or
  photos were supplied, so shapes and distances are illustrative.
- **No cycle times or headcount figures are shown.** None were provided, and
  inventing plausible-looking numbers for a customer-facing video would be
  worse than omitting them. If you supply real figures they can be added as
  on-screen callouts.
