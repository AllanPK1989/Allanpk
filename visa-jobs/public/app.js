// Visa Job Finder front end. All third-party text is inserted with textContent
// (never innerHTML), and links are only rendered for http(s) URLs.

const $ = (sel, root = document) => root.querySelector(sel);

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

function safeUrl(u) {
  try {
    const url = new URL(u);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
}

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: {
      ...(body !== undefined ? { 'content-type': 'application/json' } : {}),
      ...(method !== 'GET' ? { 'x-requested-with': 'visa-job-finder' } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

const prefs = {
  get() {
    try { return JSON.parse(localStorage.getItem('vjf-prefs') || '{}'); } catch { return {}; }
  },
  set(value) {
    try { localStorage.setItem('vjf-prefs', JSON.stringify(value)); } catch { /* private mode */ }
  },
};

const LEVEL_INFO = {
  stated: { label: 'Sponsorship offered', help: 'The posting itself says visa sponsorship or visa support is available.' },
  licensed: { label: 'Licensed sponsor', help: "The employer is on that country's official sponsor list. The ad doesn't say whether this role is sponsored." },
  tagged: { label: 'Listed as visa-sponsored', help: "The job board lists this under visa sponsorship, but the ad text doesn't say so explicitly." },
  relocation: { label: 'Relocation help', help: 'The ad offers relocation help, which often comes with visa support.' },
  keyword: { label: 'Mentions visa/sponsor', help: 'Adzuna found visa, sponsor or relocation words in the full ad, which you can only see on the job page. Check the wording.' },
  unknown: { label: 'No sponsorship info', help: 'Nothing either way. Ask the employer.' },
  no: { label: 'Says no sponsorship', help: 'The posting says it does not sponsor visas.' },
};
const SOURCE_LABEL = { adzuna: 'Adzuna', arbeitnow: 'Arbeitnow', remotive: 'Remotive', jobicy: 'Jobicy' };
const STATUS_LABEL = { saved: 'Saved', applied: 'Applied', interviewing: 'Interviewing', offer: 'Offer', rejected: 'Rejected' };
const PAGE = 30;

const state = {
  config: null,
  countries: new Set(),
  sources: new Set(['adzuna', 'arbeitnow', 'remotive', 'jobicy']),
  results: null,
  shown: PAGE,
  saved: new Map(),
  trackerFilter: 'all',
  searching: false,
};

// ---------------------------------------------------------------- helpers

function relativeDate(iso) {
  if (!iso) return '';
  const days = Math.floor((Date.now() - Date.parse(iso)) / 86400000);
  if (Number.isNaN(days)) return '';
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.round(days / 7)} weeks ago`;
  return `${Math.round(days / 30)} months ago`;
}

function countryInfo(code) {
  return state.config.countries.find((c) => c.code === code);
}

// --------------------------------------------------------------- tabs

function showView(name) {
  for (const tab of document.querySelectorAll('.tab')) {
    if (tab.dataset.view === name) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
  }
  for (const view of document.querySelectorAll('.view')) view.hidden = view.id !== `view-${name}`;
  if (name === 'tracker') renderTracker();
  if (name === 'registers') loadRegisters();
  try { history.replaceState(null, '', `#${name}`); } catch { /* ignore */ }
}

// ------------------------------------------------------------- search form

function renderPresets() {
  const box = $('#presets');
  box.replaceChildren(...state.config.presets.map((p) =>
    h('button', { type: 'button', class: 'chip', onclick: () => { $('#q').value = p; search(); } }, p)));
}

function renderCountries() {
  const box = $('#country-chips');
  box.replaceChildren(...state.config.countries.map((c) => {
    const pressed = state.countries.has(c.code);
    return h('button', {
      type: 'button', class: 'chip', 'aria-pressed': String(pressed),
      title: [c.name, c.hasRegister ? 'employers checked against the official sponsor list' : null, c.adzuna ? null : 'not covered by Adzuna'].filter(Boolean).join(' · '),
      onclick: () => {
        if (state.countries.has(c.code)) state.countries.delete(c.code); else state.countries.add(c.code);
        renderCountries();
        savePrefs();
      },
    }, `${c.flag} ${c.name}`, c.hasRegister ? h('span', { class: 'dot', 'aria-label': 'has sponsor list' }) : null,
    c.adzuna ? null : h('span', { class: 'sub' }, 'no Adzuna'));
  }));
  updateQuotaNote();
}

function renderSources() {
  const box = $('#source-chips');
  box.replaceChildren(...state.config.sources.map((s) => {
    const pressed = state.sources.has(s.id);
    return h('button', {
      type: 'button', class: 'chip', 'aria-pressed': String(pressed), disabled: s.configured ? null : true,
      title: s.configured ? (s.remote ? 'Remote jobs; used only when "Include remote jobs" is on' : '') : 'Add your Adzuna key in .env to enable',
      onclick: () => {
        if (state.sources.has(s.id)) state.sources.delete(s.id); else state.sources.add(s.id);
        renderSources();
        savePrefs();
      },
    }, s.label, s.remote ? h('span', { class: 'sub' }, 'remote') : null, s.configured ? null : h('span', { class: 'sub' }, 'needs key'));
  }));
  updateQuotaNote();
}

function updateQuotaNote() {
  const cfg = state.config;
  const note = $('#quota-note');
  if (!cfg.adzuna.configured || !state.sources.has('adzuna')) { note.textContent = ''; return; }
  const n = cfg.countries.filter((c) => c.adzuna && state.countries.has(c.code)).length;
  const q = cfg.adzuna.quota;
  const left = q.limit === null ? '' : ` · ${Math.max(0, q.limit - q.used)} of ${q.limit} left today`;
  note.textContent = `Adzuna: this search uses up to ${n} request${n === 1 ? '' : 's'} (repeat searches within 6 hours are free)${left}.`;
}

function savePrefs() {
  prefs.set({
    q: $('#q').value, countries: [...state.countries], sources: [...state.sources],
    level: $('#level').value, days: $('#days').value, sort: $('#sort').value,
    remote: $('#remote').checked, unclear: $('#unclear').checked, sponsorWords: $('#sponsorWords').value,
  });
}

function applyPrefs() {
  const d = state.config.defaults;
  const p = prefs.get();
  const valid = new Set(state.config.countries.map((c) => c.code));
  const countries = (Array.isArray(p.countries) ? p.countries : d.countries).filter((c) => valid.has(c));
  state.countries = new Set(countries.length ? countries : d.countries);
  if (Array.isArray(p.sources)) state.sources = new Set(p.sources.filter((s) => SOURCE_LABEL[s]));
  $('#q').value = typeof p.q === 'string' ? p.q : d.query;
  $('#level').value = ['likely', 'signals', 'all'].includes(p.level) ? p.level : d.level;
  $('#days').value = ['7', '14', '30', '60', '90'].includes(String(p.days)) ? String(p.days) : String(d.days);
  $('#sort').value = ['best', 'newest'].includes(p.sort) ? p.sort : d.sort;
  $('#remote').checked = Boolean(p.remote);
  $('#unclear').checked = Boolean(p.unclear);
  $('#sponsorWords').value = ['auto', 'always', 'never'].includes(p.sponsorWords) ? p.sponsorWords : 'auto';
}

function setCountries(mode) {
  const all = state.config.countries;
  if (mode === 'all') state.countries = new Set(all.map((c) => c.code));
  if (mode === 'none') state.countries = new Set();
  if (mode === 'default') state.countries = new Set(state.config.defaults.countries);
  if (mode === 'registers') state.countries = new Set(all.filter((c) => c.hasRegister).map((c) => c.code));
  renderCountries();
  savePrefs();
}

function renderSetupBanner() {
  const banner = $('#setup-banner');
  if (state.config.adzuna.configured) { banner.hidden = true; return; }
  banner.hidden = false;
  banner.replaceChildren(
    h('p', {}, h('strong', {}, 'Adzuna is not connected yet. '),
      'Most maintenance and reliability jobs in the UK, US, Canada, Australia, New Zealand, Singapore and the Netherlands come from Adzuna. Without it you only see Arbeitnow (mostly tech jobs in Europe).'),
    h('p', { class: 'hint' }, 'Get a free key at ',
      h('a', { href: 'https://developer.adzuna.com/signup', target: '_blank', rel: 'noopener noreferrer' }, 'developer.adzuna.com'),
      ', put ADZUNA_APP_ID and ADZUNA_APP_KEY in the .env file, then restart the app.'),
  );
}

// ------------------------------------------------------------------ search

async function search() {
  if (state.searching) return;
  savePrefs();
  if (!state.countries.size) {
    renderStatus([h('p', { class: 'warn' }, 'Pick at least one country.')]);
    return;
  }
  state.searching = true;
  $('#search-btn').disabled = true;
  renderStatus([h('p', { class: 'line' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), ' Searching… the first search can take up to 30 seconds while the feeds load.')]);
  $('#results').replaceChildren();
  $('#level-summary').replaceChildren();
  $('#more').hidden = true;
  const params = new URLSearchParams({
    q: $('#q').value.trim(),
    countries: [...state.countries].join(','),
    sources: [...state.sources].join(','),
    level: $('#level').value,
    days: $('#days').value,
    sort: $('#sort').value,
    remote: $('#remote').checked ? '1' : '0',
    unclear: $('#unclear').checked ? '1' : '0',
    sponsorWords: $('#sponsorWords').value,
  });
  try {
    const data = await api(`/api/search?${params}`);
    state.results = data;
    state.shown = PAGE;
    state.config.adzuna.quota = data.quota.adzuna;
    updateQuotaNote();
    renderSearchStatus(data);
    renderLevelSummary(data);
    renderResults();
  } catch (err) {
    renderStatus([h('p', { class: 'warn' }, `Search failed: ${err.message}`)]);
  } finally {
    state.searching = false;
    $('#search-btn').disabled = false;
  }
}

function renderStatus(nodes) {
  $('#search-status').replaceChildren(...nodes);
}

function renderSearchStatus(data) {
  const lines = [];
  const per = data.sources.filter((s) => !s.notConfigured)
    .map((s) => `${s.label} ${s.error ? 'failed' : s.found}`).join(' · ');
  const ex = data.excluded;
  const hiddenBits = [];
  if (ex.saidNo) hiddenBits.push(`${ex.saidNo} say they don't sponsor`);
  if (ex.india) hiddenBits.push(`${ex.india} in India`);
  if (ex.unclearCountry) hiddenBits.push(`${ex.unclearCountry} with unclear country`);
  lines.push(h('p', { class: 'line' },
    h('strong', {}, `${data.total} job${data.total === 1 ? '' : 's'}`),
    ` match your filters. Found: ${per || 'no sources'}.`,
    hiddenBits.length ? ` Hidden: ${hiddenBits.join(', ')}.` : '',
    ` (${(data.tookMs / 1000).toFixed(1)}s)`));
  for (const s of data.sources) {
    if (s.error) lines.push(h('p', { class: 'warn' }, `${s.label}: ${s.error}`));
    for (const w of s.warnings || []) if (w !== s.error) lines.push(h('p', { class: 'warn' }, `${s.label}: ${w}`));
    for (const n of s.notes || []) lines.push(h('p', { class: 'warn' }, n));
  }
  if (data.total === 0) {
    lines.push(h('p', { class: 'line' }, 'Try a broader keyword, more countries, a longer date range, or set Sponsorship to "Any visa or relocation signal".'));
  }
  renderStatus(lines);
}

function renderLevelSummary(data) {
  const box = $('#level-summary');
  const order = ['stated', 'licensed', 'tagged', 'relocation', 'keyword', 'unknown'];
  const chips = order.filter((l) => data.counts[l]).map((l) => h('span', {
    class: `badge level-${l}`, title: LEVEL_INFO[l].help,
  }, `${LEVEL_INFO[l].label}: ${data.counts[l]}`));
  box.replaceChildren(...chips);
}

function renderResults() {
  const list = $('#results');
  const data = state.results;
  if (!data) return;
  const slice = data.jobs.slice(0, state.shown);
  list.replaceChildren(...slice.map((job) => jobCard(job, { mode: 'search' })));
  if (!data.jobs.length) list.append(h('li', { class: 'empty' }, 'No jobs to show.'));
  $('#more').hidden = state.shown >= data.jobs.length;
  $('#more').textContent = `Show more (${data.jobs.length - state.shown} left)`;
}

function metaLine(job) {
  const c = countryInfo(job.country);
  const bits = [];
  if (job.company) bits.push(job.company);
  bits.push(`${c ? c.flag + ' ' : ''}${job.location || (c ? c.name : '')}`.trim());
  if (job.postedAt) bits.push(relativeDate(job.postedAt));
  if (job.salaryText) bits.push(job.salaryText);
  if (job.contract) bits.push(job.contract);
  bits.push(`via ${SOURCE_LABEL[job.source] || job.source}`);
  return bits.filter(Boolean).join(' · ');
}

function jobCard(job, { mode, entry = null }) {
  const li = $('#job-template').content.firstElementChild.cloneNode(true);
  const sp = job.sponsorship || {};
  const url = safeUrl(job.url);
  const title = $('.job-title', li);
  title.textContent = job.title;
  if (url) title.href = url; else title.removeAttribute('href');
  $('.job-meta', li).textContent = metaLine(job);

  const badges = $('.badges', li);
  if (sp.level && LEVEL_INFO[sp.level]) {
    badges.append(h('span', { class: `badge level-${sp.level}`, title: LEVEL_INFO[sp.level].help }, LEVEL_INFO[sp.level].label));
  }
  const registerShort = sp.register?.short || sp.registerShort;
  if (registerShort && sp.level !== 'licensed') badges.append(h('span', { class: 'badge level-licensed', title: LEVEL_INFO.licensed.help }, registerShort));
  if (sp.feedTagged && sp.level !== 'tagged') badges.append(h('span', { class: 'badge plain', title: LEVEL_INFO.tagged.help }, 'Board: visa-sponsored'));
  if (job.isRemoteFeed || (job.remote && mode === 'search')) {
    const elig = job.eligibility?.text;
    badges.append(h('span', { class: 'badge level-remote' }, elig ? `Remote · ${elig}` : 'Remote'));
  }
  for (const a of job.alsoOn || []) badges.append(h('span', { class: 'badge plain' }, `also on ${SOURCE_LABEL[a.source] || a.source}`));

  if (sp.evidence) {
    const q = $('.evidence', li);
    q.hidden = false;
    q.textContent = `“${sp.evidence}”`;
    if (sp.mixed) {
      q.classList.add('mixed');
      q.title = 'This ad has conditions on sponsorship. Read the wording.';
      if (sp.negativeEvidence) q.append(h('br'), h('small', {}, `But also: “${sp.negativeEvidence}”`));
    }
  }
  const reg = sp.register;
  if (reg) {
    const p = $('.register-detail', li);
    p.hidden = false;
    p.textContent = `Matched “${reg.matchedName}” on the ${reg.label}${reg.detail ? ` · ${reg.detail}` : ''}`;
  } else if (sp.registerMatch) {
    const p = $('.register-detail', li);
    p.hidden = false;
    p.textContent = `Matched “${sp.registerMatch}” on the official sponsor list`;
  }
  if (sp.cautions?.length) {
    const p = $('.caution', li);
    p.hidden = false;
    p.textContent = `Note: ${sp.cautions.join('; ')}`;
  }
  $('.snippet', li).textContent = job.snippet || '';

  if (job.description && job.description.length > (job.snippet || '').length + 20) {
    const toggle = $('.toggle-full', li);
    const full = $('.full-text', li);
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      const open = full.hidden;
      if (open && !full.textContent) full.textContent = job.description;
      full.hidden = !open;
      toggle.textContent = open ? 'Hide full text' : 'Show full text';
    });
  }

  const saveBtn = $('.save', li);
  const hideBtn = $('.hide', li);
  const isSaved = () => state.saved.has(job.id);
  const paintSave = () => {
    saveBtn.textContent = isSaved() ? '★ Saved' : '☆ Save';
    saveBtn.classList.toggle('saved', isSaved());
    saveBtn.setAttribute('aria-pressed', String(isSaved()));
  };
  paintSave();

  if (mode === 'search') {
    saveBtn.addEventListener('click', async () => {
      saveBtn.disabled = true;
      try {
        if (isSaved()) {
          await api(`/api/saved/${encodeURIComponent(job.id)}`, { method: 'DELETE' });
          state.saved.delete(job.id);
        } else {
          const e = await api(`/api/saved/${encodeURIComponent(job.id)}`, { method: 'PUT', body: { job } });
          state.saved.set(job.id, e);
        }
        paintSave();
        updateTrackerCount();
      } catch (err) {
        alert(`Could not update: ${err.message}`);
      } finally {
        saveBtn.disabled = false;
      }
    });
    hideBtn.addEventListener('click', async () => {
      try {
        await api('/api/hidden', { method: 'POST', body: { id: job.id } });
        state.results.jobs = state.results.jobs.filter((j) => j.id !== job.id);
        li.remove();
      } catch (err) {
        alert(`Could not hide: ${err.message}`);
      }
    });
  } else {
    hideBtn.remove();
    saveBtn.remove();
    li.append(trackerControls(entry, li));
  }
  return li;
}

