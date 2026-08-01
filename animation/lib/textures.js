// Procedural PBR textures, generated on canvas at load time.
//
// The first version of these scenes used flat single-colour materials — no map,
// no roughnessMap, no normalMap — which is exactly why every surface read as a
// diagram rather than a real one. Real surfaces have grain, wear and variation
// in how shiny they are across the same panel. That variation is what the eye
// reads as "material", far more than the base colour.
//
// Everything here is generated procedurally: no external image assets, so the
// scenes still run offline, and no download cost.

import * as THREE from 'three';

const TAU = Math.PI * 2;

function canvas(size) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  return c;
}

function tex(c, repeat = 1) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.anisotropy = 8;
  return t;
}

function colorTex(c, repeat = 1) {
  const t = tex(c, repeat);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Value noise, smoothed by drawing soft blobs. Cheap and good enough. */
function blobNoise(ctx, size, count, radius, alpha, hue) {
  for (let i = 0; i < count; i++) {
    const x = Math.random() * size, y = Math.random() * size;
    const r = radius * (0.4 + Math.random() * 1.2);
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    const a = alpha * (0.3 + Math.random() * 0.7);
    g.addColorStop(0, `rgba(${hue},${a})`);
    g.addColorStop(1, `rgba(${hue},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
}

/**
 * Derive a tangent-space normal map from a greyscale height canvas via Sobel.
 * Gives surfaces real relief under the moving key light instead of looking
 * like printed-on decals.
 */
function normalFromHeight(heightCanvas, strength = 2.0) {
  const size = heightCanvas.width;
  const src = heightCanvas.getContext('2d').getImageData(0, 0, size, size).data;
  const out = canvas(size);
  const dst = out.getContext('2d').createImageData(size, size);

  const at = (x, y) => {
    const xi = (x + size) % size, yi = (y + size) % size;
    return src[(yi * size + xi) * 4] / 255;
  };

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const tl = at(x - 1, y - 1), t = at(x, y - 1), tr = at(x + 1, y - 1);
      const l  = at(x - 1, y),                        r = at(x + 1, y);
      const bl = at(x - 1, y + 1), b = at(x, y + 1), br = at(x + 1, y + 1);
      const dx = (tr + 2 * r + br) - (tl + 2 * l + bl);
      const dy = (bl + 2 * b + br) - (tl + 2 * t + tr);
      let nx = -dx * strength, ny = -dy * strength, nz = 1;
      const len = Math.hypot(nx, ny, nz);
      nx /= len; ny /= len; nz /= len;
      const i = (y * size + x) * 4;
      dst.data[i]     = (nx * 0.5 + 0.5) * 255;
      dst.data[i + 1] = (ny * 0.5 + 0.5) * 255;
      dst.data[i + 2] = (nz * 0.5 + 0.5) * 255;
      dst.data[i + 3] = 255;
    }
  }
  out.getContext('2d').putImageData(dst, 0, 0);
  return out;
}

// ── Concrete floor: stains, patch marks, fine aggregate ──────────────────
function concreteMaps(size = 512) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = '#5a5d61'; ctx.fillRect(0, 0, size, size);
  blobNoise(ctx, size, 90, size * 0.13, 0.16, '30,32,35');   // dirt
  blobNoise(ctx, size, 60, size * 0.09, 0.10, '120,124,130'); // patches
  blobNoise(ctx, size, 26, size * 0.20, 0.09, '20,18,14');    // oil stains
  // aggregate speckle
  for (let i = 0; i < size * 7; i++) {
    ctx.fillStyle = `rgba(${20 + Math.random() * 150},${20 + Math.random() * 150},${20 + Math.random() * 150},0.16)`;
    ctx.fillRect(Math.random() * size, Math.random() * size, 1.4, 1.4);
  }
  // control joints
  ctx.strokeStyle = 'rgba(20,22,25,0.55)'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(0, size / 2); ctx.lineTo(size, size / 2);
  ctx.moveTo(size / 2, 0); ctx.lineTo(size / 2, size); ctx.stroke();

  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#d8d8d8'; rctx.fillRect(0, 0, size, size);
  blobNoise(rctx, size, 70, size * 0.16, 0.30, '90,90,90');   // polished/worn = smoother
  blobNoise(rctx, size, 30, size * 0.10, 0.25, '255,255,255');

  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 4; i++) {
    hctx.fillStyle = `rgba(${Math.random() > 0.5 ? '255,255,255' : '0,0,0'},0.10)`;
    hctx.fillRect(Math.random() * size, Math.random() * size, 2, 2);
  }
  return { col, rough, h };
}

// ── Brushed / galvanised steel ───────────────────────────────────────────
function steelMaps(size = 512) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = '#9aa1a9'; ctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 2.2; i++) {                     // brush streaks
    const y = Math.random() * size;
    ctx.strokeStyle = `rgba(${Math.random() > 0.5 ? '255,255,255' : '40,44,50'},${0.03 + Math.random() * 0.07})`;
    ctx.lineWidth = 0.6 + Math.random() * 1.6;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(size, y + (Math.random() - 0.5) * 5); ctx.stroke();
  }
  blobNoise(ctx, size, 26, size * 0.14, 0.07, '70,66,58');    // faint grime

  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#6e6e6e'; rctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 1.6; i++) {
    const y = Math.random() * size;
    rctx.strokeStyle = `rgba(${Math.random() > 0.5 ? '255,255,255' : '0,0,0'},0.10)`;
    rctx.lineWidth = 1 + Math.random() * 2;
    rctx.beginPath(); rctx.moveTo(0, y); rctx.lineTo(size, y); rctx.stroke();
  }
  blobNoise(rctx, size, 34, size * 0.12, 0.28, '190,190,190');

  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 1.4; i++) {
    const y = Math.random() * size;
    hctx.strokeStyle = `rgba(${Math.random() > 0.5 ? '255,255,255' : '0,0,0'},0.08)`;
    hctx.lineWidth = 1;
    hctx.beginPath(); hctx.moveTo(0, y); hctx.lineTo(size, y); hctx.stroke();
  }
  return { col, rough, h };
}

// ── Painted equipment steel: orange peel, chips, edge wear ───────────────
function paintedMaps(hex = '#2f6f9e', size = 512) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = hex; ctx.fillRect(0, 0, size, size);
  blobNoise(ctx, size, 220, size * 0.022, 0.06, '255,255,255'); // orange peel
  blobNoise(ctx, size, 190, size * 0.024, 0.07, '0,0,0');
  blobNoise(ctx, size, 26, size * 0.06, 0.08, '60,50,35');       // grime runs
  for (let i = 0; i < 90; i++) {                                  // paint chips
    const x = Math.random() * size, y = Math.random() * size;
    const r = 1 + Math.random() * 3.4;
    ctx.fillStyle = `rgba(150,152,155,${0.25 + Math.random() * 0.4})`;
    ctx.beginPath(); ctx.ellipse(x, y, r, r * (0.5 + Math.random()), Math.random() * TAU, 0, TAU);
    ctx.fill();
  }

  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#8c8c8c'; rctx.fillRect(0, 0, size, size);
  blobNoise(rctx, size, 140, size * 0.05, 0.26, '210,210,210');
  blobNoise(rctx, size, 120, size * 0.04, 0.22, '60,60,60');

  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  blobNoise(hctx, size, 130, size * 0.045, 0.16, '255,255,255');
  blobNoise(hctx, size, 110, size * 0.045, 0.16, '0,0,0');
  return { col, rough, h };
}

// ── Rubber / dark polymer ────────────────────────────────────────────────
function rubberMaps(size = 256) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = '#24272b'; ctx.fillRect(0, 0, size, size);
  blobNoise(ctx, size, 60, size * 0.08, 0.10, '90,92,96');
  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#e2e2e2'; rctx.fillRect(0, 0, size, size);
  blobNoise(rctx, size, 40, size * 0.09, 0.18, '160,160,160');
  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 3; i++) {
    hctx.fillStyle = `rgba(${Math.random() > 0.5 ? '255,255,255' : '0,0,0'},0.12)`;
    hctx.fillRect(Math.random() * size, Math.random() * size, 2, 2);
  }
  return { col, rough, h };
}

// ── Sand: fine grain ─────────────────────────────────────────────────────
function sandMaps(size = 256) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = '#c2a06a'; ctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 20; i++) {
    const g = Math.random();
    ctx.fillStyle = g > 0.5
      ? `rgba(215,190,140,${0.10 + Math.random() * 0.25})`
      : `rgba(120,96,58,${0.10 + Math.random() * 0.25})`;
    ctx.fillRect(Math.random() * size, Math.random() * size, 1.6, 1.6);
  }
  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#f0f0f0'; rctx.fillRect(0, 0, size, size);
  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * 14; i++) {
    hctx.fillStyle = `rgba(${Math.random() > 0.5 ? '255,255,255' : '0,0,0'},0.22)`;
    hctx.fillRect(Math.random() * size, Math.random() * size, 1.6, 1.6);
  }
  return { col, rough, h };
}

// ── Woven bag / paper sack ───────────────────────────────────────────────
function bagMaps(size = 256) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = '#d8cfba'; ctx.fillRect(0, 0, size, size);
  ctx.strokeStyle = 'rgba(120,110,92,0.16)'; ctx.lineWidth = 1;
  for (let i = 0; i < size; i += 4) {                            // weave
    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(size, i); ctx.stroke();
  }
  blobNoise(ctx, size, 30, size * 0.10, 0.10, '110,100,80');
  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#e6e6e6'; rctx.fillRect(0, 0, size, size);
  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  hctx.strokeStyle = 'rgba(255,255,255,0.22)'; hctx.lineWidth = 1;
  for (let i = 0; i < size; i += 4) {
    hctx.beginPath(); hctx.moveTo(i, 0); hctx.lineTo(i, size); hctx.stroke();
  }
  hctx.strokeStyle = 'rgba(0,0,0,0.22)';
  for (let i = 2; i < size; i += 4) {
    hctx.beginPath(); hctx.moveTo(0, i); hctx.lineTo(size, i); hctx.stroke();
  }
  return { col, rough, h };
}

// ── Ribbed wall cladding ─────────────────────────────────────────────────
function claddingMaps(size = 512) {
  const col = canvas(size), ctx = col.getContext('2d');
  ctx.fillStyle = '#69707a'; ctx.fillRect(0, 0, size, size);
  for (let x = 0; x < size; x += 32) {
    const g = ctx.createLinearGradient(x, 0, x + 32, 0);
    g.addColorStop(0,   'rgba(255,255,255,0.10)');
    g.addColorStop(0.5, 'rgba(0,0,0,0.00)');
    g.addColorStop(1,   'rgba(0,0,0,0.16)');
    ctx.fillStyle = g; ctx.fillRect(x, 0, 32, size);
  }
  blobNoise(ctx, size, 40, size * 0.12, 0.10, '40,38,34');
  const rough = canvas(size), rctx = rough.getContext('2d');
  rctx.fillStyle = '#c0c0c0'; rctx.fillRect(0, 0, size, size);
  blobNoise(rctx, size, 40, size * 0.12, 0.20, '160,160,160');
  const h = canvas(size), hctx = h.getContext('2d');
  hctx.fillStyle = '#808080'; hctx.fillRect(0, 0, size, size);
  for (let x = 0; x < size; x += 32) {
    const g = hctx.createLinearGradient(x, 0, x + 32, 0);
    g.addColorStop(0, '#ffffff'); g.addColorStop(0.5, '#808080'); g.addColorStop(1, '#101010');
    hctx.fillStyle = g; hctx.fillRect(x, 0, 32, size);
  }
  return { col, rough, h };
}

/**
 * Build a textured MeshStandardMaterial. `repeat` is in texture tiles per
 * world unit-ish; tune per surface so the grain sits at a believable scale.
 */
function build(maps, { repeat = 1, roughness = 1, metalness = 0, normalScale = 1, color = 0xffffff, ...rest }) {
  const m = new THREE.MeshStandardMaterial({
    color,
    map: colorTex(maps.col, repeat),
    roughnessMap: tex(maps.rough, repeat),
    normalMap: tex(normalFromHeight(maps.h, 2.2), repeat),
    roughness, metalness,
    envMapIntensity: 0.5,
    ...rest,
  });
  m.normalScale = new THREE.Vector2(normalScale, normalScale);
  return m;
}

/** All scene materials, textured. Built once at load. */
export function makeMaterials() {
  const concrete = concreteMaps();
  const steel    = steelMaps();
  const rubber   = rubberMaps();
  const sand     = sandMaps();
  const bag      = bagMaps();
  const clad     = claddingMaps();
  const blue     = paintedMaps('#2f6f9e');
  const blueLt   = paintedMaps('#4a90c4');
  const yellow   = paintedMaps('#d9a32a');
  const dark     = paintedMaps('#3a4048');

  return {
    concrete:  build(concrete, { repeat: 26,  roughness: 0.94, metalness: 0.02, normalScale: 0.8 }),
    concreteD: build(concrete, { repeat: 15,  roughness: 0.95, metalness: 0.02, normalScale: 0.7, color: 0x8d9196 }),
    wall:      build(clad,     { repeat: 17,  roughness: 0.86, metalness: 0.15, normalScale: 1.1 }),
    steel:     build(steel,    { repeat: 3,  roughness: 0.42, metalness: 0.88, normalScale: 0.55 }),
    steelMatte:build(steel,    { repeat: 3,  roughness: 0.62, metalness: 0.65, normalScale: 0.6, color: 0xc8ced6 }),
    steelDark: build(steel,    { repeat: 3,  roughness: 0.52, metalness: 0.8,  normalScale: 0.6, color: 0x7d838b }),
    painted:   build(blue,     { repeat: 4,  roughness: 0.5,  metalness: 0.35, normalScale: 0.7 }),
    paintedLt: build(blueLt,   { repeat: 4,  roughness: 0.5,  metalness: 0.3,  normalScale: 0.7 }),
    yellow:    build(yellow,   { repeat: 4,  roughness: 0.58, metalness: 0.2,  normalScale: 0.7 }),
    amrBody:   build(dark,     { repeat: 4,  roughness: 0.42, metalness: 0.5,  normalScale: 0.7 }),
    rubber:    build(rubber,   { repeat: 2,  roughness: 0.95, metalness: 0.04, normalScale: 0.9 }),
    sand:      build(sand,     { repeat: 3,  roughness: 0.97, metalness: 0.0,  normalScale: 1.2 }),
    bag:       build(bag,      { repeat: 3,  roughness: 0.9,  metalness: 0.02, normalScale: 1.0 }),
  };
}
