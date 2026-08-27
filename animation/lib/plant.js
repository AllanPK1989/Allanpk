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
import { makeMaterials } from './textures.js';

export const FLOOR_Y = 0;
export const MEZZ_Y  = 4.2;
export const MEZZ_X  = -4.5;     // mezzanine front edge
export const LIFT_POS   = new THREE.Vector3(-6, 0, -7);
export const MIXER_POS   = new THREE.Vector3(-1, 0, 0);
export const HOPPER_POS  = new THREE.Vector3(3.5, 0, 0);
export const FILLER_POS  = new THREE.Vector3(8.5, 0, 0);
export const RACK_POS     = new THREE.Vector3(-10, MEZZ_Y, -4);

// ── Materials ────────────────────────────────────────────────────────────
// Flat colours were the single biggest reason the first pass read as a diagram.
// These are real PBR materials with colour, roughness and normal maps — see
// textures.js. Solid colours are kept only for lamps and screens, where a
// texture would be wrong.
const solid = (c, r, m, extra = {}) =>
  new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m, envMapIntensity: 0.5, ...extra });

const TX = makeMaterials();

export const MAT = {
  concrete:  TX.concrete,
  concreteD: TX.concreteD,
  wall:      TX.wall,
  steel:     TX.steel,
  steelMatte:TX.steelMatte,
  steelDark: TX.steelDark,
  painted:   TX.painted,
  paintedLt: TX.paintedLt,
  yellow:    TX.yellow,
  safety:    solid(0xd8b02a, 0.82, 0.05),
  rubber:    TX.rubber,
  sand:      TX.sand,
  sandDark:  solid(0xa88954, 0.95, 0.0),
  bag:       TX.bag,
  barrel:    TX.painted,
  barrelRim: TX.steelDark,
  machineGreen: TX.machineGreen,
  amr:       TX.amrBody,
  amrTop:    TX.steelDark,
  cobot:     solid(0xe6e8ea, 0.38, 0.3),
  cobotJoint:solid(0x2b6ca8, 0.42, 0.5),
  hiVis:     solid(0xd6d53c, 0.82, 0.02),
  skin:      solid(0xc79b74, 0.8, 0.02),
  trouser:   solid(0x33425a, 0.9, 0.02),
  glass:     solid(0x8fb6cc, 0.12, 0.1, { transparent: true, opacity: 0.22 }),
  green:     solid(0x35c06a, 0.5, 0.1, { emissive: 0x1d7a40, emissiveIntensity: 1.1 }),
  red:       solid(0xd8453f, 0.5, 0.1, { emissive: 0x8a1f1b, emissiveIntensity: 1.1 }),
  amber:     solid(0xe8a32a, 0.5, 0.1, { emissive: 0x9c6408, emissiveIntensity: 1.1 }),
  screen:    solid(0x11202e, 0.35, 0.1, { emissive: 0x1d6ea8, emissiveIntensity: 0.9 }),
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

  // clerestory windows: a real bay has daylight, and the bright strips give
  // the back wall depth instead of reading as a flat panel
  for (let i = -3; i <= 3; i++) {
    const win = box(3.0, 1.5, 0.08, MAT.glass);
    win.position.set(i * 4.0, 7.0, -9.85); g.add(win);
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(3.0, 1.5),
      new THREE.MeshBasicMaterial({ color: 0xbdd6f2, transparent: true, opacity: 0.5 }));
    glow.position.set(i * 4.0, 7.0, -9.78); g.add(glow);
    const mull = box(0.08, 1.5, 0.12, MAT.steelDark);
    mull.position.set(i * 4.0, 7.0, -9.8); shade(mull); g.add(mull);
  }

  // cable tray + conduit along the back wall
  const tray = box(28, 0.12, 0.4, MAT.steelDark);
  tray.position.set(0, 5.6, -9.5); shade(tray); g.add(tray);
  for (const y of [5.2, 5.0]) {
    const pipe = cyl(0.07, 0.07, 28, MAT.steelDark, 10);
    pipe.rotation.z = Math.PI / 2; pipe.position.set(0, y, -9.55);
    shade(pipe); g.add(pipe);
  }
  for (let i = -6; i <= 6; i++) {
    const brk = box(0.08, 0.5, 0.3, MAT.steelDark);
    brk.position.set(i * 2.2, 5.35, -9.65); shade(brk); g.add(brk);
  }

  // column base plates and gussets
  for (const z of [-8, -4, 0, 4, 8]) {
    const bp = box(0.7, 0.06, 0.7, MAT.steelDark);
    bp.position.set(MEZZ_X - 0.4, 0.03, z); shade(bp); g.add(bp);
    for (const s of [-1, 1]) {
      const gus = box(0.05, 0.5, 0.34, MAT.steelDark);
      gus.position.set(MEZZ_X - 0.4 + s * 0.2, 0.3, z); shade(gus); g.add(gus);
    }
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
  for (const [x, z] of [[-0.95, -0.95], [0.95, -0.95], [-0.95, 0.95], [0.95, 0.95]]) {
    const c = box(0.12, 5.15, 0.12, MAT.steelDark);
    c.position.set(x, 2.58, z); shade(c); g.add(c);
  }
  const head = box(2.1, 0.14, 2.1, MAT.steelDark);
  head.position.set(0, 5.15, 0); shade(head); g.add(head);

  // rear + side mesh panels
  const back = box(2.0, 5.05, 0.05, MAT.glass);
  back.position.set(0, 2.55, -0.99); g.add(back);
  const side = box(0.05, 5.05, 2.0, MAT.glass);
  side.position.set(-0.99, 2.55, 0); g.add(side);

  // the car itself — animated by the scene
  const car = new THREE.Group();
  const deck = box(1.75, 0.12, 1.75, MAT.steel);
  deck.position.y = 0.07; shade(deck); car.add(deck);
  for (const side2 of [-0.85, 0.85]) {
    const w = box(0.06, 1.15, 1.75, MAT.steelDark);
    w.position.set(side2, 0.64, 0); shade(w); car.add(w);
  }
  const rear = box(1.75, 1.15, 0.06, MAT.steelDark);
  rear.position.set(0, 0.64, -0.85); shade(rear); car.add(rear);
  car.position.y = MEZZ_Y;
  g.add(car);

  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.09, 12, 12), MAT.green);
  lamp.position.set(1.08, 2.1, 0.95); g.add(lamp);

  // Car ceiling light: a diffuser panel plus the point light that sells it.
  // The shaft sits under the mezzanine slab, outside the key light, so without
  // this the whole descent reads as a dark box.
  const canopy = box(1.55, 0.06, 1.55, MAT.steelDark);
  canopy.position.y = 2.02; shade(canopy); car.add(canopy);
  const diffuser = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.04, 1.15),
    new THREE.MeshBasicMaterial({ color: 0xfff2d8 }));
  diffuser.position.y = 1.98; car.add(diffuser);
  const carLight = new THREE.PointLight(0xfff0d0, 11, 6.5, 2);
  carLight.position.set(0, 1.85, 0);
  car.add(carLight);
  for (const s of [-0.8, 0.8]) {
    const stanchion = box(0.06, 1.9, 0.06, MAT.steelDark);
    stanchion.position.set(s, 1.05, -0.82); shade(stanchion); car.add(stanchion);
  }

  // shaft head light so the landing is visible when the car is away
  const shaftLight = new THREE.PointLight(0xd8e4f4, 6, 7, 2);
  shaftLight.position.set(0, 4.9, 0);
  g.add(shaftLight);

  g.userData.carLight = carLight;
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
  // Long axis along +Z, handle at the back (-Z), so setting rotation.y to the
  // operator's own heading puts the handle in their hands.
  const g = new THREE.Group();
  const deck = box(0.78, 0.07, 1.15, MAT.steelMatte);
  deck.position.y = 0.34; shade(deck); g.add(deck);
  const lip = box(0.78, 0.05, 0.05, MAT.yellow);
  lip.position.set(0, 0.4, 0.57); shade(lip); g.add(lip);
  for (const s of [-0.33, 0.33]) {
    const up = cyl(0.022, 0.022, 0.62, MAT.steelDark, 8);
    up.position.set(s, 0.68, -0.55); shade(up); g.add(up);
  }
  const bar = cyl(0.028, 0.028, 0.72, MAT.rubber, 8);
  bar.rotation.z = Math.PI / 2;
  bar.position.set(0, 0.99, -0.55); shade(bar); g.add(bar);
  g.userData.handleY = 0.99;
  for (const [x, z] of [[-0.31, -0.45], [0.31, -0.45], [-0.31, 0.45], [0.31, 0.45]]) {
    const w = cyl(0.075, 0.075, 0.05, MAT.rubber, 12);
    w.rotation.z = Math.PI / 2; w.position.set(x, 0.075, z); shade(w); g.add(w);
    const fork = box(0.03, 0.14, 0.03, MAT.steelDark);
    fork.position.set(x, 0.17, z); shade(fork); g.add(fork);
  }
  return g;
}

