"""
Business logic for postings.

All filtering, sorting, and pagination happen here in SQL — never in Python
memory (Constitution II).  The router calls these functions and returns the
results directly; no business logic lives in the router.
"""

import io
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text
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
        # Semantic mode: rank by cosine similarity to query embedding
        from app.ingest.embed import generate_embedding
        from app.models.posting_embedding import PostingEmbedding
        from sqlalchemy import cast
        from pgvector.sqlalchemy import Vector

        try:
            query_vec = await generate_embedding(params.q)
            vec_literal = str(query_vec)
            stmt = stmt.join(
                PostingEmbedding,
                PostingEmbedding.posting_id == Posting.id,
            ).order_by(
                text(f"posting_embeddings.embedding <=> '{vec_literal}'::vector")
            )
        except Exception:
            # Embedding service unavailable — fall back to keyword
            stmt = stmt.where(
                Posting.search_vector.op("@@")(
                    func.websearch_to_tsquery("english", params.q)
                )
            )
    elif params.q:
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
    # Skip sort for semantic mode — already ordered by cosine similarity
    if params.search_mode != "semantic" or not params.q:
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


async def upload_csv(
    db: AsyncSession,
    user_id: UUID,
    file_bytes: bytes,
) -> CsvUploadResult:
    """
    Parse a CSV file and bulk-insert valid, non-duplicate postings.
    Returns a CsvUploadResult with counts and per-row errors.
    """
    import pandas as pd
    from app.ingest.csv_validator import validate_csv_row, RowError as CsvRowError

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"detail": f"CSV is not parseable: {exc}", "code": "INVALID_CSV"},
        )

    if len(df) > 1000:
        raise HTTPException(
            status_code=413,
            detail={"detail": "CSV exceeds 1,000 row limit.", "code": "FILE_TOO_LARGE"},
        )

    required_cols = {"title", "company", "city", "term", "deadline"}
    missing = required_cols - set(df.columns.str.lower())
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"detail": f"Missing required columns: {missing}", "code": "INVALID_CSV"},
        )

    # Normalise column names to lowercase
    df.columns = df.columns.str.lower()

    added = 0
    skipped = 0
    errors: list[RowError] = []

    from app.ingest.dedup import duplicate_exists

    for i, row in df.iterrows():
        row_num = int(i) + 2  # 1-indexed, header is row 1
        row_dict = row.to_dict()
        row_errors = validate_csv_row(row_dict, row_num)
        if row_errors:
            for e in row_errors:
                errors.append(RowError(row=e.row, column=e.column, message=e.message))
            continue

        is_dup = await duplicate_exists(
            db,
            str(row_dict.get("company", "")),
            str(row_dict.get("title", "")),
            str(row_dict.get("city", "")),
        )
        if is_dup:
            skipped += 1
            continue

        from datetime import date as date_type
        work_mode_val = row_dict.get("work_mode")
        work_mode = WorkMode.onsite
        if work_mode_val and str(work_mode_val).strip().lower() in WorkMode.__members__:
            work_mode = WorkMode(str(work_mode_val).strip().lower())

        raw_skills = row_dict.get("skills", "")
        skills: list[str] = []
        if raw_skills and str(raw_skills).lower() != "nan":
            skills = [s.strip() for s in str(raw_skills).split(",") if s.strip()]

        posting = Posting(
            title=str(row_dict["title"]),
            company=str(row_dict["company"]),
            city=str(row_dict["city"]),
            province=str(row_dict.get("province", "ON") or "ON"),
            work_mode=work_mode,
            term=str(row_dict["term"]),
            duration_months=int(row_dict.get("duration_months", 4) or 4),
            deadline=date_type.fromisoformat(str(row_dict["deadline"]).strip()),
            description=str(row_dict.get("description", "") or ""),
            source_url=str(row_dict.get("source_url", "") or "") or None,
            skills=skills,
        )
        db.add(posting)
        added += 1

    await db.flush()
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

    is_dup = await duplicate_exists(db, data.company, data.title, data.city)
    if is_dup:
        raise HTTPException(
            status_code=409,
            detail={"detail": "A similar posting already exists.", "code": "DUPLICATE"},
        )

    work_mode = data.work_mode or WorkMode.onsite
    posting = Posting(
        title=data.title,
        company=data.company,
        city=data.city,
        province=data.province or "ON",
        work_mode=work_mode,
        term=data.term,
        duration_months=data.duration_months or 4,
        deadline=data.deadline,
        description=data.description or "",
        source_url=data.source_url,
        skills=data.skills,
    )
    db.add(posting)
    await db.flush()
    await db.refresh(posting)
    return PostingListItem.model_validate(posting)


async def similar_postings(
    db: AsyncSession,
    posting_id: UUID,
    limit: int = 5,
) -> SimilarPostingsResponse:
    """
    Return up to `limit` postings most similar to the target by cosine similarity.
    Returns empty items list if target has no embedding.
    """
    from app.models.posting_embedding import PostingEmbedding

    # Check target posting exists
    target_posting = (await db.execute(select(Posting).where(Posting.id == posting_id))).scalar_one_or_none()
    if target_posting is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Posting not found", "code": "POSTING_NOT_FOUND"},
        )

    # Check target has an embedding
    target_emb = (
        await db.execute(
            select(PostingEmbedding).where(PostingEmbedding.posting_id == posting_id)
        )
    ).scalar_one_or_none()

    if target_emb is None:
        return SimilarPostingsResponse(items=[])

    emb_str = str(list(target_emb.embedding))

    stmt = text(
        """
        SELECT p.id, p.title, p.company, p.city, p.province, p.work_mode,
               p.term, p.deadline,
               1 - (pe.embedding <=> :target_vec::vector) AS similarity
        FROM posting_embeddings pe
        JOIN postings p ON p.id = pe.posting_id
        WHERE pe.posting_id != :posting_id
        ORDER BY pe.embedding <=> :target_vec::vector
        LIMIT :limit
        """
    )
    rows = (
        await db.execute(
            stmt,
            {"target_vec": emb_str, "posting_id": str(posting_id), "limit": limit},
        )
    ).mappings().all()

    items = [
        SimilarPostingOut(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            city=row["city"],
            province=row["province"],
            work_mode=WorkMode(row["work_mode"]) if row["work_mode"] else None,
            term=row["term"],
            deadline=row["deadline"],
            similarity=float(row["similarity"]),
        )
        for row in rows
    ]
    return SimilarPostingsResponse(items=items)
