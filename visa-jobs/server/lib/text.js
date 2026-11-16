// Text helpers: turn job-board HTML into plain text, and small string utilities.
// Output of these functions is always rendered with textContent in the browser,
// so they only need to produce readable text, not "safe HTML".

const NAMED_ENTITIES = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', ndash: '–', mdash: '—',
  hellip: '…', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“', bull: '•', middot: '·',
  euro: '€', pound: '£', copy: '©', reg: '®', trade: '™', auml: 'ä', ouml: 'ö', uuml: 'ü',
  Auml: 'Ä', Ouml: 'Ö', Uuml: 'Ü', szlig: 'ß', eacute: 'é', egrave: 'è', agrave: 'à',
  ccedil: 'ç', iacute: 'í', oacute: 'ó', aacute: 'á', uacute: 'ú', ntilde: 'ñ', shy: '',
  zwj: '', zwnj: '', laquo: '«', raquo: '»',
};

export function decodeEntities(input) {
  return String(input ?? '').replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (match, body) => {
    if (body[0] === '#') {
      const code = body[1] === 'x' || body[1] === 'X'
        ? parseInt(body.slice(2), 16)
        : parseInt(body.slice(1), 10);
      if (!Number.isFinite(code) || code <= 0 || code > 0x10ffff) return ' ';
      try { return String.fromCodePoint(code); } catch { return ' '; }
    }
    return Object.hasOwn(NAMED_ENTITIES, body) ? NAMED_ENTITIES[body] : match;
  });
}

const TAG_RE = /<\/?[a-z][^>]*>/i;

// Some feeds (seen on Arbeitnow) double-escape their HTML ("&lt;p&gt;"), so decode
// and strip twice when tags reappear after the first pass.
export function htmlToText(input) {
  let s = String(input ?? '');
  for (let pass = 0; pass < 2; pass++) {
    s = s
      .replace(/<(script|style)\b[\s\S]*?<\/\1\s*>/gi, ' ')
      .replace(/<li\b[^>]*>/gi, '\n• ')
      .replace(/<(?:br|hr)\b[^>]*>/gi, '\n')
      .replace(/<\/(?:p|div|ul|ol|h[1-6]|tr|table|section|blockquote)\s*>/gi, '\n')
      .replace(/<[^>]+>/g, ' ');
    s = decodeEntities(s);
    if (!TAG_RE.test(s)) break;
  }
  return s
    .replace(/[​‌‍﻿]/g, '')
    .replace(/[ \t \r\f\v]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function truncate(text, max) {
  const s = String(text ?? '');
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  return (lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd() + '…';
}

// Lowercase, strip accents, collapse non-alphanumerics. Used for keyword matching.
export function foldText(input) {
  return String(input ?? '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/ß/g, 'ss')
    .toLowerCase()
    .replace(/[^a-z0-9+#]+/g, ' ')
    .trim();
}

// Return the sentence containing a regex match (capped at `radius` characters
// either side), for showing evidence.
export function excerptAround(text, index, length, radius = 160) {
  const boundary = /[.!?•\n]/;
  let start = index;
  while (start > 0 && index - start < radius && !boundary.test(text[start - 1])) start--;
  let end = index + length;
  while (end < text.length && end - (index + length) < radius && !boundary.test(text[end])) end++;
  if (end < text.length && /[.!?]/.test(text[end])) end++;
  let out = text.slice(start, end).replace(/\s+/g, ' ').trim();
  if (start > 0 && !boundary.test(text[start - 1])) out = '…' + out;
  if (end < text.length && !boundary.test(text[end - 1]) && !boundary.test(text[end])) out += '…';
  return out;
}

export function isHttpUrl(value) {
  if (typeof value !== 'string' || value.length > 2048) return false;
  try {
    const u = new URL(value);
    return u.protocol === 'https:' || u.protocol === 'http:';
  } catch {
    return false;
  }
}
