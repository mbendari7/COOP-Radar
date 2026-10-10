"""
Pydantic schemas for the postings endpoints.

Shapes match the API contracts in specs/001-browse-search-postings/contracts/api.md.
PostingListItem is the lean list payload; PostingDetail adds description.
PostingListParams is the full query-param model — Pydantic validates and coerces it
so the router stays thin and the service never sees invalid input.
"""

from datetime import date, datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.posting import WorkMode

T = TypeVar("T")


# ── Response schemas ──────────────────────────────────────────────────────────

class PostingListItem(BaseModel):
    """
    One row in the postings table.
    Omits description to keep list payloads small (see contracts/api.md note).
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    company: str
    city: str
    province: str
    work_mode: WorkMode
    term: str
    duration_months: int
    deadline: date
    posted_at: datetime
    skills: list[str]
    source_url: str | None
    # Populated for authenticated requests only; None means unauthenticated
    is_saved: bool | None = None


class PostingDetail(PostingListItem):
    """Full posting detail — includes description for the detail page."""
    description: str


class Page(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    All list endpoints return Page[SomeItem] so the frontend knows the shape.
    """
    items: list[T]
    total: int
    page: int
    page_size: int


# Concrete alias so the router return type is explicit
PostingsPage = Page[PostingListItem]


# ── Filter metadata ───────────────────────────────────────────────────────────

class FilterMeta(BaseModel):
    """
    Distinct values available for each filter dropdown.
    Populated from the postings table so the frontend never shows a city
    that has zero postings.
    """
    cities: list[str]
    provinces: list[str]
    terms: list[str]
    skills: list[str]


# ── Query params ──────────────────────────────────────────────────────────────

class PostingListParams(BaseModel):
    """
    All query parameters accepted by GET /api/postings.

    Pydantic validates these before the router calls the service, so the service
    only receives clean, typed values.  Unknown sort values produce a 422
    automatically via the Literal type — no manual whitelist needed.

    CHK012 decision: multi-value params (duration, skills) use repeated query
    params (?skills=React&skills=TypeScript) which FastAPI handles natively.
    CHK014 decision: invalid values produce 422 (Pydantic rejects them);
    the frontend catches 422s and resets affected params to their defaults.
    """

    q: str | None = Field(default=None, max_length=200)
    city: str | None = None
    province: str | None = None
    term: str | None = None
    work_mode: WorkMode | None = None
    # duration accepts a list so multiple values can be OR'd (4 and/or 8 months)
    duration: list[Literal[4, 8, 12, 16]] | None = None
    skills: list[str] | None = None
    show_expired: bool = False

    # Whitelisted sort columns — anything else is a 422 before service is called
    sort: Literal["posted_at", "deadline", "company", "title"] = "posted_at"
    order: Literal["asc", "desc"] = "desc"

    page: int = Field(default=1, ge=1)
    page_size: Literal[10, 25, 50] = 25
