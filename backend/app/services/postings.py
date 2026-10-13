"""
The logic for job postings.

All filtering, sorting and paging happens in SQL and never in Python memory.
The router calls these and sends back what they return, nothing more.
"""

import io
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import SmallInteger, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from app.schemas.posting import (
    CategoryCount,
    CountryCount,
    CsvUploadResult,
    FilterMeta,
    ManualPostingIn,
    PostingDetail,
    PostingListItem,
    PostingListParams,
    PostingsPage,
    ProgramOption,
    RowError,
    SimilarPostingOut,
    SimilarPostingsResponse,
    WorkModeCount,
)
from app.services.categories import CATEGORIES, any_category, category_clause
from app.services.education import PROGRAMS

COUNTRY_LABELS = {"CA": "Canada", "US": "United States"}

# Maps each allowed sort value to its column.
# A dict means user input never gets pasted into SQL, and Pydantic already
# turned away anything we do not know before we get here.
# In Postgres regex \m means start of word and \M means end of word
STUDENT_TITLE_PATTERN = (
    r"\m(intern|interns|internship|co-?op|student|new grad(uate)?|apprentice|stagiaire)\M"
)
# Titles that are clearly not for students
SENIOR_TITLE_PATTERN = (
    r"\m(senior|sr|staff|principal|lead|manager|director|head|vp|architect|ii|iii|iv)\M"
)

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
    One filtered, sorted page of jobs.

    Every condition goes into one SELECT so Postgres can use its indexes
    instead of filtering in a subquery or in Python.
    """

    # The base query. WHERE clauses get added below
    stmt = select(Posting)

    # Filters

    # Hide jobs the import marked as closed
    if not params.show_closed:
        stmt = stmt.where(Posting.closed_at.is_(None))

    # Hide jobs whose deadline already passed unless they asked to see them.
    # show_expired just adds one more AND on top of the other filters
    if not params.show_expired:
        stmt = stmt.where(Posting.deadline >= date.today())

    if params.q and params.search_mode == "semantic":
        # Smart search ranks by how close each job's embedding is to the query.
        # Jobs with no embedding drop out of smart results
        from app.ingest.embed import generate_embedding
        from app.models.posting_embedding import PostingEmbedding

        try:
            query_vec = await generate_embedding(params.q)
        except Exception:  # noqa: BLE001 embedding service is down so use keyword search
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
        # websearch_to_tsquery understands quoted phrases and minus to exclude
        # like "react -native" and does not crash on odd characters
        stmt = stmt.where(
            Posting.search_vector.op("@@")(func.websearch_to_tsquery("english", params.q))
        )

    if params.city:
        # Remote jobs always show up when filtering by city.
        # A job counts if its city matches or it is remote
        stmt = stmt.where(
            or_(
                Posting.city.ilike(params.city),
                Posting.work_mode == WorkMode.remote,
            )
        )

    if params.students_only:
        # Fixed pattern with no user input. Whole word intern, co-op, student or new grad
        stmt = stmt.where(Posting.title.op("~*")(STUDENT_TITLE_PATTERN))

    if params.hide_senior:
        stmt = stmt.where(Posting.title.op("!~*")(SENIOR_TITLE_PATTERN))

    if params.province:
        stmt = stmt.where(Posting.province.ilike(params.province))

    if params.term:
        stmt = stmt.where(Posting.term == params.term)

    if params.work_mode:
        stmt = stmt.where(Posting.work_mode == params.work_mode)

    if params.duration:
        # More than one length means any of them, so show jobs of any picked length
        stmt = stmt.where(Posting.duration_months.in_(params.duration))

    if params.skills:
        # The job has to have every picked skill.
        # .contains() turns into the Postgres array contains check with the list
        # sent as a bound parameter, so user input never touches the SQL text
        stmt = stmt.where(Posting.skills.contains(params.skills))

    if params.category:
        stmt = stmt.where(any_category(params.category))

    if params.company:
        stmt = stmt.where(Posting.company.in_(params.company))

    if params.posted_within:
        stmt = stmt.where(Posting.posted_at >= func.now() - timedelta(days=params.posted_within))

    if params.country:
        stmt = stmt.where(Posting.country.in_(params.country))

    if params.program:
        stmt = stmt.where(program_clause(params.program))

    if params.grad_year:
        stmt = stmt.where(grad_year_clause(params.grad_year))

    # Total count before paging.
    # Run as a subquery so it sees the same WHERE clauses
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Sorting.
    # Smart search is already in order of closeness. Otherwise use the allowed sort.
    # Posting.id breaks ties so pages stay steady when sort values repeat
    if params.search_mode != "semantic" or not params.q:
        sort_col = _SORT_MAP[params.sort]
        if params.order == "desc":
            stmt = stmt.order_by(sort_col.desc(), Posting.id)
        else:
            stmt = stmt.order_by(sort_col.asc(), Posting.id)

    # Paging
    offset = (params.page - 1) * params.page_size
    stmt = stmt.offset(offset).limit(params.page_size)

    rows = (await db.execute(stmt)).scalars().all()

    # Work out which of these jobs the signed in person saved
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


def program_clause(program: str) -> Any:
    """Jobs for a program. The description names a field it covers or the title fits its types."""
    info = PROGRAMS[program]
    return or_(Posting.fields_of_study.overlap(list(info.fields)), any_category(info.categories))


def has_grad_year(year: int) -> Any:
    """The job names this grad year. The year goes in as a bound parameter."""
    return literal(year, SmallInteger) == func.any(Posting.grad_years)


def grad_year_clause(year: int) -> Any:
    """The job names no grad years or it names this one."""
    return or_(func.cardinality(Posting.grad_years) == 0, has_grad_year(year))


async def get_posting(posting_id: UUID, db: AsyncSession) -> PostingDetail:
    """
    Get one job by id.
    Answers 404 if the id is not there.
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
    The choices for each filter menu.

    They come from the real jobs table so the site never offers a
    city or skill with no jobs behind it.
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

    # Unpack the skills arrays into one flat list of skills.
    # unnest() turns each text array into rows and DISTINCT drops repeats
    skills_result = await db.execute(
        select(func.unnest(Posting.skills).label("skill"))
        .distinct()
        .order_by(text("skill"))
    )
    skills = [r for (r,) in skills_result.all() if r]

    open_postings = (Posting.closed_at.is_(None), Posting.deadline >= date.today())
    companies_result = await db.execute(
        select(Posting.company).where(*open_postings).distinct().order_by(Posting.company)
    )
    companies = [r for (r,) in companies_result.all() if r]

    counts = await _open_counts(db)
    return FilterMeta(
        cities=cities, provinces=provinces, terms=terms, skills=skills,
        companies=companies, categories=counts.categories, open_jobs=counts.open_jobs,
        countries=counts.countries, work_modes=counts.work_modes,
        programs=[ProgramOption(key=key, label=p.label) for key, p in PROGRAMS.items()],
    )