// ── Sand mixing machine ──────────────────────────────────────────────────
/** Ring of bolt heads — cheap detail that makes a vessel read as fabricated. */
function boltRing(radius, y, count, r = 0.035, m = MAT.steelDark) {
  const g = new THREE.Group();
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const b = cyl(r, r, 0.05, m, 6);
    b.rotation.x = Math.PI / 2;
    b.position.set(Math.cos(a) * radius, y, Math.sin(a) * radius);
    b.rotation.z = a;
    shade(b); g.add(b);
  }
  return g;
}

export function buildMixer() {
  // Open-pan muller, matching the reference photo: green pan with a black top
  // rim, cross bridge with two threaded muller-wheel adjusters, ploughs inside,
  // a side discharge door on a long lever, and a black steel stand.
  //
  // This replaced a closed vessel with a dome and a small charge port. That
  // shape drove the whole charging sequence — climbing a platform to tip a bag
  // into a hatch — which is not how this machine is loaded. Sand goes straight
  // over the open rim.
  const g = new THREE.Group();
  g.position.copy(MIXER_POS);

  const R = 0.62;              // pan radius
  const PAN_BOT = 0.86;        // inside floor of the pan
  const PAN_TOP = 1.42;        // top of the green body
  const RIM_TOP = 1.52;        // top of the black rim band
  g.userData.rimY = RIM_TOP;
  g.userData.portY = RIM_TOP;
  g.userData.portX = 0;

  // ---- stand ----
  const basePlate = box(1.15, 0.06, 1.15, MAT.steelDark);
  basePlate.position.y = 0.03; shade(basePlate); g.add(basePlate);
  for (const [x, z] of [[-0.42, -0.42], [0.42, -0.42], [-0.42, 0.42], [0.42, 0.42]]) {
    const leg = box(0.075, 0.5, 0.075, MAT.steelDark);
    leg.position.set(x, 0.28, z); shade(leg); g.add(leg);
  }
  for (const z of [-0.42, 0.42]) {
    const brace = box(0.9, 0.05, 0.05, MAT.steelDark);
    brace.position.set(0, 0.16, z); shade(brace); g.add(brace);
  }

  // ---- lower cone: narrow at the bottom, opening up into the pan ----
  const cone = new THREE.Mesh(
    new THREE.CylinderGeometry(R, 0.34, 0.36, 26, 1, true), MAT.machineGreen);
  cone.material.side = THREE.DoubleSide;
  cone.position.y = 0.70; shade(cone); g.add(cone);

  // ---- pan body ----
  const pan = cyl(R, R, PAN_TOP - PAN_BOT + 0.02, MAT.machineGreen, 30);
  pan.position.y = (PAN_TOP + PAN_BOT) / 2; shade(pan); g.add(pan);

  // black rim band around the open top
  const rim = cyl(R + 0.025, R + 0.025, RIM_TOP - PAN_TOP, MAT.steelDark, 30);
  rim.position.y = (RIM_TOP + PAN_TOP) / 2; shade(rim); g.add(rim);

  // pan floor (visible down the open top)
  const floor = cyl(R - 0.02, R - 0.02, 0.05, MAT.steelDark, 26);
  floor.position.y = PAN_BOT; shade(floor); g.add(floor);

  // the charge (sand in the pan) — scaled by the scene
  const charge = cyl(R - 0.05, R - 0.05, 0.3, MAT.sand, 24);
  charge.position.y = PAN_BOT + 0.15; charge.scale.y = 0.001; g.add(charge);
  g.userData.charge = charge;

  // ---- lifting lugs ----
  for (const s of [-1, 1]) {
    const lug = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.018, 8, 16), MAT.steelDark);
    lug.position.set(s * (R + 0.02), RIM_TOP - 0.02, 0);
    lug.rotation.y = Math.PI / 2; shade(lug); g.add(lug);
  }

  // ---- cross bridge with the two threaded adjusters ----
  const bridge = new THREE.Group();
  bridge.position.y = RIM_TOP + 0.06;
  const beam = box(R * 2 + 0.14, 0.1, 0.24, MAT.machineGreen);
  shade(beam); bridge.add(beam);
  const beam2 = box(0.3, 0.09, 0.5, MAT.machineGreen);
  beam2.position.set(0.1, 0, 0); shade(beam2); bridge.add(beam2);
  for (const x of [-0.24, 0.26]) {
    const postB = box(0.13, 0.12, 0.13, MAT.steelDark);
    postB.position.set(x, 0.05, 0); shade(postB); bridge.add(postB);
    // threaded rod, drawn as stacked collars
    for (let i = 0; i < 9; i++) {
      const th = cyl(0.028, 0.028, 0.022, MAT.steelDark, 8);
      th.position.set(x, 0.13 + i * 0.032, 0); shade(th); bridge.add(th);
    }
    const cap = cyl(0.038, 0.038, 0.03, MAT.steelDark, 8);
    cap.position.set(x, 0.44, 0); shade(cap); bridge.add(cap);
  }
  g.add(bridge);

  // ---- rotating muller assembly inside the pan ----
  const rotor = new THREE.Group();
  rotor.position.y = PAN_BOT + 0.02;
  const hub = cyl(0.09, 0.09, 0.42, MAT.steelDark, 12);
  hub.position.y = 0.21; shade(hub); rotor.add(hub);
  for (const s of [-1, 1]) {
    // plough blade
    const arm = box(R - 0.1, 0.05, 0.06, MAT.steelDark);
    arm.position.set(s * (R - 0.1) / 2, 0.34, 0); shade(arm); rotor.add(arm);
    const blade = box(0.07, 0.2, 0.2, MAT.steelDark);
    blade.position.set(s * (R - 0.16), 0.14, 0);
    blade.rotation.y = s * 0.5; shade(blade); rotor.add(blade);
    // muller wheel
    const wheel = cyl(0.17, 0.17, 0.1, MAT.steelDark, 16);
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(s * (R - 0.26), 0.17, s * 0.22); shade(wheel); rotor.add(wheel);
  }
  g.add(rotor);
  g.userData.rotor = rotor;
  g.userData.shaft = rotor;   // kept so existing scene code still drives it

  // ---- discharge door and its lever ----
  const door = new THREE.Group();
  door.position.set(0, 0.62, R - 0.12);
  const plate = box(0.34, 0.3, 0.06, MAT.machineGreen);
  shade(plate); door.add(plate);
  const hinge = box(0.38, 0.05, 0.05, MAT.steelDark);
  hinge.position.y = 0.16; shade(hinge); door.add(hinge);
  g.add(door);
  g.userData.door = door;

  const lever = new THREE.Group();
  lever.position.set(0.12, 0.74, R - 0.02);
  const arm2 = cyl(0.022, 0.022, 0.72, MAT.steelDark, 8);
  arm2.rotation.z = Math.PI / 2;
  arm2.position.set(0.34, 0, 0); shade(arm2); lever.add(arm2);
  const grip = cyl(0.032, 0.032, 0.14, MAT.rubber, 8);
  grip.rotation.z = Math.PI / 2;
  grip.position.set(0.66, 0, 0); shade(grip); lever.add(grip);
  const pivot = cyl(0.05, 0.05, 0.08, MAT.steelDark, 10);
  pivot.rotation.x = Math.PI / 2; shade(pivot); lever.add(pivot);
  g.add(lever);
  g.userData.lever = lever;

  // discharge spout under the cone
  const spout = cyl(0.15, 0.15, 0.16, MAT.steelDark, 12);
  spout.position.y = 0.46; shade(spout); g.add(spout);
  g.userData.spoutY = 0.4;

  // drive motor on the stand
  const motor = cyl(0.15, 0.15, 0.3, MAT.steelDark, 14);
  motor.rotation.z = Math.PI / 2;
  motor.position.set(-0.62, 0.34, 0); shade(motor); g.add(motor);

  // control panel
  const panel = box(0.34, 0.42, 0.09, MAT.painted);
  panel.position.set(-1.05, 1.0, 0.45); shade(panel); g.add(panel);
  const scr = box(0.22, 0.16, 0.03, MAT.screen);
  scr.position.set(-1.05, 1.08, 0.5); g.add(scr);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.055, 10, 10), MAT.red);
  lamp.position.set(-1.05, 0.86, 0.5); g.add(lamp);
  g.userData.lamp = lamp;

  // kept for compatibility with existing scene code
  g.userData.portLid = bridge;
  g.userData.platformY = 0;

  return g;
}

