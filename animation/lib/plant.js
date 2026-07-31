// Shared plant geometry for the sand-mixing before/after animations.
//
// Layout (metres, +x right, +z toward camera):
//   mezzanine warehouse  x -14..-4.5, floor at y 4.2
//   goods lift shaft     x -6,  z -7      (AFTER: AMR route down)
//   stair flight         x -4.5, z 2..7   (BEFORE: operator route)
//   sand mixing machine  x -1,  z 0
//   sand storage hopper  x  3.5, z 0      (AFTER only)
//   sand filling machine x  8.5, z 0
//
// Tuned for software (SwiftShader) rendering: no post-processing, a single
// shadow-casting light, MeshStandardMaterial throughout, moderate poly counts.

import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export const FLOOR_Y = 0;
export const MEZZ_Y  = 4.2;
export const MEZZ_X  = -4.5;     // mezzanine front edge
export const LIFT_POS   = new THREE.Vector3(-6, 0, -7);
export const MIXER_POS   = new THREE.Vector3(-1, 0, 0);
export const HOPPER_POS  = new THREE.Vector3(3.5, 0, 0);
export const FILLER_POS  = new THREE.Vector3(8.5, 0, 0);
export const RACK_POS     = new THREE.Vector3(-10, MEZZ_Y, -4);

// ── Materials ────────────────────────────────────────────────────────────
const mat = (c, r, m, extra = {}) =>
  new THREE.MeshStandardMaterial({
    color: c, roughness: r, metalness: m, envMapIntensity: 0.45, ...extra });

export const MAT = {
  concrete:  mat(0x55585d, 0.96, 0.02),
  concreteD: mat(0x44474b, 0.96, 0.02),
  wall:      mat(0x6a7079, 0.94, 0.02),
  steel:     mat(0xb6bcc4, 0.38, 0.85),
  steelMatte:mat(0xa9b0b8, 0.62, 0.62),
  steelDark: mat(0x6d747d, 0.45, 0.8),
  painted:   mat(0x2f6f9e, 0.55, 0.35),   // equipment blue
  paintedLt: mat(0x4a90c4, 0.55, 0.3),
  yellow:    mat(0xe0a52a, 0.6, 0.2),
  safety:    mat(0xd8b02a, 0.85, 0.05),   // floor markings
  rubber:    mat(0x23262b, 0.95, 0.05),
  sand:      mat(0xc9a86c, 0.95, 0.0),
  sandDark:  mat(0xa88954, 0.95, 0.0),
  bag:       mat(0xdcd3c0, 0.9, 0.02),
  barrel:    mat(0x2f6f9e, 0.5, 0.4),
  barrelRim: mat(0x9aa3ad, 0.4, 0.8),
  amr:       mat(0x2b3038, 0.5, 0.5),
  amrTop:    mat(0x3a4149, 0.55, 0.45),
  cobot:     mat(0xe8e9ea, 0.42, 0.35),
  cobotJoint:mat(0x2b6ca8, 0.45, 0.5),
  hiVis:     mat(0xd4d33a, 0.85, 0.02),
  skin:      mat(0xc79b74, 0.85, 0.02),
  trouser:   mat(0x34435c, 0.9, 0.02),
  glass:     mat(0x8fb6cc, 0.15, 0.1, { transparent: true, opacity: 0.28 }),
  green:     mat(0x35c06a, 0.5, 0.1, { emissive: 0x1d7a40, emissiveIntensity: 0.7 }),
  red:       mat(0xd8453f, 0.5, 0.1, { emissive: 0x8a1f1b, emissiveIntensity: 0.7 }),
  amber:     mat(0xe8a32a, 0.5, 0.1, { emissive: 0x9c6408, emissiveIntensity: 0.7 }),
  screen:    mat(0x11202e, 0.4, 0.1, { emissive: 0x1d5c8a, emissiveIntensity: 0.55 }),
};

const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
const cyl = (rt, rb, h, m, seg = 20) =>
  new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), m);

function shade(o, cast = true, receive = true) {
  o.traverse((c) => { if (c.isMesh) { c.castShadow = cast; c.receiveShadow = receive; } });
  return o;
}

// ── Text label sprite (canvas texture, cheap to render) ──────────────────
export function makeLabel(text, { size = 0.26, bg = 'rgba(12,16,22,0.88)', fg = '#eaf0f8' } = {}) {
  const pad = 18, font = 44;
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  ctx.font = `600 ${font}px ui-sans-serif, system-ui, sans-serif`;
  const w = Math.ceil(ctx.measureText(text).width) + pad * 2;
  c.width = w; c.height = font + pad * 2;
  const g = c.getContext('2d');
  g.font = `600 ${font}px ui-sans-serif, system-ui, sans-serif`;
  g.fillStyle = bg;
  g.beginPath(); g.roundRect(0, 0, c.width, c.height, 14); g.fill();
  g.strokeStyle = 'rgba(255,255,255,0.16)'; g.lineWidth = 2; g.stroke();
  g.fillStyle = fg; g.textBaseline = 'middle';
  g.fillText(text, pad, c.height / 2 + 2);

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  spr.scale.set((c.width / c.height) * size, size, 1);
  spr.renderOrder = 999;
  return spr;
}

