# Consolidated US Book

A daily-tracking dashboard for three US brokerage accounts — two Vested/DriveWealth
and one IBKR — consolidated into a single view, with a watchlist and
valuation-driven buy calls.

**27 positions · 33 tickers tracked · $53,767 market value on $33,011 invested (+62.9%)**

```
dashboard.html            open this — the whole dashboard, one self-contained file
build_data.py             the dataset and the scoring model; regenerates the dashboard
refresh.py                pulls live quotes, rewrites prices, rebuilds
dashboard.template.html   page source, with the data injected at build time
data/portfolio.json       the generated dataset
data/SOURCES.md           where every number came from, and how splits were resolved
```

## Daily use

```bash
python3 refresh.py     # fetch live prices, rewrite build_data.py, rebuild dashboard.html
open dashboard.html
```

`refresh.py` needs no API key and no third-party packages. Any ticker that fails
keeps its previous value and is listed at the end — it never invents a price.
`--dry-run` shows what would change without writing.

The dashboard also refreshes itself: opened from your own machine it fetches
quotes and a year of history in the browser, recomputes every value, weight and
score, and draws the 50/200-day and RSI readings from real data. The badge in the
header reads **Live** when that succeeds. Published as an Artifact the browser
blocks those requests, so it falls back to the 5 Sep snapshot and says **Snapshot**.

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
