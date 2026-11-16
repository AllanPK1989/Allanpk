// Small persistent state: response cache, Adzuna daily budget, saved jobs.
import path from 'node:path';
import { readJson, writeJsonAtomic } from './lib/files.js';
import { isHttpUrl } from './lib/text.js';

function debounce(fn, ms) {
  let timer = null;
  let pending = null;
  const run = () => {
    timer = null;
    const p = fn();
    pending = p.finally(() => { if (pending === p) pending = null; });
  };
  const wrapped = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(run, ms);
  };
  wrapped.flush = async () => {
    if (timer) { clearTimeout(timer); run(); }
    if (pending) await pending;
  };
  return wrapped;
}

// ---------------------------------------------------------------------------
// TTL cache so repeated searches don't spend API quota or hammer free feeds.

export class Cache {
  constructor(file, { maxEntries = 300 } = {}) {
    this.file = file;
    this.maxEntries = maxEntries;
    this.map = new Map();
    this.save = debounce(() => this.#persist(), 2000);
  }

  async load() {
    const data = await readJson(this.file, {});
    const now = Date.now();
    for (const [k, v] of Object.entries(data)) if (v && v.expires > now) this.map.set(k, v);
  }

  get(key) {
    const hit = this.map.get(key);
    if (!hit) return undefined;
    if (hit.expires <= Date.now()) { this.map.delete(key); return undefined; }
    return hit.value;
  }

  set(key, value, ttlMs) {
    this.map.delete(key);
    this.map.set(key, { value, expires: Date.now() + ttlMs });
    while (this.map.size > this.maxEntries) this.map.delete(this.map.keys().next().value);
    this.save();
  }

  async #persist() {
    const now = Date.now();
    const out = {};
    for (const [k, v] of this.map) if (v.expires > now) out[k] = v;
    await writeJsonAtomic(this.file, out).catch((err) => console.warn(`Cache not saved: ${err.message}`));
  }
}

// ---------------------------------------------------------------------------
// Per-day request budget (UTC days).

export class Quota {
  constructor(file, limits) {
    this.file = file;
    this.limits = limits; // { adzuna: 250 }
    this.state = { day: '', used: {} };
    this.save = debounce(() => writeJsonAtomic(this.file, this.state).catch(() => {}), 500);
  }

  async load() {
    this.state = await readJson(this.file, { day: '', used: {} });
  }

  #roll() {
    const today = new Date().toISOString().slice(0, 10);
    if (this.state.day !== today) this.state = { day: today, used: {} };
  }

  remaining(name) {
    this.#roll();
    return Math.max(0, (this.limits[name] ?? Infinity) - (this.state.used[name] || 0));
  }

  take(name) {
    if (this.remaining(name) <= 0) return false;
    this.state.used[name] = (this.state.used[name] || 0) + 1;
    this.save();
    return true;
  }

  summary(name) {
    this.#roll();
    return { used: this.state.used[name] || 0, limit: this.limits[name] ?? null, day: this.state.day };
  }
}

// ---------------------------------------------------------------------------
// Saved jobs ("tracker") and hidden jobs. Single-user, stored as JSON.

export const STATUSES = ['saved', 'applied', 'interviewing', 'offer', 'rejected'];
const ID_RE = /^[a-z]+:[A-Za-z0-9:._-]{1,200}$/;

function str(v, max) {
  return typeof v === 'string' ? v.slice(0, max) : '';
}

// Mass-assignment guard: only these fields of a job are ever stored.
export function sanitizeJobSnapshot(job) {
  if (!job || typeof job !== 'object') throw new Error('Missing job');
  if (!ID_RE.test(job.id || '')) throw new Error('Invalid job id');
  if (!isHttpUrl(job.url)) throw new Error('Job link must be an http(s) URL');
  const sp = job.sponsorship && typeof job.sponsorship === 'object' ? job.sponsorship : {};
  return {
    id: job.id,
    source: str(job.source, 30),
    title: str(job.title, 300),
    company: str(job.company, 200),
    location: str(job.location, 200),
    country: /^[A-Z]{2}$/.test(job.country || '') ? job.country : null,
    remote: Boolean(job.remote),
    url: job.url,
    postedAt: str(job.postedAt, 40),
    salaryText: str(job.salaryText, 120),
    snippet: str(job.snippet, 600),
    sponsorship: {
      level: str(sp.level, 20),
      evidence: str(sp.evidence, 400),
      registerShort: str(sp.register?.short || sp.registerShort, 120),
      registerMatch: str(sp.register?.matchedName || sp.registerMatch, 200),
    },
  };
}

export class SavedStore {
  constructor(file) {
    this.file = file;
    this.data = { saved: {}, hidden: {} };
    this.save = debounce(() => writeJsonAtomic(this.file, this.data), 300);
  }

  async load() {
    const d = await readJson(this.file, null);
    if (d && typeof d === 'object') this.data = { saved: d.saved || {}, hidden: d.hidden || {} };
  }

  list() {
    return Object.values(this.data.saved).sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  }

  get(id) {
    return this.data.saved[id] || null;
  }

  upsert(jobInput) {
    const job = sanitizeJobSnapshot(jobInput);
    const now = new Date().toISOString();
    const existing = this.data.saved[job.id];
    this.data.saved[job.id] = existing
      ? { ...existing, job, updatedAt: now }
      : { id: job.id, job, status: 'saved', notes: '', savedAt: now, updatedAt: now };
    this.save();
    return this.data.saved[job.id];
  }

  patch(id, body) {
    const entry = this.data.saved[id];
    if (!entry) return null;
    if (body.status !== undefined) {
      if (!STATUSES.includes(body.status)) throw new Error('Unknown status');
      entry.status = body.status;
    }
    if (body.notes !== undefined) {
      if (typeof body.notes !== 'string') throw new Error('Notes must be text');
      entry.notes = body.notes.slice(0, 5000);
    }
    entry.updatedAt = new Date().toISOString();
    this.save();
    return entry;
  }

  remove(id) {
    const existed = Boolean(this.data.saved[id]);
    delete this.data.saved[id];
    if (existed) this.save();
    return existed;
  }

  hiddenIds() {
    return new Set(Object.keys(this.data.hidden));
  }

  hide(id) {
    if (!ID_RE.test(id)) throw new Error('Invalid job id');
    this.data.hidden[id] = new Date().toISOString();
    this.save();
  }

  unhideAll() {
    this.data.hidden = {};
    this.save();
  }
}

export function stateFiles(dataDir) {
  return {
    cache: path.join(dataDir, 'cache.json'),
    usage: path.join(dataDir, 'usage.json'),
    saved: path.join(dataDir, 'saved.json'),
  };
}
