"""
`python -m seed` — load all development data in one go:
  1. ~55 sample postings          (seed/__init__.py)
  2. the ~110-entry skills taxonomy (seed/skills.py)
  3. two fixture-backed ingest sources for the admin page (seed/ingest_sources.py)

Every step is idempotent, so it is safe to re-run.
Afterwards, run `python -m app.ingest.embed` to embed postings for semantic search
and resume matching (needs OPENAI_API_KEY).
"""

import asyncio

from app.db import engine
from seed import seed
from seed.ingest_sources import seed_sources
from seed.skills import seed_skills


async def main() -> None:
    await seed()
    await seed_skills()
    await seed_sources()
    await engine.dispose()


asyncio.run(main())
