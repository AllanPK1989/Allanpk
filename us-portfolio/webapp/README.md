# Consolidated US Book — live web app

The dashboard as a running service. The server fetches quotes itself and the
page polls it, so prices update without rebuilding anything.

```bash
cd webapp
./run.sh                      # → http://localhost:8000
```

That creates a virtualenv, installs three dependencies, and starts the app on
localhost. Nothing else is needed.

## Why a server

A browser page cannot fetch a quote API by itself. Opened as a `file://`
document it sends `Origin: null` and the quote host rejects it; inside a
published Artifact the content policy blocks the request before it is sent.
Neither is fixable from the page, which is why the earlier static version could
never go live. This app fetches server-side, where those rules do not apply.

## What it does

- **Three quote sources, tried in order, each with a cooldown.** Yahoo first,
  because only it returns a year of daily closes for the moving averages and
  RSI. Finnhub next when `FINNHUB_API_KEY` is set — the one that answers from a
  datacentre, where Yahoo and Stooq both refuse. Stooq last. A source that
  hard-blocks us is rested for a quarter of an hour rather than retried on
  every poll, and `/api/health` names which are resting and why.
- **Never silently stale.** Every response says how many names are priced,
  which source answered, and how old the data is. If both sources fail, the
  last good prices are served and marked stale; if none were ever fetched, the
  statement close is shown and labelled as the reference.
- **Market-aware polling.** Once a minute while the market is open, every five
  minutes around the edges, every fifteen when it is shut, and not at all while
  the tab is hidden.
- **Live prices, dated reasoning.** Prices, values, weights, P&L and both
  scores are recomputed from the live quote on every poll. The written verdicts
  are not — they were formed at the statement close, so any call whose price has
  since moved more than 5% is flagged on its card.

## API

| Route | |
|---|---|
| `GET /` | the dashboard |
| `GET /api/portfolio` | the whole book, marked live |
| `POST /api/refresh` | force a fetch, bypassing the cache |
| `GET /api/health` | provider and cache state; 503 when nothing is cached |
| `GET /api/docs` | generated OpenAPI docs |

## Configuration

Copy `.env.example`. Every value has a working default.

| | |
|---|---|
| `FINNHUB_API_KEY` | free key from finnhub.io; needed for live quotes on a deployed host |
| `QUOTE_TTL` | seconds a quote is reused before refetching (default 60) |
| `APP_TOKEN` | shared secret; empty means no auth. The page prompts for it and remembers it per browser |
| `PORT` | listen port (container hosts set this) |
| `SKIP_WARMUP` | skip the startup fetch |

## Deploying

The page itself is served without a token — it is an empty shell of markup and
rendering code, with no positions or prices in it. Everything on screen comes
from `/api/portfolio`, which is gated. That way opening your own dashboard gives
you somewhere to enter the token rather than a JSON error.

**Before you expose this to the internet, set `APP_TOKEN`.** The app has no
login. Without a token anyone with the URL can read your positions, cost bases
and P&L. `run.sh` binds to `127.0.0.1` for exactly this reason; the container
binds to `0.0.0.0` because a host requires it.

```bash
docker build -f webapp/Dockerfile -t us-book .    # build from the repo root
docker run -p 8000:8000 -e APP_TOKEN=$(openssl rand -hex 16) us-book
```

The image works on any container host — Fly, Render, Railway, Cloud Run. They
supply `$PORT`, which the entrypoint honours. Reach the app at
`https://your-host/?token=…`.

*The Dockerfile is written against the layout the app expects and that layout is
verified by the tests, but no Docker daemon was available where this was built,
so the image itself has not been built.*

## Tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest
```

30 tests: the scoring model (including a guard that the app and the static
build cannot drift apart), the market calendar across sessions, holidays and
half-days, the provider chain under partial and total outage, and the API
against a stub feed.

## How it relates to the static build

`build_data.py` in the parent folder owns the positions and the reference
market data and writes `data/portfolio.json`. This app reads that file and lays
live prices over it. The scoring model lives in `app/analytics.py` and is
imported by both, so there is one implementation and it cannot diverge.

`build_frontend.py` regenerates `static/index.html` from
`../dashboard.template.html`, so the live app and the static page share a
design. Run it after editing the template.