// ----------------------------------------------------------------- tracker

async function loadSaved() {
  const { items } = await api('/api/saved');
  state.saved = new Map(items.map((e) => [e.id, e]));
  updateTrackerCount();
}

function updateTrackerCount() {
  $('#tracker-count').textContent = String(state.saved.size);
}

function trackerControls(entry, li) {
  const status = h('select', { 'aria-label': 'Status' },
    ...state.config.statuses.map((s) => h('option', { value: s, selected: s === entry.status ? true : null }, STATUS_LABEL[s] || s)));
  status.addEventListener('change', async () => {
    try {
      const e = await api(`/api/saved/${encodeURIComponent(entry.id)}`, { method: 'PATCH', body: { status: status.value } });
      state.saved.set(entry.id, e);
      renderStatusFilter();
    } catch (err) { alert(err.message); }
  });
  const notes = h('textarea', { 'aria-label': 'Notes', placeholder: 'Notes: contact, salary, visa questions, interview dates…', maxlength: '5000' });
  notes.value = entry.notes || '';
  let timer = null;
  const saveNotes = async () => {
    try {
      const e = await api(`/api/saved/${encodeURIComponent(entry.id)}`, { method: 'PATCH', body: { notes: notes.value } });
      state.saved.set(entry.id, e);
    } catch (err) { alert(err.message); }
  };
  notes.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(saveNotes, 800); });
  const remove = h('button', {
    type: 'button', class: 'ghost small',
    onclick: async () => {
      if (!confirm('Remove this job from your tracker?')) return;
      try {
        await api(`/api/saved/${encodeURIComponent(entry.id)}`, { method: 'DELETE' });
        state.saved.delete(entry.id);
        li.remove();
        updateTrackerCount();
        renderStatusFilter();
        if (!state.saved.size) $('#tracker-empty').hidden = false;
      } catch (err) { alert(err.message); }
    },
  }, 'Remove');
  return h('div', { class: 'tracker-extra' },
    h('div', { class: 'row-actions' }, status, remove),
    h('div', {}, notes, h('p', { class: 'hint' }, `Saved ${relativeDate(entry.savedAt)}`)));
}

