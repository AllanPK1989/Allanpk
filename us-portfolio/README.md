# Consolidated US Book

A daily-tracking dashboard for three US brokerage accounts — two Vested/DriveWealth
and one IBKR — consolidated into a single view, with a watchlist and
valuation-driven buy calls.

**27 positions · 33 tickers tracked · $53,767 market value on $33,011 invested (+62.9%)**

```
serve.py                  run this — serves the dashboard with live quotes working
dashboard.local.html      standalone page, for reading the snapshot offline
dashboard.html            the same page in the form the Artifact service wraps
build_data.py             the dataset and the scoring model; regenerates both pages
refresh.py                rewrites prices into build_data.py without a browser
dashboard.template.html   page source, with the data injected at build time
data/portfolio.json       the generated dataset
data/SOURCES.md           where every number came from, and how splits were resolved
```

## Daily use

```bash
python3 serve.py       # → http://localhost:8000, with working live quotes
```

That is the one command you need. The badge turns **Live**, prices and 52-week
ranges refresh, and the 50/200-day and RSI figures are computed from a year of
fetched history.

**Why a server rather than just opening the file.** A browser page cannot reach a
quote API by itself. Opened as `file://` it sends `Origin: null` and the quote
host rejects it; inside a published Artifact the page's content policy blocks the
request before it is sent. Neither is fixable from the page. `serve.py` fetches
quotes itself, server-side, where cross-origin rules do not apply, and the page
calls `/api/quote` on its own origin.

Open `dashboard.local.html` directly if you just want to read the last snapshot —
it works offline, and tells you plainly that the numbers are not live.

To bake fresh prices into the committed files without a browser:

```bash
python3 refresh.py     # rewrites prices in build_data.py, rebuilds both pages
python3 refresh.py --dry-run
```

Neither script needs an API key or a third-party package. Any ticker that fails
keeps its previous value and is listed at the end — nothing is ever invented.

## What the page shows

**Today's calls** — every name ranked on valuation first, entry quality second,
each with its arithmetic on the line: price, consensus target and upside, forward
multiple, distance from the 52-week high, your cost basis, and the two scores.

**The range bar** is the recurring instrument. The track spans the 52-week low to
high, the filled dot is today's price, the flag is the consensus target, and the
tinted band is the lower 40% of the range — where entries have historically had
margin of safety.

**Valuation map** — earnings multiple against upside to consensus on a log axis,
sized by position value. Thirteen names can't sit on a P/E axis (loss-making,
index funds, or no published target); they're named under the chart rather than
quietly dropped.

**Holdings** — sortable, filterable by account, so you can see how the same name
is priced across three different cost bases.

**Watchlist** — all 33 including the nine additions (AVGO, ASML, TSM, INTC, AMD,
PLTR, PANW, NOW, CRWD), with a confidence flag per row.

## Scoring

Valuation = 40% upside to consensus + 40% forward P/E versus the sector median
(30.4× semis, 19.9× software, 22× mega-cap) + 20% position in the 52-week range.

Entry quality peaks for a pullback of 12–35% off the high, and is penalised
within 5% of the high (no margin of safety) and beyond 50% off it (falling knife).

The score ranks; judgement decides. Both the score and a written verdict appear on
every row, and they disagree in places — deliberately. MU scores well on
valuation and is marked **trim**, because a 12.5× multiple on peak-cycle memory
earnings is the oldest trap in the sector.

## Caveats

Consensus targets drift toward the price and are a crowd estimate, not a
valuation. Sector medians are a blunt instrument for names with no real peer.
Prices are as of 5 Sep 2026 until you run a refresh.

This is analysis to inform your own decisions, not advice from a SEBI-registered
investment adviser.