// ── Sand filling machine ─────────────────────────────────────────────────
export function buildFiller() {
  // Four-station fuse sand-filling machine, from the reference diagram:
  // quartz sand hopper -> feed manifold -> four filling cylinders -> nozzles
  // into fuse bodies held in fixtures, over a sand spill tray, on a control
  // cabinet with castors and levelling feet, HMI on a side bracket.
  //
  // This replaced a generic hopper-and-conveyor machine. The product is fuse
  // bodies, not sacks, so the outfeed packs are gone.
  const g = new THREE.Group();
  g.position.copy(FILLER_POS);

  const W = 1.5, D = 0.78;
  const CAB_TOP = 0.80, DECK = 0.95, RAIL = 1.62;
  const HOP_BOT = 1.70, HOP_TOP = 1.95;
  g.userData.hopperRimY = HOP_TOP;

  // ---- castors and levelling feet ----
  for (const s of [-1, 1]) {
    const cas = cyl(0.075, 0.075, 0.05, MAT.rubber, 12);
    cas.rotation.z = Math.PI / 2;
    cas.position.set(s * (W / 2 - 0.1), 0.075, D / 2 - 0.1); shade(cas); g.add(cas);
    const yoke = box(0.07, 0.09, 0.09, MAT.steelDark);
    yoke.position.set(s * (W / 2 - 0.1), 0.15, D / 2 - 0.1); shade(yoke); g.add(yoke);

    const stem = cyl(0.03, 0.03, 0.16, MAT.steelDark, 8);
    stem.position.set(s * (W / 2 - 0.42), 0.1, D / 2 - 0.1); shade(stem); g.add(stem);
    const pad = cyl(0.075, 0.075, 0.025, MAT.steelDark, 10);
    pad.position.set(s * (W / 2 - 0.42), 0.02, D / 2 - 0.1); shade(pad); g.add(pad);
  }

  // ---- control cabinet ----
  const cab = box(W, CAB_TOP - 0.18, D, MAT.paintedLt);
  cab.position.y = (CAB_TOP + 0.18) / 2; shade(cab); g.add(cab);
  for (const s of [-1, 1]) {                       // twin doors with handles
    const door = box(W / 2 - 0.06, CAB_TOP - 0.3, 0.02, MAT.steelMatte);
    door.position.set(s * W / 4, (CAB_TOP + 0.18) / 2, D / 2 + 0.012);
    shade(door); g.add(door);
    const handle = box(0.02, 0.16, 0.025, MAT.steelDark);
    handle.position.set(s * 0.05, (CAB_TOP + 0.18) / 2, D / 2 + 0.03);
    shade(handle); g.add(handle);
  }

  // ---- open working frame above the cabinet ----
  for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const post = box(0.075, RAIL - CAB_TOP, 0.075, MAT.steelDark);
    post.position.set(x * (W / 2 - 0.05), (RAIL + CAB_TOP) / 2, z * (D / 2 - 0.05));
    shade(post); g.add(post);
  }
  const topRail = box(W, 0.07, D, MAT.steelDark);
  topRail.position.y = RAIL; shade(topRail); g.add(topRail);

  // ---- sand spill tray ----
  const tray = box(W - 0.16, 0.05, D - 0.18, MAT.steelMatte);
  tray.position.y = 0.87; shade(tray); g.add(tray);
  const spill = box(W - 0.22, 0.02, D - 0.24, MAT.sand);
  spill.position.y = 0.905; g.add(spill);

  // ---- station deck ----
  const deck = box(W - 0.12, 0.05, D - 0.2, MAT.steelDark);
  deck.position.y = DECK; shade(deck); g.add(deck);

  // ---- four filling stations ----
  const fuses = [];
  const xs = [-0.5, -0.17, 0.17, 0.5];
  for (const x of xs) {
    // holding fixture
    const shim = box(0.2, 0.03, 0.2, MAT.steelMatte);
    shim.position.set(x, DECK + 0.04, 0); shade(shim); g.add(shim);
    const fix = box(0.19, 0.15, 0.19, MAT.rubber);
    fix.position.set(x, DECK + 0.13, 0); shade(fix); g.add(fix);

    // fuse body + its sand fill
    const body = cyl(0.055, 0.055, 0.3, MAT.bag, 14);
    body.position.set(x, DECK + 0.35, 0); shade(body); g.add(body);
    const fill = cyl(0.048, 0.048, 0.28, MAT.sand, 12);
    fill.position.set(x, DECK + 0.34, 0); fill.scale.y = 0.001; g.add(fill);
    fuses.push(fill);

    const cap = cyl(0.07, 0.07, 0.035, MAT.steelMatte, 14);
    cap.position.set(x, DECK + 0.52, 0); shade(cap); g.add(cap);

    // filling nozzle
    const noz = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.03, 0.11, 12), MAT.steelMatte);
    noz.position.set(x, DECK + 0.60, 0); shade(noz); g.add(noz);
    const stem = cyl(0.02, 0.02, 0.12, MAT.steelMatte, 8);
    stem.position.set(x, DECK + 0.71, 0); shade(stem); g.add(stem);

    // filling cylinder + guide rod
    const cylBody = box(0.11, 0.24, 0.11, MAT.steelDark);
    cylBody.position.set(x, DECK + 0.9, 0); shade(cylBody); g.add(cylBody);
    const rod = box(0.025, 0.3, 0.025, MAT.steelMatte);
    rod.position.set(x + 0.08, DECK + 0.86, 0); shade(rod); g.add(rod);

    // feed hose curving down from the manifold
    const hose = new THREE.Mesh(new THREE.TubeGeometry(
      new THREE.CatmullRomCurve3([
        new THREE.Vector3(x - 0.14, HOP_BOT - 0.06, 0),
        new THREE.Vector3(x - 0.16, DECK + 1.12, 0.02),
        new THREE.Vector3(x - 0.02, DECK + 1.04, 0),
      ]), 14, 0.022, 8, false), MAT.rubber);
    shade(hose); g.add(hose);
  }
  g.userData.fuses = fuses;

  // ---- feed manifold ----
  const man = box(W - 0.24, 0.09, 0.26, MAT.steelMatte);
  man.position.y = HOP_BOT - 0.05; shade(man); g.add(man);

  // ---- quartz sand hopper (wide at the top, tapering into the manifold) ----
  const hop = new THREE.Mesh(
    new THREE.CylinderGeometry(0.78, 0.22, HOP_TOP - HOP_BOT, 4, 1, true), MAT.steelMatte);
  hop.material.side = THREE.DoubleSide;
  hop.rotation.y = Math.PI / 4;
  hop.scale.set(1.36, 1, 0.58);
  hop.position.y = (HOP_TOP + HOP_BOT) / 2; shade(hop); g.add(hop);
  const hopLip = box(W + 0.02, 0.045, 0.68, MAT.steelDark);
  hopLip.position.y = HOP_TOP; shade(hopLip); g.add(hopLip);

  // sand level inside the hopper
  const hopFill = new THREE.Mesh(
    new THREE.CylinderGeometry(0.72, 0.21, HOP_TOP - HOP_BOT - 0.05, 4), MAT.sand);
  hopFill.rotation.y = Math.PI / 4;
  hopFill.scale.set(1.36, 0.001, 0.58);
  hopFill.position.y = HOP_BOT + 0.02; g.add(hopFill);
  g.userData.hopFill = hopFill;

  // ---- HMI touchscreen on a side bracket ----
  const brk = box(0.16, 0.05, 0.05, MAT.steelDark);
  brk.position.set(-(W / 2 + 0.08), 1.32, 0.1); shade(brk); g.add(brk);
  const hmiBody = box(0.05, 0.3, 0.38, MAT.rubber);
  hmiBody.position.set(-(W / 2 + 0.18), 1.32, 0.1); shade(hmiBody); g.add(hmiBody);
  const hmiScr = box(0.02, 0.22, 0.3, MAT.screen);
  hmiScr.position.set(-(W / 2 + 0.21), 1.32, 0.1); g.add(hmiScr);
  g.userData.hmi = hmiScr;

  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.05, 10, 10), MAT.red);
  lamp.position.set(W / 2 - 0.12, 1.45, D / 2 - 0.05); g.add(lamp);
  g.userData.lamp = lamp;

  // step for the manual load in BEFORE — the hopper lip is at 2.12m
  const step = box(0.7, 0.22, 0.45, MAT.steelDark);
  step.position.set(-(W / 2 + 0.42), 0.11, 0.5); shade(step); g.add(step);
  g.userData.stepY = 0.22;

  // kept so existing scene code that referenced the old outfeed still runs
  g.userData.packs = new THREE.Group();
  g.add(g.userData.packs);

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

  // receiver + pump on a stand beside the muller, discharging over the open pan
  const post = box(0.12, 2.3, 0.12, MAT.steelDark);
  post.position.set(MIXER_POS.x - 1.15, 1.15, -0.5); shade(post); g.add(post);

  const rec = cyl(0.34, 0.34, 0.55, MAT.steel, 18);
  rec.position.set(MIXER_POS.x - 0.55, 2.45, -0.2); shade(rec); g.add(rec);
  const recCone = new THREE.Mesh(
    new THREE.CylinderGeometry(0.34, 0.12, 0.28, 18, 1, true), MAT.steel);
  recCone.material.side = THREE.DoubleSide;
  recCone.position.set(MIXER_POS.x - 0.55, 2.05, -0.2); shade(recCone); g.add(recCone);
  const pump = box(0.4, 0.32, 0.36, MAT.painted);
  pump.position.set(MIXER_POS.x - 0.55, 2.86, -0.2); shade(pump); g.add(pump);
  const arm = box(0.7, 0.09, 0.09, MAT.steelDark);
  arm.position.set(MIXER_POS.x - 0.85, 2.45, -0.35); shade(arm); g.add(arm);

  // suction hose from the intake wand up to the receiver
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(MIXER_POS.x + 1.9, 0.55, 1.5),
    new THREE.Vector3(MIXER_POS.x + 1.4, 1.5, 1.2),
    new THREE.Vector3(MIXER_POS.x + 0.3, 2.4, 0.5),
    new THREE.Vector3(MIXER_POS.x - 0.5, 2.62, -0.1),
  ]);
  const hose = new THREE.Mesh(new THREE.TubeGeometry(curve, 26, 0.1, 10, false), MAT.rubber);
  shade(hose); g.add(hose);

  const wand = cyl(0.08, 0.08, 0.55, MAT.steelDark, 12);
  wand.position.set(MIXER_POS.x + 1.9, 0.3, 1.5); shade(wand); g.add(wand);
  g.userData.wand = wand;

  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.07, 10, 10), MAT.red);
  lamp.position.set(MIXER_POS.x - 0.55, 3.06, 0.0); g.add(lamp);
  g.userData.lamp = lamp;
  return g;
}

