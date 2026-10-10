"""
Performance test — asserts that GET /api/postings p95 latency stays under
300 ms when the table has 10,000 rows (Constitution III).

Run separately from the main test suite:
    pytest -q -m perf

Excluded from CI default run (pytest -m "not perf") because it inserts 10k rows
and takes ~10 seconds, which would slow down the fast feedback loop.
"""

import asyncio
import statistics
import time
from datetime import date, datetime, timezone, timedelta
from random import choice, randint, sample

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db import Base
from app.main import create_app
from app.models.posting import Posting, WorkMode

# Skill pool for random assignment
SKILLS = ["Python", "Java", "Go", "TypeScript", "React", "SQL", "Docker", "AWS",
          "Kubernetes", "C++", "Rust", "PostgreSQL", "Redis", "Node.js", "Django"]

CITIES = ["Toronto", "Waterloo", "Ottawa", "Vancouver", "Hamilton", "Guelph"]
TERMS  = ["Summer 2027", "Winter 2027", "Fall 2027"]


def make_bulk_posting(i: int) -> Posting:
    return Posting(
        title=f"Co-op Role #{i}",
        company=f"Company {i % 50}",
        city=choice(CITIES),
        province="ON",
        work_mode=choice(list(WorkMode)),
        term=choice(TERMS),
        duration_months=choice([4, 8, 12, 16]),
        deadline=date.today() + timedelta(days=randint(10, 300)),
        posted_at=datetime.now(tz=timezone.utc),
        description=f"Description for role {i}. " * 10,
        skills=sample(SKILLS, k=randint(2, 5)),
        source_url=None,
    )


@pytest.mark.perf
async def test_list_postings_p95_under_300ms() -> None:
    """
    Insert 10,000 postings, fire 50 concurrent requests, assert p95 ≤ 300 ms.
    Uses a dedicated perf engine separate from the test fixture to avoid
    interfering with regular test isolation.
    """
    url = get_settings().database_url
    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    # Set up schema and insert bulk data
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await session.execute(text("DELETE FROM postings"))
        for i in range(10_000):
            session.add(make_bulk_posting(i))
        await session.commit()

    app = create_app()
    latencies: list[float] = []

    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        # Run 50 concurrent requests — simulates moderate concurrent load
        async def one_request() -> None:
            start = time.perf_counter()
            resp = await client.get("/api/postings?q=python&city=Waterloo&page_size=25")
            elapsed = (time.perf_counter() - start) * 1000  # ms
            assert resp.status_code == 200
            latencies.append(elapsed)

        await asyncio.gather(*[one_request() for _ in range(50)])

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"\nPerf: p50={statistics.median(latencies):.0f}ms  p95={p95:.0f}ms  max={max(latencies):.0f}ms")

    assert p95 < 300, f"p95 latency {p95:.0f}ms exceeds 300ms budget"

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
