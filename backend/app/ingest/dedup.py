"""Deduplication logic using PostgreSQL fuzzystrmatch (Levenshtein similarity)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def duplicate_exists(
    db: AsyncSession,
    company: str,
    title: str,
    city: str,
) -> bool:
    """
    Return True if a posting with the same company+city and a very similar title
    (Levenshtein similarity > 0.85) already exists in the postings table.

    Requires the fuzzystrmatch extension (enabled in migration 0004).
    """
    stmt = text(
        """
        SELECT 1 FROM postings
        WHERE company = :company
          AND city = :city
          AND (
            1.0 - levenshtein(lower(title), lower(:title))::float
            / GREATEST(length(title), length(:title), 1)
          ) > 0.85
        LIMIT 1
        """
    )
    result = await db.execute(stmt, {"company": company, "title": title, "city": city})
    return result.scalar_one_or_none() is not None
