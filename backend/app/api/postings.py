"""
Postings router — thin layer that delegates straight to the service.

Route order matters: /meta/filters MUST come before /{id} so FastAPI doesn't
try to interpret "meta" as a UUID and return a 422.

For authenticated requests (cookie present), each posting item gets an
is_saved: bool field injected.  Unauthenticated requests leave it as None.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user, get_optional_user
from app.schemas.posting import (
    CsvUploadResult,
    FilterMeta,
    ManualPostingIn,
    PostingDetail,
    PostingListItem,
    PostingListParams,
    PostingsPage,
    SimilarPostingsResponse,
)
from app.services.postings import (
    create_manual,
    get_filter_meta,
    get_posting,
    list_postings,
    similar_postings,
    upload_csv,
)

router = APIRouter(prefix="/postings", tags=["postings"])

_CSV_RATE_LIMIT = 3  # uploads per user per hour
_CSV_RATE_WINDOW = 3600  # seconds


@router.get("/meta/filters", response_model=FilterMeta)
async def postings_filter_meta(db: AsyncSession = Depends(get_db)) -> FilterMeta:
    """
    Return distinct values for filter dropdowns (cities, provinces, terms, skills).
    Cached by the frontend for 5 minutes — values change only when new postings arrive.
    """
    return await get_filter_meta(db)


@router.post("/upload", response_model=CsvUploadResult)
async def upload_csv_endpoint(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CsvUploadResult:
    """
    Bulk-import postings from a CSV file.
    Rate-limited to 3 uploads per user per hour.
    """
    redis = request.app.state.redis
    rate_key = f"csv_upload:{current_user.id}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, _CSV_RATE_WINDOW)
    if count > _CSV_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={"detail": "CSV upload rate limit exceeded.", "code": "RATE_LIMITED"},
        )

    file_bytes = await file.read()
    return await upload_csv(db, current_user.id, file_bytes)


@router.post("", response_model=PostingListItem, status_code=status.HTTP_201_CREATED)
async def create_manual_posting(
    data: ManualPostingIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PostingListItem:
    """Add a single posting manually. Returns 409 if a duplicate already exists."""
    return await create_manual(db, current_user.id, data)


@router.get("", response_model=PostingsPage)
async def get_postings(
    q: str | None = Query(default=None, max_length=200),
    city: str | None = Query(default=None),
    province: str | None = Query(default=None),
    term: str | None = Query(default=None),
    work_mode: str | None = Query(default=None),
    duration: list[int] | None = Query(default=None),
    skills: list[str] | None = Query(default=None),
    show_expired: bool = Query(default=False),
    show_closed: bool = Query(default=False),
    search_mode: str = Query(default="keyword"),
    sort: str = Query(default="posted_at"),
    order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> PostingsPage:
    """
    List postings with optional keyword search, filters, sort, and pagination.
    Authenticated users also get is_saved on each item.
    """
    from app.models.posting import WorkMode

    params = PostingListParams(
        q=q,
        city=city,
        province=province,
        term=term,
        work_mode=WorkMode(work_mode) if work_mode else None,
        duration=duration,  # type: ignore[arg-type]
        skills=skills,
        show_expired=show_expired,
        show_closed=show_closed,
        search_mode=search_mode,  # type: ignore[arg-type]
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
        page=page,
        page_size=page_size,  # type: ignore[arg-type]
    )
    return await list_postings(params, db, user_id=current_user.id if current_user else None)


@router.get("/{posting_id}/similar", response_model=SimilarPostingsResponse)
async def get_similar_postings(
    posting_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SimilarPostingsResponse:
    """Return up to 5 postings most similar by embedding cosine similarity."""
    return await similar_postings(db, posting_id)


@router.get("/{posting_id}", response_model=PostingDetail)
async def get_posting_detail(
    posting_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> PostingDetail:
    """Full detail for a single posting. Returns 404 if the ID doesn't exist."""
    detail = await get_posting(posting_id, db)
    # low_confidence_fields only visible to admins
    if not (current_user and current_user.is_admin):
        detail.low_confidence_fields = None
    return detail
