"""
Postings router — thin layer that delegates straight to the service.

Route order matters: /meta/filters MUST come before /{id} so FastAPI doesn't
try to interpret "meta" as a UUID and return a 422.

For authenticated requests (cookie present), each posting item gets an
is_saved: bool field injected.  Unauthenticated requests leave it as None.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_optional_user
from app.schemas.posting import FilterMeta, PostingDetail, PostingListParams, PostingsPage
from app.services.postings import get_filter_meta, get_posting, list_postings

router = APIRouter(prefix="/postings", tags=["postings"])


@router.get("/meta/filters", response_model=FilterMeta)
async def postings_filter_meta(db: AsyncSession = Depends(get_db)) -> FilterMeta:
    """
    Return distinct values for filter dropdowns (cities, provinces, terms, skills).
    Cached by the frontend for 5 minutes — values change only when new postings arrive.
    """
    return await get_filter_meta(db)


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
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
        page=page,
        page_size=page_size,  # type: ignore[arg-type]
    )
    return await list_postings(params, db, user_id=current_user.id if current_user else None)


@router.get("/{posting_id}", response_model=PostingDetail)
async def get_posting_detail(
    posting_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PostingDetail:
    """Full detail for a single posting. Returns 404 if the ID doesn't exist."""
    return await get_posting(posting_id, db)
