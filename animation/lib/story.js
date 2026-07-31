// Deterministic timeline for the plant animations.
//
// Everything is a pure function of story time `t`. Nothing reads a clock and
// nothing accumulates state between frames, so rendering frame N offline gives
// exactly the same image as scrubbing to that time interactively. That is what
// makes frame-by-frame MP4 capture correct on a machine too slow to run in
// real time.

import * as THREE from 'three';

// ── Easing ───────────────────────────────────────────────────────────────
export const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
export const smooth  = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
export const smoother = (x) => { x = clamp01(x); return x * x * x * (x * (x * 6 - 15) + 10); };
export const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
export const easeIn  = (x) => Math.pow(clamp01(x), 3);

/** Progress 0..1 through the window [t0, t1]; clamped outside it. */
export const seg = (t, t0, t1) => clamp01((t - t0) / Math.max(1e-6, t1 - t0));

/** Eased progress through [t0, t1]. */
export const segS = (t, t0, t1) => smooth(seg(t, t0, t1));

/** 1 while t is inside [t0, t1], else 0 — with soft edges of width `fade`. */
export function pulse(t, t0, t1, fade = 0.3) {
  return Math.min(smooth(seg(t, t0, t0 + fade)), 1 - smooth(seg(t, t1 - fade, t1)));
}

/** Interpolate scalar keyframes: track(t, [[time, value], ...]) */
export function track(t, keys, ease = smooth) {
  if (t <= keys[0][0]) return keys[0][1];
  const last = keys[keys.length - 1];
  if (t >= last[0]) return last[1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [ta, va] = keys[i], [tb, vb] = keys[i + 1];
    if (t >= ta && t <= tb) return va + (vb - va) * ease(seg(t, ta, tb));
  }
  return last[1];
}

/** Interpolate Vector3 keyframes into `out`: [[time, [x,y,z]], ...] */
const _a = new THREE.Vector3(), _b = new THREE.Vector3();
export function trackVec(t, keys, out, ease = smooth) {
  if (t <= keys[0][0]) return out.fromArray(keys[0][1]);
  const last = keys[keys.length - 1];
  if (t >= last[0]) return out.fromArray(last[1]);
  for (let i = 0; i < keys.length - 1; i++) {
    const [ta, va] = keys[i], [tb, vb] = keys[i + 1];
    if (t >= ta && t <= tb) {
      _a.fromArray(va); _b.fromArray(vb);
      return out.copy(_a).lerp(_b, ease(seg(t, ta, tb)));
    }
  }
  return out.fromArray(last[1]);
}

/**
 * Move along a polyline of waypoints over [t0, t1], writing position into
 * `obj` and turning it to face travel direction. Returns distance travelled,
 * which callers use to drive wheel spin or a walk cycle.
 */
const _p = new THREE.Vector3(), _q = new THREE.Vector3();
export function followPath(obj, path, u, { turn = true, turnRate = 1 } = {}) {
  // cumulative lengths
  let total = 0;
  const segs = [];
  for (let i = 0; i < path.length - 1; i++) {
    _p.fromArray(path[i]); _q.fromArray(path[i + 1]);
    const d = _p.distanceTo(_q);
    segs.push(d); total += d;
  }
  const want = clamp01(u) * total;
  let acc = 0;
  for (let i = 0; i < segs.length; i++) {
    if (want <= acc + segs[i] || i === segs.length - 1) {
      const local = segs[i] < 1e-6 ? 0 : (want - acc) / segs[i];
      _p.fromArray(path[i]); _q.fromArray(path[i + 1]);
      obj.position.copy(_p).lerp(_q, clamp01(local));
      if (turn) {
        const dx = _q.x - _p.x, dz = _q.z - _p.z;
        if (Math.abs(dx) > 1e-5 || Math.abs(dz) > 1e-5) {
          const want2 = Math.atan2(dx, dz);
          // shortest-arc blend so the unit doesn't spin the long way round
          let d = want2 - obj.rotation.y;
          while (d > Math.PI) d -= Math.PI * 2;
          while (d < -Math.PI) d += Math.PI * 2;
          obj.rotation.y += d * clamp01(turnRate);
        }
      }
      return want;
    }
    acc += segs[i];
  }
  return want;
}

/** Total length of a waypoint polyline. */
export function pathLength(path) {
  let total = 0;
  for (let i = 0; i < path.length - 1; i++) {
    _p.fromArray(path[i]); _q.fromArray(path[i + 1]);
    total += _p.distanceTo(_q);
  }
  return total;
}