// ── Operator figure with a simple walk cycle ─────────────────────────────
export function makeOperator() {
  const g = new THREE.Group();

  const hips = new THREE.Group();
  hips.position.y = 0.94; g.add(hips);

  // torso tapers and has real depth — the flat slab read as a cardboard cutout
  const pelvis = cyl(0.155, 0.15, 0.2, MAT.trouser, 12);
  pelvis.position.y = 0.09; shade(pelvis); hips.add(pelvis);

  const chest = cyl(0.19, 0.155, 0.44, MAT.hiVis, 14);
  chest.position.y = 0.4; shade(chest); hips.add(chest);

  // hi-vis vest sits proud of the shirt, with reflective bands
  const vest = cyl(0.198, 0.168, 0.34, MAT.hiVis, 14);
  vest.position.y = 0.4; shade(vest); hips.add(vest);
  for (const y of [0.34, 0.47]) {
    const band = cyl(0.202, 0.185, 0.045, MAT.steel, 14);
    band.position.y = y; shade(band); hips.add(band);
  }

  const shoulders = cyl(0.2, 0.2, 0.12, MAT.hiVis, 14);
  shoulders.rotation.z = Math.PI / 2;
  shoulders.scale.set(1, 1.85, 1);
  shoulders.position.y = 0.6; shade(shoulders); hips.add(shoulders);

  const neck = cyl(0.055, 0.06, 0.09, MAT.skin, 10);
  neck.position.y = 0.68; shade(neck); hips.add(neck);

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.105, 16, 14), MAT.skin);
  head.scale.set(0.92, 1.1, 1.0);
  head.position.y = 0.79; shade(head); hips.add(head);

  const helmet = new THREE.Mesh(
    new THREE.SphereGeometry(0.125, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2), MAT.yellow);
  helmet.scale.set(1, 0.92, 1.06);
  helmet.position.y = 0.805; shade(helmet); hips.add(helmet);
  const brim = cyl(0.135, 0.135, 0.018, MAT.yellow, 16);
  brim.scale.set(1, 1, 1.25);
  brim.position.set(0, 0.803, 0.03); shade(brim); hips.add(brim);

  const arms = [], legs = [];
  for (const s of [-1, 1]) {
    const shoulder = new THREE.Group();
    shoulder.position.set(s * 0.215, 0.575, 0); hips.add(shoulder);

    const upper = cyl(0.058, 0.05, 0.3, MAT.hiVis, 10);
    upper.position.y = -0.15; shade(upper); shoulder.add(upper);

    const elbow = new THREE.Group();
    elbow.position.y = -0.3; shoulder.add(elbow);
    const fore = cyl(0.05, 0.043, 0.28, MAT.skin, 10);
    fore.position.y = -0.14; shade(fore); elbow.add(fore);
    const glove = new THREE.Mesh(new THREE.SphereGeometry(0.058, 10, 8), MAT.painted);
    glove.scale.set(1, 1.25, 0.8);
    glove.position.y = -0.3; shade(glove); elbow.add(glove);

    arms.push(shoulder);
    shoulder.userData.elbow = elbow;

    const hip = new THREE.Group();
    hip.position.set(s * 0.105, 0, 0); hips.add(hip);
    const thigh = cyl(0.082, 0.068, 0.46, MAT.trouser, 10);
    thigh.position.y = -0.23; shade(thigh); hip.add(thigh);

    const knee = new THREE.Group();
    knee.position.y = -0.46; hip.add(knee);
    const shin = cyl(0.065, 0.055, 0.44, MAT.trouser, 10);
    shin.position.y = -0.22; shade(shin); knee.add(shin);
    const boot = box(0.105, 0.085, 0.24, MAT.rubber);
    boot.position.set(0, -0.47, 0.045); shade(boot); knee.add(boot);

    legs.push(hip);
    hip.userData.knee = knee;
  }

  g.userData = { hips, arms, legs, head, helmet };
  return g;
}

