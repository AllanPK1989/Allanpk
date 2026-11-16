// Runs one search across all enabled sources, then: removes jobs located in
// India, applies country/date filters, checks employers against the official
// sponsor registers, scores each job's sponsorship evidence, de-duplicates and
// sorts.

import * as adzuna from './sources/adzuna.js';
import * as arbeitnow from './sources/arbeitnow.js';
import { remotive, jobicy } from './sources/remote.js';
import { verdict, FILTERS, LEVELS } from './lib/sponsorship.js';
import { COUNTRY_BY_CODE, EXCLUDED_COUNTRY } from './lib/countries.js';
import { normalizeCompany } from './lib/company.js';
import { foldText } from './lib/text.js';

export const SOURCES = { adzuna, arbeitnow, remotive, jobicy };
const REMOTE_SOURCES = new Set(['remotive', 'jobicy']);
export const DEFAULT_COUNTRIES = ['GB', 'IE', 'DE', 'NL', 'CA', 'AU', 'NZ', 'US', 'SG'];

export const PRESETS = [
  'Reliability engineer -site -software', 'Maintenance engineer', 'Maintenance manager', 'Maintenance planner',
  'Asset management', 'Condition monitoring', 'Asset integrity', 'Mechanical maintenance',
  'Electrical maintenance', 'Maintenance technician', 'Instandhaltung',
];

function oneOf(value, allowed, fallback) {
  return allowed.includes(value) ? value : fallback;
}

// Validate and normalise query-string input (never trust the browser).
export function parseParams(q) {
  const get = (k) => (typeof q[k] === 'string' ? q[k] : '');
  const query = get('q').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, 120);
  const requested = get('countries').split(',').map((c) => c.trim().toUpperCase())
    .filter((c) => COUNTRY_BY_CODE.has(c) && c !== EXCLUDED_COUNTRY);
  const countries = new Set(get('countries') ? requested : DEFAULT_COUNTRIES);
  const days = Math.min(90, Math.max(1, Number.parseInt(get('days'), 10) || 30));
  const includeRemote = get('remote') === '1';
  const wanted = get('sources') ? get('sources').split(',') : ['adzuna', 'arbeitnow', 'remotive', 'jobicy'];
  const sources = wanted.filter((s) => Object.hasOwn(SOURCES, s) && (!REMOTE_SOURCES.has(s) || includeRemote));
  return {
    query,
    countries,
    days,
    includeRemote,
    includeUnclear: get('unclear') === '1',
    sources: [...new Set(sources)],
    level: oneOf(get('level'), ['likely', 'signals', 'all'], 'likely'),
    sort: oneOf(get('sort'), ['best', 'newest'], 'best'),
    sponsorWords: oneOf(get('sponsorWords'), ['auto', 'always', 'never'], 'auto'),
  };
}

function remoteEligible(job, countries) {
  const e = job.eligibility;
  if (!e || !e.text) return true;
  if (e.countries.some((c) => countries.has(c))) return true;
  return e.regions.length > 0 && e.countries.length === 0;
}

function dedupeKey(job) {
  return `${normalizeCompany(job.company)}|${foldText(job.title)}|${job.country || ''}`;
}

export async function runSearch(params, ctx) {
  const { registers, store } = ctx;
  const started = Date.now();
  const runs = await Promise.all(params.sources.map(async (sid) => {
    const src = SOURCES[sid];
    if (sid === 'adzuna' && !adzuna.isConfigured(ctx.config)) {
      return { sid, result: { jobs: [], notes: [], error: null, warnings: [], stats: {}, notConfigured: true } };
    }
    try {
      return { sid, result: await src.search(params, ctx) };
    } catch (err) {
      return { sid, result: { jobs: [], notes: [], error: err.message, warnings: [], stats: {} } };
    }
  }));

  const sourceStatus = runs.map(({ sid, result }) => ({
    id: sid,
    label: SOURCES[sid].label,
    homepage: SOURCES[sid].homepage,
    found: result.jobs.length,
    error: result.error,
    warnings: result.warnings,
    notes: result.notes,
    stats: result.stats,
    notConfigured: Boolean(result.notConfigured),
  }));

  const since = Date.now() - params.days * 86400000;
  const hidden = store.hiddenIds();
  const counts = Object.fromEntries(LEVELS.map((l) => [l, 0]));
  let excludedIndia = 0;
  let unclearCountry = 0;
  let outsideCountries = 0;

  const byKey = new Map();
  for (const { sid, result } of runs) {
    for (const job of result.jobs) {
      if (hidden.has(job.id)) continue;
      if (job.country === EXCLUDED_COUNTRY) { excludedIndia++; continue; }
      if (job.postedAt && Date.parse(job.postedAt) < since) continue;
      const isRemoteFeed = REMOTE_SOURCES.has(sid);
      if (job.country) {
        if (!params.countries.has(job.country)) { outsideCountries++; continue; }
      } else if (isRemoteFeed || job.remote) {
        if (!params.includeRemote || !remoteEligible(job, params.countries)) continue;
      } else if (!params.includeUnclear) {
        unclearCountry++;
        continue;
      }

      const register = job.country ? registers.lookup(job.company, job.country) : null;
      const sponsorship = verdict({
        text: `${job.title}\n${job.description}`,
        feedTagged: job.feedTagged,
        keywordMatched: job.keywordMatched,
        register,
      });
      const enriched = { ...job, isRemoteFeed, sponsorship };
      const key = dedupeKey(job);
      const prev = byKey.get(key);
      if (!prev) {
        byKey.set(key, enriched);
      } else {
        const [keep, drop] = prev.sponsorship.score >= enriched.sponsorship.score ? [prev, enriched] : [enriched, prev];
        keep.alsoOn = [...(keep.alsoOn || []), { source: drop.source, url: drop.url }, ...(drop.alsoOn || [])];
        byKey.set(key, keep);
      }
    }
  }

  const allowed = FILTERS[params.level];
  const jobs = [];
  for (const job of byKey.values()) {
    counts[job.sponsorship.level]++;
    if (job.sponsorship.level === 'no') continue;
    // Remote-feed jobs don't need a visa if you can work from where you are, so
    // they are shown regardless of the sponsorship filter.
    if (!job.isRemoteFeed && !allowed.has(job.sponsorship.level)) continue;
    jobs.push(job);
  }

  const time = (j) => (j.postedAt ? Date.parse(j.postedAt) : 0);
  jobs.sort(params.sort === 'newest'
    ? (a, b) => time(b) - time(a)
    : (a, b) => b.sponsorship.score - a.sponsorship.score || time(b) - time(a));

  return {
    query: { ...params, countries: [...params.countries] },
    total: jobs.length,
    jobs: jobs.slice(0, 500),
    counts,
    excluded: { india: excludedIndia, unclearCountry, outsideCountries, saidNo: counts.no },
    sources: sourceStatus,
    quota: { adzuna: ctx.quota.summary('adzuna') },
    tookMs: Date.now() - started,
  };
}
