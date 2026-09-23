#!/usr/bin/env python3
"""Generate webapp/static/index.html from the shared dashboard template.

The template owns the design and the rendering code; this script swaps the data
layer for one that talks to the API, so the static page and the live app never
drift apart visually.
"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent
tpl = (ROOT.parent / "dashboard.template.html").read_text()

markup = tpl[:tpl.index('<script id="book" type="application/json">')]
js = tpl[tpl.index('(() => {\n"use strict";'):]
render_block = js[js.index("/* ── the 52-week range bar"):js.index("/* ── wiring")]

# the render block declares its own UI state; the new wiring owns it instead
for decl in ('let side = "buy";\n',
             'let acct = "all", hsort = { k: "value", dir: -1 };\n',
             'let wfilter = "all", wsort = { k: "combined", dir: -1 };\n'):
    render_block = render_block.replace(decl, "")

EXTRA_CSS = """
/* ── view switcher ──────────────────────────────────────────────────────── */
.views{display:flex;gap:2px;padding:3px;background:var(--surface-2);
  border:1px solid var(--rule);border-radius:9px}
.vbtn{padding:5px 13px;border:none;border-radius:7px;background:transparent;
  color:var(--ink-2);font-size:12.5px;font-weight:600;font-family:var(--sans)}
.vbtn[aria-selected="true"]{background:var(--surface);color:var(--ink);
  box-shadow:0 1px 2px rgba(0,0,0,.08)}
.vbtn:hover{color:var(--ink)}
.vbtn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}

/* ── allocation bar: four real buckets, each directly labelled ──────────── */
:root{--a1:#2E6DA8;--a2:#0E7A52;--a3:#BF8419;--a4:#96508C}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --a1:#5AA0D6;--a2:#2C9A70;--a3:#C9A23A;--a4:#B57BAE}}
:root[data-theme="dark"]{--a1:#5AA0D6;--a2:#2C9A70;--a3:#C9A23A;--a4:#B57BAE}
.allo{display:flex;height:34px;border-radius:8px;overflow:hidden;
  border:1px solid var(--rule);background:var(--surface-2)}
.allo div{display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-size:11px;font-weight:600;color:#fff;
  min-width:0;overflow:hidden;white-space:nowrap}
.allo div+div{box-shadow:inset 2px 0 0 var(--surface)}
.allokey{display:flex;gap:18px;flex-wrap:wrap;margin-top:11px;font-size:12.5px;
  color:var(--ink-2)}
.allokey i{display:inline-block;width:10px;height:10px;border-radius:3px;
  margin-right:6px;vertical-align:-1px}

/* ── side-by-side book cards ────────────────────────────────────────────── */
.books{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:700px){.books{grid-template-columns:1fr}}
.bookcard{background:var(--surface);border:1px solid var(--rule);border-radius:12px;
  padding:17px 19px}
.bookcard h3{font-size:13px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink-3);font-family:var(--mono);margin-bottom:7px}
.bookcard .v{font-family:var(--mono);font-size:26px;font-weight:600;letter-spacing:-.02em}
.bookcard .alt{font-family:var(--mono);font-size:12.5px;color:var(--ink-3);margin-top:2px}
.bookcard .sh{height:5px;border-radius:3px;background:var(--surface-3);margin-top:12px;
  overflow:hidden}
.bookcard .sh i{display:block;height:100%}
.split{display:flex;justify-content:space-between;font-size:12px;
  font-family:var(--mono);color:var(--ink-2);margin-top:6px}
.stat3{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.stat{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:13px 15px}
.stat .k{font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-3);font-family:var(--mono)}
.stat .n{font-family:var(--mono);font-size:21px;font-weight:600;margin-top:3px;
  letter-spacing:-.02em}
.stat .s{font-size:12px;color:var(--ink-2);margin-top:2px}
.grp{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--ink-3);background:var(--surface-2)}
.tagpill{font-family:var(--mono);font-size:10px;padding:2px 6px;border-radius:4px;
  border:1px solid var(--rule-2);color:var(--ink-3)}
