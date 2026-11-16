import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { buildUrl, mapResult } from '../server/sources/adzuna.js';
import { mapItem } from '../server/sources/arbeitnow.js';
import { mapRemotive, mapJobicy } from '../server/sources/remote.js';
import { titleMatcher, splitQuery } from '../server/sources/common.js';
import { parseParams, runSearch } from '../server/search.js';
import { Registers } from '../server/registers.js';
import { Cache, Quota, SavedStore } from '../server/state.js';
import { COUNTRY_BY_CODE } from '../server/lib/countries.js';
import { redact } from '../server/lib/fetch.js';

const config = {
  adzuna: { appId: 'test-id', appKey: 'secret-key-123', dailyLimit: 5 },
  arbeitnowPages: 2,
};

// Shapes follow each API's real response (Adzuna: its documented example).
const adzunaResult = (id, title, company, extra = {}) => ({
  __CLASS__: 'Adzuna::API::Response::Job',
  id, title, created: new Date(Date.now() - 2 * 86400000).toISOString(),
  company: { display_name: company }, location: { display_name: 'Derby, Derbyshire', area: ['UK', 'East Midlands', 'Derbyshire', 'Derby'] },
  description: 'Maintenance engineer for a large site...', redirect_url: `https://www.adzuna.co.uk/jobs/land/ad/${id}`,
  salary_min: 45000, salary_max: 55000, salary_is_predicted: '0', contract_type: 'permanent', category: { label: 'Engineering Jobs' },
  ...extra,
});

const arbeitnowItem = (slug, title, location, description, extra = {}) => ({
  slug, company_name: 'Example GmbH', title, description, remote: false,
  url: `https://www.arbeitnow.com/jobs/companies/example/${slug}`, tags: ['Engineering'], job_types: ['Full Time'],
  location, created_at: Math.floor(Date.now() / 1000) - 3600, ...extra,
});

test('splitQuery and titleMatcher: words, synonyms and -exclusions', () => {
  assert.deepEqual(splitQuery('Reliability engineer -site -software'), { include: ['reliability', 'engineer'], exclude: ['site', 'software'] });
  const m = titleMatcher('Reliability engineer -site');
  assert.ok(m({ title: 'Senior Reliability Engineer (m/w/d)' }));
  assert.ok(!m({ title: 'Site Reliability Engineer' }));
  assert.ok(!m({ title: 'Reliability Analyst' }));
  const de = titleMatcher('maintenance engineer');
  assert.ok(de({ title: 'Instandhaltungsingenieur (m/w/d)' }));
  assert.ok(de({ title: 'Ingénieur Méthodes Opérations et Maintenance (H/F)' }));
  assert.ok(titleMatcher('')({ title: 'anything' }));
});

test('Adzuna URL: keywords, exclusions, sponsorship filter, never India', () => {
  const url = new URL(buildUrl(config, 'gb', { query: 'reliability engineer -site', days: 30 }, true));
  assert.equal(url.pathname, '/v1/api/jobs/gb/search/1');
  assert.equal(url.searchParams.get('what'), 'reliability engineer');
  assert.equal(url.searchParams.get('what_exclude'), 'site');
  assert.equal(url.searchParams.get('what_or'), 'visa sponsorship sponsor relocation');
  assert.equal(url.searchParams.get('max_days_old'), '30');
  assert.equal(url.searchParams.get('results_per_page'), '50');
  assert.equal(redact(url.toString()).includes('secret-key-123'), false);
});

test('Adzuna result mapping', () => {
  const job = mapResult(adzunaResult('129698749', ' Maintenance Engineer ', 'Rolls-Royce plc'), COUNTRY_BY_CODE.get('GB'), false);
  assert.equal(job.id, 'adzuna:gb:129698749');
  assert.equal(job.title, 'Maintenance Engineer');
  assert.equal(job.country, 'GB');
  assert.match(job.salaryText, /£45,000 – £55,000/);
  assert.equal(job.contract, 'permanent');
  assert.equal(job.descriptionIsSnippet, true);
});

test('Arbeitnow mapping infers country from city or text', () => {
  assert.equal(mapItem(arbeitnowItem('a', 'Engineer', 'Munich', '<p>Hi</p>')).country, 'DE');
  assert.equal(mapItem(arbeitnowItem('b', 'Engineer', 'Molbergen', '<p>Arbeiten in Deutschland</p>')).country, 'DE');
  assert.equal(mapItem(arbeitnowItem('c', 'Engineer', 'Ypenburg, Nederlands', '<p>x</p>')).country, null);
  assert.equal(mapItem(arbeitnowItem('d', 'Engineer', 'Pune, India', '<p>x</p>')).country, 'IN');
});

