"""
Real employers whose public career boards CoopRadar imports from (Greenhouse, Lever, Ashby).

Each board's public API is meant for showing that company's jobs elsewhere; every posting
links back to the employer's own page to apply. All of these had jobs located in Canada when
added (2026-10-11). Add a company by appending (company, adapter_type, board) — the board name
is the last part of its careers URL, e.g. boards.greenhouse.io/<board>, jobs.lever.co/<board>,
jobs.ashbyhq.com/<board>. Admins can pause or re-enable any source on the Admin page.
"""

import asyncio
import json

from sqlalchemy import text

from app.db import AsyncSessionLocal

JOB_BOARDS: list[tuple[str, str, str]] = [
    # (company display name, adapter_type, board name)
    ("Stripe", "greenhouse", "stripe"),
    ("Robinhood", "greenhouse", "robinhood"),
    ("Databricks", "greenhouse", "databricks"),
    ("Instacart", "greenhouse", "instacart"),
    ("Samsara", "greenhouse", "samsara"),
    ("Affirm", "greenhouse", "affirm"),
    ("Asana", "greenhouse", "asana"),
    ("Faire", "greenhouse", "faire"),
    ("Geotab", "greenhouse", "geotab"),
    ("D2L", "greenhouse", "d2l"),
    ("Hootsuite", "greenhouse", "hootsuite"),
    ("Lyft", "greenhouse", "lyft"),          # Toronto office, many summer interns
    ("Pinterest", "greenhouse", "pinterest"),  # Toronto interns
    ("Okta", "greenhouse", "okta"),
    ("Reddit", "greenhouse", "reddit"),
    ("Flipp", "greenhouse", "flipp"),
    ("Wattpad", "lever", "wattpad"),
    ("Float", "ashby", "float"),
    ("Cohere", "ashby", "cohere"),
    ("Wealthsimple", "ashby", "wealthsimple"),
    ("1Password", "ashby", "1password"),
    ("Lightspeed", "ashby", "lightspeedhq"),
    ("Jobber", "ashby", "jobber"),
    ("Miovision", "ashby", "miovision"),
    ("Benevity", "ashby", "benevity"),
    ("Trulioo", "ashby", "trulioo"),
    ("Thinkific", "ashby", "thinkific"),
]


async def seed_job_boards() -> None:
    """Insert one ingest source per board, skipping names that already exist (idempotent)."""
    async with AsyncSessionLocal() as db:
        for company, adapter_type, board in JOB_BOARDS:
            await db.execute(
                text(
                    "INSERT INTO ingest_sources (id, name, adapter_type, config) "
                    "SELECT gen_random_uuid(), :name, :adapter_type, CAST(:config AS jsonb) "
                    "WHERE NOT EXISTS (SELECT 1 FROM ingest_sources WHERE name = :name)"
                ),
                {
                    "name": f"{company} careers",
                    "adapter_type": adapter_type,
                    "config": json.dumps({"board": board, "company": company}),
                },
            )
        await db.commit()
    print(f"Seeded {len(JOB_BOARDS)} employer career boards.")


if __name__ == "__main__":
    asyncio.run(seed_job_boards())
