// HTTP plumbing: security headers, request guards, JSON I/O, static files.
import fs from 'node:fs/promises';
import path from 'node:path';

export const CLIENT_HEADER = 'x-requested-with';
export const CLIENT_HEADER_VALUE = 'visa-job-finder';

const SECURITY_HEADERS = {
  'content-security-policy': [
    "default-src 'self'", "script-src 'self'", "style-src 'self'", "img-src 'self' data:",
    "connect-src 'self'", "font-src 'self'", "object-src 'none'", "base-uri 'none'",
    "form-action 'self'", "frame-ancestors 'none'",
  ].join('; '),
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'no-referrer',
  'cross-origin-opener-policy': 'same-origin',
  'cross-origin-resource-policy': 'same-origin',
  'permissions-policy': 'camera=(), microphone=(), geolocation=()',
};

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function applySecurityHeaders(res) {
  for (const [k, v] of Object.entries(SECURITY_HEADERS)) res.setHeader(k, v);
}

export function sendJson(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'content-length': Buffer.byteLength(data) });
  res.end(data);
}

function hostnameOf(hostHeader) {
  const h = String(hostHeader || '').trim().toLowerCase();
  if (h.startsWith('[')) return h.slice(0, h.indexOf(']') + 1);
  return h.split(':')[0];
}

// DNS-rebinding guard: the Host header must be this machine (or a name the user
// explicitly allowed). CSRF guard for writes: same-origin + a custom header,
// which a cross-site form or <img> cannot send without a CORS preflight that this
// server never approves.
export function checkRequest(req, { extraHosts = [] } = {}) {
  const allowed = new Set(['localhost', '127.0.0.1', '[::1]', ...extraHosts]);
  const host = hostnameOf(req.headers.host);
  if (!allowed.has(host)) throw new HttpError(421, 'Unknown host. Open the app at http://localhost:<port>.');
  const origin = req.headers.origin;
  if (origin && origin !== 'null') {
    let originHost;
    try { originHost = new URL(origin).host; } catch { throw new HttpError(403, 'Bad origin'); }
    if (originHost.toLowerCase() !== String(req.headers.host).toLowerCase()) throw new HttpError(403, 'Cross-site request blocked');
  } else if (origin === 'null') {
    throw new HttpError(403, 'Cross-site request blocked');
  }
  const unsafe = !['GET', 'HEAD'].includes(req.method);
  if (unsafe && req.headers[CLIENT_HEADER] !== CLIENT_HEADER_VALUE) {
    throw new HttpError(403, 'Missing client header');
  }
  if (req.headers['sec-fetch-site'] && !['same-origin', 'none'].includes(req.headers['sec-fetch-site']) && (unsafe || req.url.startsWith('/api/'))) {
    throw new HttpError(403, 'Cross-site request blocked');
  }
}

export async function readJsonBody(req, maxBytes = 64 * 1024) {
  const type = String(req.headers['content-type'] || '');
  if (!type.startsWith('application/json')) throw new HttpError(415, 'Send JSON');
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > maxBytes) throw new HttpError(413, 'Request too large');
    chunks.push(chunk);
  }
  try {
    const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('not an object');
    return parsed;
  } catch {
    throw new HttpError(400, 'Invalid JSON');
  }
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
};

export async function serveStatic(req, res, publicDir, pathname) {
  let rel;
  try { rel = decodeURIComponent(pathname); } catch { throw new HttpError(400, 'Bad path'); }
  if (rel.includes('\0')) throw new HttpError(400, 'Bad path');
  if (rel === '/' || rel === '') rel = '/index.html';
  const root = path.resolve(publicDir);
  const file = path.resolve(root, '.' + path.posix.normalize(rel));
  if (file !== root && !file.startsWith(root + path.sep)) throw new HttpError(404, 'Not found');
  const type = MIME[path.extname(file).toLowerCase()];
  if (!type) throw new HttpError(404, 'Not found');
  let data;
  try {
    data = await fs.readFile(file);
  } catch {
    throw new HttpError(404, 'Not found');
  }
  res.writeHead(200, { 'content-type': type, 'content-length': data.length, 'cache-control': 'no-cache' });
  res.end(req.method === 'HEAD' ? undefined : data);
}
