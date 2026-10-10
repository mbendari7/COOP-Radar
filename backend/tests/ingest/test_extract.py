"""Tests for extract_fields — skill extraction with regex and LLM fallback."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.extract import extract_fields


async def _seed_skills(db: AsyncSession) -> None:
    """Seed a few skills into the DB for testing."""
    from sqlalchemy import text
    skills = [
        ("Python", ["py", "python3"], "Language"),
        ("C", ["c programming"], "Language"),
        ("Embedded Systems", ["embedded"], "Domain"),
    ]
    for name, aliases, category in skills:
        await db.execute(
            text(
                "INSERT INTO skills (id, name, aliases, category) "
                "VALUES (gen_random_uuid(), :name, :aliases, :category) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "aliases": aliases, "category": category},
        )
    await db.flush()


@pytest.mark.asyncio
async def test_known_skill_extracted(db_session: AsyncSession):
    """Text mentioning 'Python developer' → skills contains 'Python'."""
    await _seed_skills(db_session)
    result = await extract_fields(db_session, "We need a Python developer for our backend team.")
    assert "Python" in result.skills


@pytest.mark.asyncio
async def test_work_mode_extraction(db_session: AsyncSession):
    """Text mentioning 'remote position' → work_mode='remote'."""
    await _seed_skills(db_session)
    result = await extract_fields(db_session, "This is a remote position suitable for students.")
    assert result.work_mode == "remote"


@pytest.mark.asyncio
async def test_llm_fallback_triggered(db_session: AsyncSession):
    """Text with no taxonomy matches and low confidence triggers LLM fallback."""
    await _seed_skills(db_session)

    mock_response = AsyncMock()
    mock_response.content = [AsyncMock(text='{"work_mode": "hybrid", "skills": ["Python"], "term": null, "duration_months": null}')]

    with patch("app.ingest.extract._llm_extract", new=AsyncMock(return_value={
        "work_mode": "hybrid",
        "skills": ["Python"],
        "term": None,
        "duration_months": None,
    })) as mock_llm:
        # Use text with no clear signals to trigger low confidence
        result = await extract_fields(db_session, "Unique role with specialized responsibilities in niche domain.")
        # Verify LLM was called (confidence < 0.6)
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_term_extraction(db_session: AsyncSession):
    """Text mentioning 'Summer 2027' → term='Summer 2027'."""
    await _seed_skills(db_session)
    result = await extract_fields(db_session, "Join us for a Summer 2027 co-op position.")
    assert result.term == "Summer 2027"
