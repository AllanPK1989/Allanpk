import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { createApp } from '../server/index.js';

let app;
let port;
let dir;

function request(method, pathname, { headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body);
    const req = http.request({
      host: '127.0.0.1', port, method, path: pathname,
      headers: { host: `localhost:${port}`, ...(data ? { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data) } : {}), ...headers },
    }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null;
        try { json = JSON.parse(text); } catch { /* not json */ }
        resolve({ status: res.statusCode, headers: res.headers, text, json });
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

const WRITE = { 'x-requested-with': 'visa-job-finder' };
const job = {
  id: 'adzuna:gb:42', source: 'adzuna', title: 'Reliability Engineer', company: 'Rolls-Royce plc', location: 'Derby',
  country: 'GB', url: 'https://www.adzuna.co.uk/jobs/land/ad/42', postedAt: new Date().toISOString(),
  sponsorship: { level: 'licensed', register: { short: 'UK licensed sponsor', matchedName: 'Rolls-Royce plc' } },
  role: 'admin', // must be ignored
};

before(async () => {
  dir = await fs.mkdtemp(path.join(os.tmpdir(), 'vjf-server-'));
  app = await createApp({
    host: '127.0.0.1', port: 0, dataDir: dir, extraHosts: [], arbeitnowPages: 1,
    adzuna: { appId: '', appKey: '', dailyLimit: 10 }, registerMaxAgeDays: 7, autoUpdateRegisters: false,
  });
  await new Promise((r) => app.server.listen(0, '127.0.0.1', r));
  port = app.server.address().port;
});

after(async () => {
  await new Promise((r) => app.server.close(r));
  await app.flush();
  await fs.rm(dir, { recursive: true, force: true });
});

test('serves the app with security headers', async () => {
  const res = await request('GET', '/');
  assert.equal(res.status, 200);
  assert.match(res.headers['content-security-policy'], /script-src 'self'/);
  assert.equal(res.headers['x-frame-options'], 'DENY');
  assert.equal(res.headers['x-content-type-options'], 'nosniff');
  assert.match(res.text, /Visa Job Finder/);
});

test('config never exposes secrets and never lists India', async () => {
  const res = await request('GET', '/api/config');
  assert.equal(res.status, 200);
  assert.equal(res.json.countries.some((c) => c.code === 'IN'), false);
  assert.equal(res.json.adzuna.configured, false);
  assert.equal(/app_?key/i.test(res.text), false);
});

test('rejects foreign Host headers (DNS rebinding)', async () => {
  const res = await request('GET', '/api/config', { headers: { host: 'attacker.example' } });
  assert.equal(res.status, 421);
});

test('rejects cross-site and header-less writes', async () => {
  assert.equal((await request('POST', '/api/hidden', { body: { id: 'adzuna:gb:1' } })).status, 403);
  assert.equal((await request('POST', '/api/hidden', { body: { id: 'adzuna:gb:1' }, headers: { ...WRITE, origin: 'https://evil.example' } })).status, 403);
  assert.equal((await request('POST', '/api/hidden', { body: { id: 'adzuna:gb:1' }, headers: { ...WRITE, 'sec-fetch-site': 'cross-site' } })).status, 403);
  assert.equal((await request('POST', '/api/hidden', { body: 'id=x', headers: { ...WRITE, 'content-type': 'application/x-www-form-urlencoded' } })).status, 415);
});

test('static files cannot escape the public folder', async () => {
  for (const p of ['/../server/config.js', '/%2e%2e/%2e%2e/etc/passwd', '/.env', '/..%2fpackage.json']) {
    const res = await request('GET', p);
    assert.equal(res.status === 404 || res.status === 400, true, p);
  }
});

test('saved jobs: save, update status/notes, export CSV, remove', async () => {
  const id = encodeURIComponent(job.id);
  const saved = await request('PUT', `/api/saved/${id}`, { body: { job }, headers: WRITE });
  assert.equal(saved.status, 200);
  assert.equal(saved.json.status, 'saved');
  assert.equal(saved.json.job.role, undefined);
  assert.equal(saved.json.job.sponsorship.registerMatch, 'Rolls-Royce plc');

  assert.equal((await request('PATCH', `/api/saved/${id}`, { body: { status: 'admin' }, headers: WRITE })).status, 400);
  const patched = await request('PATCH', `/api/saved/${id}`, { body: { status: 'applied', notes: '=HYPERLINK("x")' }, headers: WRITE });
  assert.equal(patched.json.status, 'applied');

  const csv = await request('GET', '/api/saved/export.csv');
  assert.match(csv.headers['content-type'], /text\/csv/);
  assert.match(csv.text, /"'=HYPERLINK\(""x""\)"/); // formula neutralised

  const bad = await request('PUT', '/api/saved/adzuna%3Agb%3A43', { body: { job: { ...job, id: 'adzuna:gb:43', url: 'javascript:alert(1)' } }, headers: WRITE });
  assert.equal(bad.status, 400);

  assert.equal((await request('DELETE', `/api/saved/${id}`, { headers: WRITE })).status, 200);
  assert.equal((await request('GET', '/api/saved')).json.items.length, 0);
});

test('unknown API routes are 404 and errors do not leak stack traces', async () => {
  const res = await request('GET', '/api/nope');
  assert.equal(res.status, 404);
  assert.equal(res.text.includes('at '), false);
});
