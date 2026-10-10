"""Base adapter ABC and RawPosting dataclass for ingest sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.ingest_source import IngestSource


class AdapterError(Exception):
    """Raised when an adapter cannot fetch postings (e.g. non-200 HTTP response)."""


@dataclass
class RawPosting:
    """Normalised posting data as returned by any adapter before DB insertion."""

    title: str
    company: str
    city: str
    term: str
    work_mode: str | None = None
    deadline: date | None = None
    description: str | None = None
    skills: list[str] = field(default_factory=list)
    source_ref: str | None = None
    source_url: str | None = None


class BaseAdapter(ABC):
    """Abstract base class for all ingestion source adapters."""

    user_agent: str = "CoopRadar-Ingest/1.0 (+https://github.com/mbendari7/COOP-Radar)"

    @abstractmethod
    async def fetch(self, source: "IngestSource") -> list[RawPosting]:
        """Fetch raw postings from the source. Must not make live network calls in tests."""
