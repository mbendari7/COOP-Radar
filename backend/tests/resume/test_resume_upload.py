"""
Tests for resume upload, match pipeline, stored results, and delete endpoints.
Covers US1 (upload + match), US3 (view metadata, delete, cross-user isolation).
All Anthropic and OpenAI calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client: AsyncClient, email: str) -> None:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password1!"},
    )
    await client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password1!"},
    )


def _make_mock_haiku_response(n: int = 5) -> MagicMock:
    """Return a mocked Anthropic message with JSON rankings."""
    import json

    items = [
        {"posting_id": str(uuid4()), "score": 90 - i * 5, "reason": f"Good match reason {i}."}
        for i in range(n)
    ]
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(items))]
    return msg


def _mock_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch generate_embedding to return a deterministic 1536-dim vector."""
    monkeypatch.setattr(
        "app.ingest.embed.generate_embedding",
        AsyncMock(return_value=[0.1] * 1536),
    )


def _mock_anthropic(monkeypatch: pytest.MonkeyPatch, n: int = 5) -> None:
    """Patch Anthropic client.messages.create to return fake rankings."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_make_mock_haiku_response(n))
    monkeypatch.setattr(
        "anthropic.AsyncAnthropic",
        MagicMock(return_value=mock_client),
    )


# ---------------------------------------------------------------------------
# US1: Upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf_happy_path(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_embed(monkeypatch)
    _mock_anthropic(monkeypatch)

    await _register_and_login(client, "upload_pdf@test.com")

    resp = await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "resume" in data
    assert data["resume"]["filename"] == "resume.pdf"
    assert isinstance(data["matches"], list)


@pytest.mark.asyncio
async def test_upload_docx_happy_path(
    client: AsyncClient,
    sample_docx_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_embed(monkeypatch)
    _mock_anthropic(monkeypatch)

    await _register_and_login(client, "upload_docx@test.com")

    resp = await client.post(
        "/api/resume",
        files={"file": ("resume.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200
    assert resp.json()["resume"]["filename"] == "resume.docx"


@pytest.mark.asyncio
async def test_upload_invalid_file_type(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _register_and_login(client, "upload_invalid@test.com")

    resp = await client.post(
        "/api/resume",
        files={"file": ("image.png", b"PNGDATA", "image/png")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_file_too_large(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _register_and_login(client, "upload_large@test.com")

    big_bytes = b"A" * (5 * 1024 * 1024 + 1)
    resp = await client.post(
        "/api/resume",
        files={"file": ("big.pdf", big_bytes, "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_upload_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", b"data", "application/pdf")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reupload_replaces_previous(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_embed(monkeypatch)
    _mock_anthropic(monkeypatch)

    await _register_and_login(client, "reupload@test.com")

    r1 = await client.post(
        "/api/resume",
        files={"file": ("v1.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert r1.status_code == 200
    id1 = r1.json()["resume"]["id"]

    r2 = await client.post(
        "/api/resume",
        files={"file": ("v2.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert r2.status_code == 200
    id2 = r2.json()["resume"]["id"]

    # Second upload produces a new resume row
    assert id1 != id2

    # GET /matches returns results for the new resume
    matches = await client.get("/api/resume/matches")
    assert matches.status_code == 200
    assert matches.json()["resume"]["id"] == id2


# ---------------------------------------------------------------------------
# US3: View and Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_resume_metadata(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_embed(monkeypatch)
    _mock_anthropic(monkeypatch)

    await _register_and_login(client, "get_meta@test.com")
    await client.post(
        "/api/resume",
        files={"file": ("myresume.pdf", sample_pdf_bytes, "application/pdf")},
    )

    resp = await client.get("/api/resume")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "myresume.pdf"
    assert data["file_size"] > 0
    assert "uploaded_at" in data


@pytest.mark.asyncio
async def test_get_resume_not_found(client: AsyncClient) -> None:
    await _register_and_login(client, "noresume@test.com")
    resp = await client.get("/api/resume")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RESUME_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_resume(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_embed(monkeypatch)
    _mock_anthropic(monkeypatch)

    await _register_and_login(client, "delete_test@test.com")
    await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
    )

    del_resp = await client.delete("/api/resume")
    assert del_resp.status_code == 204

    get_resp = await client.get("/api/resume")
    assert get_resp.status_code == 404

    matches_resp = await client.get("/api/resume/matches")
    assert matches_resp.status_code == 200
    assert matches_resp.json()["resume"] is None
    assert matches_resp.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_resume_not_found(client: AsyncClient) -> None:
    await _register_and_login(client, "delete_none@test.com")
    resp = await client.delete("/api/resume")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_isolation(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User B cannot see User A's resume."""
    _mock_embed(monkeypatch)
    _mock_anthropic(monkeypatch)

    # User A uploads
    await _register_and_login(client, "user_a@test.com")
    await client.post(
        "/api/resume",
        files={"file": ("a.pdf", sample_pdf_bytes, "application/pdf")},
    )

    # User B logs in (separate session via logout first)
    await client.post("/api/auth/logout")
    await _register_and_login(client, "user_b@test.com")

    resp = await client.get("/api/resume")
    assert resp.status_code == 404
