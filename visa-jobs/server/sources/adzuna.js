// Adzuna job search API (free key). One request per country per search; results
// are cached for 6 hours and counted against a daily budget.
// Docs: https://developer.adzuna.com/  (OpenAPI spec: /swagger/spec/test2.json)

import { fetchJson, mapLimit } from '../lib/fetch.js';
import { htmlToText } from '../lib/text.js';
import { ADZUNA_COUNTRIES } from '../lib/countries.js';
import { makeJob, formatSalary, isoDate, splitQuery } from './common.js';

export const id = 'adzuna';
export const label = 'Adzuna';
export const homepage = 'https://www.adzuna.com/';
const TTL = 6 * 3600 * 1000;
// Words that make Adzuna search the FULL advert text for sponsorship hints.
export const SPONSOR_WORDS = 'visa sponsorship sponsor relocation';

export function isConfigured(config) {
  return Boolean(config.adzuna.appId && config.adzuna.appKey);
}

export function buildUrl(config, cc, { query, days }, keywordFilter) {
  const u = new URL(`https://api.adzuna.com/v1/api/jobs/${cc}/search/1`);
  u.searchParams.set('app_id', config.adzuna.appId);
  u.searchParams.set('app_key', config.adzuna.appKey);
  u.searchParams.set('results_per_page', '50');
  const { include, exclude } = splitQuery(query);
  if (include.length) u.searchParams.set('what', include.join(' '));
  if (exclude.length) u.searchParams.set('what_exclude', exclude.join(' '));
  if (keywordFilter) u.searchParams.set('what_or', SPONSOR_WORDS);
  u.searchParams.set('max_days_old', String(days));
  u.searchParams.set('sort_by', 'date');
  u.searchParams.set('content-type', 'application/json');
  return u.toString();
}

export function mapResult(r, country, keywordFilter) {
  const currency = country.currency;
  const predicted = String(r.salary_is_predicted) === '1';
  const min = Number(r.salary_min);
  const max = Number(r.salary_max);
  return makeJob({
    id: `adzuna:${country.adzuna}:${r.id}`,
    source: id,
    title: htmlToText(r.title),
    company: r.company?.display_name || '',
    location: r.location?.display_name || country.name,
    country: country.code,
    url: r.redirect_url,
    postedAt: isoDate(r.created),
    salaryText: formatSalary(min, max, currency, { predicted, period: 'a year' }),
    salaryMax: Number.isFinite(max) && max > 0 ? max : null,
    tags: [r.category?.label && !/unknown/i.test(r.category.label) ? r.category.label : null],
    contract: [r.contract_type, r.contract_time].filter(Boolean).join(', ').replace(/_/g, ' '),
    description: htmlToText(r.description),
    descriptionIsSnippet: true,
    keywordMatched: keywordFilter,
  });
}

// params: { query, countries:Set, days, sponsorWords: 'auto'|'always'|'never' }
// ctx: { config, cache, quota, registers }
export async function search(params, ctx) {
  const { config, cache, quota, registers } = ctx;
  const targets = ADZUNA_COUNTRIES.filter((c) => params.countries.has(c.code));
  const notes = [];
  let cached = 0;
  let requested = 0;
  let skipped = 0;
  const errors = [];

  const perCountry = await mapLimit(targets, 3, async (country) => {
    // "auto": where we hold an official register (UK, NL, CA...) every job can be
    // checked against it, so search all ads; elsewhere ask Adzuna to keep only
    // ads whose full text mentions visa/sponsor/relocation.
    const keywordFilter = params.sponsorWords === 'always'
      || (params.sponsorWords === 'auto' && !registers.hasCountry(country.code));
    const key = `adzuna|${country.adzuna}|${params.query.toLowerCase()}|${params.days}|${keywordFilter ? 1 : 0}`;
    let data = cache.get(key);
    if (data) {
      cached++;
    } else {
      if (!quota.take('adzuna')) {
        skipped++;
        return [];
      }
      requested++;
      try {
        data = await fetchJson(buildUrl(config, country.adzuna, params, keywordFilter), { timeoutMs: 20000 });
      } catch (err) {
        errors.push(err.status === 401 || /AUTH_FAIL/.test(err.body || '')
          ? 'Adzuna rejected the app ID/key; check ADZUNA_APP_ID and ADZUNA_APP_KEY in .env'
          : err.status === 429 ? 'Adzuna rate limit reached; try again later'
            : `${country.name}: ${err.message}`);
        return [];
      }
      cache.set(key, data, TTL);
    }
    return (data.results || []).filter((r) => r.redirect_url).map((r) => mapResult(r, country, keywordFilter));
  });

  if (skipped) notes.push(`Daily Adzuna budget used up: ${skipped} ${skipped === 1 ? 'country was' : 'countries were'} skipped. It resets at midnight UTC.`);
  const uniqueErrors = [...new Set(errors)];
  return {
    jobs: perCountry.flat(),
    notes,
    error: uniqueErrors.length && !perCountry.flat().length ? uniqueErrors.join('; ') : null,
    warnings: uniqueErrors,
    stats: { countries: targets.length, requested, cached, skipped },
  };
}
