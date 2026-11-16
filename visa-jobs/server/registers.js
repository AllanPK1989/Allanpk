// Official sponsor registers: download, parse, store, and look up employers.
//
//   GB  Home Office "Register of licensed sponsors: workers" (CSV, daily)
//   NL  IND public register of recognised sponsors, work (HTML table)
//   CA  ESDC positive LMIA employers list, latest 4 quarters (XLSX)
//   **  Any CSV/XLSX you drop into DATA_DIR/registers/import/ named
//       "<country code>-<anything>.csv", e.g. "us-h1b-fy2025.csv" from the
//       USCIS H-1B Employer Data Hub (USCIS blocks automated downloads).
//
// A match means the EMPLOYER holds a licence / has hired through the scheme. It
// does not promise that a particular job is open to sponsorship.

import fs from 'node:fs/promises';
import path from 'node:path';
import { fetchBuffer, fetchJson } from './lib/fetch.js';
import { readJson, writeJsonAtomic } from './lib/files.js';
import { parseCsv, decodeTextFile } from './lib/csv.js';
import { readFirstSheet } from './lib/xlsx.js';
import { companyAliases } from './lib/company.js';
import { decodeEntities } from './lib/text.js';
import { COUNTRY_BY_CODE, EXCLUDED_COUNTRY } from './lib/countries.js';

export const REGISTER_DEFS = [
  {
    id: 'gb',
    country: 'GB',
    label: 'UK Home Office register of licensed sponsors (workers)',
    short: 'UK licensed sponsor',
    page: 'https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers',
  },
  {
    id: 'nl',
    country: 'NL',
    label: 'IND public register of recognised sponsors (work)',
    short: 'NL recognised sponsor',
    page: 'https://ind.nl/en/public-register-recognised-sponsors/public-register-regular-labour-and-highly-skilled-migrants',
  },
  {
    id: 'ca',
    country: 'CA',
    label: 'Canada positive LMIA employers (latest 4 quarters)',
    short: 'Canada LMIA employer',
    page: 'https://open.canada.ca/data/en/dataset/90fed587-1364-4f33-a9ee-208181dc0b97',
  },
];

// UK routes that matter for an ordinary skilled job (not religious, sport, charity...).
const UK_EMPLOYMENT_ROUTE = /skilled worker|global business mobility|scale-up|tier 2 general|intra[- ]company/i;

// ---------------------------------------------------------------------------
// Parsers (pure functions, unit-tested with fixtures)

function headerIndex(header, patterns) {
  const cells = header.map((h) => String(h ?? '').trim().toLowerCase());
  for (const p of patterns) {
    const i = cells.findIndex((c) => (p instanceof RegExp ? p.test(c) : c === p));
    if (i !== -1) return i;
  }
  return -1;
}

export function parseUkRegister(csvText) {
  const rows = parseCsv(csvText, ',');
  if (!rows.length) throw new Error('UK register is empty');
  const h = rows[0];
  const nameCol = headerIndex(h, ['organisation name', /organi[sz]ation/]);
  const cityCol = headerIndex(h, ['town/city', /town|city/]);
  const routeCol = headerIndex(h, ['route']);
  const ratingCol = headerIndex(h, ['type & rating', /rating/]);
  if (nameCol === -1 || routeCol === -1) throw new Error('UK register columns not recognised (expected "Organisation Name" and "Route")');
  const byName = new Map();
  for (const row of rows.slice(1)) {
    const name = (row[nameCol] || '').trim();
    if (!name) continue;
    const route = (row[routeCol] || '').trim();
    let e = byName.get(name);
    if (!e) {
      e = { name, city: (row[cityCol] || '').trim(), routes: new Set(), ratings: new Set() };
      byName.set(name, e);
    }
    if (route) e.routes.add(route);
    if (ratingCol !== -1 && row[ratingCol]) e.ratings.add(row[ratingCol].trim());
  }
  const entries = [];
  for (const e of byName.values()) {
    const routes = [...e.routes];
    if (!routes.some((r) => UK_EMPLOYMENT_ROUTE.test(r))) continue;
    const detail = [e.city, routes.join(', ')].filter(Boolean).join(' · ');
    const bRated = [...e.ratings].some((r) => /\bB rating\b/i.test(r));
    entries.push([e.name, bRated ? `${detail} · B-rated licence` : detail]);
  }
  return entries;
}