"""

WEALTH_VIEW = """  <div id="view-wealth">
    <div class="hero">
      <div>
        <div class="eyebrow">Total net worth &middot; two books, one rate</div>
        <div class="big num" id="wTotal">&mdash;</div>
        <div class="hero-sub">
          <span>Invested <b id="wCost">&mdash;</b></span>
          <span>Gain <b id="wPl">&mdash;</b></span>
          <span>&asymp; <b id="wUsd">&mdash;</b></span>
        </div>
      </div>
      <div class="books" id="wBooks"></div>
    </div>

    <p class="note" id="wFx" style="margin:14px 0 0;font-size:12px;
       font-family:var(--mono);color:var(--ink-3)"></p>

    <section id="w-alloc">
      <div class="shead">
        <h2>Where the money is</h2>
        <p>Four buckets that actually change the risk. Foreign equity held through
           Indian funds counts as overseas, not as India.</p>
      </div>
      <div class="allo" id="wAllo"></div>
      <div class="allokey" id="wAlloKey"></div>
      <div class="stat3" id="wMix" style="margin-top:20px"></div>
      <div class="tblwrap" style="margin-top:18px"><table id="wClass">
        <thead></thead><tbody></tbody></table></div>
    </section>

    <section id="w-top">
      <div class="shead">
        <h2>Largest positions</h2>
        <p>Every holding from both books in one list &mdash; the only way to see
           real single-name concentration when the same theme is owned on two
           continents.</p>
      </div>
      <div class="tblwrap"><table id="wPos"><thead></thead><tbody></tbody></table></div>
    </section>
  </div>

"""

INDIA_VIEW = """  <div id="view-india" hidden>
    <div class="hero">
      <div>
        <div class="eyebrow">India &middot; mutual funds, ETFs and unlisted</div>
        <div class="big num" id="iTotal">&mdash;</div>
        <div class="hero-sub">
          <span>Invested <b id="iCost">&mdash;</b></span>
          <span>Gain <b id="iPl">&mdash;</b></span>
          <span><b id="iCount">&mdash;</b></span>
        </div>
      </div>
      <div class="acct-grid" id="iAccts"></div>
    </div>

    <p class="note" id="iFeed" style="margin:14px 0 0;font-size:12px;
       font-family:var(--mono);color:var(--ink-3)"></p>

    <section id="i-calls">
      <div class="shead">
        <h2>Today's calls</h2>
        <p>An index fund is priced by its index, a gilt fund by the rate cycle,
           and an unlisted holding by neither &mdash; so each is judged on what
           actually moves it, not on one borrowed formula.</p>
      </div>
      <div class="alert" id="iHeadline"></div>
      <div class="stat3" id="iMarket" style="margin-top:16px"></div>
      <div class="calls" id="iCallList" style="margin-top:16px"></div>
    </section>

    <section id="i-class">
      <div class="shead"><h2>By asset class</h2></div>
      <div class="stat3" id="iClasses"></div>
    </section>

    <section id="i-holdings">
      <div class="shead">
        <h2>Holdings</h2>
        <p>Grouped by where they are held. Click any column to sort within a group.</p>
      </div>
      <div class="tools">
        <select id="iFilter">
          <option value="all">Everything</option>
          <option value="mutual_fund">Mutual funds</option>
          <option value="etf">ETFs</option>
          <option value="pre_ipo">Pre-IPO</option>
        </select>
      </div>
      <div class="tblwrap"><table id="iTbl"><thead></thead><tbody></tbody></table></div>
    </section>
  </div>

