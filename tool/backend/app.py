"""UpBain FastAPI application.

Single entry point. All routes under /api/...
Static frontend served from frontend/dist/ (or frontend/ in dev).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes.auth import router as auth_router
from .api.routes.backup import router as backup_router
from .api.routes.channels import router as channels_router
from .api.routes.health import router as health_router
from .api.routes.mappings import router as mappings_router
from .api.routes.runtime import router as runtime_router
from .api.routes.sse import router as sse_router
from .api.routes.telegram import router as telegram_router
from .database.init_db import init_db
from .services.job_queue import start_worker
from .services.log_stream import install_log_handler

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="UpBain Control API",
        description="Admin dashboard for Telegram channel management",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — restrict to localhost only in development
    allowed_origins = os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
    )

    # Security headers middleware
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # CSP: allow scripts from self only, no inline eval
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # allow inline styles for now
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    # Routes
    app.include_router(auth_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(channels_router, prefix="/api")
    app.include_router(mappings_router, prefix="/api")
    app.include_router(runtime_router, prefix="/api")
    app.include_router(sse_router, prefix="/api")
    app.include_router(telegram_router, prefix="/api")
    app.include_router(backup_router, prefix="/api")

    # Serve frontend static files
    _FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"
    _FRONTEND_SRC = Path(__file__).parent.parent / "frontend"

    static_dir = _FRONTEND_DIR if _FRONTEND_DIR.exists() else _FRONTEND_SRC

    if (static_dir / "index.html").exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def serve_spa():
            return (static_dir / "index.html").read_text()

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def serve_spa_catch(full_path: str):
            # Don't intercept API routes
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            index = static_dir / "index.html"
            if index.exists():
                return index.read_text()
            return JSONResponse({"detail": "Frontend not built"}, status_code=503)

    # Lifecycle
    @app.on_event("startup")
    async def startup():
        install_log_handler()
        logging.basicConfig(level=logging.INFO)
        log.info("UpBain starting up...")
        await init_db()
        await start_worker()
        log.info("UpBain ready.")

    @app.on_event("shutdown")
    async def shutdown():
        from .services.job_queue import stop_worker
        await stop_worker()
        from .telegram.adapters.mtproto import destroy_adapter
        await destroy_adapter()
        log.info("UpBain shut down cleanly.")

    return app


app = create_app()
