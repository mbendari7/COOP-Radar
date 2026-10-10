"""Pydantic schemas for admin ingest source and run endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IngestSourceOut(BaseModel):
    """Public representation of an IngestSource."""

    id: UUID
    name: str
    adapter_type: str
    enabled: bool
    auto_paused: bool
    last_run_at: datetime | None
    last_run_status: str | None
    last_run_added: int | None
    last_run_updated: int | None
    last_run_closed: int | None
    last_run_errors: int | None


class IngestRunOut(BaseModel):
    """Public representation of an IngestRun."""

    id: UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    added: int
    updated: int
    closed: int
    errors: int
    error_log: list[str]


class RunsPage(BaseModel):
    """Paginated list of IngestRun objects."""

    items: list[IngestRunOut]
    total: int
    page: int
    page_size: int


class SourcePatchIn(BaseModel):
    """Fields that can be patched on an IngestSource (all optional)."""

    enabled: bool | None = None
    auto_paused: bool | None = None


class TriggerRunOut(BaseModel):
    """Response from POST /api/admin/sources/{id}/run."""

    run_id: UUID
    message: str
