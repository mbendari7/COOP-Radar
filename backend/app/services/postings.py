"""
Business logic for postings.

All filtering, sorting, and pagination happen here in SQL — never in Python
memory (Constitution II).  The router calls these functions and returns the
results directly; no business logic lives in the router.
"""

import io
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from app.schemas.posting import (
    CsvUploadResult,
    FilterMeta,
    ManualPostingIn,
    PostingDetail,
    PostingListItem,
    PostingListParams,
    PostingsPage,
    RowError,
    SimilarPostingOut,
    SimilarPostingsResponse,
)

# Maps the whitelisted sort param values to their ORM column.
# Using a dict means we never interpolate user input into SQL —
# unknown values are already rejected by Pydantic before we get here.
# Postgres regex: \m = start of word, \M = end of word
STUDENT_TITLE_PATTERN = r"\m(intern|interns|internship|co-?op|student|new grad(uate)?|apprentice)\M"

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

    # Hide closed postings (those marked by ingest as no longer available)
    if not params.show_closed:
        stmt = stmt.where(Posting.closed_at.is_(None))

    # Hide postings whose deadline has already passed unless the user opted in.
    # CHK008: show_expired is an additional AND predicate on top of all other filters.
    if not params.show_expired:
        stmt = stmt.where(Posting.deadline >= date.today())

    if params.q and params.search_mode == "semantic":
        # Semantic mode: rank by cosine distance to the query embedding (pgvector).
        # Postings without an embedding drop out of semantic results.
        from app.ingest.embed import generate_embedding
        from app.models.posting_embedding import PostingEmbedding

        try:
            query_vec = await generate_embedding(params.q)
        except Exception:  # noqa: BLE001 — embedding service down: fall back to keyword
            query_vec = None

        if query_vec is not None:
            stmt = stmt.join(
                PostingEmbedding, PostingEmbedding.posting_id == Posting.id
            ).order_by(PostingEmbedding.embedding.cosine_distance(query_vec))
        else:
            stmt = stmt.where(
                Posting.search_vector.op("@@")(func.websearch_to_tsquery("english", params.q))
            )
    elif params.q:
        # websearch_to_tsquery handles quoted phrases and minus exclusions
        # (e.g. "react -native") without crashing on special characters.
        stmt = stmt.where(
            Posting.search_vector.op("@@")(func.websearch_to_tsquery("english", params.q))
        )

    if params.city:
        # Remote postings always appear in city-filtered results (FR-004a).
        # We include a posting if its city matches OR it's flagged as remote work.
        stmt = stmt.where(
            or_(
                Posting.city.ilike(params.city),
                Posting.work_mode == WorkMode.remote,
            )
        )

    if params.students_only:
        # Constant pattern (no user input): whole-word intern / co-op / student / new grad
        stmt = stmt.where(Posting.title.op("~*")(STUDENT_TITLE_PATTERN))

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
        # .contains() compiles to the Postgres array "contains" operator (@>) with the
        # list sent as a bound parameter — user input never touches the SQL string.
        stmt = stmt.where(Posting.skills.contains(params.skills))

    # --- Total count (before pagination) ---
    # We run this as a subquery so it sees the same WHERE clauses.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # --- Sort ---
    # Semantic mode is already ordered by similarity; otherwise apply the whitelisted sort.
    # Posting.id is a tiebreaker so pagination is stable when sort values repeat.
    if params.search_mode != "semantic" or not params.q:
        sort_col = _SORT_MAP[params.sort]
        if params.order == "desc":
            stmt = stmt.order_by(sort_col.desc(), Posting.id)
        else:
            stmt = stmt.order_by(sort_col.asc(), Posting.id)

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


def _clean(value: object) -> str:
    """Normalise a pandas cell: NaN/None become '', everything else a stripped string."""
    if value is None:
        return ""
    text_value = str(value).strip()
    return "" if text_value.lower() == "nan" else text_value