/**
 * Fade station labels by camera distance. Sprites are sized in world units, so
 * without this a close camera turns a label into a full-screen banner.
 */
export function updateLabels(labels, camera) {
  for (const l of labels) {
    const d = l.position.distanceTo(camera.position);
    const near = THREE.MathUtils.smoothstep(d, 4.0, 7.5);
    const far  = 1 - THREE.MathUtils.smoothstep(d, 26, 34);
    l.material.opacity = Math.min(near, far);
    l.visible = l.material.opacity > 0.02;
  }
}

// ── Building shell ───────────────────────────────────────────────────────
export function buildShell() {
  const g = new THREE.Group();

  const slab = box(30, 0.3, 20, MAT.concrete);
  slab.position.set(0, -0.15, 0);
  slab.receiveShadow = true;
  g.add(slab);

  // back and side walls (front left open for the camera)
  const back = box(30, 8.6, 0.25, MAT.wall);
  back.position.set(0, 4.3, -10);
  back.receiveShadow = true; g.add(back);

  const left = box(0.25, 8.6, 20, MAT.wall);
  left.position.set(-15, 4.3, 0); left.receiveShadow = true; g.add(left);

  const right = box(0.25, 8.6, 20, MAT.wall);
  right.position.set(15, 4.3, 0); right.receiveShadow = true; g.add(right);

  // mezzanine slab (warehouse level)
  const mez = box(10.5, 0.28, 20, MAT.concreteD);
  mez.position.set(-9.75, MEZZ_Y - 0.14, 0);
  mez.castShadow = true; mez.receiveShadow = true; g.add(mez);

  // support columns under the mezzanine
  for (const z of [-8, -4, 0, 4, 8]) {
    const col = box(0.34, MEZZ_Y - 0.28, 0.34, MAT.steelDark);
    col.position.set(MEZZ_X - 0.4, (MEZZ_Y - 0.28) / 2, z);
    shade(col); g.add(col);
  }

  // mezzanine edge railing
  const railGroup = new THREE.Group();
  for (const z of [-9, -6, -3, 0, 3, 6, 9]) {
    const p = box(0.07, 1.05, 0.07, MAT.yellow);
    p.position.set(MEZZ_X - 0.1, MEZZ_Y + 0.52, z); shade(p); railGroup.add(p);
  }
  const topRail = box(0.08, 0.08, 20, MAT.yellow);
  topRail.position.set(MEZZ_X - 0.1, MEZZ_Y + 1.05, 0); shade(topRail); railGroup.add(topRail);
  const midRail = box(0.06, 0.06, 20, MAT.yellow);
  midRail.position.set(MEZZ_X - 0.1, MEZZ_Y + 0.55, 0); shade(midRail); railGroup.add(midRail);
  g.add(railGroup);

  const ceil = box(30, 0.25, 20, MAT.concreteD);
  ceil.position.set(0, 8.7, 0); ceil.receiveShadow = true; g.add(ceil);

  // roof trusses for depth
  for (let i = -3; i <= 3; i++) {
    const tr = box(30, 0.16, 0.16, MAT.steelDark);
    tr.position.set(0, 8.45, i * 3); shade(tr); g.add(tr);
  }

  // floor safety marking down the main aisle
  const aisle = new THREE.Mesh(new THREE.PlaneGeometry(26, 0.12), MAT.safety);
  aisle.rotation.x = -Math.PI / 2; aisle.position.set(1, 0.012, 2.6); g.add(aisle);
  const aisle2 = aisle.clone(); aisle2.position.z = -2.6; g.add(aisle2);

  return g;
}

// ── Stair flight (BEFORE: operator route) ────────────────────────────────
export function buildStairs() {
  const g = new THREE.Group();
  const steps = 14, rise = MEZZ_Y / steps, run = 0.34;
  for (let i = 0; i < steps; i++) {
    const s = box(1.6, 0.07, run, MAT.steelDark);
    s.position.set(MEZZ_X + 0.55, rise * (i + 1), 6.6 - i * run);
    shade(s); g.add(s);
  }
  for (const side of [-0.78, 0.78]) {
    const r = box(0.06, 0.06, steps * run * 1.02, MAT.yellow);
    r.position.set(MEZZ_X + 0.55 + side, MEZZ_Y / 2 + 1.0, 6.6 - (steps * run) / 2);
    r.rotation.x = Math.atan2(MEZZ_Y, steps * run);
    shade(r); g.add(r);
  }
  return g;
}

