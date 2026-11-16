// Visa Job Finder — local web app.  Start with:  npm start
import http from 'node:http';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { loadConfig, APP_ROOT } from './config.js';
import { Registers } from './registers.js';
import { Cache, Quota, SavedStore, stateFiles, STATUSES } from './state.js';
import { runSearch, parseParams, SOURCES, DEFAULT_COUNTRIES, PRESETS } from './search.js';
import { isConfigured as adzunaConfigured } from './sources/adzuna.js';
import { COUNTRIES, flagEmoji, EXCLUDED_COUNTRY } from './lib/countries.js';
import { redact } from './lib/fetch.js';
import { HttpError, applySecurityHeaders, checkRequest, sendJson, readJsonBody, serveStatic } from './http.js';

export async function createApp(config) {
  const files = stateFiles(config.dataDir);
  const registers = new Registers(config.dataDir);
  const cache = new Cache(files.cache);
  const quota = new Quota(files.usage, { adzuna: config.adzuna.dailyLimit });
  const store = new SavedStore(files.saved);
  await Promise.all([registers.load(), cache.load(), quota.load(), store.load()]);
  const ctx = { config, registers, cache, quota, store };
  const publicDir = path.join(APP_ROOT, 'public');

  function configPayload() {
    return {
      countries: COUNTRIES.filter((c) => c.code !== EXCLUDED_COUNTRY).map((c) => ({
        code: c.code, name: c.name, flag: flagEmoji(c.code), adzuna: Boolean(c.adzuna),
        hasRegister: registers.hasCountry(c.code), visaInfo: c.visaInfo || null, visaName: c.visaName || null,
      })),
      defaults: { countries: DEFAULT_COUNTRIES, query: PRESETS[0], days: 30, level: 'likely', sort: 'best' },
      presets: PRESETS,
      statuses: STATUSES,
      sources: Object.values(SOURCES).map((s) => ({
        id: s.id, label: s.label, homepage: s.homepage,
        remote: s.id === 'remotive' || s.id === 'jobicy',
        configured: s.id === 'adzuna' ? adzunaConfigured(config) : true,
      })),
      adzuna: { configured: adzunaConfigured(config), quota: quota.summary('adzuna') },
      registers: registers.status(),
    };
  }

  function savedId(pathname) {
    try {
      return decodeURIComponent(pathname.slice('/api/saved/'.length));
    } catch {
      throw new HttpError(400, 'Bad id');
    }
  }

  async function route(req, res, url) {
    const { pathname } = url;
    const m = req.method;

    if (pathname === '/api/config' && m === 'GET') return sendJson(res, 200, configPayload());

    if (pathname === '/api/search' && m === 'GET') {
      const params = parseParams(Object.fromEntries(url.searchParams));
      return sendJson(res, 200, await runSearch(params, ctx));
    }

    if (pathname === '/api/saved' && m === 'GET') return sendJson(res, 200, { items: store.list() });

    if (pathname === '/api/saved/export.csv' && m === 'GET') {
      const cell = (v) => {
        let s = String(v ?? '');
        if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`; // spreadsheet formula injection guard
        return `"${s.replace(/"/g, '""')}"`;
      };
      const rows = [['Status', 'Title', 'Company', 'Location', 'Country', 'Sponsorship', 'Register match', 'Notes', 'Saved', 'Link']];
      for (const e of store.list()) {
        rows.push([e.status, e.job.title, e.job.company, e.job.location, e.job.country, e.job.sponsorship.level,
          e.job.sponsorship.registerMatch, e.notes, e.savedAt.slice(0, 10), e.job.url]);
      }
      const csv = '﻿' + rows.map((r) => r.map(cell).join(',')).join('\r\n');
      res.writeHead(200, {
        'content-type': 'text/csv; charset=utf-8',
        'content-disposition': 'attachment; filename="visa-jobs-tracker.csv"',
        'cache-control': 'no-store',
      });
      return res.end(csv);
    }

    if (pathname.startsWith('/api/saved/')) {
      const id = savedId(pathname);
      if (m === 'PUT') {
        const body = await readJsonBody(req);
        if (!body.job || body.job.id !== id) throw new HttpError(400, 'Job id mismatch');
        try { return sendJson(res, 200, store.upsert(body.job)); } catch (err) { throw new HttpError(400, err.message); }
      }
      if (m === 'PATCH') {
        const body = await readJsonBody(req);
        let entry;
        try { entry = store.patch(id, { status: body.status, notes: body.notes }); } catch (err) { throw new HttpError(400, err.message); }
        if (!entry) throw new HttpError(404, 'Not saved');
        return sendJson(res, 200, entry);
      }
      if (m === 'DELETE') {
        if (!store.remove(id)) throw new HttpError(404, 'Not saved');
        return sendJson(res, 200, { ok: true });
      }
    }

    if (pathname === '/api/hidden' && m === 'POST') {
      const body = await readJsonBody(req);
      try { store.hide(String(body.id || '')); } catch (err) { throw new HttpError(400, err.message); }
      return sendJson(res, 200, { ok: true });
    }
    if (pathname === '/api/hidden' && m === 'DELETE') {
      store.unhideAll();
      return sendJson(res, 200, { ok: true });
    }

    if (pathname === '/api/registers' && m === 'GET') return sendJson(res, 200, registers.status());
    if (pathname === '/api/registers/update' && m === 'POST') {
      registers.update({ log: (msg) => console.log(`[registers] ${msg}`) }).catch((err) => console.error(`[registers] ${err.message}`));
      return sendJson(res, 202, registers.status());
    }

    if (pathname.startsWith('/api/')) throw new HttpError(404, 'Not found');
    if (m !== 'GET' && m !== 'HEAD') throw new HttpError(405, 'Method not allowed');
    return serveStatic(req, res, publicDir, pathname);
  }

  const server = http.createServer(async (req, res) => {
    applySecurityHeaders(res);
    try {
      checkRequest(req, { extraHosts: config.extraHosts });
      const url = new URL(req.url, 'http://localhost');
      await route(req, res, url);
    } catch (err) {
      const status = err instanceof HttpError ? err.status : 500;
      if (status === 500) console.error(redact(err.stack || err.message));
      if (!res.headersSent) sendJson(res, status, { error: status === 500 ? 'Something went wrong on the server' : err.message });
      else res.end();
    }
  });
  server.requestTimeout = 120000;

  async function flush() {
    await Promise.allSettled([store.save.flush(), cache.save.flush(), quota.save.flush()]);
  }

  return { server, ctx, flush };
}

