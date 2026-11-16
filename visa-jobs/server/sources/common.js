import { foldText, truncate } from '../lib/text.js';

// Words that don't help match a job title.
const STOP = new Set(['and', 'or', 'the', 'a', 'an', 'of', 'in', 'for', 'to', 'with', 'm', 'f', 'd', 'w', 'x']);

// English -> German alternatives, so a search for "maintenance engineer" also
// finds "Instandhaltungsingenieur" on German boards. Matching is on word starts.
const SYNONYMS = {
  maintenance: ['instandhaltung', 'wartung', 'instandsetzung'],
  reliability: ['zuverlassigkeit'],
  engineer: ['ingenieur', 'engineering'],
  engineering: ['engineer', 'ingenieur'],
  technician: ['techniker', 'mechaniker', 'mechatroniker', 'elektroniker', 'tech'],
  manager: ['leiter', 'leitung', 'management', 'head'],
  planner: ['planer', 'planung', 'scheduler'],
  electrical: ['elektro', 'elektriker', 'elektrotechnik'],
  mechanical: ['mechanisch', 'maschinenbau', 'mechaniker'],
  plant: ['anlagen', 'werk', 'site'],
  asset: ['assets', 'anlagen'],
};

// Split "reliability engineer -site -software" into include and exclude words.
export function splitQuery(query) {
  const include = [];
  const exclude = [];
  for (const raw of String(query ?? '').split(/\s+/)) {
    if (!raw) continue;
    if (raw.startsWith('-') && raw.length > 1) exclude.push(...foldText(raw.slice(1)).split(' ').filter(Boolean));
    else include.push(...foldText(raw).split(' ').filter(Boolean));
  }
  return { include: include.filter((t) => t.length > 1 && !STOP.has(t)), exclude: exclude.filter((t) => t.length > 1) };
}

// Returns a predicate over a job: every query word (or a synonym) must start a
// word in the title or tags, and no "-excluded" word may appear in the title.
// Empty query matches everything.
export function titleMatcher(query) {
  const { include, exclude } = splitQuery(query);
  if (!include.length && !exclude.length) return () => true;
  const groups = include.map((t) => [t, ...(SYNONYMS[t] || [])]);
  return (job) => {
    const title = ' ' + foldText(job.title) + ' ';
    if (exclude.some((x) => title.includes(' ' + x))) return false;
    const hay = ' ' + foldText(`${job.title} ${(job.tags || []).join(' ')}`) + ' ';
    // The typed word must start a word; longer synonyms may also sit inside a
    // German compound ("Instandhaltungsingenieur", "Industriemechaniker").
    return groups.every(([word, ...alts]) => hay.includes(' ' + word)
      || alts.some((a) => (a.length >= 6 ? hay.includes(a) : hay.includes(' ' + a))));
  };
}

export function makeJob(fields) {
  const description = truncate(fields.description || '', 6000);
  return {
    id: fields.id,
    source: fields.source,
    title: (fields.title || '').trim() || 'Untitled role',
    company: (fields.company || '').trim(),
    location: (fields.location || '').trim(),
    country: fields.country || null,
    remote: Boolean(fields.remote),
    eligibility: fields.eligibility || null,
    url: fields.url,
    postedAt: fields.postedAt || null,
    salaryText: fields.salaryText || '',
    salaryMax: Number.isFinite(fields.salaryMax) ? fields.salaryMax : null,
    tags: (fields.tags || []).filter(Boolean).slice(0, 8),
    contract: fields.contract || '',
    description,
    snippet: truncate(description.replace(/\s+/g, ' '), 320),
    feedTagged: Boolean(fields.feedTagged),
    keywordMatched: Boolean(fields.keywordMatched),
    descriptionIsSnippet: Boolean(fields.descriptionIsSnippet),
  };
}

export function formatSalary(min, max, currency, { predicted = false, period = '' } = {}) {
  const fmt = (n) => {
    if (!Number.isFinite(n) || n <= 0) return null;
    try {
      return new Intl.NumberFormat('en', { style: 'currency', currency, maximumFractionDigits: 0, notation: n >= 100000 ? 'compact' : 'standard' }).format(n);
    } catch {
      return `${Math.round(n)} ${currency}`;
    }
  };
  const a = fmt(min);
  const b = fmt(max);
  let text = a && b && a !== b ? `${a} – ${b}` : a || b || '';
  if (text && period) text += ` ${period}`;
  if (text && predicted) text += ' (estimate)';
  return text;
}

export function isoDate(value) {
  if (value === null || value === undefined || value === '') return null;
  const d = typeof value === 'number' ? new Date(value < 1e12 ? value * 1000 : value) : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}