test('remote feeds mark India-only jobs', () => {
  const r = mapRemotive({ id: 1, url: 'https://remotive.com/x', title: 'Planner', company_name: 'X', candidate_required_location: 'India', description: '' });
  assert.equal(r.indiaOnly, true);
  const j = mapJobicy({ id: 2, url: 'https://jobicy.com/x', jobTitle: 'Planner', companyName: 'Y', jobGeo: 'UK', jobDescription: '<p>x</p>', annualSalaryMin: 40000, annualSalaryMax: 50000, salaryCurrency: 'GBP' });
  assert.equal(j.indiaOnly, false);
  assert.equal(j.job.country, 'GB');
});

test('parseParams validates input and never allows India', () => {
  const p = parseParams({ q: '  pump\u0000 engineer ', countries: 'gb,IN,xx,de', days: '999', level: 'evil', sort: 'x', sources: 'adzuna,evil,remotive' });
  assert.equal(p.query, 'pump  engineer');
  assert.deepEqual([...p.countries], ['GB', 'DE']);
  assert.equal(p.days, 90);
  assert.equal(p.level, 'likely');
  assert.equal(p.sort, 'best');
  assert.deepEqual(p.sources, ['adzuna']); // remotive needs remote=1
});

// --- full pipeline with a fake network -----------------------------------

let dir;
let realFetch;
let calls;

function mockFetch(routes) {
  calls = [];
  globalThis.fetch = async (url) => {
    const u = String(url);
    calls.push(u);
    for (const [pattern, body] of routes) {
      if (u.includes(pattern)) {
        const payload = typeof body === 'function' ? body(u) : body;
        if (payload instanceof Response) return payload;
        return new Response(JSON.stringify(payload), { status: 200, headers: { 'content-type': 'application/json' } });
      }
    }
    return new Response('not found', { status: 404 });
  };
}

beforeEach(async () => {
  dir = await fs.mkdtemp(path.join(os.tmpdir(), 'vjf-search-'));
  realFetch = globalThis.fetch;
});
afterEach(async () => {
  globalThis.fetch = realFetch;
  await fs.rm(dir, { recursive: true, force: true });
});

async function makeCtx() {
  const registers = new Registers(dir);
  await registers.load();
  await fs.writeFile(path.join(registers.importDir, 'gb-test.csv'), 'Organisation Name\nRolls-Royce plc\n');
  await registers.importManual();
  const ctx = {
    config,
    registers,
    cache: new Cache(path.join(dir, 'cache.json')),
    quota: new Quota(path.join(dir, 'usage.json'), { adzuna: config.adzuna.dailyLimit }),
    store: new SavedStore(path.join(dir, 'saved.json')),
  };
  return ctx;
}