async function main() {
  const config = loadConfig();
  const { server, ctx, flush } = await createApp(config);
  const { registers } = ctx;
  const log = (msg) => console.log(`[registers] ${msg}`);

  server.listen(config.port, config.host, () => {
    const shown = config.host === '0.0.0.0' || config.host === '::' ? 'localhost' : config.host;
    console.log(`\nVisa Job Finder is running:  http://${shown}:${config.port}\n`);
    if (!adzunaConfigured(config)) {
      console.log('Adzuna is not set up yet. Add ADZUNA_APP_ID and ADZUNA_APP_KEY to .env for UK, US, Canada,');
      console.log('Australia, Germany, Netherlands, Singapore and more (free key: https://developer.adzuna.com/signup).\n');
    }
  });

  if (config.autoUpdateRegisters && registers.needsUpdate(config.registerMaxAgeDays)) {
    log('Sponsor registers are missing or older than ' + config.registerMaxAgeDays + ' days; downloading in the background…');
    registers.update({ log }).catch((err) => log(`update failed: ${err.message}`));
  } else {
    registers.importManual(log).catch(() => {});
  }

  let closing = false;
  const shutdown = async () => {
    if (closing) return;
    closing = true;
    server.close();
    await flush();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch((err) => {
    console.error(redact(err.stack || err.message));
    process.exit(1);
  });
}
