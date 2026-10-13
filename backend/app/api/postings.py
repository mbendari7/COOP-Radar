"""
Job postings. A thin layer that hands everything to the service.

Order matters here. /meta/filters has to come before /{id} or FastAPI tries
to read "meta" as an id and answers 422.

When someone is signed in each job gets is_saved set to true or false.
Everyone else just gets None.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user, get_optional_user
from app.models.user import User
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

_CSV_RATE_LIMIT = 3  # uploads per person per hour
_CSV_RATE_WINDOW = 3600  # seconds


@router.get("/meta/filters", response_model=FilterMeta)
async def postings_filter_meta(db: AsyncSession = Depends(get_db)) -> FilterMeta:
    """
    The choices for the filter menus like cities, provinces, terms and skills.
    The site caches this for 5 minutes since it only changes when new jobs come in.
    """
    return await get_filter_meta(db)


@router.post("/upload", response_model=CsvUploadResult)
async def upload_csv_endpoint(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CsvUploadResult:
    """
    Import a bunch of jobs from a CSV file.
    Limited to 3 uploads per person per hour.
    """
    store = request.app.state.store
    rate_key = f"csv_upload:{current_user.id}"
    count = await store.incr(rate_key)
    if count == 1:
        await store.expire(rate_key, _CSV_RATE_WINDOW)
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
    current_user: User = Depends(get_current_user),
) -> PostingListItem:
    """Add one job by hand. Answers 409 if it is already there."""
    return await create_manual(db, current_user.id, data)


@router.get("", response_model=PostingsPage)
async def get_postings(
    params: Annotated[PostingListParams, Query()],
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> PostingsPage:
    """
    List jobs with search, filters, sorting and pages.
    FastAPI checks every query param against PostingListParams so a sort column or
    page size we do not allow is a 422 before the service even runs.
    Signed in people also get is_saved on each job.
    """
    return await list_postings(params, db, user_id=current_user.id if current_user else None)


@router.get("/{posting_id}/similar", response_model=SimilarPostingsResponse)
async def get_similar_postings(
    posting_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SimilarPostingsResponse:
    """Up to 5 jobs that are most alike by embedding."""
    return await similar_postings(db, posting_id)


@router.get("/{posting_id}", response_model=PostingDetail)
async def get_posting_detail(
    posting_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> PostingDetail:
    """Everything about one job. Answers 404 if the id is not there."""
    detail = await get_posting(posting_id, db)
    # Only admins see low_confidence_fields
    if not (current_user and current_user.is_admin):
        detail.low_confidence_fields = None
    return detail
