"""
Shapes for the saved jobs endpoints.

They match the contracts in specs/002-accounts-tracker/contracts/api.md.
SavedPostingOut carries the whole PostingListItem so the site gets every
job field in one response without asking twice.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.saved_posting import ApplicationStatus
from app.schemas.posting import PostingListItem


class ApplicationEventOut(BaseModel):
    """One entry in a saved job's status history."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ApplicationStatus
    notes: str | None
    event_date: date | None
    created_at: datetime


class EventCreateIn(BaseModel):
    """Body for POST /api/saved/{id}/events. Logs a status change with an optional note."""
    status: ApplicationStatus
    notes: str | None = None
    event_date: date | None = None


class SaveIn(BaseModel):
    """Body for POST /api/saved. Just the id of the job to save."""
    posting_id: UUID


class StatusUpdateIn(BaseModel):
    """Body for PATCH /api/saved/{id}/status. Send null to clear the status."""
    status: ApplicationStatus | None
    # An optional note saved with the status change
    notes: str | None = None
    event_date: date | None = None


class SavedPostingOut(BaseModel):
    """
    A saved job with the whole posting inside it.
    GET /api/saved items and the POST and PATCH calls send this back.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    saved_at: datetime
    last_status_at: datetime | None
    status: ApplicationStatus | None
    posting: PostingListItem
    events: list[ApplicationEventOut] = []


class SavedPostingsPage(BaseModel):
    """A page of saved jobs with a count for each status."""
    items: list[SavedPostingOut]
    total: int
    page: int
    page_size: int
    # How many saved jobs are in each status plus "none" for no status
    status_counts: dict[str, int]
    # Numbers for the stats panel
    total_applied: int
    total_interview: int
    total_offer: int
    # Deadlines in the next 7 days with job ids
    deadlines_this_week: list[dict[str, str]]
