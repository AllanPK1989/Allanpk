/** Password hashing with WebCrypto PBKDF2-SHA256. Runs in the browser and in Node 20+ tests. */

const ITERATIONS = 120_000;
const KEY_BYTES = 32;

function subtle(): SubtleCrypto {
  const c = globalThis.crypto;
  if (!c || !c.subtle) throw new Error("WebCrypto is not available in this browser");
  return c.subtle;
}

function toHex(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += b.toString(16).padStart(2, "0");
  return s;
}

function fromHex(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

async function derive(password: string, salt: Uint8Array): Promise<string> {
  const key = await subtle().importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await subtle().deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: salt as BufferSource, iterations: ITERATIONS },
    key,
    KEY_BYTES * 8,
  );
  return toHex(new Uint8Array(bits));
}

export async function hashPassword(password: string): Promise<{ hash: string; salt: string }> {
  const salt = new Uint8Array(16);
  globalThis.crypto.getRandomValues(salt);
  return { hash: await derive(password, salt), salt: toHex(salt) };
}

export async function verifyPassword(password: string, saltHex: string, expectedHash: string): Promise<boolean> {
  if (!saltHex || !expectedHash) return false;
  const actual = await derive(password, fromHex(saltHex));
  if (actual.length !== expectedHash.length) return false;
  let diff = 0;
  for (let i = 0; i < actual.length; i++) diff |= actual.charCodeAt(i) ^ expectedHash.charCodeAt(i);
  return diff === 0;
}

export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

export function validatePassword(password: string): string | null {
  if (password.length < PASSWORD_MIN) return `Use at least ${PASSWORD_MIN} characters`;
  if (password.length > PASSWORD_MAX) return `Use at most ${PASSWORD_MAX} characters`;
  return null;
}

export const MAX_FAILED_LOGINS = 5;
export const LOCK_MINUTES = 15;

const EMPLOYEE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$/;
export function validateEmployeeId(id: string): string | null {
  return EMPLOYEE_ID_RE.test(id) ? null : "Employee ID: 2 to 40 letters, digits, dots, dashes or underscores";
}