// Drive the walk cycle. `speed` 0 = idle.
export function poseWalk(op, phase, speed = 1) {
  const { arms, legs, hips } = op.userData;
  const a = Math.sin(phase) * 0.62 * speed;
  legs[0].rotation.x = a;
  legs[1].rotation.x = -a;
  // knees only bend backwards, and most on the recovery stroke
  legs[0].userData.knee.rotation.x = -Math.max(0, -a * 1.5) - 0.06 * speed;
  legs[1].userData.knee.rotation.x = -Math.max(0,  a * 1.5) - 0.06 * speed;
  arms[0].rotation.x = -a * 0.75;
  arms[1].rotation.x = a * 0.75;
  arms[0].userData.elbow.rotation.x = -0.28 * speed;
  arms[1].userData.elbow.rotation.x = -0.28 * speed;
  hips.position.y = 0.94 + Math.abs(Math.sin(phase)) * 0.032 * speed;
  hips.rotation.z = Math.sin(phase) * 0.03 * speed;
}

// Both arms forward, as if carrying a load.
export function poseCarry(op, t = 1) {
  const { arms } = op.userData;
  for (const a of arms) {
    a.rotation.x = -1.15 * t;
    a.userData.elbow.rotation.x = -0.85 * t;
  }
}

// Both arms raised overhead, as if lifting to a high port.
export function poseLift(op, t = 1) {
  const { arms } = op.userData;
  for (const a of arms) {
    a.rotation.x = -2.35 * t;
    a.userData.elbow.rotation.x = -0.45 * t;
  }
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

  const hemi = new THREE.HemisphereLight(0xa8c2e0, 0x241f18, 0.30);
  scene.add(hemi);

  const ambient = new THREE.AmbientLight(0xffffff, 0.055);
  scene.add(ambient);

  // single shadow caster keeps software rendering affordable
  const key = new THREE.DirectionalLight(0xffeacc, 3.6);
  key.position.set(9, 15, 11);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.near = 4;
  key.shadow.camera.far = 48;
  key.shadow.camera.left = -20;
  key.shadow.camera.right = 20;
  key.shadow.camera.top = 16;
  key.shadow.camera.bottom = -12;
  key.shadow.bias = -0.0009;
  key.shadow.normalBias = 0.02;
  key.shadow.radius = 2.2;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x86a6cf, 0.42);
  fill.position.set(-12, 8, 6);
  scene.add(fill);

  const back = new THREE.DirectionalLight(0x7f9ec6, 0.62);
  back.position.set(-4, 6, -14);
  scene.add(back);

  // practical high-bay lights over the aisle: adds falloff and pooling that a
  // purely directional rig never produces
  for (const x of [-8, -1, 6, 12]) {
    const bay = new THREE.PointLight(0xffe6c0, 26, 15, 2);
    bay.position.set(x, 7.6, 1);
    scene.add(bay);
  }

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

