"""
Tests for the saved jobs endpoints.

These need a job to save, so a fixture makes one, and they use
the in memory store from conftest.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode


@pytest.fixture
async def posting(db_session: AsyncSession) -> Posting:
    """Make a small job to save in tests."""
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
async def saved_client(client: AsyncClient, posting: Posting) -> AsyncClient:
    """A signed in client. Signs up a user and plugs in the fake store."""

    await client.post(
        "/api/auth/register",
        json={"email": "saver@example.com", "password": "password1234"},
    )
    return client


# Tests

async def test_list_saved_unauthenticated_returns_401(client: AsyncClient):
    """GET /api/saved with no cookie answers 401."""

    res = await client.get("/api/saved")
    assert res.status_code == 401


async def test_save_posting_returns_201(saved_client: AsyncClient, posting: Posting):
    """Saving a job the first time answers 201."""
    res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    assert res.status_code == 201
    data = res.json()
    assert data["posting"]["id"] == str(posting.id)
    assert data["status"] is None


async def test_save_posting_idempotent_returns_200(saved_client: AsyncClient, posting: Posting):
    """Saving the same job twice answers 200 the second time."""
    await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    assert res.status_code == 200


async def test_list_saved_returns_saved_posting(saved_client: AsyncClient, posting: Posting):
    """After saving, GET /api/saved gives back the job."""
    await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    res = await saved_client.get("/api/saved")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["posting"]["id"] == str(posting.id)


async def test_unsave_returns_204_and_removes(saved_client: AsyncClient, posting: Posting):
    """Unsaving a job takes it off the saved list."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    del_res = await saved_client.delete(f"/api/saved/{saved_id}")
    assert del_res.status_code == 204

    list_res = await saved_client.get("/api/saved")
    assert list_res.json()["total"] == 0


async def test_update_status(saved_client: AsyncClient, posting: Posting):
    """PATCH /api/saved/{id}/status changes the status."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    patch_res = await saved_client.patch(
        f"/api/saved/{saved_id}/status",
        json={"status": "applied"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["status"] == "applied"
    # A status change event should be logged
    assert len(data["events"]) == 1
    assert data["events"][0]["status"] == "applied"


async def test_update_status_clear_to_null(saved_client: AsyncClient, posting: Posting):
    """Setting the status to null clears it."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    await saved_client.patch(f"/api/saved/{saved_id}/status", json={"status": "applied"})
    res = await saved_client.patch(f"/api/saved/{saved_id}/status", json={"status": None})
    assert res.status_code == 200
    assert res.json()["status"] is None


async def test_status_counts_in_list_response(saved_client: AsyncClient, posting: Posting):
    """GET /api/saved includes status_counts and the stats summary."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]
    await saved_client.patch(f"/api/saved/{saved_id}/status", json={"status": "applied"})

    res = await saved_client.get("/api/saved")
    data = res.json()
    counts = data["status_counts"]
    assert counts["applied"] == 1
    assert counts["none"] == 0
    assert data["total_applied"] == 1
    assert "deadlines_this_week" in data


async def test_add_event_with_notes(saved_client: AsyncClient, posting: Posting):
    """POST /api/saved/{id}/events logs a status change with notes."""
    save_res = await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})
    saved_id = save_res.json()["id"]

    res = await saved_client.post(
        f"/api/saved/{saved_id}/events",
        json={"status": "interview", "notes": "Phone screen scheduled", "event_date": "2027-02-01"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "interview"
    assert data["events"][0]["notes"] == "Phone screen scheduled"
    assert data["events"][0]["event_date"] == "2027-02-01"


async def test_export_csv_downloads_tracker(saved_client: AsyncClient, posting: Posting):
    """CSV export used to crash calling .date() on a DATE column."""
    await saved_client.post("/api/saved", json={"posting_id": str(posting.id)})

    res = await saved_client.get("/api/saved/export/csv")

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    lines = res.text.strip().splitlines()
    assert lines[0].startswith("Title,Company")
    assert "2027-03-01" in lines[1]


async def test_deadlines_this_week_includes_postings_without_status(
    saved_client: AsyncClient, db_session: AsyncSession
):
    """A NULL status has to count as still open. NULL NOT IN (...) used to drop it."""
    from datetime import date, timedelta

    soon = Posting(
        title="Due Soon", company="Acme Inc", city="Toronto", province="ON",
        work_mode=WorkMode.onsite, term="Winter 2027", duration_months=4,
        deadline=date.today() + timedelta(days=2), description="d", skills=[],
    )
    db_session.add(soon)
    await db_session.flush()
    await saved_client.post("/api/saved", json={"posting_id": str(soon.id)})

    data = (await saved_client.get("/api/saved")).json()

    assert [d["title"] for d in data["deadlines_this_week"]] == ["Due Soon"]