// ── Goods lift (AFTER: AMR route down) ───────────────────────────────────
export function buildLift() {
  const g = new THREE.Group();
  g.position.copy(LIFT_POS);

  // shaft frame
  for (const [x, z] of [[-1.3, -1.3], [1.3, -1.3], [-1.3, 1.3], [1.3, 1.3]]) {
    const c = box(0.16, 5.6, 0.16, MAT.steelDark);
    c.position.set(x, 2.8, z); shade(c); g.add(c);
  }
  const head = box(2.9, 0.18, 2.9, MAT.steelDark);
  head.position.set(0, 5.6, 0); shade(head); g.add(head);

  // rear + side mesh panels
  const back = box(2.8, 5.5, 0.06, MAT.glass);
  back.position.set(0, 2.75, -1.35); g.add(back);
  const side = box(0.06, 5.5, 2.8, MAT.glass);
  side.position.set(-1.35, 2.75, 0); g.add(side);

  // the car itself — animated by the scene
  const car = new THREE.Group();
  const deck = box(2.5, 0.14, 2.5, MAT.steel);
  deck.position.y = 0.07; shade(deck); car.add(deck);
  for (const side2 of [-1.2, 1.2]) {
    const w = box(0.08, 1.1, 2.5, MAT.steelDark);
    w.position.set(side2, 0.62, 0); shade(w); car.add(w);
  }
  const rear = box(2.5, 1.1, 0.08, MAT.steelDark);
  rear.position.set(0, 0.62, -1.2); shade(rear); car.add(rear);
  car.position.y = MEZZ_Y;
  g.add(car);

  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 12), MAT.green);
  lamp.position.set(1.45, 2.4, 1.3); g.add(lamp);

  g.userData.car = car;
  g.userData.lamp = lamp;
  return g;
}

// ── Pallet racking with sand bags (warehouse) ────────────────────────────
export function buildRacking() {
  const g = new THREE.Group();
  g.position.copy(RACK_POS);

  for (const x of [-2.6, 2.6]) {
    for (const z of [-1.4, 1.4]) {
      const c = box(0.14, 3.2, 0.14, MAT.painted);
      c.position.set(x, 1.6, z); shade(c); g.add(c);
    }
  }
  for (const y of [0.85, 2.0]) {
    for (const z of [-1.4, 1.4]) {
      const b = box(5.4, 0.1, 0.16, MAT.painted);
      b.position.set(0, y, z); shade(b); g.add(b);
    }
    const deck = box(5.4, 0.06, 2.9, MAT.steelDark);
    deck.position.set(0, y + 0.08, 0); shade(deck); g.add(deck);
  }

  // stacked bags on the shelves
  for (const [y, n] of [[0.99, 5], [2.14, 5]]) {
    for (let i = 0; i < n; i++) {
      const bag = makeSandBag();
      bag.position.set(-2.1 + i * 1.05, y + 0.16, (i % 2) * 0.5 - 0.25);
      bag.rotation.y = (i % 2) * 0.2;
      g.add(bag);
    }
  }
  return g;
}

// ── Consumables ──────────────────────────────────────────────────────────
export function makeSandBag() {
  const g = new THREE.Group();
  const b = box(0.82, 0.3, 0.52, MAT.bag);
  shade(b); g.add(b);
  // pinched seams
  for (const x of [-0.41, 0.41]) {
    const s = box(0.05, 0.2, 0.5, MAT.bag);
    s.position.set(x, 0.04, 0); shade(s); g.add(s);
  }
  const stripe = box(0.5, 0.02, 0.3, MAT.painted);
  stripe.position.set(0, 0.155, 0); g.add(stripe);
  return g;
}

export function makeBarrel() {
  const g = new THREE.Group();
  const body = cyl(0.42, 0.42, 1.05, MAT.barrel, 24);
  body.position.y = 0.52; shade(body); g.add(body);
  for (const y of [0.24, 0.8]) {
    const r = cyl(0.445, 0.445, 0.07, MAT.barrelRim, 24);
    r.position.y = y; shade(r); g.add(r);
  }
  const lip = cyl(0.45, 0.45, 0.08, MAT.barrelRim, 24);
  lip.position.y = 1.04; shade(lip); g.add(lip);
  // sand fill level — scaled by the scene
  const fill = cyl(0.38, 0.38, 1.0, MAT.sand, 20);
  fill.position.y = 0.5; fill.scale.y = 0.001; g.add(fill);
  g.userData.fill = fill;
  return g;
}

export function makeBin() {
  const g = new THREE.Group();
  const b = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.26, 0.46, 16), MAT.paintedLt);
  b.position.y = 0.23; shade(b); g.add(b);
  const fill = new THREE.Mesh(new THREE.CylinderGeometry(0.31, 0.24, 0.42, 16), MAT.sand);
  fill.position.y = 0.22; fill.scale.y = 0.001; g.add(fill);
  g.userData.fill = fill;
  return g;
}

