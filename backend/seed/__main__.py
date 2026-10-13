"""
`python -m seed` loads the starting data. Every step is safe to run again.

Environment variables decide what gets loaded, each true or false
  SEED_JOB_BOARDS        real employer career boards to import live jobs from. On by default
  SEED_SAMPLE_POSTINGS   about 55 made up jobs, handy offline. Off by default so
                         visitors only see real jobs
  SEED_DEV_SOURCES       two file based sources to try the Admin page with. Off by default
The skills list always gets loaded since skill matching needs it.

Jobs from the career boards show up when the background scheduler runs them
(app/jobs.py), once on start and then every 6 hours.
"""

import asyncio
import os

from app.db import engine
from seed import seed
from seed.ingest_sources import seed_sources
from seed.job_boards import seed_job_boards
from seed.skills import seed_skills


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


async def main() -> None:
    await seed_skills()
    if _flag("SEED_JOB_BOARDS", "true"):
        await seed_job_boards()
    if _flag("SEED_SAMPLE_POSTINGS", "false"):
        await seed()
    if _flag("SEED_DEV_SOURCES", "false"):
        await seed_sources()
    await engine.dispose()


asyncio.run(main())
