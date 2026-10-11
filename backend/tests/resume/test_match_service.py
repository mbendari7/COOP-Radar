"""
Unit tests for text extraction and match service functions.
No database or live API calls required.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.resume import extract_docx_text, extract_pdf_text, extract_text


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def test_extract_pdf_text(sample_pdf_bytes: bytes) -> None:
    text = extract_pdf_text(sample_pdf_bytes)
    assert len(text) > 0
    # Our fixture embeds these keywords
    assert any(kw in text for kw in ("Python", "Django", "PostgreSQL", "python", "django"))


def test_extract_docx_text(sample_docx_bytes: bytes) -> None:
    text = extract_docx_text(sample_docx_bytes)
    assert len(text) > 0
    assert any(kw in text for kw in ("Python", "React", "python", "react"))


def test_extract_text_dispatches_pdf(sample_pdf_bytes: bytes) -> None:
    text = extract_text("myresume.PDF", sample_pdf_bytes)
    assert len(text) > 0


def test_extract_text_dispatches_docx(sample_docx_bytes: bytes) -> None:
    text = extract_text("resume.Docx", sample_docx_bytes)
    assert len(text) > 0


def test_extract_text_unsupported_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text("photo.png", b"PNGDATA")


def test_extract_text_no_extension_raises() -> None:
    with pytest.raises(ValueError):
        extract_text("resumenoext", b"data")


# ---------------------------------------------------------------------------
# embed_and_rank (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_and_rank_returns_top20(monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    from app.services.resume import embed_and_rank

    # Mock generate_embedding
    monkeypatch.setattr(
        "app.ingest.embed.generate_embedding",
        AsyncMock(return_value=[0.1] * 1536),
    )

    # Mock DB execute to return 40 candidate rows
    fake_rows = [
        {
            "id": uuid4(),
            "title": f"Dev Co-op {i}",
            "company": f"Company {i}",
            "city": "Toronto",
            "province": "ON",
            "term": "Winter 2027",
            "deadline": "2026-12-01",
            "description": f"We need Python and Django skills. Job {i}.",
        }
        for i in range(40)
    ]

    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = fake_rows

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Mock Anthropic to return scores for all 40
    haiku_items = [
        {"posting_id": str(r["id"]), "score": 90 - i, "reason": f"Reason {i}."}
        for i, r in enumerate(fake_rows)
    ]
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(haiku_items))]

    mock_anthropic_client = AsyncMock()
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_msg)
    monkeypatch.setattr(
        "anthropic.AsyncAnthropic",
        MagicMock(return_value=mock_anthropic_client),
    )

    results = await embed_and_rank(mock_db, "Python Django PostgreSQL developer")

    assert len(results) <= 20
    # Results sorted by score descending
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    # Each result has required fields
    for r in results:
        assert 0 <= r.score <= 100
        assert r.reason
        assert r.title


@pytest.mark.asyncio
async def test_embed_and_rank_empty_db(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.resume import embed_and_rank

    monkeypatch.setattr(
        "app.ingest.embed.generate_embedding",
        AsyncMock(return_value=[0.1] * 1536),
    )

    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await embed_and_rank(mock_db, "some resume text")
    assert results == []
