"""
Performance test — asserts that GET /api/postings p95 latency stays under
300 ms when the table has 10,000 rows (Constitution III).

Run separately from the main test suite:
    pytest -q -m perf

Excluded from CI default run (pytest -m "not perf") because it inserts 10k rows
and takes ~10 seconds, which would slow down the fast feedback loop.
"""

import statistics
import time
from datetime import UTC, date, datetime, timedelta
from random import choice, randint, sample

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import create_app
from app.models.posting import Posting, WorkMode
from tests.conftest import MockRedis, get_test_db_url

# Skill pool for random assignment
SKILLS = ["Python", "Java", "Go", "TypeScript", "React", "SQL", "Docker", "AWS",
          "Kubernetes", "C++", "Rust", "PostgreSQL", "Redis", "Node.js", "Django"]

CITIES = ["Toronto", "Waterloo", "Ottawa", "Vancouver", "Hamilton", "Guelph"]
TERMS  = ["Summer 2027", "Winter 2027", "Fall 2027"]


PERF_PREFIX = "Perf Co-op Role #"

QUERIES = [
    "/api/postings",
    "/api/postings?q=python&city=Waterloo&page_size=25",
    "/api/postings?skills=Python&skills=Docker&sort=deadline&order=asc",
    "/api/postings?term=Summer%202027&work_mode=remote&page=3&page_size=50",
    "/api/postings?q=developer&duration=4&duration=8&sort=company",
]


def make_bulk_posting(i: int) -> Posting:
    return Posting(
        title=f"{PERF_PREFIX}{i}",
        company=f"Company {i % 50}",
        city=choice(CITIES),
        province="ON",
        work_mode=choice(list(WorkMode)),
        term=choice(TERMS),
        duration_months=choice([4, 8, 12, 16]),
        deadline=date.today() + timedelta(days=randint(10, 300)),
        posted_at=datetime.now(tz=UTC),
        description=f"Description for role {i}. " * 10,
        skills=sample(SKILLS, k=randint(2, 5)),
        source_url=None,
    )


@pytest.mark.perf
async def test_list_postings_p95_under_300ms(db_engine) -> None:  # type: ignore[no-untyped-def]
    """
    Insert 10,000 postings into the TEST database, time 100 list/search requests,
    assert p95 <= 300 ms. Only the rows it inserted are deleted afterwards, and it
    never touches the dev database (it uses TEST_DATABASE_URL / DATABASE_URL like
    the rest of the suite — point those at a throwaway DB).
    """
    engine = create_async_engine(get_test_db_url(), echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all([make_bulk_posting(i) for i in range(10_000)])
        await session.commit()
        await session.execute(text("ANALYZE postings"))  # fresh planner stats, like production

    app = create_app()
    app.state.redis = MockRedis()  # lifespan doesn't run under ASGITransport
    latencies: list[float] = []

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Warm up (first requests pay for connection setup and query planning)
            for url in QUERIES:
                await client.get(url)

            # Measure per-request latency (the constitution's budget) across a mix of
            # realistic list/search queries. Requests run one at a time: firing many
            # concurrently into a single in-process app measures event-loop throughput,
            # not the latency a user sees.
            for i in range(100):
                url = QUERIES[i % len(QUERIES)]
                start = time.perf_counter()
                resp = await client.get(url)
                latencies.append((time.perf_counter() - start) * 1000)  # ms
                assert resp.status_code == 200
    finally:
        async with session_factory() as session:
            await session.execute(delete(Posting).where(Posting.title.startswith(PERF_PREFIX)))
            await session.commit()
        await engine.dispose()

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"\nPerf: p50={statistics.median(latencies):.0f}ms  p95={p95:.0f}ms  max={max(latencies):.0f}ms")

    assert p95 < 300, f"p95 latency {p95:.0f}ms exceeds 300ms budget"
