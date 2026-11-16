import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

export const APP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function int(value, fallback, min, max) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : fallback;
}

export function loadConfig(env = process.env) {
  const envFile = path.join(APP_ROOT, '.env');
  if (env === process.env && fs.existsSync(envFile)) {
    try { process.loadEnvFile(envFile); } catch (err) { console.warn(`Could not read .env: ${err.message}`); }
  }
  const dataDir = path.resolve(APP_ROOT, env.DATA_DIR || './data');
  return {
    host: env.HOST || '127.0.0.1',
    port: int(env.PORT, 8080, 1, 65535),
    dataDir,
    adzuna: {
      appId: (env.ADZUNA_APP_ID || '').trim(),
      appKey: (env.ADZUNA_APP_KEY || '').trim(),
      dailyLimit: int(env.ADZUNA_DAILY_LIMIT, 250, 0, 100000),
    },
    registerMaxAgeDays: int(env.REGISTER_MAX_AGE_DAYS, 7, 1, 365),
    autoUpdateRegisters: env.AUTO_UPDATE_REGISTERS !== '0',
    arbeitnowPages: int(env.ARBEITNOW_PAGES, 8, 1, 15),
    // Extra Host header values to accept (e.g. a LAN name), comma-separated.
    extraHosts: (env.ALLOWED_HOSTS || '').split(',').map((h) => h.trim().toLowerCase()).filter(Boolean),
  };
}