export function makeTrolley() {
  const g = new THREE.Group();
  const deck = box(1.3, 0.09, 0.9, MAT.steel);
  deck.position.y = 0.34; shade(deck); g.add(deck);
  const handle = box(0.07, 0.95, 0.07, MAT.steelDark);
  handle.position.set(-0.6, 0.82, 0); shade(handle); g.add(handle);
  const bar = box(0.07, 0.07, 0.8, MAT.steelDark);
  bar.position.set(-0.6, 1.28, 0); shade(bar); g.add(bar);
  for (const [x, z] of [[-0.5, -0.38], [-0.5, 0.38], [0.5, -0.38], [0.5, 0.38]]) {
    const w = cyl(0.15, 0.15, 0.07, MAT.rubber, 14);
    w.rotation.z = Math.PI / 2; w.position.set(x, 0.15, z); shade(w); g.add(w);
  }
  return g;
}

// ── Sand mixing machine ──────────────────────────────────────────────────
export function buildMixer() {
  const g = new THREE.Group();
  g.position.copy(MIXER_POS);

  for (const [x, z] of [[-0.7, -0.7], [0.7, -0.7], [-0.7, 0.7], [0.7, 0.7]]) {
    const l = box(0.13, 0.55, 0.13, MAT.steelDark);
    l.position.set(x, 0.28, z); shade(l); g.add(l);
  }

  // conical bottom hopper (discharge at 0.40)
  const hopper = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.2, 0.7, 24, 1, true), MAT.steel);
  hopper.material.side = THREE.DoubleSide;
  hopper.position.y = 0.9; shade(hopper); g.add(hopper);
  const valve = cyl(0.16, 0.16, 0.26, MAT.painted, 14);
  valve.position.y = 0.47; shade(valve); g.add(valve);
  g.userData.spoutY = 0.36;

  // vessel
  const vessel = cyl(0.85, 0.85, 0.9, MAT.steelMatte, 26);
  vessel.position.y = 1.7; shade(vessel); g.add(vessel);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(0.85, 26, 12, 0, Math.PI * 2, 0, Math.PI / 2), MAT.steelMatte);
  dome.position.y = 2.15; shade(dome); g.add(dome);

  // charge port — the manual tipping point in BEFORE (rim at 2.62)
  const port = cyl(0.32, 0.32, 0.26, MAT.painted, 16);
  port.position.set(0.45, 2.42, 0); shade(port); g.add(port);
  const portLid = cyl(0.38, 0.38, 0.05, MAT.steelDark, 16);
  portLid.position.set(0.45, 2.57, 0); shade(portLid); g.add(portLid);
  g.userData.portLid = portLid;
  g.userData.portY = 2.54;
  g.userData.portX = 0.45;

  // drive motor
  const motor = cyl(0.24, 0.24, 0.38, MAT.painted, 14);
  motor.position.set(-0.55, 2.6, 0); shade(motor); g.add(motor);
  const gearbox = box(0.4, 0.28, 0.4, MAT.steelDark);
  gearbox.position.set(-0.55, 2.32, 0); shade(gearbox); g.add(gearbox);

  // operator access platform + steps (BEFORE)
  const plat = box(1.5, 0.09, 1.2, MAT.steelDark);
  plat.position.set(1.55, 0.5, 0.35); shade(plat); g.add(plat);
  for (const [i, y] of [[0, 0.17], [1, 0.33]]) {
    const s = box(0.9, 0.06, 0.3, MAT.steelDark);
    s.position.set(2.15, y, 1.15 - i * 0.3); shade(s); g.add(s);
  }
  for (const [x, z] of [[2.2, 0.35], [1.0, 0.35]]) {
    const r = box(0.05, 1.0, 0.05, MAT.yellow);
    r.position.set(x, 1.0, z - 0.55); shade(r); g.add(r);
  }
  g.userData.platformY = 0.55;

  // control panel
  const panel = box(0.42, 0.5, 0.1, MAT.painted);
  panel.position.set(-1.25, 1.2, 0.6); shade(panel); g.add(panel);
  const scr = box(0.28, 0.2, 0.03, MAT.screen);
  scr.position.set(-1.25, 1.3, 0.66); g.add(scr);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 10), MAT.red);
  lamp.position.set(-1.25, 1.02, 0.66); g.add(lamp);
  g.userData.lamp = lamp;

  const shaft = cyl(0.06, 0.06, 0.85, MAT.steelDark, 10);
  shaft.position.y = 1.9; g.add(shaft);
  g.userData.shaft = shaft;

  return g;
}