/** Both arms out and down, hands on a trolley handle. */
export function posePush(op, t = 1) {
  const { arms } = op.userData;
  for (const a of arms) {
    a.rotation.x = -1.0 * t;
    a.userData.elbow.rotation.x = -0.2 * t;   // near-straight, leaning into the load
  }
}

/** Heavier trolley for moving a drum. */
export function makeDrumTrolley() {
  // Same convention: long axis +Z, handle at the back.
  const g = new THREE.Group();
  const deck = box(0.85, 0.08, 1.0, MAT.steelDark);
  deck.position.y = 0.3; shade(deck); g.add(deck);
  const kerb = box(0.85, 0.06, 0.05, MAT.yellow);
  kerb.position.set(0, 0.37, 0.49); shade(kerb); g.add(kerb);
  for (const s of [-0.36, 0.36]) {
    const up = cyl(0.024, 0.024, 0.66, MAT.painted, 8);
    up.position.set(s, 0.65, -0.48); shade(up); g.add(up);
  }
  const bar = cyl(0.03, 0.03, 0.78, MAT.rubber, 8);
  bar.rotation.z = Math.PI / 2;
  bar.position.set(0, 0.99, -0.48); shade(bar); g.add(bar);
  g.userData.handleY = 0.99;
  for (const [x, z] of [[-0.34, -0.38], [0.34, -0.38], [-0.34, 0.38], [0.34, 0.38]]) {
    const w = cyl(0.08, 0.08, 0.055, MAT.rubber, 12);
    w.rotation.z = Math.PI / 2; w.position.set(x, 0.08, z); shade(w); g.add(w);
  }
  return g;
}