// ── Camera rig ───────────────────────────────────────────────────────────
export class CameraRig {
  /** keys: [{ t, pos:[x,y,z], target:[x,y,z] }, ...] sorted by t */
  constructor(camera, keys) {
    this.camera = camera;
    this.posKeys    = keys.map((k) => [k.t, k.pos]);
    this.targetKeys = keys.map((k) => [k.t, k.target]);
    this._p = new THREE.Vector3();
    this._t = new THREE.Vector3();
  }
  setTime(t) {
    trackVec(t, this.posKeys, this._p, smoother);
    trackVec(t, this.targetKeys, this._t, smoother);
    this.camera.position.copy(this._p);
    this.camera.lookAt(this._t);
  }
  get target() { return this._t; }
}

// ── Timeline / step model ────────────────────────────────────────────────
export class Timeline {
  /** steps: [{ t0, t1, title, note }] */
  constructor(steps) {
    this.steps = steps;
    this.duration = steps[steps.length - 1].t1;
  }
  indexAt(t) {
    for (let i = 0; i < this.steps.length; i++) {
      if (t < this.steps[i].t1) return i;
    }
    return this.steps.length - 1;
  }
  stepAt(t) { return this.steps[this.indexAt(t)]; }
}

// ── Overlay UI ───────────────────────────────────────────────────────────
export function buildUI(root, { title, subtitle, timeline, onSeek, onToggle, onStep, accent = '#4aa3e0' }) {
  root.innerHTML = `
    <div class="hdr">
      <div class="ttl">${title}</div>
      <div class="sub">${subtitle}</div>
    </div>
    <div class="steps"></div>
    <div class="bar">
      <button class="btn" data-act="prev" title="Previous step">◀</button>
      <button class="btn play" data-act="play" title="Play / pause">❚❚</button>
      <button class="btn" data-act="next" title="Next step">▶</button>
      <input class="scrub" type="range" min="0" max="1000" value="0">
      <div class="time">0.0s</div>
    </div>
    <div class="caption"><b class="cap-t"></b><span class="cap-n"></span></div>
  `;

  const stepsEl = root.querySelector('.steps');
  timeline.steps.forEach((s, i) => {
    const d = document.createElement('div');
    d.className = 'step';
    d.dataset.i = i;
    d.innerHTML = `<i>${String(i + 1).padStart(2, '0')}</i><span>${s.title}</span>`;
    d.addEventListener('click', () => onSeek(s.t0 + 0.01));
    stepsEl.appendChild(d);
  });

  const scrub = root.querySelector('.scrub');
  const timeEl = root.querySelector('.time');
  const capT = root.querySelector('.cap-t');
  const capN = root.querySelector('.cap-n');
  const playBtn = root.querySelector('.play');

  scrub.addEventListener('input', () => onSeek((scrub.value / 1000) * timeline.duration));
  root.querySelector('[data-act="prev"]').addEventListener('click', () => onStep(-1));
  root.querySelector('[data-act="next"]').addEventListener('click', () => onStep(1));
  playBtn.addEventListener('click', () => onToggle());

  root.style.setProperty('--accent', accent);

  let lastIdx = -1;
  return {
    sync(t, playing) {
      scrub.value = String((t / timeline.duration) * 1000);
      timeEl.textContent = t.toFixed(1) + 's';
      playBtn.textContent = playing ? '❚❚' : '▶';
      const i = timeline.indexAt(t);
      if (i !== lastIdx) {
        lastIdx = i;
        const s = timeline.steps[i];
        capT.textContent = `Step ${i + 1} — ${s.title}`;
        capN.textContent = s.note ? ' · ' + s.note : '';
        stepsEl.querySelectorAll('.step').forEach((el, j) =>
          el.classList.toggle('on', j === i));
        const active = stepsEl.querySelector('.step.on');
        if (active) active.scrollIntoView({ block: 'nearest' });
      }
    },
  };
}