// ── Sand filling machine ─────────────────────────────────────────────────
export function buildFiller() {
  const g = new THREE.Group();
  g.position.copy(FILLER_POS);

  const base = box(2.2, 1.0, 1.5, MAT.painted);
  base.position.y = 0.5; shade(base); g.add(base);
  const frame = box(1.5, 0.34, 1.2, MAT.steelDark);
  frame.position.y = 1.17; shade(frame); g.add(frame);

  // top hopper — manual lift target in BEFORE, cobot discharge target in AFTER.
  // Rim at 1.95 m: liftable by hand (chest height) and inside a deck-mounted
  // cobot's reach, which is what makes both scenarios physically plausible.
  const hop = new THREE.Mesh(new THREE.CylinderGeometry(0.68, 0.28, 0.62, 22, 1, true), MAT.steel);
  hop.material.side = THREE.DoubleSide;
  hop.position.y = 1.62; shade(hop); g.add(hop);
  const rim = cyl(0.7, 0.7, 0.06, MAT.painted, 22);
  rim.position.y = 1.94; shade(rim); g.add(rim);
  g.userData.hopperRimY = 1.95;

  const hopFill = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.28, 0.56, 18), MAT.sand);
  hopFill.position.y = 1.6; hopFill.scale.y = 0.001; g.add(hopFill);
  g.userData.hopFill = hopFill;

  // outfeed conveyor with filled packs
  const belt = box(3.0, 0.09, 0.6, MAT.rubber);
  belt.position.set(2.4, 0.72, 0); shade(belt); g.add(belt);
  for (const x of [1.4, 2.4, 3.4]) {
    for (const z of [0.24, -0.24]) {
      const l = box(0.08, 0.68, 0.08, MAT.steelDark);
      l.position.set(x, 0.34, z); shade(l); g.add(l);
    }
  }
  const packs = new THREE.Group();
  for (let i = 0; i < 4; i++) {
    const p = box(0.36, 0.26, 0.4, MAT.bag);
    p.position.set(1.35 + i * 0.66, 0.9, 0); shade(p); packs.add(p);
  }
  g.add(packs);
  g.userData.packs = packs;

  const panel = box(0.38, 0.46, 0.09, MAT.painted);
  panel.position.set(-1.25, 1.1, 0.6); shade(panel); g.add(panel);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 10), MAT.red);
  lamp.position.set(-1.25, 1.32, 0.66); g.add(lamp);
  g.userData.lamp = lamp;

  return g;
}

// ── AFTER-only: storage hopper with high/low level probes ────────────────
export function buildStorageHopper() {
  const g = new THREE.Group();
  g.position.copy(HOPPER_POS);

  // Legs are tall enough that the discharge spout (1.85 m) clears the top of a
  // barrel standing on an AMR deck (0.57 + 1.05 = 1.62 m).
  for (const [x, z] of [[-0.75, -0.75], [0.75, -0.75], [-0.75, 0.75], [0.75, 0.75]]) {
    const l = box(0.12, 1.95, 0.12, MAT.steelDark);
    l.position.set(x, 0.98, z); shade(l); g.add(l);
  }
  for (const z of [-0.75, 0.75]) {
    const br = box(1.6, 0.07, 0.07, MAT.steelDark);
    br.position.set(0, 1.0, z); shade(br); g.add(br);
  }

  const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.2, 0.75, 22, 1, true), MAT.steel);
  cone.material.side = THREE.DoubleSide;
  cone.position.y = 2.32; shade(cone); g.add(cone);
  const body = cyl(0.85, 0.85, 1.15, MAT.steel, 22);
  body.position.y = 3.27; shade(body); g.add(body);
  const lid = cyl(0.89, 0.89, 0.06, MAT.painted, 22);
  lid.position.y = 3.87; shade(lid); g.add(lid);

  const fill = cyl(0.8, 0.8, 1.1, MAT.sand, 18);
  fill.position.y = 3.25; fill.scale.y = 0.001; g.add(fill);
  g.userData.fill = fill;

  // high / low level probes with indicator lamps
  for (const [name, y] of [['hi', 3.62], ['lo', 2.85]]) {
    const probe = box(0.14, 0.14, 0.14, MAT.steelDark);
    probe.position.set(0.9, y, 0); shade(probe); g.add(probe);
    const lampM = MAT.red.clone();
    const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.08, 10, 10), lampM);
    lamp.position.set(1.07, y, 0); g.add(lamp);
    g.userData[name + 'Lamp'] = lamp;
  }

  const valve = cyl(0.17, 0.17, 0.28, MAT.painted, 14);
  valve.position.y = 1.97; shade(valve); g.add(valve);
  g.userData.spoutY = 1.83;

  return g;
}

