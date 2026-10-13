"""The base adapter and the RawPosting shape every import source fills in."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.ingest_source import IngestSource


class AdapterError(Exception):
    """Raised when an adapter cannot get jobs, like when the server does not answer 200."""


@dataclass
class RawPosting:
    """A job as any adapter hands it over, cleaned up but not saved yet."""

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
    # Extras some sources give us. Career board APIs do and feeds often do not
    province: str | None = None
    posted_at: datetime | None = None
    country: str = "CA"  # "CA" or "US"


class BaseAdapter(ABC):
    """The base class every import source adapter builds on."""

    user_agent: str = "CoopRadar-Ingest/1.0 (+https://github.com/mbendari7/COOP-Radar)"

    @abstractmethod
    async def fetch(self, source: "IngestSource") -> list[RawPosting]:
        """Get raw jobs from the source. Tests should never hit the real network."""