async def upload_csv(
    db: AsyncSession,
    user_id: UUID,
    file_bytes: bytes,
) -> CsvUploadResult:
    """
    Parse a CSV file and bulk-insert valid, non-duplicate postings.
    Returns a CsvUploadResult with counts and per-row errors.
    New postings get an embedding job queued after the commit.
    """
    import pandas as pd

    from app.ingest.csv_validator import validate_csv_row
    from app.ingest.dedup import duplicate_exists
    from app.ingest.embed import enqueue_embed_job

    try:
        # dtype=str keeps values like "2027-03-01" and "4" exactly as typed
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail={"detail": f"CSV is not parseable: {exc}", "code": "INVALID_CSV"},
        ) from exc

    if len(df) > 1000:
        raise HTTPException(
            status_code=413,
            detail={"detail": "CSV exceeds 1,000 row limit.", "code": "FILE_TOO_LARGE"},
        )

    df.columns = df.columns.str.strip().str.lower()
    required_cols = {"title", "company", "city", "term", "deadline"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": f"Missing required columns: {', '.join(sorted(missing))}",
                "code": "INVALID_CSV",
            },
        )

    added = 0
    skipped = 0
    errors: list[RowError] = []
    new_postings: list[Posting] = []

    for i, row in enumerate(df.to_dict(orient="records")):
        row_num = i + 2  # 1-indexed, header is row 1
        row_errors = validate_csv_row(row, row_num)
        if row_errors:
            errors.extend(
                RowError(row=e.row, column=e.column, message=e.message) for e in row_errors
            )
            continue

        title, company, city = _clean(row["title"]), _clean(row["company"]), _clean(row["city"])
        if await duplicate_exists(db, company, title, city):
            skipped += 1
            continue

        work_mode_val = _clean(row.get("work_mode")).lower()
        work_mode = WorkMode(work_mode_val) if work_mode_val in WorkMode.__members__ else None
        duration_val = _clean(row.get("duration_months"))
        skills_val = _clean(row.get("skills"))

        posting = Posting(
            title=title,
            company=company,
            city=city,
            province=_clean(row.get("province")) or "ON",
            work_mode=work_mode or WorkMode.onsite,
            term=_clean(row["term"]),
            duration_months=int(duration_val) if duration_val in {"4", "8", "12", "16"} else 4,
            deadline=date.fromisoformat(_clean(row["deadline"])),
            description=_clean(row.get("description")),
            source_url=_clean(row.get("source_url")) or None,
            skills=[s.strip() for s in skills_val.split(",") if s.strip()],
        )
        db.add(posting)
        # Flush so the next row's duplicate check sees this one too
        await db.flush()
        new_postings.append(posting)
        added += 1

    await db.commit()
    for posting in new_postings:
        enqueue_embed_job(posting.id)

    return CsvUploadResult(added=added, skipped_duplicates=skipped, errors=errors)


async def create_manual(
    db: AsyncSession,
    user_id: UUID,
    data: ManualPostingIn,
) -> PostingListItem:
    """
    Insert a single manually-entered posting.
    Raises 409 DUPLICATE if a near-identical posting already exists.
    """
    from app.ingest.dedup import duplicate_exists
    from app.ingest.embed import enqueue_embed_job

    if await duplicate_exists(db, data.company, data.title, data.city):
        raise HTTPException(
            status_code=409,
            detail={"detail": "A similar posting already exists.", "code": "DUPLICATE"},
        )

    posting = Posting(
        title=data.title,
        company=data.company,
        city=data.city,
        province=data.province or "ON",
        work_mode=data.work_mode or WorkMode.onsite,
        term=data.term,
        duration_months=data.duration_months or 4,
        deadline=data.deadline,
        description=data.description or "",
        source_url=data.source_url,
        skills=data.skills,
    )
    db.add(posting)
    await db.commit()
    await db.refresh(posting)
    enqueue_embed_job(posting.id)
    return PostingListItem.model_validate(posting)


async def similar_postings(
    db: AsyncSession,
    posting_id: UUID,
    limit: int = 5,
) -> SimilarPostingsResponse:
    """
    Return up to `limit` open postings most similar to the target by cosine similarity.
    Returns an empty list if the target has no embedding yet.
    """
    from app.models.posting_embedding import PostingEmbedding

    target_posting = await db.get(Posting, posting_id)
    if target_posting is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Posting not found", "code": "POSTING_NOT_FOUND"},
        )

    target_emb = await db.get(PostingEmbedding, posting_id)
    if target_emb is None:
        return SimilarPostingsResponse(items=[])

    distance = PostingEmbedding.embedding.cosine_distance(target_emb.embedding)
    stmt = (
        select(Posting, (1 - distance).label("similarity"))
        .join(PostingEmbedding, PostingEmbedding.posting_id == Posting.id)
        .where(Posting.id != posting_id, Posting.closed_at.is_(None))
        .order_by(distance)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    items = [
        SimilarPostingOut(
            id=p.id,
            title=p.title,
            company=p.company,
            city=p.city,
            province=p.province,
            work_mode=p.work_mode,
            term=p.term,
            deadline=p.deadline,
            similarity=float(similarity),
        )
        for p, similarity in rows
    ]
    return SimilarPostingsResponse(items=items)