// ── AFTER-only: inclined conveyor, mixer hopper -> storage hopper ────────
export function buildInclinedConveyor() {
  const g = new THREE.Group();
  const from = new THREE.Vector3(MIXER_POS.x + 0.3, 0.55, -1.3);
  const to   = new THREE.Vector3(HOPPER_POS.x - 0.7, 3.9, -1.3);
  const mid  = from.clone().add(to).multiplyScalar(0.5);
  const len  = from.distanceTo(to);
  const ang  = Math.atan2(to.y - from.y, to.x - from.x);

  const trough = box(len, 0.12, 0.5, MAT.steelMatte);
  trough.position.copy(mid); trough.rotation.z = ang; shade(trough); g.add(trough);
  for (const s of [-0.26, 0.26]) {
    const w = box(len, 0.26, 0.05, MAT.steelMatte);
    w.position.set(mid.x, mid.y + 0.13, mid.z + s); w.rotation.z = ang; shade(w); g.add(w);
  }
  // support legs
  for (const t of [0.3, 0.62, 0.9]) {
    const p = from.clone().lerp(to, t);
    const l = box(0.09, p.y, 0.09, MAT.steelDark);
    l.position.set(p.x, p.y / 2, p.z); shade(l); g.add(l);
  }
  const motor = cyl(0.24, 0.24, 0.4, MAT.painted, 14);
  motor.rotation.x = Math.PI / 2; motor.position.copy(to); shade(motor); g.add(motor);

  // sand riding the belt — scene toggles visibility and slides the offset
  const lumps = new THREE.Group();
  for (let i = 0; i < 14; i++) {
    const l = box(0.24, 0.1, 0.3, MAT.sand);
    lumps.add(l);
  }
  g.add(lumps);
  g.userData.lumps = lumps;
  g.userData.from = from;
  g.userData.to = to;
  return g;
}

// ── AFTER-only: vacuum transfer from bag to mixing vessel ────────────────
export function buildVacuumSystem() {
  const g = new THREE.Group();

  // receiver on top of the mixer
  const rec = cyl(0.44, 0.44, 0.7, MAT.steel, 18);
  rec.position.set(MIXER_POS.x - 0.75, 5.25, 0); shade(rec); g.add(rec);
  const pump = box(0.5, 0.4, 0.44, MAT.painted);
  pump.position.set(MIXER_POS.x - 0.75, 5.78, 0); shade(pump); g.add(pump);

  // flexible suction hose from the intake wand up to the receiver
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(MIXER_POS.x + 1.9, 0.55, 1.5),
    new THREE.Vector3(MIXER_POS.x + 1.3, 2.4, 1.4),
    new THREE.Vector3(MIXER_POS.x - 0.2, 4.4, 0.9),
    new THREE.Vector3(MIXER_POS.x - 0.75, 5.05, 0.15),
  ]);
  const hose = new THREE.Mesh(new THREE.TubeGeometry(curve, 26, 0.115, 10, false), MAT.rubber);
  shade(hose); g.add(hose);

  // intake wand that dips into the opened bag
  const wand = cyl(0.09, 0.09, 0.6, MAT.steelDark, 12);
  wand.position.set(MIXER_POS.x + 1.9, 0.3, 1.5); shade(wand); g.add(wand);
  g.userData.wand = wand;

  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.08, 10, 10), MAT.red);
  lamp.position.set(MIXER_POS.x - 0.75, 6.05, 0.2); g.add(lamp);
  g.userData.lamp = lamp;
  return g;
}

// ── Operator figure with a simple walk cycle ─────────────────────────────
export function makeOperator() {
  const g = new THREE.Group();

  const hips = new THREE.Group();
  hips.position.y = 0.92; g.add(hips);

  const torso = box(0.46, 0.62, 0.26, MAT.hiVis);
  torso.position.y = 0.31; shade(torso); hips.add(torso);
  const collar = box(0.48, 0.1, 0.28, MAT.painted);
  collar.position.y = 0.6; shade(collar); hips.add(collar);

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.115, 14, 12), MAT.skin);
  head.position.y = 0.78; shade(head); hips.add(head);
  const helmet = new THREE.Mesh(new THREE.SphereGeometry(0.135, 14, 10, 0, Math.PI * 2, 0, Math.PI / 2), MAT.yellow);
  helmet.position.y = 0.8; shade(helmet); hips.add(helmet);

  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const shoulder = new THREE.Group();
    shoulder.position.set(s * 0.3, 0.52, 0); hips.add(shoulder);
    const arm = box(0.12, 0.56, 0.13, MAT.hiVis);
    arm.position.y = -0.28; shade(arm); shoulder.add(arm);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.075, 10, 8), MAT.skin);
    hand.position.y = -0.56; shade(hand); shoulder.add(hand);
    arms.push(shoulder);

    const hip = new THREE.Group();
    hip.position.set(s * 0.13, 0, 0); hips.add(hip);
    const leg = box(0.155, 0.9, 0.17, MAT.trouser);
    leg.position.y = -0.45; shade(leg); hip.add(leg);
    const boot = box(0.17, 0.11, 0.26, MAT.rubber);
    boot.position.set(0, -0.94, 0.04); shade(boot); hip.add(boot);
    legs.push(hip);
  }

  g.userData = { hips, arms, legs, head };
  return g;
}

