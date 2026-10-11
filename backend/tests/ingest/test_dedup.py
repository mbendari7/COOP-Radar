"""Tests for duplicate_exists — same company + city and a near-identical title."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.dedup import duplicate_exists


@pytest.mark.asyncio
async def test_exact_match_is_duplicate(db_session: AsyncSession):
    """An exact title/company/city match is detected as a duplicate."""
    # Insert a posting
    from sqlalchemy import text
    await db_session.execute(
        text(
            "INSERT INTO postings (id, title, company, city, province, work_mode, "
            "term, duration_months, deadline, description, skills, low_confidence_fields) "
            "VALUES (gen_random_uuid(), :title, :company, :city, 'ON', 'onsite', "
            "'Summer 2027', 4, '2027-03-01', '', '{}', '{}')"
        ),
        {"title": "Backend Developer Co-op", "company": "Acme Corp", "city": "Waterloo"},
    )
    await db_session.flush()

    result = await duplicate_exists(db_session, "Acme Corp", "Backend Developer Co-op", "Waterloo")
    assert result is True


@pytest.mark.asyncio
async def test_near_duplicate_title_is_duplicate(db_session: AsyncSession):
    """A title with >85% Levenshtein similarity to an existing one is a duplicate."""
    from sqlalchemy import text
    await db_session.execute(
        text(
            "INSERT INTO postings (id, title, company, city, province, work_mode, "
            "term, duration_months, deadline, description, skills, low_confidence_fields) "
            "VALUES (gen_random_uuid(), :title, :company, :city, 'ON', 'onsite', "
            "'Summer 2027', 4, '2027-03-01', '', '{}', '{}')"
        ),
        {"title": "Frontend React Developer", "company": "TechCo", "city": "Toronto"},
    )
    await db_session.flush()

    # Slightly different title — should still be caught
    result = await duplicate_exists(db_session, "TechCo", "Frontend React Develoer", "Toronto")
    assert result is True


@pytest.mark.asyncio
async def test_different_city_not_duplicate(db_session: AsyncSession):
    """Same title and company but different city is NOT a duplicate."""
    from sqlalchemy import text
    await db_session.execute(
        text(
            "INSERT INTO postings (id, title, company, city, province, work_mode, "
            "term, duration_months, deadline, description, skills, low_confidence_fields) "
            "VALUES (gen_random_uuid(), :title, :company, :city, 'ON', 'onsite', "
            "'Summer 2027', 4, '2027-03-01', '', '{}', '{}')"
        ),
        {"title": "Data Analyst Co-op", "company": "DataCo", "city": "Waterloo"},
    )
    await db_session.flush()

    result = await duplicate_exists(db_session, "DataCo", "Data Analyst Co-op", "Ottawa")
    assert result is False


@pytest.mark.asyncio
async def test_different_company_not_duplicate(db_session: AsyncSession):
    """Same title and city but different company is NOT a duplicate."""
    from sqlalchemy import text
    await db_session.execute(
        text(
            "INSERT INTO postings (id, title, company, city, province, work_mode, "
            "term, duration_months, deadline, description, skills, low_confidence_fields) "
            "VALUES (gen_random_uuid(), :title, :company, :city, 'ON', 'hybrid', "
            "'Summer 2027', 4, '2027-03-01', '', '{}', '{}')"
        ),
        {"title": "ML Engineer Co-op", "company": "AICorp", "city": "Toronto"},
    )
    await db_session.flush()

    result = await duplicate_exists(db_session, "OtherCorp", "ML Engineer Co-op", "Toronto")
    assert result is False
