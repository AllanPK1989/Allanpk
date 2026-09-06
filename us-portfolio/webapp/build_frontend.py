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

markup = markup.replace(
    '  <span class="badge" id="feed"><span class="dot"></span><span id="feedtxt">Snapshot</span></span>',
    '  <span class="badge" id="mkt"><span id="mkttxt">—</span></span>\n'
    '  <span class="badge" id="feed"><span class="dot"></span>'
    '<span id="feedtxt">Connecting…</span></span>')
markup = markup.replace('<button class="btn" id="refresh">Refresh quotes</button>',
                        '<button class="btn" id="refresh">Refresh now</button>')
markup = markup.replace('  <section id="calls">',
    '  <p class="note" id="freshness" style="margin:14px 0 0;font-size:12px;'
    'font-family:var(--mono);color:var(--ink-3)"></p>\n\n  <section id="calls">')
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
      '<p style="margin:0 0 16px;color:var(--ink-2);font-size:13.5px;line-height:1.55">' +
      'It needs the access token. On Render it is under your service &rarr; ' +
      '<b>Environment</b> &rarr; <code>APP_TOKEN</code>.</p>' +
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
        err.textContent = "That token was not accepted. Check it against APP_TOKEN.";
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
  if (wrong) err.textContent = "That token was not accepted. Check it against APP_TOKEN.";
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
    const r = await fetch("/api/" + (force ? "refresh" : "portfolio"),
      { method: force ? "POST" : "GET", headers: authHeaders(), cache: "no-store" });
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
  const f = BOOK.feed, m = BOOK.market;
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

/* --- wiring ----------------------------------------------------------- */
let side = "buy", acct = "all", wfilter = "all";
let hsort = { k: "value", dir: -1 }, wsort = { k: "combined", dir: -1 };

function render() {
  renderTop(); renderHeadline(); renderCalls();
  renderHoldings(); renderWatch(); renderMap(); renderRisk();
}
document.querySelectorAll("[data-side]").forEach(b =>
  b.addEventListener("click", () => {
    side = b.dataset.side;
    document.querySelectorAll("[data-side]").forEach(o =>
      o.setAttribute("aria-pressed", String(o === b)));
    renderCalls();
  }));
document.querySelectorAll("[data-acct]").forEach(b =>
  b.addEventListener("click", () => {
    acct = b.dataset.acct;
    document.querySelectorAll("[data-acct]").forEach(o =>
      o.setAttribute("aria-pressed", String(o === b)));
    renderHoldings();
  }));
$("#wfilter").addEventListener("change", e => { wfilter = e.target.value; renderWatch(); });
$("#refresh").addEventListener("click", () => load(true));
$("#themebtn").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const dark = cur ? cur === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
  if (BOOK) renderMap();
});
addEventListener("resize", () => { if (BOOK) renderMap(); });
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