// Drive the walk cycle. `speed` 0 = idle.
export function poseWalk(op, phase, speed = 1) {
  const { arms, legs, hips } = op.userData;
  const a = Math.sin(phase) * 0.62 * speed;
  legs[0].rotation.x = a;
  legs[1].rotation.x = -a;
  arms[0].rotation.x = -a * 0.8;
  arms[1].rotation.x = a * 0.8;
  hips.position.y = 0.92 + Math.abs(Math.sin(phase)) * 0.035 * speed;
}

// Both arms forward, as if carrying a load.
export function poseCarry(op, t = 1) {
  const { arms } = op.userData;
  arms[0].rotation.x = -1.35 * t;
  arms[1].rotation.x = -1.35 * t;
}

// Both arms raised overhead, as if lifting to a high port.
export function poseLift(op, t = 1) {
  const { arms } = op.userData;
  arms[0].rotation.x = -2.5 * t;
  arms[1].rotation.x = -2.5 * t;
}

// ── AMR ──────────────────────────────────────────────────────────────────
export function makeAMR({ withCobot = false } = {}) {
  const g = new THREE.Group();

  const chassis = box(1.5, 0.34, 1.05, MAT.amr);
  chassis.position.y = 0.32; shade(chassis); g.add(chassis);
  const deck = box(1.42, 0.08, 0.98, MAT.amrTop);
  deck.position.y = 0.53; shade(deck); g.add(deck);
  const bumper = box(1.54, 0.1, 1.09, MAT.yellow);
  bumper.position.y = 0.17; shade(bumper); g.add(bumper);

  for (const [x, z] of [[-0.5, -0.5], [0.5, -0.5], [-0.5, 0.5], [0.5, 0.5]]) {
    const w = cyl(0.16, 0.16, 0.1, MAT.rubber, 14);
    w.rotation.z = Math.PI / 2; w.position.set(x, 0.16, z); shade(w); g.add(w);
  }

  // lidar puck + status beacon
  const lidar = cyl(0.1, 0.1, 0.09, MAT.steelDark, 14);
  lidar.position.set(0.62, 0.6, 0); shade(lidar); g.add(lidar);
  const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.09, 12, 12), MAT.green);
  beacon.position.set(-0.6, 0.63, 0); g.add(beacon);
  g.userData.beacon = beacon;

  // side status strips
  for (const s of [-0.53, 0.53]) {
    const strip = box(1.3, 0.05, 0.02, MAT.green);
    strip.position.set(0, 0.38, s); g.add(strip);
  }

  if (withCobot) {
    const cobot = makeCobot();
    cobot.position.set(-0.32, 0.57, 0);
    g.add(cobot);
    g.userData.cobot = cobot;
  }

  return g;
}

// ── Cobot: 3-axis arm with a gripper ─────────────────────────────────────
export function makeCobot() {
  const g = new THREE.Group();

  const base = cyl(0.19, 0.22, 0.14, MAT.cobotJoint, 18);
  base.position.y = 0.07; shade(base); g.add(base);

  const yaw = new THREE.Group();
  yaw.position.y = 0.14; g.add(yaw);

  const j1 = cyl(0.14, 0.14, 0.2, MAT.cobot, 16);
  j1.rotation.x = Math.PI / 2; j1.position.y = 0.12; shade(j1); yaw.add(j1);

  const shoulder = new THREE.Group();
  shoulder.position.y = 0.12; yaw.add(shoulder);
  const upper = cyl(0.085, 0.085, 0.82, MAT.cobot, 14);
  upper.position.y = 0.41; shade(upper); shoulder.add(upper);

  const elbow = new THREE.Group();
  elbow.position.y = 0.82; shoulder.add(elbow);
  const j2 = cyl(0.11, 0.11, 0.17, MAT.cobotJoint, 16);
  j2.rotation.x = Math.PI / 2; shade(j2); elbow.add(j2);
  const fore = cyl(0.072, 0.072, 0.72, MAT.cobot, 14);
  fore.position.y = 0.36; shade(fore); elbow.add(fore);

  const wrist = new THREE.Group();
  wrist.position.y = 0.72; elbow.add(wrist);
  const j3 = cyl(0.09, 0.09, 0.14, MAT.cobotJoint, 14);
  j3.rotation.x = Math.PI / 2; shade(j3); wrist.add(j3);

  // gripper — two jaws that close on the barrel rim
  const grip = new THREE.Group();
  grip.position.y = 0.16; wrist.add(grip);
  const palm = box(0.26, 0.1, 0.2, MAT.cobot);
  shade(palm); grip.add(palm);
  const jaws = [];
  for (const s of [-1, 1]) {
    const jaw = box(0.06, 0.3, 0.16, MAT.steelDark);
    jaw.position.set(s * 0.13, 0.19, 0); shade(jaw); grip.add(jaw);
    jaws.push(jaw);
  }

  g.userData = { yaw, shoulder, elbow, wrist, grip, jaws };
  return g;
}

