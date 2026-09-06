# Deploying the dashboard

Everything below is committed and ready. The one step no one can take for you
is authenticating to a host with your own account.

**Set a token before it is reachable from the internet.** The app has no login.
Without `APP_TOKEN` anyone with the URL sees your positions, cost bases and P&L.
The Render blueprint generates one for you; on Fly you set it yourself.

---

## Render — recommended, no local tooling

Nothing to install. Render reads `render.yaml`, which sits at the repository
root because that is the only place Render looks for it.

1. <https://dashboard.render.com/blueprints> → **New Blueprint Instance**
2. Pick this repo. The blueprint pins
   `branch: claude/us-portfolio-dashboard-analysis-3ymsyv` itself — the code is
   not on `main`, so do not let it default there.
3. Apply. Render builds `us-portfolio/webapp/Dockerfile` with `us-portfolio/`
   as the build context, and generates `APP_TOKEN` for you.
4. Copy that value from the service's **Environment** tab, then open
   `https://us-book.onrender.com/?token=<value>`

Pushes to that branch redeploy automatically. The free tier sleeps when idle, so
the first request after a quiet spell takes ~30s to wake.

If you later merge this to `main`, change `branch:` in `render.yaml` to match,
or the blueprint will keep tracking the old branch.

`python3 scripts/check_deploy_config.py` (run from the repo root) checks the
blueprint before you click: that the file is where Render looks, that the branch
it names actually carries the code, and that every Dockerfile `COPY` resolves
inside the declared build context. CI runs it on every push.

## Fly.io — if you would rather use a CLI

```bash
cd us-portfolio                      # fly.toml lives here; it is the build context
fly auth login
fly apps create us-book
fly secrets set APP_TOKEN=$(openssl rand -hex 16) --app us-book
fly deploy
fly open
```

`fly secrets list` will not show the value back, so save it when you generate it.

## Deploy from CI instead

`.github/workflows/portfolio-deploy.yml` deploys to Fly on every push. After the
Fly steps above:

```bash
fly tokens create deploy --app us-book
```

Put that in the repo under **Settings → Secrets and variables → Actions**:
- secret `FLY_API_TOKEN` — the token
- variable `DEPLOY_ENABLED` — `true`

The workflow skips itself until `DEPLOY_ENABLED` is set, so it will not fail
builds for anyone who has not configured it. It waits for `/api/health` to
answer 200 before reporting success.

## Anywhere else

The image is a plain container that reads `$PORT`. Railway, Cloud Run, Koyeb
and a VPS all work:

```bash
docker build -f webapp/Dockerfile -t us-book .     # from us-portfolio/
docker run -p 8000:8000 -e APP_TOKEN=$(openssl rand -hex 16) us-book
```

---

## Checking it worked

```bash
curl https://<your-host>/api/health          # open, no token needed
```

```json
{"ok": true, "market": {"phase": "closed", ...}, "quotes": {"cached_tickers": 33, ...}}
```

`ok: false` with `cached_tickers: 0` means the host cannot reach either quote
source. The app still serves the statement close and labels it — check
`last_error` in that response for the reason.

## What deployment does not fix

Quotes come from public endpoints that may rate-limit or block a datacentre IP
even when they work from a laptop. If that happens the dashboard falls back to
Stooq, then to the reference close, and says which. It never shows a stale price
as a live one. Should both sources stay blocked from your host, the fix is a
keyed provider — the provider chain in `webapp/app/providers.py` takes a new
class without touching anything else.

## Privacy

The served data has no name, email, PAN or account number in it. It does have
every position, cost basis and the consolidated total. Treat the URL and the
token as you would a brokerage login.
