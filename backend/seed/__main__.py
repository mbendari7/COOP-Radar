"""
`python -m seed` — load starting data. Every step is idempotent (safe to re-run).

What gets loaded is controlled by environment variables (all default to "true"):
  SEED_JOB_BOARDS        real employer career boards to import live jobs from (seed/job_boards.py)
  SEED_SAMPLE_POSTINGS   ~55 made-up sample postings — handy for development; the hosted site
                         turns this off so visitors only see real jobs
  SEED_DEV_SOURCES       two fixture-file sources used to demo the Admin page in development
The skills taxonomy (used for skill detection) is always loaded.

Jobs from the career boards arrive when the worker runs them (on start, then every 6 hours).
"""

import asyncio
import os

from app.db import engine
from seed import seed
from seed.ingest_sources import seed_sources
from seed.job_boards import seed_job_boards
from seed.skills import seed_skills


def _flag(name: str) -> bool:
    return os.getenv(name, "true").strip().lower() in ("1", "true", "yes")


async def main() -> None:
    await seed_skills()
    if _flag("SEED_JOB_BOARDS"):
        await seed_job_boards()
    if _flag("SEED_SAMPLE_POSTINGS"):
        await seed()
    if _flag("SEED_DEV_SOURCES"):
        await seed_sources()
    await engine.dispose()


asyncio.run(main())