// Pose the arm from explicit joint angles (radians).
export function poseCobot(cobot, { yaw = 0, shoulder = 0, elbow = 0, wrist = 0, open = 1 } = {}) {
  const u = cobot.userData;
  u.yaw.rotation.y = yaw;
  u.shoulder.rotation.x = shoulder;
  u.elbow.rotation.x = elbow;
  u.wrist.rotation.x = wrist;
  u.jaws[0].position.x = -0.09 - open * 0.05;
  u.jaws[1].position.x = 0.09 + open * 0.05;
}

// ── MES / MO terminal ────────────────────────────────────────────────────
export function buildTerminal() {
  const g = new THREE.Group();
  const post = box(0.1, 1.35, 0.1, MAT.steelDark);
  post.position.y = 0.68; shade(post); g.add(post);
  const body = box(0.78, 0.56, 0.09, MAT.painted);
  body.position.y = 1.6; shade(body); g.add(body);
  const scr = box(0.66, 0.44, 0.03, MAT.screen);
  scr.position.set(0, 1.6, 0.06); g.add(scr);
  g.userData.screen = scr;
  return g;
}

// ── Falling-sand stream between two heights ──────────────────────────────
export function makeSandStream(radius = 0.1) {
  const g = new THREE.Group();
  const col = cyl(radius, radius * 1.25, 1, MAT.sand, 10);
  col.position.y = -0.5;
  g.add(col);
  g.userData.col = col;
  g.visible = false;
  return g;
}

// Position a stream from `topY` down to `bottomY` at (x, z).
export function setStream(stream, x, z, topY, bottomY) {
  const h = Math.max(0.001, topY - bottomY);
  stream.position.set(x, topY, z);
  stream.userData.col.scale.y = h;
  stream.userData.col.position.y = -h / 2;
}

// ── Lighting rig tuned for software rendering ────────────────────────────
export function addLighting(scene, renderer) {
  // Image-based lighting so the steel and painted equipment read as metal
  // rather than flat colour. One-time cost; nothing per frame.
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);
  scene.environment = envRT.texture;
  pmrem.dispose();

  const hemi = new THREE.HemisphereLight(0xb9cbe4, 0x2a2925, 0.34);
  scene.add(hemi);

  const ambient = new THREE.AmbientLight(0xffffff, 0.10);
  scene.add(ambient);

  // single shadow caster keeps software rendering affordable
  const key = new THREE.DirectionalLight(0xfff2da, 3.1);
  key.position.set(9, 15, 11);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.near = 4;
  key.shadow.camera.far = 48;
  key.shadow.camera.left = -20;
  key.shadow.camera.right = 20;
  key.shadow.camera.top = 16;
  key.shadow.camera.bottom = -12;
  key.shadow.bias = -0.0016;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x9fb8d8, 0.34);
  fill.position.set(-12, 8, 6);
  scene.add(fill);

  const back = new THREE.DirectionalLight(0x8fa8cc, 0.5);
  back.position.set(-4, 6, -14);
  scene.add(back);

  return { key, fill, back, hemi, ambient, envRT };
}

/**
 * Two-link inverse kinematics for the cobot.
 *
 * Hand-tuned joint angles put the gripper 2.8 m from the target it was supposed
 * to be holding over. Solving the angles from the target position instead means
 * the arm actually reaches what it is meant to reach, and stays correct if the
 * AMR parks somewhere slightly different.
 *
 * Rig: yaw about Y at the base; shoulder and elbow about X, so the arm swings
 * in the local YZ plane and yaw orients that plane.
 */
const L1 = 0.82;          // shoulder -> elbow
const L2 = 0.88;          // elbow -> gripper tip
const SHOULDER_Y = 0.26;  // shoulder height in cobot-local space
const _tl = new THREE.Vector3();

export function solveCobot(cobot, targetWorld, { open = 0, wristExtra = 0 } = {}) {
  _tl.copy(targetWorld);
  cobot.worldToLocal(_tl);

  const yaw = Math.atan2(_tl.x, _tl.z);
  const r = Math.hypot(_tl.x, _tl.z);
  const h = _tl.y - SHOULDER_Y;

  let d = Math.hypot(r, h);
  const dMin = Math.abs(L1 - L2) + 1e-3;
  const dMax = L1 + L2 - 1e-3;
  d = Math.min(dMax, Math.max(dMin, d));

  const cosElbow = (L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2);
  const elbowInterior = Math.acos(Math.min(1, Math.max(-1, cosElbow)));
  const elbow = Math.PI - elbowInterior;

  const cosA = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d);
  const a = Math.acos(Math.min(1, Math.max(-1, cosA)));
  const shoulder = Math.atan2(r, h) - a;

  poseCobot(cobot, { yaw, shoulder, elbow, wrist: -(shoulder + elbow) + wristExtra, open });
  return { yaw, shoulder, elbow, reached: Math.hypot(r, h) <= dMax };
}