export function parseIndRegister(html) {
  const entries = [];
  for (const m of String(html).matchAll(/<th\b[^>]*scope="row"[^>]*>([\s\S]*?)<\/th>\s*<td\b[^>]*>([\s\S]*?)<\/td>/gi)) {
    const name = decodeEntities(m[1].replace(/<[^>]+>/g, '')).trim();
    const kvk = decodeEntities(m[2].replace(/<[^>]+>/g, '')).trim();
    if (name) entries.push([name, kvk ? `KvK ${kvk}` : '']);
  }
  if (!entries.length) throw new Error('IND register page format not recognised (no table rows found)');
  return entries;
}

// rows: array of arrays from one LMIA quarter (XLSX or CSV). Accumulates into `acc`.
export function collectLmiaRows(rows, acc = new Map()) {
  const headerRow = rows.findIndex((r) => r.some((c) => String(c).trim().toLowerCase() === 'employer'));
  if (headerRow === -1) throw new Error('LMIA file has no "Employer" column');
  const h = rows[headerRow];
  const emp = headerIndex(h, ['employer']);
  const prov = headerIndex(h, [/province/]);
  const occ = headerIndex(h, [/occupation/]);
  const stream = headerIndex(h, [/stream/]);
  const positions = headerIndex(h, [/approved positions/]);
  for (const row of rows.slice(headerRow + 1)) {
    const name = String(row[emp] ?? '').trim();
    if (!name || row.filter((c) => String(c).trim()).length < 3) continue; // skip footnotes
    let e = acc.get(name);
    if (!e) {
      e = { province: String(row[prov] ?? '').trim(), occupations: new Set(), streams: new Set(), positions: 0 };
      acc.set(name, e);
    }
    const o = String(row[occ] ?? '').trim().replace(/^\d+\s*-\s*/, '');
    if (o) e.occupations.add(o);
    const s = String(row[stream] ?? '').trim();
    if (s) e.streams.add(s);
    e.positions += Number(row[positions]) || 0;
  }
  return acc;
}

export function lmiaEntries(acc) {
  const entries = [];
  for (const [name, e] of acc) {
    const occs = [...e.occupations];
    const occText = occs.slice(0, 4).join('; ') + (occs.length > 4 ? `; +${occs.length - 4} more` : '');
    const detail = [e.province, e.positions ? `${e.positions} approved positions` : '', occText].filter(Boolean).join(' · ');
    entries.push([name, detail]);
  }
  return entries;
}

// Generic import: pick the employer-name column by its header.
export function parseImportedRows(rows) {
  const headerRow = rows.findIndex((r) => headerIndex(r, [/employer|petitioner|organi[sz]ation|company|sponsor/]) !== -1);
  if (headerRow === -1) throw new Error('No column named like Employer / Petitioner / Organisation / Company');
  const h = rows[headerRow];
  const nameCol = headerIndex(h, ['employer (petitioner) name', 'employer name', 'employer', 'petitioner name', /employer|petitioner/, /organi[sz]ation/, /company/, /sponsor/]);
  const cityCol = headerIndex(h, [/city/]);
  const stateCol = headerIndex(h, [/state|province|county/]);
  const approvalCols = h
    .map((c, i) => [String(c).toLowerCase(), i])
    .filter(([c]) => /approv/.test(c))
    .map(([, i]) => i);
  const byName = new Map();
  for (const row of rows.slice(headerRow + 1)) {
    const name = String(row[nameCol] ?? '').trim();
    if (!name) continue;
    const place = [row[cityCol], row[stateCol]].map((v) => String(v ?? '').trim()).filter(Boolean).join(', ');
    const approvals = approvalCols.reduce((s, i) => s + (Number(String(row[i]).replace(/,/g, '')) || 0), 0);
    const e = byName.get(name) || { place, approvals: 0 };
    e.approvals += approvals;
    byName.set(name, e);
  }
  return [...byName].map(([name, e]) => [name, [e.place, e.approvals ? `${e.approvals} approvals` : ''].filter(Boolean).join(' · ')]);
}

// ---------------------------------------------------------------------------
// Downloaders

async function downloadUk() {
  const meta = await fetchJson('https://www.gov.uk/api/content/government/publications/register-of-licensed-sponsors-workers', { retries: 1 });
  const attachment = (meta.details?.attachments || []).find((a) => a.content_type === 'text/csv' || /\.csv$/i.test(a.url || ''));
  if (!attachment) throw new Error('gov.uk page has no CSV attachment');
  const { buffer } = await fetchBuffer(attachment.url, { timeoutMs: 180000, retries: 1 });
  return { entries: parseUkRegister(decodeTextFile(buffer)), sourceUrl: attachment.url, publishedAt: meta.public_updated_at || null };
}

