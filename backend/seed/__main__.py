"""
`python -m seed` loads the starting data. Every step is safe to run again.

Environment variables decide what gets loaded, each true or false
  SEED_JOB_BOARDS        real employer career boards to import live jobs from. On by default
  SEED_SAMPLE_POSTINGS   about 55 made up jobs, handy offline. Off by default so
                         visitors only see real jobs
  SEED_DEV_SOURCES       two file based sources to try the Admin page with. Off by default
  SEED_FORCE             load everything again even when nothing changed. Off by default
The skills list always gets loaded since skill matching needs it.

A free host starts the site again every time it wakes up, so the seed remembers a fingerprint
of its files and settings in kv_store and skips the work when they have not changed.

Jobs from the career boards show up when the background scheduler runs them
(app/jobs.py), once on start and then every 6 hours.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import text

from app.db import engine
from seed import seed
from seed.ingest_sources import seed_sources
from seed.job_boards import seed_job_boards
from seed.skills import seed_skills


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


_FINGERPRINT_KEY = "seed:fingerprint"
_SETTINGS = (
    "SEED_JOB_BOARDS", "SEED_SAMPLE_POSTINGS", "SEED_DEV_SOURCES", "ADZUNA_APP_ID", "ADZUNA_APP_KEY",
)


def fingerprint() -> str:
    """A hash of every seed file and the settings that change what gets loaded."""
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.*")):
        if path.suffix in (".py", ".json"):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    for name in _SETTINGS:
        value = os.getenv(name, "")
        if name.startswith("ADZUNA"):
            value = str(bool(value))  # only whether it is set, never the key itself
        digest.update(f"{name}={value}".encode())
    return digest.hexdigest()


async def _stored_fingerprint() -> str | None:
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT fields->>'hash' FROM kv_store WHERE key = :key"), {"key": _FINGERPRINT_KEY}
        )
        return row.scalar_one_or_none()


async def _store_fingerprint(value: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO kv_store (key, fields) VALUES (:key, CAST(:fields AS jsonb)) "
                "ON CONFLICT (key) DO UPDATE SET fields = EXCLUDED.fields"
            ),
            {"key": _FINGERPRINT_KEY, "fields": json.dumps({"hash": value})},
        )


async def main() -> None:
    current = fingerprint()
    if not _flag("SEED_FORCE", "false") and await _stored_fingerprint() == current:
        print("The skills list and career boards are already loaded.")
        await engine.dispose()
        return
    await seed_skills()
    if _flag("SEED_JOB_BOARDS", "true"):
        await seed_job_boards()
    if _flag("SEED_SAMPLE_POSTINGS", "false"):
        await seed()
    if _flag("SEED_DEV_SOURCES", "false"):
        await seed_sources()
    await _store_fingerprint(current)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