test('runSearch: India excluded, register match, "no sponsorship" hidden, dedupe, ranking', async () => {
  mockFetch([
    ['api.adzuna.com/v1/api/jobs/gb/', { results: [
      adzunaResult('1', 'Maintenance Engineer', 'Rolls-Royce plc'),
      adzunaResult('2', 'Maintenance Engineer', 'Small Shop Ltd', { description: 'We are unable to offer visa sponsorship for this role.' }),
      adzunaResult('3', 'Maintenance Engineer', 'Open Doors Ltd', { description: 'Visa sponsorship is available for the right candidate.' }),
    ] }],
    ['api.adzuna.com/v1/api/jobs/de/', { results: [adzunaResult('9', 'Maintenance Engineer', 'Werk AG', { location: { display_name: 'Hamburg' } })] }],
    ['arbeitnow.com/api/job-board-api', (u) => (u.includes('page=1') ? { data: [
      arbeitnowItem('x1', 'Maintenance Engineer (m/w/d)', 'Hamburg', '<p>Relocation support and visa support provided.</p>'),
      arbeitnowItem('x2', 'Maintenance Engineer', 'Pune, India', '<p>Visa sponsorship available.</p>'),
      arbeitnowItem('x3', 'Maintenance Engineer', 'Hamburg', '<p>This position is NOT eligible for Visa sponsorship.</p>'),
      arbeitnowItem('x4', 'Software Engineer', 'Berlin', '<p>Visa sponsorship available.</p>'),
    ], links: { next: null } } : { data: [], links: { next: null } })],
  ]);
  const ctx = await makeCtx();
  const params = parseParams({ q: 'maintenance engineer', countries: 'GB,DE', level: 'likely', sources: 'adzuna,arbeitnow' });
  const res = await runSearch(params, ctx);

  // Germany has no register here, so the Adzuna sponsorship keyword filter is on for DE only.
  const deCall = calls.find((c) => c.includes('/jobs/de/'));
  const gbCall = calls.find((c) => c.includes('/jobs/gb/'));
  assert.ok(new URL(deCall).searchParams.get('what_or'));
  assert.equal(new URL(gbCall).searchParams.get('what_or'), null);
  assert.equal(calls.some((c) => c.includes('/jobs/in/')), false);

  const titles = res.jobs.map((j) => `${j.company}|${j.sponsorship.level}`);
  // Example GmbH: stated + board tag + relocation outranks a plain "stated".
  assert.deepEqual(titles, [
    'Example GmbH|stated',
    'Open Doors Ltd|stated',
    'Rolls-Royce plc|licensed',
  ]);
  assert.equal(res.jobs[2].sponsorship.register.matchedName, 'Rolls-Royce plc');
  assert.equal(res.excluded.india, 1);
  assert.equal(res.counts.no, 2);
  assert.equal(res.counts.keyword, 1); // Werk AG: matched by Adzuna full-text filter only
  assert.equal(res.quota.adzuna.used, 2);

  // Second identical search is served from cache: no new Adzuna requests.
  const before = calls.length;
  const again = await runSearch(params, ctx);
  assert.equal(calls.length, before);
  assert.equal(again.quota.adzuna.used, 2);

  // "signals" level also shows the keyword-only job.
  const wider = await runSearch(parseParams({ q: 'maintenance engineer', countries: 'GB,DE', level: 'signals', sources: 'adzuna,arbeitnow' }), ctx);
  assert.ok(wider.jobs.some((j) => j.company === 'Werk AG'));
});

test('runSearch: Adzuna daily budget is enforced and reported', async () => {
  mockFetch([['api.adzuna.com', { results: [] }], ['arbeitnow.com', { data: [], links: {} }]]);
  const ctx = await makeCtx();
  const res = await runSearch(parseParams({ q: 'planner', countries: 'GB,DE,NL,CA,AU,NZ,US', sources: 'adzuna' }), ctx);
  const adz = res.sources.find((s) => s.id === 'adzuna');
  assert.equal(adz.stats.requested, 5);
  assert.equal(adz.stats.skipped, 2);
  assert.match(adz.notes[0], /budget used up/);
});

test('runSearch: Adzuna auth failure gives a clear message without leaking the key', async () => {
  mockFetch([['api.adzuna.com', () => new Response('{"exception":"AUTH_FAIL"}', { status: 401 })]]);
  const ctx = await makeCtx();
  const res = await runSearch(parseParams({ q: 'planner', countries: 'GB', sources: 'adzuna' }), ctx);
  const adz = res.sources.find((s) => s.id === 'adzuna');
  assert.match(adz.error, /rejected the app ID\/key/);
  assert.equal(JSON.stringify(res).includes('secret-key-123'), false);
});

test('runSearch: remote feeds only when asked, India-only remote jobs dropped', async () => {
  mockFetch([
    ['remotive.com', { jobs: [
      { id: 1, url: 'https://remotive.com/1', title: 'Maintenance Planner', company_name: 'A', candidate_required_location: 'Worldwide', description: '', publication_date: new Date().toISOString() },
      { id: 2, url: 'https://remotive.com/2', title: 'Maintenance Planner', company_name: 'B', candidate_required_location: 'India', description: '', publication_date: new Date().toISOString() },
    ] }],
    ['jobicy.com', { jobs: [] }],
    ['arbeitnow.com', { data: [], links: {} }],
  ]);
  const ctx = await makeCtx();
  const off = await runSearch(parseParams({ q: 'maintenance planner', countries: 'GB', sources: 'arbeitnow,remotive,jobicy' }), ctx);
  assert.equal(off.jobs.length, 0);
  assert.equal(calls.some((c) => c.includes('remotive')), false);
  const on = await runSearch(parseParams({ q: 'maintenance planner', countries: 'GB', remote: '1', sources: 'arbeitnow,remotive,jobicy' }), ctx);
  assert.deepEqual(on.jobs.map((j) => j.company), ['A']);
});