"""

markup = markup.replace(
    '  <span class="badge" id="feed"><span class="dot"></span><span id="feedtxt">Snapshot</span></span>',
    '  <span class="badge" id="mkt"><span id="mkttxt">—</span></span>\n'
    '  <span class="badge" id="feed"><span class="dot"></span>'
    '<span id="feedtxt">Connecting…</span></span>')
markup = markup.replace('<button class="btn" id="refresh">Refresh quotes</button>',
                        '<button class="btn" id="refresh">Refresh now</button>')

# view switcher in the masthead
markup = markup.replace(
    '  <span class="badge" id="mkt">',
    '  <nav class="views" role="tablist">'
    '<button class="vbtn" data-view="wealth" role="tab" aria-selected="true">Wealth</button>'
    '<button class="vbtn" data-view="india" role="tab" aria-selected="false">India</button>'
    '<button class="vbtn" data-view="us" role="tab" aria-selected="false">US</button>'
    '</nav>\n  <span class="badge" id="mkt">')

# the US dashboard becomes one of three views; wealth and india sit beside it
markup = markup.replace('  <div class="hero">', WEALTH_VIEW + INDIA_VIEW +
                        '  <div id="view-us" hidden>\n  <div class="hero">')
markup = markup.replace('  <footer>', '  </div>\n\n  <footer>')
markup = markup.replace('  <section id="calls">',
    '  <p class="note" id="freshness" style="margin:14px 0 0;font-size:12px;'
    'font-family:var(--mono);color:var(--ink-3)"></p>\n\n  <section id="calls">')
markup = markup.replace('</style>', EXTRA_CSS + '</style>')
markup = re.sub(
    r'    <p><b>Live quotes\.</b>.*?</p>\n',
    '    <p><b>Live quotes.</b> This server fetches prices itself and the page polls it, so quotes '
    'refresh without a rebuild. Two independent sources are tried in order, and the strip under the '
    'headline names the one that answered and how old its data is. If both are unreachable the last '
    'good prices are served and marked stale rather than replaced with nothing; if none were ever '
    'fetched, the statement close is shown and labelled as such.</p>\n',
    markup, flags=re.S)


PREAMBLE = '''<script>
(() => {
"use strict";
let BOOK = null;                     // filled from the API before the first paint
const $ = s => document.querySelector(s);
const el = (t, c, x) => { const n = document.createElement(t);
  if (c) n.className = c; if (x != null) n.textContent = x; return n; };
const addCls = (n, c) => { if (c) n.classList.add(c); };

/* --- formatting ------------------------------------------------------- */
const usd = (v, d = 2) => v == null ? "\\u2014" : (v < 0 ? "-$" : "$") +
  Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const usd0 = v => usd(v, 0);
const pct = (v, d = 1) => v == null ? "\\u2014" : (v > 0 ? "+" : "") + v.toFixed(d) + "%";
const inr = v => v == null ? "\\u2014" : "\\u20b9" + (v / 1e5).toFixed(2) + " L";
const sign = v => v == null ? "" : v >= 0 ? "pos" : "neg";
const x1 = v => v == null ? "\\u2014" : v.toFixed(1) + "\\u00d7";
/* the server sends row.tier; this mirrors it for anything built client-side */
const TIER = v => {
  const u = String(v).toUpperCase();
  if (/TRIM|AVOID|DO NOT ADD/.test(u)) return "sell";
  if (/BUY|ACCUMULATE|DIP/.test(u)) return "buy";
  return "warn";
};
const inrFull = v => v == null ? "\\u2014" : "\\u20b9" +
  Math.round(v).toLocaleString("en-IN");
const inrShort = v => v == null ? "\\u2014"
  : Math.abs(v) >= 1e7 ? "\\u20b9" + (v / 1e7).toFixed(2) + " Cr"
  : "\\u20b9" + (v / 1e5).toFixed(2) + " L";
const ago = s => s == null ? "\\u2014"
  : s < 90 ? Math.round(s) + "s ago"
  : s < 5400 ? Math.round(s / 60) + "m ago"
  : (s / 3600).toFixed(1) + "h ago";

'''

TAIL = '''
/* --- access token ------------------------------------------------------
   Taken from ?token= once, then kept in localStorage and sent as a header, so
   it stops riding in the URL where it would sit in history and server logs. */
const KEY = "us-book-token";
let TOKEN = "";
try {
  const q = new URLSearchParams(location.search).get("token");
  if (q) {
    localStorage.setItem(KEY, q);
    history.replaceState(null, "", location.pathname);   // strip it from the bar
  }
  TOKEN = localStorage.getItem(KEY) || "";
} catch { TOKEN = new URLSearchParams(location.search).get("token") || ""; }
const authHeaders = () => TOKEN ? { "X-App-Token": TOKEN } : {};
let timer = null;

/* Shown instead of the dashboard when the server wants a token we do not have.
   Built here rather than in the shared template: only the deployed app is
   ever gated. */
function askForToken(wrong) {
  clearTimeout(timer);
  document.querySelector(".wrap").hidden = true;
  document.getElementById("refresh").hidden = true;
  let box = document.getElementById("unlock");
  if (!box) {
    box = document.createElement("div");
    box.id = "unlock";
    box.innerHTML =
      '<form style="max-width:26rem;margin:12vh auto;padding:26px 28px;' +
      'background:var(--surface);border:1px solid var(--rule);border-radius:12px;' +
      'box-shadow:var(--shadow)">' +
      '<h2 style="font-family:var(--disp);font-size:19px;margin:0 0 8px">' +
      'This dashboard is private</h2>' +
      '<p style="margin:0 0 14px;color:var(--ink-2);font-size:13.5px;line-height:1.55">' +
      'It needs the access token \\u2014 on Render, your service &rarr; ' +
      '<b>Environment</b> &rarr; <code>APP_TOKEN</code>.</p>' +
      '<p style="margin:0 0 16px;color:var(--ink-3);font-size:12.5px;line-height:1.5">' +
      'Not the Finnhub key. <code>FINNHUB_API_KEY</code> fetches prices and is ' +
      'never typed here; <code>APP_TOKEN</code> is what opens this page.</p>' +
      '<input id="tok" type="password" autocomplete="current-password" ' +
      'placeholder="Paste the token" style="width:100%;padding:9px 11px;' +
      'font-family:var(--mono);font-size:13px;border:1px solid var(--rule-2);' +
      'border-radius:8px;background:var(--bg);color:var(--ink)">' +
      '<p id="tokerr" style="color:var(--neg);font-size:12.5px;margin:9px 0 0" hidden></p>' +
      '<button class="btn" style="margin-top:14px;width:100%">Unlock</button></form>';
    document.body.append(box);
    box.querySelector("form").addEventListener("submit", async e => {
      e.preventDefault();
      const v = box.querySelector("#tok").value.trim();
      if (!v) return;
      const r = await fetch("/api/auth", { headers: { "X-App-Token": v } })
        .catch(() => ({ ok: false }));
      if (!r.ok) {
        const err = box.querySelector("#tokerr");
        err.hidden = false;
        err.textContent = "That was not accepted. It should be APP_TOKEN from "
          + "Render's Environment tab \\u2014 not the Finnhub key.";
        return;
      }
      try { localStorage.setItem(KEY, v); } catch { /* private window */ }
      TOKEN = v;
      box.remove();
      document.querySelector(".wrap").hidden = false;
      document.getElementById("refresh").hidden = false;
      load(false);
    });
  }
  const err = box.querySelector("#tokerr");
  err.hidden = !wrong;
  if (wrong) err.textContent = "The stored token was rejected. Paste APP_TOKEN "
    + "from Render's Environment tab.";
}

function setFeed(live, text, title) {
  const b = $("#feed");
  b.className = "badge" + (live ? " live" : "");
  $("#feedtxt").textContent = text;
  b.title = title || "";
}

async function load(force) {
  const btn = $("#refresh");
  btn.disabled = true;
  if (BOOK) btn.textContent = "Refreshing\\u2026";
  try {
    const r = await fetch("/api/wealth" + (force ? "?force=true" : ""),
      { headers: authHeaders(), cache: "no-store" });
    if (r.status === 401) {
      try { localStorage.removeItem(KEY); } catch { /* ignore */ }
      askForToken(Boolean(TOKEN));       // "wrong" only if we actually sent one
      TOKEN = "";
      return;
    }
    if (!r.ok) throw new Error("server returned " + r.status);
    BOOK = await r.json();
    render();
    paintFeed();
    schedule();
  } catch (e) {
    const msg = String(e.message || e);
    setFeed(false, "Disconnected", msg);
    $("#freshness").textContent =
      "Cannot reach the server \\u2014 " + msg + ". Retrying every 15s.";
    if (!BOOK) $("#headline").innerHTML =
      "<b>Waiting for the server.</b> Nothing has loaded yet. If you started it yourself, " +
      "check that terminal for errors \\u2014 " + msg;
    clearTimeout(timer);
    timer = setTimeout(() => load(false), 15000);
  } finally {
    btn.disabled = false;
    btn.textContent = "Refresh now";
  }
}

function paintFeed() {
  const f = BOOK.us.feed, m = BOOK.market;
  $("#mkttxt").textContent = m.label;
  $("#mkt").title = m.next_session
    ? "Next session " + m.next_session : "Last session " + m.last_session;

  if (f.live) {
    const stale = f.age_seconds != null && f.age_seconds > 900;
    setFeed(!stale,
      (stale ? "Stale" : "Live") + " \\u00b7 " + f.live_count + "/" + f.total +
      " \\u00b7 " + ago(f.age_seconds),
      "Quotes from " + (f.sources.join(", ") || "cache") + ".");
    $("#freshness").textContent =
      f.live_count + " of " + f.total + " priced from " +
      (f.sources.join(" + ") || "cache") + ", " + ago(f.age_seconds) +
      " \\u00b7 last close " + m.last_session + " \\u00b7 " + m.label +
      (f.live_count < f.total
        ? " \\u00b7 " + (f.total - f.live_count) + " on the " + f.reference_date + " reference close"
        : "");
  } else {
    setFeed(false, "Reference \\u00b7 " + f.reference_date,
      f.error || "No quote source reachable.");
    $("#freshness").textContent =
      "No live quotes \\u2014 all " + f.total + " names show the " + f.reference_date +
      " statement close. " + (f.error ? "Server reported: " + f.error : "");
  }
}

/* Poll at the cadence the market state justifies: every minute while it is
   open, rarely once it is shut. */
function schedule() {
  clearTimeout(timer);
  timer = setTimeout(() => load(false), (BOOK.market.poll_seconds || 300) * 1000);
}

/* The US renderers were written against a flat book and are shared with the
   static page, so they are run with BOOK pointed at the US half rather than
   rewritten. One helper, so the swap cannot be forgotten at a call site. */
const inUs = fn => {
  const saved = BOOK;
  BOOK = BOOK.us;
  try { return fn(); } finally { BOOK = saved; }
};

/* --- wealth view -------------------------------------------------------- */
const BUCKETS = [
  ["India equity",        ["India equity"],                                   "var(--a1)"],
  ["Overseas equity",     ["US equity", "US equity ETF", "International equity", "Crypto"], "var(--a2)"],
  ["Debt & cash",         ["Debt / cash"],                                    "var(--a3)"],
  ["Unlisted",            ["Unlisted / pre-IPO"],                             "var(--a4)"],
];

function renderWealth() {
  const w = BOOK, t = w.totals;
  $("#wTotal").textContent = inrShort(t.value_inr);
  $("#wCost").textContent = inrShort(t.cost_inr);
  const pl = $("#wPl");
  pl.textContent = `${inrShort(t.pl_inr)} (${pct(t.pl_pct)})`;
  pl.className = sign(t.pl_inr);
  $("#wUsd").textContent = usd0(t.value_usd);
  $("#wFx").textContent =
    `${t.holdings} holdings \u00b7 converted at \u20b9${w.usdinr} per USD `
    + `(${w.fx.source}${w.fx.age_seconds != null ? ", " + ago(w.fx.age_seconds) : ""})`
    + (w.fx.source === "fallback" ? " \u2014 live rate unavailable, using the last known" : "");

  const g = $("#wBooks"); g.textContent = "";
  w.sides.forEach((s, i) => {
    const c = el("div", "bookcard");
    c.append(el("h3", "", s.label));
    c.append(el("div", "v num", inrShort(s.value_inr)));
    c.append(el("div", "alt", s.currency === "USD"
      ? `${usd0(s.value_native)} \u00b7 ${pct(s.pl_pct)} in USD`
      : `${inrFull(s.value_native)} \u00b7 ${pct(s.pl_pct)}`));
    const sh = el("div", "sh"), fill = el("i");
    fill.style.width = s.share + "%";
    fill.style.background = i === 0 ? "var(--a1)" : "var(--a2)";
    sh.append(fill); c.append(sh);
    const sp = el("div", "split");
    sp.append(el("span", "", s.share.toFixed(1) + "% of net worth"));
    const p2 = el("span", sign(s.pl_inr), inrShort(s.pl_inr) + " gain");
    sp.append(p2); c.append(sp);
    g.append(c);
  });

  // allocation: four buckets, each labelled in place
  const total = t.value_inr;
  const rows = BUCKETS.map(([name, keys, col]) => ({
    name, col, value: keys.reduce((a, k) => a + (w.by_class[k] || 0), 0)
  })).filter(r => r.value > 0);
  const bar = $("#wAllo"); bar.textContent = "";
  const key = $("#wAlloKey"); key.textContent = "";
  for (const r of rows) {
    const share = r.value / total * 100;
    const seg = el("div");
    seg.style.width = share + "%";
    seg.style.background = r.col;
    seg.title = `${r.name} \u00b7 ${inrShort(r.value)} \u00b7 ${share.toFixed(1)}%`;
    if (share > 7) seg.textContent = share.toFixed(0) + "%";
    bar.append(seg);
    const k = el("span");
    const sw = el("i"); sw.style.background = r.col;
    k.append(sw, document.createTextNode(`${r.name} \u00b7 ${inrShort(r.value)} (${share.toFixed(1)}%)`));
    key.append(k);
  }

  const mix = $("#wMix"); mix.textContent = "";
  const stat = (k, n, sub, cls) => {
    const d = el("div", "stat");
    d.append(el("div", "k", k));
    const v = el("div", "n", n); if (cls) v.classList.add(cls); d.append(v);
    d.append(el("div", "s", sub)); mix.append(d);
  };
  stat("In equities", w.mix.equity_pct.toFixed(1) + "%",
       "Including crypto and the unlisted names");
  stat("Held overseas", w.mix.overseas_pct.toFixed(1) + "%",
       "US book plus foreign funds bought in India");
  stat("Top 5 names", w.mix.top5_pct.toFixed(1) + "%",
       "Of total net worth, across both books");
  stat("Rupee exposure", (100 - w.mix.overseas_pct).toFixed(1) + "%",
       "The rest moves with USD/INR");

  buildTable($("#wClass"),
    [["name", "Asset class", r => r.name],
     ["value", "Value", r => inrFull(r.value)],
     ["share", "Share", r => r.share.toFixed(2) + "%"],
     ["bar", "", r => barCell(r.share, r.col)]],
    Object.entries(w.by_class).map(([name, value]) => {
      const b = BUCKETS.find(([, keys]) => keys.includes(name));
      return { name, value, share: value / total * 100, col: b ? b[2] : "var(--ink-3)" };
    }).sort((a, b) => b.value - a.value),
    { k: "value", dir: -1 }, () => {});

  buildTable($("#wPos"),
    [["name", "Holding", r => { const d = el("div", "tk", r.symbol);
        d.append(el("small", "", r.name)); return d; }],
     ["book", "Book", r => r.book],
     ["asset_class", "Class", r => r.asset_class],
     ["value_inr", "Value", r => inrFull(r.value_inr)],
     ["weight", "Weight", r => r.weight.toFixed(2) + "%"],
     ["pl_pct", "Return", r => pct(r.pl_pct), r => sign(r.pl_pct)],
     ["bar", "", r => barCell(r.weight * 4, r.book === "India" ? "var(--a1)" : "var(--a2)")]],
    w.positions.slice(0, 30), { k: "value_inr", dir: -1 }, () => {});
}

function barCell(pctWide, col) {
  const d = el("div"); d.style.cssText =
    "height:6px;border-radius:3px;background:var(--surface-3);width:110px";
  const i = el("i"); i.style.cssText =
    `display:block;height:100%;border-radius:3px;background:${col};` +
    `width:${Math.max(2, Math.min(100, pctWide))}%`;
  d.append(i); return d;
}

/* --- india view --------------------------------------------------------- */
let iFilter = "all", isort = { k: "value", dir: -1 };
function renderIndia() {
  const b = BOOK.india, t = b.totals;
  $("#iTotal").textContent = inrShort(t.value);
  $("#iCost").textContent = inrShort(t.cost);
  const pl = $("#iPl");
  pl.textContent = `${inrShort(t.pl)} (${pct(t.pl_pct)})`;
  pl.className = sign(t.pl);
  $("#iCount").textContent = `${t.holdings} holdings`;

  const f = b.feed;
  $("#iFeed").textContent = f.live_count
    ? `${f.live_count} of ${f.priceable} priced live \u00b7 NAVs from AMFI `
      + `(${f.navs.schemes} schemes${f.navs.age_seconds != null ? ", " + ago(f.navs.age_seconds) : ""})`
      + ` \u00b7 pre-IPO held at statement value`
    : `Statement values as at ${f.reference_date} \u2014 no live NAV or price source reached`
      + (f.navs.last_error ? ` (${f.navs.last_error})` : "");

  const g = $("#iAccts"); g.textContent = "";
  for (const [name, a] of Object.entries(b.by_account)) {
    const c = el("div", "acct");
    c.append(el("div", "nm", name));
    c.append(el("div", "v num", inrShort(a.value)));
    const p = el("div", "p num", `${inrShort(a.pl)}  ${pct(a.pl_pct)}`);
    p.classList.add(sign(a.pl)); c.append(p);
    const bar = el("div", "bar"), fill = el("i");
    fill.style.width = (a.value / t.value * 100).toFixed(1) + "%";
    bar.append(fill); c.append(bar);
    g.append(c);
  }

  const cl = $("#iClasses"); cl.textContent = "";
  for (const [name, a] of Object.entries(b.by_class)) {
    const d = el("div", "stat");
    d.append(el("div", "k", name));
    d.append(el("div", "n", inrShort(a.value)));
    const s = el("div", "s");
    s.append(document.createTextNode(`${(a.value / t.value * 100).toFixed(1)}% \u00b7 ${a.n} holdings \u00b7 `));
    s.append(el("span", sign(a.pl), pct(a.pl_pct)));
    d.append(s); cl.append(d);
  }

  // calls
  const ca = b.calls;
  $("#iHeadline").textContent = ca.headline;
  const im = $("#iMarket"); im.textContent = "";
  for (const [, ix] of Object.entries(ca.market.indices)) {
    if (ix.label.startsWith("Broad")) continue;
    const d = el("div", "stat");
    d.append(el("div", "k", ix.label));
    d.append(el("div", "n", ix.pe.toFixed(1) + "\u00d7"));
    const gap = (1 - ix.pe / ix.median) * 100;
    const s2 = el("div", "s");
    s2.append(el("span", gap >= 0 ? "pos" : "neg",
      `${Math.abs(gap).toFixed(0)}% ${gap >= 0 ? "below" : "above"}`));
    s2.append(document.createTextNode(` its ${ix.window} median of ${ix.median.toFixed(1)}\u00d7`));
    d.append(s2); im.append(d);
  }

  const order = { ADD: 0, TRIM: 1, REDUCE: 2, PAUSE: 3, FAVOURED: 4,
                  "CAP IT": 5, "KEEP BUYING": 6, HOLD: 7, "NO CALL": 8 };
  const cl2 = $("#iCallList"); cl2.textContent = "";
  const seen = new Set();
  const ranked = b.holdings.slice().sort((x, y) =>
    (order[x.call.action] ?? 9) - (order[y.call.action] ?? 9) || y.value - x.value);
  for (const h of ranked) {
    // one card per distinct call, not per folio
    const sig = h.call.action + "|" + h.call.basis + "|" + h.symbol;
    if (seen.has(sig)) continue;
    seen.add(sig);
    const tier = h.call.tier === "buy" ? "buy" : h.call.tier === "sell" ? "sell" : "warn";
    const card = el("div", "call");
    card.append(el("div", "rank", String(seen.size)));
    const box = el("div", "call-in");
    const top = el("div", "call-top");
    top.append(el("span", "tkr", h.symbol));
    top.append(el("span", "co", h.sub_class + " \u00b7 " + h.account));
    top.append(el("span", "chip " + tier, h.call.action));
    top.append(el("span", "chip own", inrShort(h.value) + " \u00b7 "
      + (h.value / b.totals.value * 100).toFixed(1) + "%"));
    box.append(top);
    box.append(el("p", "why", h.call.why));
    const m2 = el("div", "mathline");
    const bit = (k, v, c) => { const sp = el("span"); sp.append(k + " ");
      sp.append(el("b", c || "", v)); return sp; };
    m2.append(bit("basis", h.call.basis));
    if (h.call.discount != null)
      m2.append(bit("index", Math.abs(h.call.discount).toFixed(0) + "% "
        + (h.call.discount >= 0 ? "below median" : "above median"),
        h.call.discount >= 0 ? "pos" : "neg"));
    m2.append(bit("your return", pct(h.pl_pct), sign(h.pl_pct)));
    m2.append(bit("invested", inrShort(h.cost)));
    box.append(m2);
    card.append(box); cl2.append(card);
  }

  let rows = b.holdings.filter(h => iFilter === "all" || h.kind === iFilter);
  rows.sort((x, y) => {
    const a = x[isort.k], c = y[isort.k];
    if (typeof a === "string") return isort.dir * a.localeCompare(c);
    return isort.dir * ((a ?? -1e12) - (c ?? -1e12));
  });
  buildTable($("#iTbl"),
    [["name", "Holding", r => { const d = el("div", "tk", r.symbol);
        d.append(el("small", "", r.name)); return d; }],
     ["account", "Held at", r => r.account],
     ["sub_class", "Type", r => r.sub_class],
     ["units", "Units", r => r.units.toLocaleString("en-IN",
        { maximumFractionDigits: 3 })],
     ["price", "Price", r => r.unpriced ? "no price"
        : (r.price_label === "NAV" ? "\u20b9" : "\u20b9") + r.price.toLocaleString("en-IN",
            { minimumFractionDigits: 2, maximumFractionDigits: 4 })],
     ["value", "Value", r => inrFull(r.value)],
     ["cost", "Invested", r => inrFull(r.cost)],
     ["pl", "Gain", r => inrFull(r.pl), r => sign(r.pl)],
     ["pl_pct", "Return", r => pct(r.pl_pct), r => sign(r.pl_pct)],
     ["call", "Call", r => el("span", "chip " + (r.call.tier === "buy" ? "buy"
        : r.call.tier === "sell" ? "sell" : "warn"), r.call.action)],
     ["live", "Priced", r => el("span", "tagpill",
        r.live ? "live" : r.kind === "pre_ipo" ? "statement" : r.priced_on)]],
    rows, isort, k => { isort = { k, dir: isort.k === k ? -isort.dir : -1 };
                        renderIndia(); });
}

/* --- views -------------------------------------------------------------- */
let view = "wealth";
const SUBLINE = {
  wealth: b => `India + US \u00b7 ${b.totals.holdings} holdings \u00b7 `
    + `\u20b9${b.usdinr}/USD`,
  india:  b => `As at ${b.india.as_of} \u00b7 ${b.india.totals.holdings} holdings \u00b7 `
    + `${b.india.live_count} priced live`,
  us:     b => `Statements ${b.us.as_of} \u00b7 ${b.us.totals.positions} positions \u00b7 `
    + `${b.us.totals.tickers_tracked} tracked`,
};

function showView(v) {
  view = v;
  if (BOOK) $("#asof").textContent = SUBLINE[v](BOOK);
  for (const id of ["wealth", "india", "us"])
    $("#view-" + id).hidden = id !== v;
  document.querySelectorAll("[data-view]").forEach(b =>
    b.setAttribute("aria-selected", String(b.dataset.view === v)));
  if (v === "us" && BOOK && BOOK.us) inUs(renderMap);
}

/* --- wiring ----------------------------------------------------------- */
let side = "buy", acct = "all", wfilter = "all";
let hsort = { k: "value", dir: -1 }, wsort = { k: "combined", dir: -1 };

function render() {
  $("#asof").textContent = SUBLINE[view](BOOK);
  renderWealth();
  renderIndia();
  inUs(() => {
    renderTop(); renderHeadline(); renderCalls();
    renderHoldings(); renderWatch(); renderRisk();
    if (view === "us") renderMap();
  });
}
document.querySelectorAll("[data-side]").forEach(b =>
  b.addEventListener("click", () => {
    side = b.dataset.side;
    document.querySelectorAll("[data-side]").forEach(o =>
      o.setAttribute("aria-pressed", String(o === b)));
    inUs(renderCalls);
  }));
document.querySelectorAll("[data-acct]").forEach(b =>
  b.addEventListener("click", () => {
    acct = b.dataset.acct;
    document.querySelectorAll("[data-acct]").forEach(o =>
      o.setAttribute("aria-pressed", String(o === b)));
    inUs(renderHoldings);
  }));
$("#wfilter").addEventListener("change", e => {
  wfilter = e.target.value;
  inUs(renderWatch);
});
$("#iFilter").addEventListener("change", e => { iFilter = e.target.value; renderIndia(); });
document.querySelectorAll("[data-view]").forEach(b =>
  b.addEventListener("click", () => showView(b.dataset.view)));
$("#refresh").addEventListener("click", () => load(true));
$("#themebtn").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const dark = cur ? cur === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
  if (BOOK) { render(); }
});
addEventListener("resize", () => {
  if (BOOK && BOOK.us && view === "us") inUs(renderMap);
});
/* don't poll a tab nobody is looking at; catch up the moment it comes back */
addEventListener("visibilitychange", () => {
  if (document.hidden) clearTimeout(timer); else load(false);
});

load(false);
})();
</script>
'''

head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n')
markup = markup.replace('\n<div class="mast">', '\n</head>\n<body>\n<div class="mast">', 1)

out = ROOT / "static" / "index.html"
out.write_text(head + markup + PREAMBLE + render_block + TAIL + "\n</body>\n</html>\n")
print(f"wrote {out}  ({out.stat().st_size:,} bytes)")
