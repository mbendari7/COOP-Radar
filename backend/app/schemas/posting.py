"""
Shapes for the job posting endpoints.

They match the contracts in specs/001-browse-search-postings/contracts/api.md.
PostingListItem is the light version for lists and PostingDetail adds the description.
PostingListParams holds every query param. Pydantic checks and converts it
so the router stays thin and the service never sees bad input.
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
Season = Literal["winter", "spring", "summer", "fall"]
RoleType = Literal["coop", "internship", "new_grad", "job"]

# Python copies of the title patterns in app/services/postings.py, used for the role badge
_COOP_TITLE = re.compile(r"(?i)\b(co-?op|stagiaire)\b")
_INTERN_TITLE = re.compile(r"(?i)\b(intern|interns|internship|student|apprentice)\b")
_NEW_GRAD_TITLE = re.compile(
    r"(?i)\b(new grad(uate)?|university grad(uate)?|early career|graduate program)\b"
)


def role_of(title: str) -> RoleType:
    """Co-op, internship, new grad or regular job, worked out from the title."""
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


# What we send back

class PostingListItem(BaseModel):
    """
    One job in the list.
    Leaves out the description to keep lists small.
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
    # winter, spring, summer or fall, worked out from term. None when the job does not say
    season: Season | None = None
    # The first day of the term like 2027-05-01. None when the term has no year
    term_start: date | None = None
    # 4, 8, 12 or 16. None when the job does not say how long it is
    duration_months: int | None = None
    deadline: date
    posted_at: datetime
    skills: list[str]
    source_url: str | None
    # What the description asks for, grad years and programs. Empty means it did not say
    grad_years: list[int] = []
    fields_of_study: list[str] = []
    closed_at: datetime | None = None
    # Set when the job came from a live employer career board. None for sample, manual or CSV jobs
    source_id: UUID | None = None
    # Only filled in when someone is signed in. None means nobody is
    is_saved: bool | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def role(self) -> RoleType:
        return role_of(self.title)


class PostingDetail(PostingListItem):
    """Everything about one job, description included."""
    description: str
    low_confidence_fields: dict[str, float] | None = None


class Page[T](BaseModel):
    """
    The wrapper every list sends back.
    All list endpoints return Page[SomeItem] so the site always knows the shape.
    """
    items: list[T]
    total: int
    page: int
    page_size: int


# A named version so the router's return type is clear
PostingsPage = Page[PostingListItem]


# Filter choices

class CategoryCount(BaseModel):
    """A job type for the filter list with how many open jobs it has."""
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


class SeasonCount(BaseModel):
    key: Season
    count: int


class DurationCount(BaseModel):
    months: int
    count: int


class ProgramOption(BaseModel):
    key: ProgramKey
    label: str


class FilterMeta(BaseModel):
    """
    The choices for each filter menu.
    They come from the jobs table so the site never offers a city
    that has no jobs.
    """
    cities: list[str]
    provinces: list[str]
    terms: list[str]
    skills: list[str]
    companies: list[str] = []
    categories: list[CategoryCount] = []
    # Open jobs in total. Job types overlap so their counts do not add up to this
    open_jobs: int = 0
    countries: list[CountryCount] = []
    work_modes: list[WorkModeCount] = []
    # Programs a student can pick (see app/services/education.py)
    programs: list[ProgramOption] = []
    # Open jobs by term season and by length. Jobs that do not say are left out of both
    seasons: list[SeasonCount] = []
    durations: list[DurationCount] = []


# Query params

class ManualPostingIn(BaseModel):
    """A job someone adds by hand through POST /api/postings."""

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
    """One problem with one row of a CSV upload."""

    row: int
    column: str
    message: str


class CsvUploadResult(BaseModel):
    """What POST /api/postings/upload sends back."""

    added: int
    skipped_duplicates: int
    errors: list[RowError] = []


class SimilarPostingOut(BaseModel):
    """One job in the similar jobs list."""

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
    """What GET /api/postings/{id}/similar sends back."""

    items: list[SimilarPostingOut]


class PostingListParams(BaseModel):
    """
    Every query param GET /api/postings accepts.

    Pydantic checks these before the router calls the service so the service
    only ever gets clean typed values. A sort value we do not know is a 422
    right away thanks to the Literal type, so there is no list to keep by hand.

    Params with more than one value like duration and skills just repeat
    in the URL like ?skills=React&skills=TypeScript and FastAPI handles it.
    Bad values get a 422 and the site resets those params to their defaults.
    """

    q: str | None = Field(default=None, max_length=200)
    city: str | None = None
    province: str | None = None
    term: str | None = None
    # Term seasons, any of them, like ?season=summer&season=fall
    season: list[Season] | None = None
    work_mode: WorkMode | None = None
    # duration takes a list so you can pick more than one, like 4 or 8 months
    duration: list[int] | None = None
    skills: list[str] | None = None
    # Job types, any of them, worked out from the title (see app/services/categories.py)
    category: list[CategoryKey] | None = None
    # Employers, any of them, using the exact names from /meta/filters
    company: list[str] | None = None
    # Only jobs posted in the last N days
    posted_within: int | None = None
    # Countries, any of CA and US. None means all
    country: list[CountryCode] | None = None
    # Jobs for a program. The description names it or the job fits its job types
    program: ProgramKey | None = None
    # Hide jobs that ask for a different grad year. Jobs that do not say stay in
    grad_year: int | None = Field(default=None, ge=2000, le=2100)
    show_expired: bool = False
    show_closed: bool = False
    # Only internships, co-ops, student and new grad roles, judged by the title
    students_only: bool = False
    # Hide senior, staff, lead, manager and director roles, judged by the title
    hide_senior: bool = False
    search_mode: Literal["keyword", "semantic"] = "keyword"

    # The only sort columns we allow. Anything else is a 422 before the service runs
    # duration_months sorts by length and term_start by when the term begins. Jobs that do not
    # say go last either way
    sort: Literal[
        "posted_at", "deadline", "company", "title", "duration_months", "term_start"
    ] = "posted_at"
    order: Literal["asc", "desc"] = "desc"

    page: int = Field(default=1, ge=1)
    page_size: int = 25

    # Query strings come in as text and Literal int fields reject "10", so these are
    # plain ints checked against the allowed values. Still a 422 when wrong
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
