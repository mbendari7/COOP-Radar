"""
Business logic for postings.

All filtering, sorting, and pagination happen here in SQL — never in Python
memory (Constitution II).  The router calls these functions and returns the
results directly; no business logic lives in the router.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from app.schemas.posting import FilterMeta, PostingDetail, PostingListItem, PostingsPage, PostingListParams

# Maps the whitelisted sort param values to their ORM column.
# Using a dict means we never interpolate user input into SQL —
# unknown values are already rejected by Pydantic before we get here.
_SORT_MAP = {
    "posted_at": Posting.posted_at,
    "deadline": Posting.deadline,
    "company": Posting.company,
    "title": Posting.title,
}


async def list_postings(
    params: PostingListParams,
    db: AsyncSession,
    user_id: UUID | None = None,
) -> PostingsPage:
    """
    Return a paginated, filtered, sorted page of postings.

    All predicates are added to a single SELECT so Postgres can use indexes
    efficiently instead of filtering in a subquery or in Python.
    """

    # Build the base query — we'll add WHERE clauses below
    stmt = select(Posting)

    # --- Filters ---

    # Hide postings whose deadline has already passed unless the user opted in.
    # CHK008: show_expired is an additional AND predicate on top of all other filters.
    if not params.show_expired:
        stmt = stmt.where(Posting.deadline >= date.today())

    if params.q:
        # websearch_to_tsquery handles quoted phrases and minus exclusions
        # (e.g. "react -native") without crashing on special characters.
        stmt = stmt.where(
            Posting.search_vector.op("@@")(
                func.websearch_to_tsquery("english", params.q)
            )
        )

    if params.city:
        # Remote postings always appear in city-filtered results (FR-004a).
        # We include a posting if its city matches OR it's flagged as remote work.
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(
                Posting.city.ilike(params.city),
                Posting.work_mode == WorkMode.remote,
            )
        )

    if params.province:
        stmt = stmt.where(Posting.province.ilike(params.province))

    if params.term:
        stmt = stmt.where(Posting.term == params.term)

    if params.work_mode:
        stmt = stmt.where(Posting.work_mode == params.work_mode)

    if params.duration:
        # Multiple duration values are OR'd — show postings of any selected length
        stmt = stmt.where(Posting.duration_months.in_(params.duration))

    if params.skills:
        # AND logic: posting must have ALL selected skills.
        # @> is the Postgres array "contains" operator.
        # cast keeps mypy and asyncpg happy about the array literal type.
        stmt = stmt.where(
            Posting.skills.op("@>")(
                text(f"ARRAY{params.skills!r}::text[]")
            )
        )

    # --- Total count (before pagination) ---
    # We run this as a subquery so it sees the same WHERE clauses.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # --- Sort ---
    sort_col = _SORT_MAP[params.sort]
    if params.order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    # --- Pagination ---
    offset = (params.page - 1) * params.page_size
    stmt = stmt.offset(offset).limit(params.page_size)

    rows = (await db.execute(stmt)).scalars().all()

    # Build a set of saved posting IDs for this user if authenticated
    saved_ids: set[UUID] = set()
    if user_id is not None and rows:
        from app.models.saved_posting import SavedPosting
        row_ids = [row.id for row in rows]
        saved_stmt = select(SavedPosting.posting_id).where(
            SavedPosting.user_id == user_id,
            SavedPosting.posting_id.in_(row_ids),
        )
        saved_ids = set((await db.execute(saved_stmt)).scalars().all())

    items = []
    for row in rows:
        item = PostingListItem.model_validate(row)
        if user_id is not None:
            item.is_saved = row.id in saved_ids
        items.append(item)

    return PostingsPage(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


async def get_posting(posting_id: UUID, db: AsyncSession) -> PostingDetail:
    """
    Fetch a single posting by ID.
    Raises 404 via HTTPException if the ID doesn't exist.
    """
    from fastapi import HTTPException

    stmt = select(Posting).where(Posting.id == posting_id)
    posting = (await db.execute(stmt)).scalar_one_or_none()

    if posting is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Posting not found", "code": "POSTING_NOT_FOUND"},
        )

    return PostingDetail.model_validate(posting)


async def get_filter_meta(db: AsyncSession) -> FilterMeta:
    """
    Return the distinct values available for each filter dropdown.

    Values come from the actual postings table so the UI never shows a
    city or skill that has zero matching postings.
    """

    cities_result = await db.execute(
        select(Posting.city).distinct().order_by(Posting.city)
    )
    cities = [r for (r,) in cities_result.all() if r]

    provinces_result = await db.execute(
        select(Posting.province).distinct().order_by(Posting.province)
    )
    provinces = [r for (r,) in provinces_result.all() if r]

    terms_result = await db.execute(
        select(Posting.term).distinct().order_by(Posting.term)
    )
    terms = [r for (r,) in terms_result.all() if r]

    # Unnest the skills arrays to get a flat list of distinct skills.
    # unnest() expands TEXT[] into individual rows, DISTINCT deduplicates.
    skills_result = await db.execute(
        select(func.unnest(Posting.skills).label("skill"))
        .distinct()
        .order_by(text("skill"))
    )
    skills = [r for (r,) in skills_result.all() if r]

    return FilterMeta(cities=cities, provinces=provinces, terms=terms, skills=skills)
