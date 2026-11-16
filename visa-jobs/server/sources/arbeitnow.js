// Arbeitnow free job board API (Europe, mostly Germany). No key needed.
// We read its visa-sponsorship feed (?visa_sponsorship=true). The flag is not in
// the job objects and the feed includes some "NOT eligible for visa sponsorship"
// ads, so every posting's text is still checked.
// Terms: free public API, "please do not abuse", link back to arbeitnow.com.

import { fetchJson } from '../lib/fetch.js';
import { htmlToText } from '../lib/text.js';
import { parseLocation, countryFromText } from '../lib/countries.js';
import { makeJob, isoDate, titleMatcher } from './common.js';

export const id = 'arbeitnow';
export const label = 'Arbeitnow';
export const homepage = 'https://www.arbeitnow.com/';
const TTL = 2 * 3600 * 1000;

export function mapItem(item) {
  const description = htmlToText(item.description);
  const loc = parseLocation(item.location);
  const country = loc.country || countryFromText(`${item.location} ${description}`);
  return makeJob({
    id: `arbeitnow:${item.slug}`,
    source: id,
    title: item.title,
    company: item.company_name,
    location: item.location || (item.remote ? 'Remote' : ''),
    country,
    remote: Boolean(item.remote) || loc.remote,
    url: item.url,
    postedAt: isoDate(item.created_at),
    tags: [...(item.tags || []), ...(item.job_types || [])],
    contract: (item.job_types || []).join(', '),
    description,
    feedTagged: true,
  });
}

export async function search(params, { cache, config }) {
  const pages = config.arbeitnowPages;
  const all = [];
  let cached = 0;
  let requested = 0;
  let error = null;
  for (let page = 1; page <= pages; page++) {
    const key = `arbeitnow|visa|${page}`;
    let data = cache.get(key);
    if (data) cached++;
    else {
      try {
        requested++;
        data = await fetchJson(`https://www.arbeitnow.com/api/job-board-api?visa_sponsorship=true&page=${page}`, { timeoutMs: 20000 });
        // Keep only what we use so the cache file stays small.
        data = {
          data: (data.data || []).map(({ slug, company_name, title, description, remote, url, tags, job_types, location, created_at }) =>
            ({ slug, company_name, title, description, remote, url, tags, job_types, location, created_at })),
          hasNext: Boolean(data.links?.next),
        };
        cache.set(key, data, TTL);
      } catch (err) {
        error = err.message;
        break;
      }
    }
    all.push(...data.data);
    if (!data.hasNext) break;
  }
  const matches = titleMatcher(params.query);
  const jobs = all.filter((item) => item.url && item.slug).map(mapItem).filter(matches);
  return {
    jobs,
    notes: [],
    error: error && !all.length ? error : null,
    warnings: error && all.length ? [`Only part of the feed loaded: ${error}`] : [],
    stats: { scanned: all.length, requested, cached },
  };
}
