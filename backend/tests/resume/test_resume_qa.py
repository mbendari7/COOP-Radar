"""
Tests for the streaming Q&A endpoint.
Anthropic streaming is mocked; no live API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def _setup_user_with_resume(
    client: AsyncClient,
    email: str,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Register, log in, upload resume, and return a posting_id from matches."""
    import json
    from unittest.mock import AsyncMock, MagicMock

    posting_id = str(uuid4())

    monkeypatch.setattr(
        "app.ingest.embed.generate_embedding",
        AsyncMock(return_value=[0.1] * 1536),
    )

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps([
        {"posting_id": posting_id, "score": 85, "reason": "Strong Python match."}
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_msg)
    monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=mock_client))

    await client.post("/api/auth/register", json={"email": email, "password": "Password1!"})
    await client.post("/api/auth/login", json={"email": email, "password": "Password1!"})
    await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
    )
    return posting_id


def _mock_streaming_anthropic(monkeypatch: pytest.MonkeyPatch, response_text: str) -> None:
    """Mock Anthropic streaming to yield characters from response_text."""

    async def fake_text_stream():  # type: ignore[return]
        for char in response_text:
            yield char

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_stream_ctx.text_stream = fake_text_stream()

    mock_client = MagicMock()
    mock_client.messages.stream = MagicMock(return_value=mock_stream_ctx)
    monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=mock_client))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_streams_response(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posting_id = await _setup_user_with_resume(
        client, "qa_happy@test.com", sample_pdf_bytes, monkeypatch
    )

    response_text = "Resume: Python projects listed. Posting: requires Python."
    _mock_streaming_anthropic(monkeypatch, response_text)

    resp = await client.post(
        f"/api/resume/matches/{posting_id}/ask",
        json={"question": "What Python skills match?"},
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    body = resp.text
    assert "data: " in body
    assert "[DONE]" in body
    # Response includes some content
    assert any(c in body for c in ("Resume", "Posting", "python", "Python", "match"))


@pytest.mark.asyncio
async def test_ask_dont_know_response(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posting_id = await _setup_user_with_resume(
        client, "qa_dontknow@test.com", sample_pdf_bytes, monkeypatch
    )

    _mock_streaming_anthropic(
        monkeypatch,
        "I don't have enough information to answer that.",
    )

    resp = await client.post(
        f"/api/resume/matches/{posting_id}/ask",
        json={"question": "What is the company's GPA requirement?"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "don't have enough information" in body


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_no_resume_returns_404(client: AsyncClient) -> None:
    await client.post("/api/auth/register", json={"email": "qa_noresume@test.com", "password": "Password1!"})
    await client.post("/api/auth/login", json={"email": "qa_noresume@test.com", "password": "Password1!"})

    resp = await client.post(
        f"/api/resume/matches/{uuid4()}/ask",
        json={"question": "anything"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "RESUME_NOT_FOUND"


@pytest.mark.asyncio
async def test_ask_wrong_posting_returns_404(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _setup_user_with_resume(
        client, "qa_wrongposting@test.com", sample_pdf_bytes, monkeypatch
    )

    _mock_streaming_anthropic(monkeypatch, "some answer")

    resp = await client.post(
        f"/api/resume/matches/{uuid4()}/ask",
        json={"question": "any question"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "MATCH_NOT_FOUND"


@pytest.mark.asyncio
async def test_ask_empty_question_returns_400(
    client: AsyncClient,
    sample_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posting_id = await _setup_user_with_resume(
        client, "qa_empty@test.com", sample_pdf_bytes, monkeypatch
    )

    resp = await client.post(
        f"/api/resume/matches/{posting_id}/ask",
        json={"question": "   "},
    )
    assert resp.status_code == 422  # Pydantic validation error
