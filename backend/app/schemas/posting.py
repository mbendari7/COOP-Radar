"""
Pydantic schemas for the postings endpoints.

Shapes match the API contracts in specs/001-browse-search-postings/contracts/api.md.
PostingListItem is the lean list payload; PostingDetail adds description.
PostingListParams is the full query-param model — Pydantic validates and coerces it
so the router stays thin and the service never sees invalid input.
"""

import re
from datetime import date, datetime
from typing import Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.posting import WorkMode
from app.services.categories import CategoryKey
from app.services.education import ProgramKey

CountryCode = Literal["CA", "US"]
RoleType = Literal["coop", "internship", "new_grad", "job"]

# Python twins of the title patterns in app/services/postings.py, for the role badge
_COOP_TITLE = re.compile(r"(?i)\b(co-?op|stagiaire)\b")
_INTERN_TITLE = re.compile(r"(?i)\b(intern|interns|internship|student|apprentice)\b")
_NEW_GRAD_TITLE = re.compile(
    r"(?i)\b(new grad(uate)?|university grad(uate)?|early career|graduate program)\b"
)


def role_of(title: str) -> RoleType:
    """Co-op, internship, new-grad or regular job, from the title."""
    if _COOP_TITLE.search(title):
        return "coop"
    if _INTERN_TITLE.search(title):
        return "internship"
    if _NEW_GRAD_TITLE.search(title):
        return "new_grad"
    return "job"

T = TypeVar("T")

_DURATIONS = {4, 8, 12, 16}
_PAGE_SIZES = {10, 25, 50}
_POSTED_WITHIN = {1, 3, 7, 14, 30}


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
    country: str = "CA"
    work_mode: WorkMode
    term: str
    duration_months: int
    deadline: date
    posted_at: datetime
    skills: list[str]
    source_url: str | None
    # What the description asks for: graduation years and programs of study (empty = not stated)
    grad_years: list[int] = []
    fields_of_study: list[str] = []
    closed_at: datetime | None = None
    # Set for postings imported from a live employer career board (None = sample/manual/CSV)
    source_id: UUID | None = None
    # Populated for authenticated requests only; None means unauthenticated
    is_saved: bool | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def role(self) -> RoleType:
        return role_of(self.title)


class PostingDetail(PostingListItem):
    """Full posting detail — includes description for the detail page."""
    description: str
    low_confidence_fields: dict[str, float] | None = None


class Page[T](BaseModel):
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

class CategoryCount(BaseModel):
    """A job type for the filter list, with how many open postings it has."""
    key: CategoryKey
    label: str
    count: int


class CountryCount(BaseModel):
    code: CountryCode
    label: str
    count: int


class WorkModeCount(BaseModel):
    key: WorkMode
    count: int


class ProgramOption(BaseModel):
    key: ProgramKey
    label: str


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
    companies: list[str] = []
    categories: list[CategoryCount] = []
    # Open postings in total (job types overlap, so their counts don't add up to this)
    open_jobs: int = 0
    countries: list[CountryCount] = []
    work_modes: list[WorkModeCount] = []
    # Programs of study a student can pick (see app/services/education.py)
    programs: list[ProgramOption] = []


# ── Query params ──────────────────────────────────────────────────────────────

class ManualPostingIn(BaseModel):
    """Schema for manually submitted postings via POST /api/postings."""

    title: str
    company: str
    city: str
    term: str
    deadline: date
    province: str | None = None
    work_mode: WorkMode | None = None
    duration_months: int | None = None
    description: str | None = None
    skills: list[str] = []
    source_url: str | None = None


class RowError(BaseModel):
    """A single per-row validation error from a CSV upload."""

    row: int
    column: str
    message: str


class CsvUploadResult(BaseModel):
    """Response from POST /api/postings/upload."""

    added: int
    skipped_duplicates: int
    errors: list[RowError] = []


class SimilarPostingOut(BaseModel):
    """One item in the similar postings response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    company: str
    city: str
    province: str
    work_mode: WorkMode | None
    term: str
    deadline: date | None
    similarity: float


class SimilarPostingsResponse(BaseModel):
    """Response from GET /api/postings/{id}/similar."""

    items: list[SimilarPostingOut]


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
    duration: list[int] | None = None
    skills: list[str] | None = None
    # Job types (OR'd), inferred from the title: see app/services/categories.py
    category: list[CategoryKey] | None = None
    # Employers (OR'd), exact names from /meta/filters
    company: list[str] | None = None
    # Only postings published in the last N days
    posted_within: int | None = None
    # Countries (OR'd): CA, US. None = all
    country: list[CountryCode] | None = None
    # Jobs for a program of study: they name it in the description or fit its job types
    program: ProgramKey | None = None
    # Hide jobs that ask for a different graduation year (jobs that don't say are kept)
    grad_year: int | None = Field(default=None, ge=2000, le=2100)
    show_expired: bool = False
    show_closed: bool = False
    # Only internships, co-ops, student and new-grad roles (matched on the job title)
    students_only: bool = False
    # Hide senior / staff / lead / manager / director roles (matched on the job title)
    hide_senior: bool = False
    search_mode: Literal["keyword", "semantic"] = "keyword"

    # Whitelisted sort columns — anything else is a 422 before service is called
    sort: Literal["posted_at", "deadline", "company", "title"] = "posted_at"
    order: Literal["asc", "desc"] = "desc"

    page: int = Field(default=1, ge=1)
    page_size: int = 25

    # Query strings arrive as text, and Literal[...] int fields reject "10" — so these
    # are plain ints validated against the allowed values (still a 422 when invalid).
    @field_validator("duration")
    @classmethod
    def _valid_durations(cls, v: list[int] | None) -> list[int] | None:
        if v is not None and any(d not in _DURATIONS for d in v):
            raise ValueError(f"duration must be one of {sorted(_DURATIONS)}")
        return v

    @field_validator("posted_within")
    @classmethod
    def _valid_posted_within(cls, v: int | None) -> int | None:
        if v is not None and v not in _POSTED_WITHIN:
            raise ValueError(f"posted_within must be one of {sorted(_POSTED_WITHIN)}")
        return v

    @field_validator("page_size")
    @classmethod
    def _valid_page_size(cls, v: int) -> int:
        if v not in _PAGE_SIZES:
            raise ValueError(f"page_size must be one of {sorted(_PAGE_SIZES)}")
        return v