async function downloadNl() {
  const def = REGISTER_DEFS.find((d) => d.id === 'nl');
  const { buffer, url } = await fetchBuffer(def.page, { timeoutMs: 60000, retries: 1, headers: { accept: 'text/html' } });
  return { entries: parseIndRegister(buffer.toString('utf8')), sourceUrl: url, publishedAt: null };
}

async function downloadCa() {
  const pkg = await fetchJson('https://open.canada.ca/data/api/action/package_show?id=90fed587-1364-4f33-a9ee-208181dc0b97', { retries: 1 });
  const resources = (pkg.result?.resources || [])
    .filter((r) => (r.language || []).includes('en') && /^(xlsx|csv)$/i.test(r.format || '') && /^\d{4}\s*Q\d/i.test(r.name || ''))
    .sort((a, b) => String(b.name).localeCompare(String(a.name)))
    .slice(0, 4);
  if (!resources.length) throw new Error('No recent LMIA files listed on open.canada.ca');
  const acc = new Map();
  for (const r of resources) {
    const { buffer } = await fetchBuffer(r.url, { timeoutMs: 120000, retries: 1 });
    const rows = /xlsx/i.test(r.format) ? readFirstSheet(buffer) : parseCsv(decodeTextFile(buffer));
    collectLmiaRows(rows, acc);
  }
  const quarters = resources.map((r) => String(r.name).match(/^\d{4}\s*Q\d/i)[0].replace(/\s+/g, '')).join(', ');
  return { entries: lmiaEntries(acc), sourceUrl: resources[0].url, publishedAt: resources[0].created || null, note: `Quarters: ${quarters}` };
}

const DOWNLOADERS = { gb: downloadUk, nl: downloadNl, ca: downloadCa };

// ---------------------------------------------------------------------------
// Store + lookup

export class Registers {
  constructor(dataDir) {
    this.dir = path.join(dataDir, 'registers');
    this.importDir = path.join(this.dir, 'import');
    this.byCountry = new Map(); // country -> [{ meta, index: Map(alias -> [name, detail]) }]
    this.meta = new Map(); // id -> meta (without entries)
    this.errors = new Map(); // id -> last error message
    this.updating = null;
  }

  async load() {
    await fs.mkdir(this.importDir, { recursive: true });
    this.byCountry.clear();
    this.meta.clear();
    let files = [];
    try { files = (await fs.readdir(this.dir)).filter((f) => f.endsWith('.json')); } catch { /* empty */ }
    for (const f of files) {
      const reg = await readJson(path.join(this.dir, f), null);
      if (!reg || !Array.isArray(reg.entries)) continue;
      this.#index(reg);
    }
  }

