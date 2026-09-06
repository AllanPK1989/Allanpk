"""US portfolio dashboard — live web app.

Routes
    GET  /                 the dashboard
    GET  /api/portfolio    the book, marked to live prices
    GET  /api/health       provider and cache state
    POST /api/refresh      force a fetch, bypassing the cache
"""
from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import secrets
import time

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import calendar_us
from .book import Book
from .providers import QuoteService

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("portfolio")

STATIC = pathlib.Path(__file__).resolve().parent.parent / "static"
CACHE_TTL = float(os.environ.get("QUOTE_TTL", "60"))
APP_TOKEN = os.environ.get("APP_TOKEN") or ""

book = Book()
quotes = QuoteService(ttl=CACHE_TTL)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Warm the cache in the background.

    Warming inline used to hold up startup for as long as the quote hosts took
    to refuse 33 requests, which delayed readiness on a cold start. The app can
    serve from the reference data immediately, so it does.
    """
    task = None
    if not os.environ.get("SKIP_WARMUP"):
        async def warm():
            try:
                got = await quotes.get(book.tickers)
                log.info("warm-up: %d/%d quotes", len(got), len(book.tickers))
            except Exception as e:                        # noqa: BLE001
                log.warning("warm-up failed, serving reference prices: %s", e)
        task = asyncio.create_task(warm())
    yield
    if task and not task.done():
        task.cancel()


app = FastAPI(title="Consolidated US Book", docs_url="/api/docs",
              redoc_url=None, lifespan=lifespan)


def require_token(x_app_token: str | None = Header(default=None),
                  token: str | None = Query(default=None)):
    """Optional shared-secret gate. Set APP_TOKEN when the app is reachable
    from the internet; without it every route is open."""
    if not APP_TOKEN:
        return
    supplied = x_app_token or token or ""
    if not secrets.compare_digest(supplied, APP_TOKEN):
        raise HTTPException(status_code=401, detail="bad or missing token")


async def _payload(force: bool = False) -> dict:
    got = await quotes.get(book.tickers, force=force)
    marked = book.mark(got)
    now = time.time()
    ages = []
    for row in marked["universe"]:
        q = got.get(row["ticker"])
        if q:
            row["quote_age"] = round(now - q.fetched_at, 1)
            ages.append(now - q.fetched_at)
    marked["market"] = calendar_us.status()
    marked["feed"] = {
        "live": marked["live_count"] > 0,
        "live_count": marked["live_count"],
        "total": marked["universe_count"],
        "sources": sorted({r["quote_source"] for r in marked["universe"]
                           if r.get("quote_source")}),
        "age_seconds": round(max(ages), 1) if ages else None,
        "error": quotes.last_error,
        "reference_date": marked["as_of"],
    }
    return marked


@app.get("/api/portfolio", dependencies=[Depends(require_token)])
async def api_portfolio():
    return await _payload()


@app.post("/api/refresh", dependencies=[Depends(require_token)])
async def api_refresh():
    return await _payload(force=True)


@app.get("/api/health")
async def api_health():
    """Liveness, not feed quality.

    This previously answered 503 whenever no quote had been fetched, which is
    what failed the first Render deploy: the quote hosts refuse that egress IP,
    so health never went green and the platform killed a service that was in
    fact serving every page correctly. A degraded feed is reported in the body
    and the page says so on screen; it is not an unhealthy service. Only a book
    that will not load is.
    """
    healthy = bool(book.base.get("universe"))
    h = quotes.health()
    return JSONResponse(
        {"ok": healthy,
         "degraded": h["cached_tickers"] == 0,
         "detail": ("serving live quotes" if h["cached_tickers"]
                    else "serving the reference close — no quote source reachable"),
         "market": calendar_us.status(), "quotes": h,
         "reference_date": book.base["as_of"],
         "tickers": len(book.tickers)},
        status_code=200 if healthy else 503)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
        '<rect width="16" height="16" rx="3" fill="#8A5D14"/>'
        '<path d="M3 11.5 6.5 7l3 2.5L13 4" stroke="#F4F2ED" stroke-width="1.8" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"})


@app.api_route("/", methods=["GET", "HEAD"], dependencies=[Depends(require_token)])
async def index():
    # HEAD as well as GET: platform port probes use it, and a 405 there reads
    # as a broken service.
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
