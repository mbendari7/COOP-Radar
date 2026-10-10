"""
Tests for saved postings endpoints.

These tests require a seeded posting to save.  We create one in a fixture
and use the same MockRedis pattern as test_auth.py.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from app.redis import get_redis
from tests.api.test_auth import MockRedis


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
async def posting(db_session: AsyncSession) -> Posting:
    """Create a minimal posting to save in tests."""
    from datetime import date, datetime
    p = Posting(
        title="Test Co-op",
        company="Acme Inc",
        city="Waterloo",
        province="ON",
        work_mode=WorkMode.hybrid,
        term="Summer 2027",
        duration_months=4,
        deadline=date(2027, 3, 1),
        posted_at=datetime(2026, 10, 1, 12, 0, 0),
        description="A test posting for automated tests.",
        skills=["Python"],
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def saved_client(client: AsyncClient, mock_redis: MockRedis, posting: Posting) -> AsyncClient:
    """Authenticated client — registers a user and injects mock Redis."""
    app = client._transport.app  # type: ignore[attr-defined]

    async def override_redis(request=None):
        yield mock_redis

    app.dependency_overrides[get_redis] = override_redis
    app.state.redis = mock_redis

    await client.post(
        "/api/auth/register",
        json={"email": "saver@example.com", "password": "password1234"},
    )
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_list_saved_unauthenticated_returns_401(client: AsyncClient, mock_redis: MockRedis):
    """GET /api/saved without cookie returns 401."""
    app = client._transport.app  # type: ignore[attr-defined]

    async def override_redis(request=None):
        yield mock_redis

    app.dependency_overrides[get_redis] = override_redis
    app.state.redis = mock_redis

    res = await client.get("/api/saved")
    assert res.status_code == 401


async def test_save_posting_returns_201(saved_client: AsyncClient, posting: Posting):
    """Saving a posting for the first time returns 201."""
    res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    assert res.status_code == 201
    data = res.json()
    assert data["posting"]["id"] == str(posting.id)
    assert data["status"] is None


async def test_save_posting_idempotent_returns_200(saved_client: AsyncClient, posting: Posting):
    """Saving the same posting twice returns 200 on the second call (FR-007)."""
    await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    assert res.status_code == 200


async def test_list_saved_returns_saved_posting(saved_client: AsyncClient, posting: Posting):
    """After saving, GET /api/saved returns the posting."""
    await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    res = await saved_client.get("/api/saved")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["posting"]["id"] == str(posting.id)


async def test_unsave_returns_204_and_removes(saved_client: AsyncClient, posting: Posting):
    """Unsaving a posting removes it from the saved list."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    del_res = await saved_client.delete(f"/api/saved/{saved_id}")
    assert del_res.status_code == 204

    list_res = await saved_client.get("/api/saved")
    assert list_res.json()["total"] == 0


async def test_update_status(saved_client: AsyncClient, posting: Posting):
    """PATCH /api/saved/{id}/status updates the status field."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    patch_res = await saved_client.patch(
        f"/api/saved/{saved_id}/status",
        json={"status": "applied"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "applied"


async def test_update_status_clear_to_null(saved_client: AsyncClient, posting: Posting):
    """Setting status to null clears it."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    await saved_client.patch(f"/api/saved/{saved_id}/status", json={"status": "applied"})
    res = await saved_client.patch(f"/api/saved/{saved_id}/status", json={"status": None})
    assert res.status_code == 200
    assert res.json()["status"] is None


async def test_status_counts_in_list_response(saved_client: AsyncClient, posting: Posting):
    """GET /api/saved includes status_counts summary."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]
    await saved_client.patch(f"/api/saved/{saved_id}/status", json={"status": "applied"})

    res = await saved_client.get("/api/saved")
    counts = res.json()["status_counts"]
    assert counts["applied"] == 1
    assert counts["none"] == 0
