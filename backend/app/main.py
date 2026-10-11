"""
FastAPI application factory.

Keeping app creation in a function (create_app) makes it easy to
instantiate the app in tests with different settings without side effects.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.me import router as me_router
from app.api.meta import router as meta_router
from app.api.postings import router as postings_router
from app.api.resume import router as resume_router
from app.api.saved import router as saved_router
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.redis import create_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup: verify the DB is reachable and create the Redis pool.
    Both checks surface misconfigurations at startup rather than on the first request.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

    app.state.redis = create_redis_pool()

    yield

    # Clean shutdown — close the Redis connection pool
    await app.state.redis.aclose()


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Flatten our error payloads so every error has one shape:
        {"detail": "Human-readable message", "code": "SNAKE_CASE"}

    Services raise HTTPException(detail={"detail": ..., "code": ...}); FastAPI's default
    handler would nest that under another "detail" key. Plain-string details (e.g. from
    FastAPI itself) get a generic code derived from the status.
    """
    assert isinstance(exc, HTTPException)
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        body = {"detail": exc.detail.get("detail", ""), "code": exc.detail["code"]}
    else:
        body = {"detail": str(exc.detail), "code": f"HTTP_{exc.status_code}"}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """
    Serve the built React app from the API process, so a single container is the whole
    website (same origin: no CORS, first-party cookies). Must run after the API routers.

    - /assets/* → hashed JS/CSS bundles
    - any other GET that isn't /api/* → a real file if one exists, else index.html,
      so client-side routes like /saved survive a page refresh.
    """
    index = static_dir / "index.html"
    if not index.is_file():
        return
    root = static_dir.resolve()
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (root / full_path).resolve()
        # The parents check blocks path traversal (e.g. /../../etc/passwd)
        if full_path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CoopRadar API",
        description=(
            "Co-op posting aggregator — browse, search, save, track, and match your resume."
        ),
        version="0.4.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(HTTPException, http_exception_handler)

    # Allow the Vite dev server (and any configured origins) to call the API.
    # allow_credentials=True is required for cookie-based auth to work cross-origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
        allow_headers=["*"],
    )

    app.include_router(postings_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(me_router, prefix="/api")
    app.include_router(saved_router, prefix="/api")
    app.include_router(resume_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness probe used by Docker/CI — no DB or Redis calls."""
        return {"status": "ok"}

    if settings.static_dir:
        mount_frontend(app, Path(settings.static_dir))

    return app


# Module-level app instance so uvicorn can find it via "app.main:app"
app = create_app()