@dataclass
class _OpenCounts:
    open_jobs: int
    categories: list[CategoryCount]
    countries: list[CountryCount]
    work_modes: list[WorkModeCount]


# Job type counts run nine title regexes over every open job, about 250 ms at 10k rows, and
# jobs only change every few hours, so we keep the result for a couple of minutes
_COUNTS_TTL = 120.0
_counts_cache: tuple[float, _OpenCounts] | None = None


def clear_category_counts_cache() -> None:
    global _counts_cache
    _counts_cache = None


async def _open_counts(db: AsyncSession) -> _OpenCounts:
    """Open jobs in total and by job type, country and work mode in one pass over the table."""
    global _counts_cache
    if _counts_cache is not None and time.monotonic() - _counts_cache[0] < _COUNTS_TTL:
        return _counts_cache[1]
    counts = (
        await db.execute(
            select(
                func.count().label("open_jobs"),
                *(
                    func.count().filter(category_clause(key)).label(key)
                    for key in CATEGORIES
                ),
                *(
                    func.count().filter(Posting.country == code).label(f"country_{code}")
                    for code in COUNTRY_LABELS
                ),
                *(
                    func.count().filter(Posting.work_mode == mode).label(f"mode_{mode.value}")
                    for mode in WorkMode
                ),
            ).where(Posting.closed_at.is_(None), Posting.deadline >= date.today())
        )
    ).one()
    result = _OpenCounts(
        open_jobs=int(counts.open_jobs),
        categories=[
            CategoryCount(key=key, label=label, count=int(getattr(counts, key)))
            for key, (label, _) in CATEGORIES.items()
        ],
        countries=[
            CountryCount(code=code, label=label, count=int(getattr(counts, f"country_{code}")))
            for code, label in COUNTRY_LABELS.items()
        ],
        work_modes=[
            WorkModeCount(key=mode, count=int(getattr(counts, f"mode_{mode.value}")))
            for mode in WorkMode
        ],
    )
    _counts_cache = (time.monotonic(), result)
    return result


def _clean(value: object) -> str:
    """Clean up a pandas cell. NaN and None become '' and anything else a trimmed string."""
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
    Read a CSV file and add every good row that is not a duplicate.
    Gives back counts and the problems found in each row.
    New jobs get an embedding job queued after the commit.
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
        row_num = i + 2  # counting from 1 and the header is row 1
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
        # Flush so the next row's duplicate check can see this one
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
    Add one job typed in by hand.
    Answers 409 DUPLICATE if almost the same job is already there.
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
    Up to `limit` open jobs most like this one by embedding.
    Gives back an empty list if this job has no embedding yet.
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
