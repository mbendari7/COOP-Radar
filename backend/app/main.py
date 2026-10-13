"""
Builds the FastAPI app.

Making the app inside a function (create_app) lets tests build
a fresh one with different settings and no side effects.
"""

import asyncio
import contextlib
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
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.me import router as me_router
from app.api.meta import router as meta_router
from app.api.postings import router as postings_router
from app.api.resume import router as resume_router
from app.api.saved import router as saved_router
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.store import create_store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    On startup check the database is there, open the session store and start the
    scheduler that imports jobs from the career boards (app/jobs.py).
    """
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

    app.state.store = create_store()

    scheduler: asyncio.Task[None] | None = None
    if get_settings().background_jobs:
        from app.jobs import scheduler as run_scheduler

        scheduler = asyncio.create_task(run_scheduler(app.state.store))

    yield

    if scheduler is not None:
        scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler
    await app.state.store.aclose()


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Give every error the same simple shape
        {"detail": "Message a person can read", "code": "SNAKE_CASE"}

    Our services raise HTTPException(detail={"detail": ..., "code": ...}) and FastAPI would
    normally wrap that in another "detail". Plain text details, like the ones FastAPI makes
    itself, get a code based on the status.
    """
    assert isinstance(exc, HTTPException)
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        body = {"detail": exc.detail.get("detail", ""), "code": exc.detail["code"]}
    else:
        body = {"detail": str(exc.detail), "code": f"HTTP_{exc.status_code}"}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """
    Serve the built React site from the API too, so one server is the whole website.
    Same origin means no CORS trouble and normal cookies. Has to run after the API routers.

    /assets/* gives the hashed JS and CSS files
    any other GET that is not /api/* gives a real file if there is one or else index.html
    so pages like /saved still work after a refresh
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
        # Checking the parents stops sneaky paths like /../../etc/passwd
        if full_path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CoopRadar API",
        description=(
            "Co-op jobs from real employers. Browse, search, save, track and match your resume."
        ),
        version="0.4.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(HTTPException, http_exception_handler)

    # Let the Vite dev server and any sites in the settings call the API
    # allow_credentials=True is needed so cookies work across origins
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
    app.include_router(ai_router, prefix="/api")

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Health check for the host and CI. It never touches the database."""
        return {"status": "ok"}

    if settings.static_dir:
        mount_frontend(app, Path(settings.static_dir))

    return app


# The app itself so uvicorn can find it at "app.main:app"
app = create_app()
