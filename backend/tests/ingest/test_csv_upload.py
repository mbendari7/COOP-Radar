"""Tests for CSV upload and manual posting entry endpoints."""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ingest"


async def _login(client: AsyncClient, db: AsyncSession) -> str:
    """Register and login a user; return session cookie value."""
    await client.post(
        "/api/auth/register",
        json={"email": "csv_user@example.com", "password": "TestPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "csv_user@example.com", "password": "TestPass123!"},
    )
    assert resp.status_code == 200
    return resp.cookies.get("session", "")


@pytest.mark.asyncio
async def test_valid_csv_adds_five_postings(client: AsyncClient, db_session: AsyncSession):
    """Uploading valid 5-row CSV adds 5 postings."""
    session_token = await _login(client, db_session)
    csv_content = (FIXTURE_DIR / "sample_postings.csv").read_bytes()

    resp = await client.post(
        "/api/postings/upload",
        files={"file": ("sample.csv", io.BytesIO(csv_content), "text/csv")},
        cookies={"session": session_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["added"] == 5
    assert body["skipped_duplicates"] == 0
    assert body["errors"] == []


@pytest.mark.asyncio
async def test_csv_with_error_row(client: AsyncClient, db_session: AsyncSession):
    """CSV with one invalid deadline: 4 added, 1 error on line 4 (3rd data row; header is line 1)."""
    session_token = await _login(client, db_session)
    csv_content = (FIXTURE_DIR / "sample_postings_with_error.csv").read_bytes()

    resp = await client.post(
        "/api/postings/upload",
        files={"file": ("err.csv", io.BytesIO(csv_content), "text/csv")},
        cookies={"session": session_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["added"] == 4
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 4
    assert body["errors"][0]["column"] == "deadline"


@pytest.mark.asyncio
async def test_duplicate_csv_skips_all(client: AsyncClient, db_session: AsyncSession):
    """Uploading the same CSV twice: second upload skips all 5 as duplicates."""
    session_token = await _login(client, db_session)
    csv_content = (FIXTURE_DIR / "sample_postings.csv").read_bytes()

    await client.post(
        "/api/postings/upload",
        files={"file": ("s.csv", io.BytesIO(csv_content), "text/csv")},
        cookies={"session": session_token},
    )
    resp = await client.post(
        "/api/postings/upload",
        files={"file": ("s2.csv", io.BytesIO(csv_content), "text/csv")},
        cookies={"session": session_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["added"] == 0
    assert body["skipped_duplicates"] == 5


@pytest.mark.asyncio
async def test_oversized_csv_returns_413(client: AsyncClient, db_session: AsyncSession):
    """CSV with more than 1,000 rows returns 413 FILE_TOO_LARGE."""
    session_token = await _login(client, db_session)

    # Build a CSV with 1001 data rows
    header = "title,company,city,term,deadline\n"
    rows = "".join(
        f"Job {i},Corp {i},Toronto,Summer 2027,2027-03-01\n" for i in range(1001)
    )
    big_csv = (header + rows).encode()

    resp = await client.post(
        "/api/postings/upload",
        files={"file": ("big.csv", io.BytesIO(big_csv), "text/csv")},
        cookies={"session": session_token},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_rate_limit_on_fourth_upload(client: AsyncClient, db_session: AsyncSession):
    """4th CSV upload within the rate window returns 429 RATE_LIMITED."""
    session_token = await _login(client, db_session)
    csv_content = (FIXTURE_DIR / "sample_postings.csv").read_bytes()

    for _ in range(3):
        await client.post(
            "/api/postings/upload",
            files={"file": ("f.csv", io.BytesIO(csv_content), "text/csv")},
            cookies={"session": session_token},
        )

    resp = await client.post(
        "/api/postings/upload",
        files={"file": ("f4.csv", io.BytesIO(csv_content), "text/csv")},
        cookies={"session": session_token},
    )
    assert resp.status_code == 429
    assert resp.json()["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_manual_entry_returns_201(client: AsyncClient, db_session: AsyncSession):
    """Manual posting entry returns 201 with the new posting."""
    session_token = await _login(client, db_session)

    resp = await client.post(
        "/api/postings",
        json={
            "title": "Firmware Co-op",
            "company": "StartupCo",
            "city": "Waterloo",
            "term": "Summer 2027",
            "deadline": "2027-03-15",
        },
        cookies={"session": session_token},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Firmware Co-op"


@pytest.mark.asyncio
async def test_manual_duplicate_returns_409(client: AsyncClient, db_session: AsyncSession):
    """Submitting the same manual posting twice returns 409 DUPLICATE."""
    session_token = await _login(client, db_session)
    payload = {
        "title": "Duplicate Job Co-op",
        "company": "DupCo",
        "city": "Ottawa",
        "term": "Fall 2027",
        "deadline": "2027-07-01",
    }

    resp1 = await client.post("/api/postings", json=payload, cookies={"session": session_token})
    assert resp1.status_code == 201

    resp2 = await client.post("/api/postings", json=payload, cookies={"session": session_token})
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "DUPLICATE"


@pytest.mark.asyncio
async def test_manual_entry_is_committed_and_queued_for_embedding(
    client: AsyncClient, db_session: AsyncSession, fake_queue, monkeypatch
):
    """create_manual used to flush without committing, so postings vanished."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "openai_api_key", "sk-owner")  # smart search on
    session_token = await _login(client, db_session)

    resp = await client.post(
        "/api/postings",
        json={"title": "Persisted Co-op", "company": "KeepCo", "city": "Guelph",
              "term": "Fall 2027", "deadline": "2027-07-01"},
        cookies={"session": session_token},
    )
    posting_id = resp.json()["id"]

    detail = await client.get(f"/api/postings/{posting_id}")
    assert detail.status_code == 200
    fake_queue.enqueue.assert_called_with("app.ingest.embed.run_embed_job", posting_id)


@pytest.mark.asyncio
async def test_no_embedding_jobs_without_openai_key(
    client: AsyncClient, db_session: AsyncSession, fake_queue, monkeypatch
):
    """With smart search off, nothing is queued (failing jobs would pile up in Redis)."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "openai_api_key", "")
    session_token = await _login(client, db_session)
    resp = await client.post(
        "/api/postings",
        json={"title": "No Vector Co-op", "company": "PlainCo", "city": "Guelph",
              "term": "Fall 2027", "deadline": "2027-07-01"},
        cookies={"session": session_token},
    )
    assert resp.status_code == 201
    fake_queue.enqueue.assert_not_called()