  #index(reg) {
    const index = new Map();
    for (const entry of reg.entries) {
      for (const alias of companyAliases(entry[0])) if (!index.has(alias)) index.set(alias, entry);
    }
    const { entries, ...meta } = reg;
    meta.count = entries.length;
    this.meta.set(meta.id, meta);
    const list = (this.byCountry.get(meta.country) || []).filter((r) => r.meta.id !== meta.id);
    list.push({ meta, index });
    this.byCountry.set(meta.country, list);
  }

  hasCountry(country) {
    return (this.byCountry.get(country) || []).length > 0;
  }

  // company: display name from a job board; country: ISO code of the job.
  lookup(company, country) {
    const regs = this.byCountry.get(country);
    if (!regs || !company) return null;
    const aliases = companyAliases(company);
    for (const { meta, index } of regs) {
      for (const alias of aliases) {
        const hit = index.get(alias);
        if (hit) return { registerId: meta.id, short: meta.short, label: meta.label, page: meta.page, matchedName: hit[0], detail: hit[1] || '' };
      }
    }
    return null;
  }

  status() {
    const now = Date.now();
    const known = REGISTER_DEFS.map((d) => {
      const m = this.meta.get(d.id);
      return {
        id: d.id, country: d.country, label: d.label, page: d.page, automatic: true,
        count: m?.count || 0, fetchedAt: m?.fetchedAt || null, publishedAt: m?.publishedAt || null,
        note: m?.note || null, ageDays: m?.fetchedAt ? Math.floor((now - Date.parse(m.fetchedAt)) / 86400000) : null,
        error: this.errors.get(d.id) || null,
      };
    });
    const imported = [...this.meta.values()].filter((m) => m.imported).map((m) => ({
      id: m.id, country: m.country, label: m.label, automatic: false, count: m.count, fetchedAt: m.fetchedAt,
      ageDays: Math.floor((now - Date.parse(m.fetchedAt)) / 86400000), error: this.errors.get(m.id) || null,
    }));
    const importErrors = [...this.errors].filter(([id]) => id.startsWith('import:') && !this.meta.has(id))
      .map(([id, error]) => ({ id, label: id.slice(7), country: null, automatic: false, count: 0, error }));
    return { registers: [...known, ...imported, ...importErrors], updating: Boolean(this.updating), importDir: this.importDir };
  }

  needsUpdate(maxAgeDays) {
    return REGISTER_DEFS.some((d) => {
      const m = this.meta.get(d.id);
      return !m || Date.now() - Date.parse(m.fetchedAt) > maxAgeDays * 86400000;
    });
  }

  // Downloads run one at a time; concurrent callers share the same run.
  update({ ids = null, log = () => {} } = {}) {
    if (!this.updating) {
      this.updating = this.#runUpdate(ids, log).finally(() => { this.updating = null; });
    }
    return this.updating;
  }

  async #runUpdate(ids, log) {
    await fs.mkdir(this.importDir, { recursive: true });
    const results = [];
    for (const def of REGISTER_DEFS) {
      if (ids && !ids.includes(def.id)) continue;
      const started = Date.now();
      try {
        log(`Downloading ${def.label}…`);
        const { entries, sourceUrl, publishedAt, note } = await DOWNLOADERS[def.id]();
        const reg = { ...def, sourceUrl, publishedAt, note: note || null, fetchedAt: new Date().toISOString(), entries };
        await writeJsonAtomic(path.join(this.dir, `${def.id}.json`), reg);
        this.#index(reg);
        this.errors.delete(def.id);
        log(`  ${entries.length.toLocaleString('en')} employers (${((Date.now() - started) / 1000).toFixed(1)}s)`);
        results.push({ id: def.id, ok: true, count: entries.length });
      } catch (err) {
        this.errors.set(def.id, err.message);
        log(`  failed: ${err.message}`);
        results.push({ id: def.id, ok: false, error: err.message });
      }
    }
    results.push(...(await this.importManual(log)));
    return results;
  }

  #importJsonPath(id) {
    return path.join(this.dir, `${id.replace(/[^a-z0-9._-]/gi, '_')}.json`);
  }

  async importManual(log = () => {}) {
    const results = [];
    let files = [];
    try { files = await fs.readdir(this.importDir); } catch { return results; }
    // Forget imports whose source file has been removed.
    for (const meta of [...this.meta.values()]) {
      if (!meta.imported || files.includes(meta.id.slice('import:'.length))) continue;
      await fs.rm(this.#importJsonPath(meta.id), { force: true });
      this.meta.delete(meta.id);
      this.byCountry.set(meta.country, (this.byCountry.get(meta.country) || []).filter((r) => r.meta.id !== meta.id));
      log(`Removed import ${meta.id.slice(7)} (file no longer present)`);
    }
    for (const file of files) {
      if (!/\.(csv|tsv|txt|xlsx)$/i.test(file)) continue;
      const id = `import:${file}`;
      const code = file.slice(0, 2).toUpperCase();
      try {
        if (!/^[a-z]{2}[-_]/i.test(file) || !COUNTRY_BY_CODE.has(code) || code === EXCLUDED_COUNTRY) {
          throw new Error('File name must start with a supported country code, e.g. "us-h1b-2025.csv"');
        }
        const buffer = await fs.readFile(path.join(this.importDir, file));
        const rows = /\.xlsx$/i.test(file) ? readFirstSheet(buffer) : parseCsv(decodeTextFile(buffer));
        const entries = parseImportedRows(rows);
        const reg = {
          id, country: code, imported: true, label: `Imported list: ${file}`,
          short: `On your imported ${COUNTRY_BY_CODE.get(code).name} sponsor list`, page: null,
          fetchedAt: new Date((await fs.stat(path.join(this.importDir, file))).mtimeMs).toISOString(), entries,
        };
        await writeJsonAtomic(this.#importJsonPath(id), reg);
        this.#index(reg);
        this.errors.delete(id);
        log(`Imported ${file}: ${entries.length.toLocaleString('en')} employers for ${code}`);
        results.push({ id, ok: true, count: entries.length });
      } catch (err) {
        this.errors.set(id, err.message);
        log(`Import ${file} failed: ${err.message}`);
        results.push({ id, ok: false, error: err.message });
      }
    }
    return results;
  }
}
