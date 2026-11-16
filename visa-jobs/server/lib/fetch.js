// Outbound HTTP for fixed, hard-coded data sources only (no user-supplied URLs,
// so no SSRF surface). Adds a timeout, a response-size cap, and redaction of
// API keys from any error message.

const USER_AGENT = 'visa-job-finder/1.0 (personal job search tool)';

export function redact(text) {
  return String(text ?? '').replace(/(app_key|app_id|api_key|apikey|key|token)=([^&\s"]+)/gi, '$1=***');
}

export class FetchError extends Error {
  constructor(message, { status = 0, body = '' } = {}) {
    super(redact(message));
    this.status = status;
    this.body = redact(String(body).slice(0, 300));
  }
}

export async function fetchBuffer(url, { timeoutMs = 30000, maxBytes = 80 * 1024 * 1024, headers = {}, retries = 0 } = {}) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { 'user-agent': USER_AGENT, accept: '*/*', ...headers },
        signal: AbortSignal.timeout(timeoutMs),
        redirect: 'follow',
      });
      const chunks = [];
      let total = 0;
      if (res.body) {
        for await (const chunk of res.body) {
          total += chunk.length;
          if (total > maxBytes) throw new FetchError(`Response from ${new URL(url).host} is larger than ${maxBytes} bytes`);
          chunks.push(chunk);
        }
      }
      const buffer = Buffer.concat(chunks);
      if (!res.ok) {
        throw new FetchError(`${new URL(url).host} answered HTTP ${res.status}`, { status: res.status, body: buffer.toString('utf8') });
      }
      return { buffer, status: res.status, url: res.url, headers: res.headers };
    } catch (err) {
      lastError = err instanceof FetchError ? err : new FetchError(`Could not reach ${safeHost(url)}: ${err.cause?.code || err.name || err.message}`);
      const retryable = !(err instanceof FetchError) || err.status >= 500 || err.status === 429;
      if (!retryable || attempt === retries) break;
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }
  throw lastError;
}

export async function fetchJson(url, options = {}) {
  const { buffer } = await fetchBuffer(url, { maxBytes: 20 * 1024 * 1024, ...options, headers: { accept: 'application/json', ...(options.headers || {}) } });
  try {
    return JSON.parse(buffer.toString('utf8'));
  } catch {
    throw new FetchError(`${safeHost(url)} did not return valid JSON`);
  }
}

function safeHost(url) {
  try { return new URL(url).host; } catch { return 'source'; }
}

// Run async tasks with a concurrency limit.
export async function mapLimit(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  });
  await Promise.all(workers);
  return results;
}