function renderStatusFilter() {
  const counts = { all: state.saved.size };
  for (const e of state.saved.values()) counts[e.status] = (counts[e.status] || 0) + 1;
  const opts = ['all', ...state.config.statuses];
  $('#status-filter').replaceChildren(...opts.filter((s) => s === 'all' || counts[s]).map((s) => h('button', {
    type: 'button', class: 'chip', 'aria-pressed': String(state.trackerFilter === s),
    onclick: () => { state.trackerFilter = s; renderTracker(); },
  }, s === 'all' ? 'All' : STATUS_LABEL[s], h('span', { class: 'sub' }, String(counts[s] || 0)))));
}

function renderTracker() {
  if (state.trackerFilter !== 'all' && !Array.from(state.saved.values()).some((e) => e.status === state.trackerFilter)) state.trackerFilter = 'all';
  renderStatusFilter();
  const entries = [...state.saved.values()]
    .filter((e) => state.trackerFilter === 'all' || e.status === state.trackerFilter)
    .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  $('#tracker-list').replaceChildren(...entries.map((e) => jobCard({ ...e.job }, { mode: 'tracker', entry: e })));
  $('#tracker-empty').hidden = state.saved.size > 0;
}

// --------------------------------------------------------------- registers

let registerPoll = null;

async function loadRegisters() {
  const data = await api('/api/registers');
  renderRegisters(data);
  clearTimeout(registerPoll);
  if (data.updating) registerPoll = setTimeout(loadRegisters, 3000);
}

