"""
FastAPI application factory.

Keeping app creation in a function (create_app) makes it easy to
instantiate the app in tests with different settings without side effects.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.postings import router as postings_router
from app.config import get_settings
from app.db import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup: verify the DB is reachable before accepting requests.
    This surfaces misconfigured DATABASE_URLs at startup rather than on
    the first request, which is much easier to debug.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    yield
    # Nothing to tear down for now; engine connections close naturally.


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CoopRadar API",
        description="Co-op posting aggregator — browse, search, and filter postings.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Allow the Vite dev server (and any configured origins) to call the API.
    # In production you'd restrict this to your actual domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET"],      # Feature 001 is read-only
        allow_headers=["*"],
    )

    app.include_router(postings_router, prefix="/api")

    return app


# Module-level app instance so uvicorn can find it via "app.main:app"
app = create_app()
