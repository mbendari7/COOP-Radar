"""
Duplicate detection: same company + same city + a near-identical title.

Titles are compared in Python (difflib similarity > 0.85) against the few postings that share
the company and city, so the database needs no extra extension and the check works on any
hosted Postgres.
"""

from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting

_SIMILARITY = 0.85


def titles_match(a: str, b: str) -> bool:
    """True when two job titles are near-identical (case-insensitive)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() > _SIMILARITY


async def duplicate_exists(
    db: AsyncSession,
    company: str,
    title: str,
    city: str,
) -> bool:
    """Return True if a posting with the same company and city has a near-identical title."""
    stmt = select(Posting.title).where(
        func.lower(Posting.company) == company.lower().strip(),
        func.lower(Posting.city) == city.lower().strip(),
    )
    return any(titles_match(existing, title) for existing in (await db.execute(stmt)).scalars())
