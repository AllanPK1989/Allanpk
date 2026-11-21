"""Nudge API. Run: uvicorn app.main:app  (docs at /api/docs)."""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import scheduler, seed
from .config import get_config
from .db import SessionLocal, init_db
from .routers import assistant, auth, system, tasks, views

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nudge")


def prepare() -> None:
    """Create tables, default baskets, first PIN and (in demo mode) sample data."""
    cfg = get_config()
    init_db()
    db = SessionLocal()
    try:
        seed.ensure_baskets(db)
        seed.ensure_pin(db)
        if cfg.seed_sample_data:
            n = seed.seed_sample(db)
            if n:
                log.info("Added %s sample tasks (demo mode)", n)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = get_config()
    prepare()
    job = None
    if cfg.scheduler_enabled:
        job = asyncio.create_task(scheduler.run_forever(cfg.scheduler_interval_s))
    yield
    if job:
        job.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await job


_docs = get_config().api_docs
app = FastAPI(title="Nudge", version=system.VERSION, lifespan=lifespan, redoc_url=None,
              docs_url="/api/docs" if _docs else None, openapi_url="/api/openapi.json" if _docs else None)
for r in (auth.router, tasks.router, assistant.router, views.router, system.router):
    app.include_router(r)

_static = get_config().static_dir
if _static and Path(_static).is_dir():
    app.mount("/assets", StaticFiles(directory=Path(_static) / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = Path(_static) / path
        if path and target.is_file() and Path(_static).resolve() in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(Path(_static) / "index.html")
