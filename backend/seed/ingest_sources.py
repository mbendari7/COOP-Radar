"""Seed fixture-backed dev/test ingest sources."""

import asyncio
import os
from sqlalchemy import text
from app.db import AsyncSessionLocal

# Path to fixture files relative to the backend root (mounted as /app in Docker)
_FIXTURE_BASE = "/app/tests/fixtures/ingest"


SOURCES = [
    {
        "name": "Acme Jobs (Dev Fixture)",
        "adapter_type": "json_api",
        "config": {
            "url": f"file://{_FIXTURE_BASE}/acme_jobs.json",
            "field_map": {},
        },
    },
    {
        "name": "Shopify RSS (Dev Fixture)",
        "adapter_type": "rss",
        "config": {
            "url": f"file://{_FIXTURE_BASE}/shopify_rss.xml",
        },
    },
]


async def seed_sources() -> None:
    async with AsyncSessionLocal() as db:
        for source in SOURCES:
            import json
            await db.execute(
                text(
                    "INSERT INTO ingest_sources (id, name, adapter_type, config) "
                    "VALUES (gen_random_uuid(), :name, :adapter_type, :config) "
                    "ON CONFLICT DO NOTHING"
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