function renderRegisters(data) {
  $('#import-dir').textContent = data.importDir;
  const btn = $('#update-registers');
  btn.disabled = data.updating;
  btn.textContent = data.updating ? 'Updating…' : 'Update now';
  $('#register-list').replaceChildren(...data.registers.map((r) => {
    const c = r.country ? countryInfo(r.country) : null;
    return h('div', { class: 'panel register-card' },
      h('h3', {}, h('span', { 'aria-hidden': 'true' }, c ? c.flag : '📄'), h('span', {}, r.label)),
      h('p', { class: 'stat' }, r.count ? r.count.toLocaleString() : '–', h('span', { class: 'hint' }, r.count ? ' employers' : '')),
      r.fetchedAt ? h('p', { class: 'hint' }, `${r.automatic ? 'Downloaded' : 'File date'} ${new Date(r.fetchedAt).toLocaleDateString()}${r.ageDays ? ` (${r.ageDays} days ago)` : ''}`) : h('p', { class: 'hint' }, data.updating ? 'Downloading…' : 'Not downloaded yet'),
      r.note ? h('p', { class: 'hint' }, r.note) : null,
      r.error ? h('p', { class: 'err' }, `Last update failed: ${r.error}`) : null,
      r.page && safeUrl(r.page) ? h('p', {}, h('a', { href: safeUrl(r.page), target: '_blank', rel: 'noopener noreferrer' }, 'Official source')) : null);
  }));
  if (!data.updating) refreshConfig();
}

