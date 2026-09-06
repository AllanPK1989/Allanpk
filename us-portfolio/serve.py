#!/usr/bin/env python3
"""
Serve the dashboard with a working live-quote feed.

    python3 serve.py            # http://localhost:8000
    python3 serve.py --port 9000 --no-open

Why this exists: the dashboard's "Refresh quotes" button cannot reach a quote
API on its own. Opened as a file:// page the browser sends Origin: null and the
quote host refuses it (CORS); inside a published Artifact the page's CSP blocks
the request outright. Neither is fixable from the page.

This server sidesteps both. It serves the dashboard over http://localhost and
fetches quotes itself, server-side, where CORS does not apply. The page calls
/api/quote on its own origin, so nothing is cross-origin.

Set QUOTE_BASE to point the proxy somewhere else (used by the test suite).
"""
import argparse, json, os, sys, threading, urllib.error, urllib.parse, urllib.request, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent.resolve()
QUOTE_BASE = os.environ.get(
    "QUOTE_BASE", "https://query1.finance.yahoo.com/v8/finance/chart/")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept": "application/json"}
TIMEOUT = 15


def fetch_quote(ticker):
    """Fetch one ticker upstream and normalise it. Raises on failure."""
    url = f"{QUOTE_BASE}{urllib.parse.quote(ticker)}?range=1y&interval=1d"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        payload = json.load(r)
    res = (payload.get("chart") or {}).get("result") or []
    if not res:
        err = (payload.get("chart") or {}).get("error")
        raise ValueError(f"no result for {ticker}" + (f": {err}" if err else ""))
    res = res[0]
    meta = res.get("meta") or {}
    ind = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [c for c in (ind.get("close") or []) if isinstance(c, (int, float))]
    px = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    if px is None:
        raise ValueError(f"no price for {ticker}")
    return {"ticker": ticker, "px": px,
            "prev": meta.get("chartPreviousClose"),
            "lo": meta.get("fiftyTwoWeekLow"), "hi": meta.get("fiftyTwoWeekHigh"),
            "hist": closes[-260:]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def _json(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def guess_type(self, path):
        """Declare UTF-8 on text, or the browser falls back to Latin-1 and the
        rupee signs and middots render as mojibake."""
        t = super().guess_type(path)
        base = t.split(";")[0].strip()
        if base.startswith("text/") or base in ("application/javascript", "application/json"):
            return base + "; charset=utf-8"
        return t

    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path == "/api/quote":
            tickers = [t.strip().upper()
                       for t in urllib.parse.parse_qs(parts.query).get("t", [])
                       if t.strip()]
            if not tickers:
                return self._json(400, {"error": "pass ?t=TICKER (repeatable)"})
            out, errors = {}, {}
            for t in tickers:
                try:
                    out[t] = fetch_quote(t)
                except urllib.error.HTTPError as e:
                    errors[t] = f"upstream HTTP {e.code}"
                except urllib.error.URLError as e:
                    errors[t] = f"network: {e.reason}"
                except Exception as e:                     # noqa: BLE001
                    errors[t] = f"{type(e).__name__}: {e}"
            return self._json(200, {"quotes": out, "errors": errors,
                                    "source": QUOTE_BASE})
        if parts.path == "/":
            self.path = "/dashboard.local.html"
        return super().do_GET()

    def log_message(self, fmt, *args):
        if "/api/quote" in (args[0] if args else ""):
            sys.stderr.write("  quote request: %s\n" % (args[0],))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://localhost:{a.port}/"
    print(f"Dashboard on {url}   (Ctrl-C to stop)")
    print(f"Quotes proxied from {QUOTE_BASE}")
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
