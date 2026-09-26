"""A tiny local web server for the dashboards, on 127.0.0.1 only.

It serves the dashboard pages and the two status files they read, and nothing else:
never .env, never results/session.json (your Firstock session), never the ledgers.
"""

from __future__ import annotations

import posixpath
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = ("/results/shop.json", "/results/backtest.json")


class _Handler(SimpleHTTPRequestHandler):
    page = "shop.html"  # which dashboard "/" opens

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = posixpath.normpath(unquote(self.path.split("?", 1)[0].split("#", 1)[0]))
        if path in ("/", "/index.html"):
            self.path = f"/dashboard/{self.page}"
        elif not (path in ALLOWED or path.startswith("/dashboard/")):
            self.send_error(404)
            return
        return super().do_GET()

    def do_HEAD(self):
        self.send_error(405)

    def log_message(self, *args):  # keep the terminal clean
        pass


def serve(port: int = 8765, open_browser: bool = True, page: str = "shop.html") -> ThreadingHTTPServer:
    handler = type("Handler", (_Handler,), {"page": page})
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), partial(handler, directory=str(ROOT)))
    except OSError:
        raise SystemExit(f"  port {port} is busy. Stop the other dashboard (Ctrl+C) or add --port {port + 1}")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print(f"  dashboard: {url}")
    if open_browser:
        webbrowser.open(url)
    return server
