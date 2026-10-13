"""Add the dev and test import sources that read from local files."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from app.db import AsyncSessionLocal

# The test files live in backend/tests/fixtures/ingest
_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ingest"


SOURCES = [
    {
        "name": "Acme Jobs (Dev Fixture)",
        "adapter_type": "json_api",
        "config": {
            "url": (_FIXTURE_DIR / "acme_jobs.json").as_uri(),
            "field_map": {},
        },
    },
    {
        "name": "Shopify RSS (Dev Fixture)",
        "adapter_type": "rss",
        "config": {
            "url": (_FIXTURE_DIR / "shopify_rss.xml").as_uri(),
        },
    },
]


async def seed_sources() -> None:
    """Add the dev sources and skip any whose name is already there, so it is safe to rerun."""
    async with AsyncSessionLocal() as db:
        for source in SOURCES:
            await db.execute(
                text(
                    "INSERT INTO ingest_sources (id, name, adapter_type, config) "
                    "SELECT gen_random_uuid(), :name, :adapter_type, CAST(:config AS jsonb) "
                    "WHERE NOT EXISTS (SELECT 1 FROM ingest_sources WHERE name = :name)"
                ),
                {
                    "name": source["name"],
                    "adapter_type": source["adapter_type"],
                    "config": json.dumps(source["config"]),
                },
            )
        await db.commit()
    print(f"Seeded {len(SOURCES)} ingest sources.")


if __name__ == "__main__":
    asyncio.run(seed_sources())
