"""
Tests for the streaming Q&A endpoint.
Claude streaming and OpenAI embeddings are mocked; no live API calls.
"""

import json
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from app.models.posting_embedding import PostingEmbedding


async def _setup_user_with_match(
    client: AsyncClient,
    db_session: AsyncSession,
    email: str,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
) -> str:
    """Create an embedded posting, upload a resume that matches it, return the posting id."""
    posting = Posting(
        title="Python Developer Co-op",
        company="Acme",
        city="Toronto",
        province="ON",
        work_mode=WorkMode.hybrid,
        term="Summer 2027",
        duration_months=4,
        deadline=date.today() + timedelta(days=30),
        description="Requires Python, Django and PostgreSQL.",
        skills=["Python", "Django"],
    )
    db_session.add(posting)
    await db_session.flush()
    db_session.add(PostingEmbedding(posting_id=posting.id, embedding=[0.1] * 1536, model="test"))
    await db_session.flush()

    mock_claude_create(
        json.dumps([{"posting_id": str(posting.id), "score": 85, "reason": "Strong Python match."}])
    )
    await client.post("/api/auth/register", json={"email": email, "password": "Password1!"})
    upload = await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 200
    assert [m["posting_id"] for m in upload.json()["matches"]] == [str(posting.id)]
    return str(posting.id)


def _deltas(body: str) -> str:
    """Join the delta payloads of an SSE body."""
    out = []
    for line in body.splitlines():
        if line.startswith("data: ") and "[DONE]" not in line:
            out.append(json.loads(line[6:]).get("delta", ""))
    return "".join(out)


async def test_ask_streams_response(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_embedding: AsyncMock,
    mock_claude_create: Callable[[str], AsyncMock],
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    posting_id = await _setup_user_with_match(
        client, db_session, "qa_happy@test.com", sample_pdf_bytes, mock_claude_create
    )
    response_text = "Resume: Python projects listed. Posting: requires Python."
    stream = mock_claude_stream(response_text)

    resp = await client.post(
        f"/api/resume/matches/{posting_id}/ask",
        json={"question": "What Python skills match?"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert resp.text.rstrip().endswith("data: [DONE]")
    assert _deltas(resp.text) == response_text

    # The posting description and resume text are both sent as context
    kwargs: dict[str, Any] = stream.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    assert "Requires Python, Django and PostgreSQL." in user_content
    assert "<resume>" in user_content


async def test_ask_dont_know_response(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_embedding: AsyncMock,
    mock_claude_create: Callable[[str], AsyncMock],
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    posting_id = await _setup_user_with_match(
        client, db_session, "qa_dontknow@test.com", sample_pdf_bytes, mock_claude_create
    )
    mock_claude_stream("I don't have enough information to answer that.")

    resp = await client.post(
        f"/api/resume/matches/{posting_id}/ask",
        json={"question": "What is the company's GPA requirement?"},
    )
    assert resp.status_code == 200
    assert _deltas(resp.text) == "I don't have enough information to answer that."


async def test_ask_refusal_is_reported(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_embedding: AsyncMock,
    mock_claude_create: Callable[[str], AsyncMock],
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    posting_id = await _setup_user_with_match(
        client, db_session, "qa_refusal@test.com", sample_pdf_bytes, mock_claude_create
    )
    mock_claude_stream("", stop_reason="refusal")

    resp = await client.post(
        f"/api/resume/matches/{posting_id}/ask",
        json={"question": "anything"},
    )
    assert resp.status_code == 200
    assert "can't help" in _deltas(resp.text)


async def test_ask_no_resume_returns_404(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register", json={"email": "qa_noresume@test.com", "password": "Password1!"}
    )

    resp = await client.post(f"/api/resume/matches/{uuid4()}/ask", json={"question": "anything"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "RESUME_NOT_FOUND"


async def test_ask_wrong_posting_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_embedding: AsyncMock,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    await _setup_user_with_match(
        client, db_session, "qa_wrongposting@test.com", sample_pdf_bytes, mock_claude_create
    )

    resp = await client.post(f"/api/resume/matches/{uuid4()}/ask", json={"question": "any question"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "MATCH_NOT_FOUND"


async def test_ask_empty_question_returns_422(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_embedding: AsyncMock,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    posting_id = await _setup_user_with_match(
        client, db_session, "qa_empty@test.com", sample_pdf_bytes, mock_claude_create
    )

    resp = await client.post(f"/api/resume/matches/{posting_id}/ask", json={"question": "   "})
    assert resp.status_code == 422
