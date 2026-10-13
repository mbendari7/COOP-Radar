"""
Spotting duplicates. Same company, same city and almost the same title.

Titles get compared in Python, with difflib needing more than 0.85 alike, against the few
jobs that share the company and city. That way the database needs no extra extension and
this works on any hosted Postgres.
"""

from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting

_SIMILARITY = 0.85


def titles_match(a: str, b: str) -> bool:
    """True when two job titles are almost the same, ignoring case."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() > _SIMILARITY


async def duplicate_exists(
    db: AsyncSession,
    company: str,
    title: str,
    city: str,
) -> bool:
    """True if a job with the same company and city has almost the same title."""
    stmt = select(Posting.title).where(
        func.lower(Posting.company) == company.lower().strip(),
        func.lower(Posting.city) == city.lower().strip(),
    )
    return any(titles_match(existing, title) for existing in (await db.execute(stmt)).scalars())