async function refreshConfig() {
  try {
    const cfg = await api('/api/config');
    state.config.countries = cfg.countries;
    state.config.registers = cfg.registers;
    renderCountries();
  } catch { /* ignore */ }
}

// ---------------------------------------------------------------- visa info

function renderVisa() {
  const withInfo = state.config.countries.filter((c) => c.visaInfo && safeUrl(c.visaInfo));
  $('#visa-list').replaceChildren(...withInfo.map((c) => h('div', { class: 'panel visa-card' },
    h('h3', {}, h('span', { 'aria-hidden': 'true' }, c.flag), h('span', {}, c.name)),
    h('p', {}, h('a', { href: safeUrl(c.visaInfo), target: '_blank', rel: 'noopener noreferrer' }, c.visaName || 'Official work visa information')),
    h('p', { class: 'hint' }, c.hasRegister ? 'Employers in search results are checked against the official sponsor list.' : 'No official employer list is used for this country.'))));
}

// --------------------------------------------------------------------- init

async function init() {
  try {
    state.config = await api('/api/config');
  } catch (err) {
    document.body.prepend(h('p', { class: 'banner' }, `Could not reach the app server: ${err.message}`));
    return;
  }
  applyPrefs();
  renderPresets();
  renderCountries();
  renderSources();
  renderSetupBanner();
  renderVisa();
  await loadSaved().catch(() => {});

  for (const tab of document.querySelectorAll('.tab')) tab.addEventListener('click', () => showView(tab.dataset.view));
  for (const b of document.querySelectorAll('[data-countries]')) b.addEventListener('click', () => setCountries(b.dataset.countries));
  $('#search-form').addEventListener('submit', (e) => { e.preventDefault(); search(); });
  for (const id of ['level', 'days', 'sort', 'remote', 'unclear', 'sponsorWords']) $(`#${id}`).addEventListener('change', savePrefs);
  $('#more').addEventListener('click', () => { state.shown += PAGE; renderResults(); });
  $('#update-registers').addEventListener('click', async () => {
    try {
      renderRegisters(await api('/api/registers/update', { method: 'POST', body: {} }));
      registerPoll = setTimeout(loadRegisters, 2000);
    } catch (err) { alert(err.message); }
  });

  const initial = location.hash.slice(1);
  if (['tracker', 'registers', 'visa'].includes(initial)) showView(initial);
  search();
}

init();
