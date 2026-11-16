import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

export async function readJson(file, fallback) {
  try {
    return JSON.parse(await fs.readFile(file, 'utf8'));
  } catch (err) {
    if (err.code === 'ENOENT') return fallback;
    if (err instanceof SyntaxError) {
      // Keep the unreadable file for inspection instead of silently losing it.
      await fs.rename(file, `${file}.corrupt-${Date.now()}`).catch(() => {});
      return fallback;
    }
    throw err;
  }
}

// Write to a temp file then rename, so a crash never leaves half-written JSON.
export async function writeJsonAtomic(file, data) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${crypto.randomBytes(6).toString('hex')}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(data), 'utf8');
  await fs.rename(tmp, file);
}
