"""FastAPI app: JSON API under /api and the built PWA everywhere else."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from . import db as dbmod
from .api import auth, chat, routes
from .config import check_production_settings, get_settings
from .security import same_origin

log = logging.getLogger(__name__)
STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; font-src 'self'; manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; "
       "base-uri 'self'; form-action 'self'; object-src 'none'")


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if settings.environment == "production":
        problems = check_production_settings(settings)
        if problems:
            raise RuntimeError("Refusing to start: " + "; ".join(problems))
    dbmod.init_db()

    app = FastAPI(title=settings.app_name, docs_url=None if settings.environment == "production" else "/api/docs",
                  redoc_url=None, openapi_url=None if settings.environment == "production" else "/api/openapi.json")

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/"):
            if not same_origin(request, settings):
                return JSONResponse({"detail": "Cross-site request blocked"}, status_code=403)
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", CSP)
        if settings.cookie_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.include_router(auth.router, prefix="/api")
    app.include_router(routes.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")

    @app.get("/api/health", include_in_schema=False)
    def health():
        return {"ok": True}

    @app.get("/api/{rest:path}", include_in_schema=False)
    def api_not_found(rest: str):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        root = STATIC_DIR.resolve()
        index = root / "index.html"
        if not index.exists():
            return JSONResponse({"detail": "Frontend not built. Run npm run build in frontend/."}, status_code=404)
        target = (root / path).resolve()
        if path and target.is_file() and target.is_relative_to(root):
            headers = {}
            if target.name in ("sw.js", "manifest.webmanifest", "index.html"):
                headers["Cache-Control"] = "no-cache"
            elif "/assets/" in target.as_posix():
                headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return FileResponse(target, headers=headers)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


app = create_app() if os.environ.get("IA_NO_APP") != "1" else None  # tests build their own app