export const UI_CSS = `
  :root { color-scheme: dark; --accent: #4aa3e0; }
  * { margin:0; padding:0; box-sizing:border-box; }
  html, body { height:100%; overflow:hidden; background:#0b0d11;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
  canvas { display:block; }
  #ui { position:fixed; inset:0; pointer-events:none; z-index:5; }
  #ui > * { pointer-events:auto; }
  .hdr { position:absolute; top:22px; left:24px; }
  .ttl { font-size:19px; font-weight:700; letter-spacing:.04em; color:#f2f6fc;
    text-transform:uppercase; }
  .sub { font-size:13px; color:#9aa6b8; margin-top:3px; }
  .steps { position:absolute; top:86px; left:24px; width:268px; max-height:62vh;
    overflow:auto; display:grid; gap:3px; scrollbar-width:thin; }
  .step { display:flex; gap:9px; align-items:baseline; padding:6px 9px;
    border-radius:6px; font-size:12.5px; color:#8894a6; cursor:pointer;
    border:1px solid transparent; line-height:1.35; }
  .step i { font-style:normal; font-variant-numeric:tabular-nums; font-size:10.5px;
    color:#5b6678; min-width:16px; }
  .step:hover { background:rgba(255,255,255,.045); }
  .step.on { background:rgba(74,163,224,.14); border-color:rgba(74,163,224,.4);
    color:#eaf2fb; }
  .step.on i { color:var(--accent); }
  .bar { position:absolute; bottom:26px; left:50%; transform:translateX(-50%);
    display:flex; align-items:center; gap:10px; padding:9px 14px;
    background:rgba(14,18,24,.9); border:1px solid rgba(255,255,255,.1);
    border-radius:10px; backdrop-filter:blur(8px); }
  .btn { background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.12);
    color:#dbe4f0; width:32px; height:30px; border-radius:6px; cursor:pointer;
    font-size:12px; display:grid; place-items:center; }
  .btn:hover { background:rgba(255,255,255,.14); }
  .scrub { width:330px; accent-color:var(--accent); cursor:pointer; }
  .time { font-variant-numeric:tabular-nums; font-size:12px; color:#9aa6b8;
    min-width:46px; text-align:right; }
  .caption { position:absolute; bottom:84px; left:50%; transform:translateX(-50%);
    max-width:min(760px, 88vw); text-align:center; font-size:14.5px; color:#dfe7f2;
    background:rgba(12,16,22,.82); border:1px solid rgba(255,255,255,.09);
    padding:9px 18px; border-radius:8px; line-height:1.45; }
  .caption b { color:#fff; font-weight:650; }
  .caption span { color:#9fb0c6; }
  .loader { position:fixed; inset:0; z-index:20; display:grid; place-items:center;
    background:#0b0d11; color:#67728a; font-size:13px; letter-spacing:.1em;
    text-transform:uppercase; transition:opacity .5s ease; }
  .loader.hidden { opacity:0; pointer-events:none; }
`;

// ── Burned-in caption overlay ────────────────────────────────────────────
// This ffmpeg build has no drawtext filter, and toDataURL only captures the
// WebGL canvas — so DOM captions never reach the video. Rendering the caption
// as a sprite parented to the camera puts it inside the framebuffer instead,
// where frame capture picks it up.
export function makeOverlay(camera, THREE) {
  const cv = document.createElement('canvas');
  cv.width = 1600; cv.height = 260;
  const ctx = cv.getContext('2d');

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const spr = new THREE.Sprite(new THREE.SpriteMaterial({
    map: tex, depthTest: false, depthWrite: false, transparent: true }));

  // sized against the frustum at z = -1.6 for a 42° vertical FOV
  const dist = 1.6;
  const h = 2 * dist * Math.tan((42 * Math.PI / 180) / 2);
  const w = h * (16 / 9);
  spr.scale.set(w * 0.86, w * 0.86 * (cv.height / cv.width), 1);
  spr.position.set(0, -h * 0.36, -dist);
  spr.renderOrder = 10000;
  spr.visible = false;
  camera.add(spr);

  function draw(kicker, title, note) {
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = 'rgba(10,14,20,0.86)';
    ctx.beginPath(); ctx.roundRect(0, 0, cv.width, cv.height, 22); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.14)'; ctx.lineWidth = 3; ctx.stroke();

    ctx.fillStyle = spr.userData.accent || '#4aa3e0';
    ctx.fillRect(0, 0, 12, cv.height);

    ctx.textBaseline = 'middle';
    ctx.fillStyle = spr.userData.accent || '#4aa3e0';
    ctx.font = '600 46px "Liberation Sans", sans-serif';
    ctx.fillText(kicker, 46, 62);

    ctx.fillStyle = '#f4f8fd';
    ctx.font = '700 68px "Liberation Sans", sans-serif';
    ctx.fillText(title, 46, 140);

    ctx.fillStyle = '#9fb2c8';
    ctx.font = '400 44px "Liberation Sans", sans-serif';
    ctx.fillText(note || '', 46, 210);

    tex.needsUpdate = true;
  }

  return {
    sprite: spr,
    setAccent(c) { spr.userData.accent = c; },
    set(kicker, title, note) { draw(kicker, title, note); },
    setVisible(v) { spr.visible = v; },
  };
}
