// Company-name normalisation so a job board's "Siemens Energy" matches the
// register's "Siemens Energy Limited". Matching is deliberately exact after
// normalisation: a false "licensed sponsor" badge is worse than a missed one.

// Words removed from the END of a name (legal forms, country/group suffixes).
const TRAILING_NOISE = new Set([
  'ltd', 'limited', 'plc', 'llp', 'llc', 'lp', 'inc', 'incorporated', 'corp', 'corporation',
  'co', 'company', 'cos', 'gmbh', 'mbh', 'ag', 'kg', 'kgaa', 'se', 'bv', 'nv', 'vof', 'sa', 'sas',
  'sarl', 'srl', 'spa', 'sl', 'slu', 'pty', 'pte', 'oy', 'oyj', 'ab', 'asa', 'aps', 'ulc', 'ltee',
  'group', 'holdings', 'holding', 'international', 'intl', 'uk', 'gb', 'usa', 'us', 'canada',
  'nederland', 'netherlands', 'europe', 'emea', 'cic', 'the',
]);

export function normalizeCompany(name) {
  let s = String(name ?? '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/ß/g, 'ss');
  // "B.V." -> "bv", "S.A." -> "sa", "N.V." -> "nv" before punctuation is stripped.
  s = s.replace(/\b([a-z])\.\s?([a-z])\.(?:\s?([a-z])\.)?/g, (_, a, b, c) => a + b + (c || ''));
  s = s
    .replace(/[&+]/g, ' and ')
    .replace(/['’`]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
  const tokens = s.split(' ').filter(Boolean);
  if (tokens[0] === 'the' && tokens.length > 1) tokens.shift();
  while (tokens.length > 1 && TRAILING_NOISE.has(tokens[tokens.length - 1])) tokens.pop();
  return tokens.join(' ');
}

// One register line can name several entities:
//   "Branos Oxford Ltd T/A Lilo"                     -> both names
//   "Siemens Holdings plc (including Siemens plc)"   -> both names
//   "Acme Ltd (trading as Acme Engineering)"         -> both names
export function companyAliases(raw) {
  const name = String(raw ?? '').trim();
  if (!name) return [];
  const parts = new Set();
  const parenthetical = [];
  const base = name.replace(/\(([^)]*)\)/g, (_, inner) => {
    parenthetical.push(inner);
    return ' ';
  });
  for (const piece of base.split(/\s+(?:t\/a|trading as|t\/as|formerly|aka|a\.k\.a\.)\s+/i)) parts.add(piece);
  for (const inner of parenthetical) {
    const m = inner.match(/^\s*(?:including|incl\.?|t\/a|trading as|formerly|aka)\s+(.+)$/i);
    if (m) for (const piece of m[1].split(/\s*(?:,|;| and )\s*/i)) parts.add(piece);
  }
  const out = new Set();
  for (const p of parts) {
    const n = normalizeCompany(p);
    if (n.length >= 2) out.add(n);
  }
  return [...out];
}
