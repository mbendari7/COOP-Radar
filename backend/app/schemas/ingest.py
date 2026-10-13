"""Shapes for the admin import source and run endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IngestSourceOut(BaseModel):
    """An import source as we send it out."""

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
    """One import run as we send it out."""

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
    """A page of import runs."""

    items: list[IngestRunOut]
    total: int
    page: int
    page_size: int


class SourcePatchIn(BaseModel):
    """What you can change on a source. Everything is optional."""

    enabled: bool | None = None
    auto_paused: bool | None = None


class TriggerRunOut(BaseModel):
    """What POST /api/admin/sources/{id}/run sends back."""

    run_id: UUID
    message: str
