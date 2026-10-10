"""
Pydantic schemas for saved postings endpoints.

Shapes match the API contracts in specs/002-accounts-tracker/contracts/api.md.
SavedPostingOut embeds the PostingListItem so the frontend gets all posting
fields in a single response without a second request.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.saved_posting import ApplicationStatus
from app.schemas.posting import PostingListItem


class SaveIn(BaseModel):
    """Body for POST /api/saved — just the posting ID to bookmark."""
    posting_id: UUID


class StatusUpdateIn(BaseModel):
    """Body for PATCH /api/saved/{id}/status — pass null to clear the status."""
    status: ApplicationStatus | None


class SavedPostingOut(BaseModel):
    """
    A saved posting record with the full posting embedded.
    Returned by GET /api/saved items and POST/PATCH operations.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    saved_at: datetime
    status: ApplicationStatus | None
    posting: PostingListItem


class SavedPostingsPage(BaseModel):
    """Paginated list of saved postings with per-status counts."""
    items: list[SavedPostingOut]
    total: int
    page: int
    page_size: int
    # Count of saved postings per status + "none" for unset
    status_counts: dict[str, int]
