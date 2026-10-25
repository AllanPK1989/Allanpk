"""FastAPI application. API docs at /api/docs."""
import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import jobs  # noqa: F401  (registers the after-commit job hooks)
from .config import get_config
from .db import SessionLocal
from .models import CopilotCall
from .routers import (
    admin,
    ai,
    auth,
    copilot,
    dashboard,
    documents,
    fault_cards,
    integrations,
    logs,
    machines,
    media,
    parts,
    review,
    skills,
    tips,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
cfg = get_config()
if cfg.environment == "production" and (cfg.secret_key == "change-me-in-production" or len(cfg.secret_key) < 32):
    raise RuntimeError("Set SECRET_KEY to a random value of at least 32 characters before running in production")

app = FastAPI(title="Thunai API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
if cfg.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cfg.cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )
for module in (auth, machines, logs, media, ai, review, fault_cards, tips, documents, dashboard, skills, parts, integrations, copilot, admin):
    app.include_router(module.router)
log = logging.getLogger("thunai.copilot")


@app.middleware("http")
async def record_copilot_calls(request: Request, call_next):
    """One copilot_calls row per tool call from the Copilot agent (SPEC 13.3)."""
    if not request.url.path.startswith("/api/copilot/"):
        return await call_next(request)
    started = time.monotonic()
    response = await call_next(request)
    route = request.scope.get("route")
    try:
        with SessionLocal() as db:
            db.add(
                CopilotCall(
                    operation=(getattr(route, "operation_id", None) or getattr(route, "name", None) or "unknown")[:60],
                    user_id=getattr(request.state, "copilot_user_id", None),
                    status_code=response.status_code,
                    ok=response.status_code < 400,
                    error="" if response.status_code < 400 else f"HTTP {response.status_code}",
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            )
            db.commit()
    except Exception:  # monitoring must never break a tool call
        log.exception("Could not record a Copilot call")
    return response


@app.get("/api/health", tags=["meta"])
def health():
    return {"ok": True}


@app.get("/api/meta", tags=["meta"])
def meta():
    return {
        "app": cfg.app_name,
        "version": app.version,
        "copilot": {"enabled": cfg.copilot_ready, "teams_url": cfg.copilot_teams_url},
        "stt_provider": cfg.stt_provider,
        "environment": cfg.environment,
    }


# Optional: serve the built PWA from the API process (single-container installs and local demos).
# In Docker Compose, Caddy serves the PWA instead.
_static = Path(cfg.static_dir) if cfg.static_dir else None
if _static and (_static / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (_static / path).resolve()
        if path and candidate.is_file() and _static.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
