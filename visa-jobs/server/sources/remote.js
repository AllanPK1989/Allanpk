// Remote-job feeds (no key). Only queried when "Include remote jobs" is on.
//   Remotive: https://remotive.com/api/remote-jobs  — max ~4 calls/day advised,
//             link back to Remotive and credit it as the source.
//   Jobicy:   https://jobicy.com/api/v2/remote-jobs — credit Jobicy, link to the
//             original job URL.

import { fetchJson } from '../lib/fetch.js';
import { htmlToText } from '../lib/text.js';
import { parseEligibility } from '../lib/countries.js';
import { makeJob, isoDate, titleMatcher, formatSalary } from './common.js';

const TTL = 6 * 3600 * 1000;

function remoteFields(eligibilityText) {
  const elig = parseEligibility(eligibilityText);
  const country = elig.countries.length === 1 && !elig.regions.length ? elig.countries[0] : null;
  return { elig, country };
}

export function mapRemotive(j) {
  const { elig, country } = remoteFields(j.candidate_required_location);
  return {
    indiaOnly: elig.indiaOnly,
    job: makeJob({
      id: `remotive:${j.id}`,
      source: 'remotive',
      title: j.title,
      company: j.company_name,
      location: `Remote · ${j.candidate_required_location || 'location not stated'}`,
      country,
      remote: true,
      eligibility: { text: j.candidate_required_location || '', countries: elig.countries, regions: elig.regions },
      url: j.url,
      postedAt: isoDate(j.publication_date),
      salaryText: j.salary || '',
      tags: [j.category, ...(j.tags || []).slice(0, 5)],
      contract: String(j.job_type || '').replace(/_/g, ' '),
      description: htmlToText(j.description),
    }),
  };
}

export function mapJobicy(j) {
  const geo = String(j.jobGeo || '');
  const { elig, country } = remoteFields(geo);
  const min = Number(j.annualSalaryMin);
  const max = Number(j.annualSalaryMax);
  return {
    indiaOnly: elig.indiaOnly,
    job: makeJob({
      id: `jobicy:${j.id}`,
      source: 'jobicy',
      title: htmlToText(j.jobTitle),
      company: j.companyName,
      location: `Remote · ${geo || 'location not stated'}`,
      country,
      remote: true,
      eligibility: { text: geo, countries: elig.countries, regions: elig.regions },
      url: j.url,
      postedAt: isoDate(j.pubDate),
      salaryText: j.salaryCurrency ? formatSalary(min, max, j.salaryCurrency, { period: 'a year' }) : '',
      salaryMax: Number.isFinite(max) && max > 0 ? max : null,
      tags: [...(j.jobIndustry || []), j.jobLevel].map((t) => htmlToText(t)),
      contract: (j.jobType || []).join(', '),
      description: htmlToText(j.jobDescription || j.jobExcerpt),
    }),
  };
}

async function cachedFetch(cache, key, url) {
  const hit = cache.get(key);
  if (hit) return { data: hit, cached: true };
  const data = await fetchJson(url, { timeoutMs: 20000 });
  return { data, cached: false };
}

export const remotive = {
  id: 'remotive',
  label: 'Remotive',
  homepage: 'https://remotive.com/',
  async search(params, { cache }) {
    const q = params.query.trim().toLowerCase();
    const key = `remotive|${q}`;
    try {
      const { data, cached } = await cachedFetch(cache, key,
        `https://remotive.com/api/remote-jobs?limit=100${q ? `&search=${encodeURIComponent(q)}` : ''}`);
      const slim = cached ? data : { jobs: (data.jobs || []).map(({ id, url, title, company_name, category, tags, job_type, publication_date, candidate_required_location, salary, description }) => ({ id, url, title, company_name, category, tags, job_type, publication_date, candidate_required_location, salary, description })) };
      if (!cached) cache.set(key, slim, TTL);
      const matches = titleMatcher(params.query);
      const mapped = slim.jobs.filter((j) => j.url).map(mapRemotive);
      return {
        jobs: mapped.filter((m) => !m.indiaOnly).map((m) => m.job).filter(matches),
        notes: [], error: null, warnings: [],
        stats: { scanned: slim.jobs.length, cached: cached ? 1 : 0, requested: cached ? 0 : 1 },
      };
    } catch (err) {
      return { jobs: [], notes: [], error: err.message, warnings: [], stats: {} };
    }
  },
};

export const jobicy = {
  id: 'jobicy',
  label: 'Jobicy',
  homepage: 'https://jobicy.com/',
  async search(params, { cache }) {
    const q = params.query.trim().toLowerCase();
    const key = `jobicy|${q}`;
    try {
      const { data, cached } = await cachedFetch(cache, key,
        `https://jobicy.com/api/v2/remote-jobs?count=50${q ? `&tag=${encodeURIComponent(q)}` : ''}`);
      const slim = cached ? data : { jobs: data.jobs || [] };
      if (!cached) cache.set(key, slim, TTL);
      const matches = titleMatcher(params.query);
      const mapped = slim.jobs.filter((j) => j.url).map(mapJobicy);
      return {
        jobs: mapped.filter((m) => !m.indiaOnly).map((m) => m.job).filter(matches),
        notes: [], error: null, warnings: [],
        stats: { scanned: slim.jobs.length, cached: cached ? 1 : 0, requested: cached ? 0 : 1 },
      };
    } catch (err) {
      // Jobicy answers 404 or an empty list when a tag has no jobs.
      if (err.status === 404) return { jobs: [], notes: [], error: null, warnings: [], stats: {} };
      return { jobs: [], notes: [], error: err.message, warnings: [], stats: {} };
    }
  },
};
