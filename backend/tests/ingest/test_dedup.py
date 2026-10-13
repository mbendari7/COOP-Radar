"""Tests for duplicate_exists. Same company and city and almost the same title."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.dedup import duplicate_exists


@pytest.mark.asyncio
async def test_exact_match_is_duplicate(db_session: AsyncSession):
    """An exact title, company and city match counts as a duplicate."""
    # Add a job
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
    """A title more than 85% alike an existing one is a duplicate."""
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

    # A slightly different title should still get caught
    result = await duplicate_exists(db_session, "TechCo", "Frontend React Develoer", "Toronto")
    assert result is True


@pytest.mark.asyncio
async def test_different_city_not_duplicate(db_session: AsyncSession):
    """Same title and company in a different city is NOT a duplicate."""
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
    """Same title and city at a different company is NOT a duplicate."""
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
