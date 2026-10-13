"""Maps each adapter_type name to its adapter class."""

from app.ingest.base import BaseAdapter
from app.ingest.boards import (
    AshbyAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
)
from app.ingest.json_api import JsonApiAdapter
from app.ingest.rss import RssAdapter

_ADAPTERS: dict[str, type[BaseAdapter]] = {
    "json_api": JsonApiAdapter,
    "rss": RssAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "smartrecruiters": SmartRecruitersAdapter,
}


def adapter_for(source: object) -> BaseAdapter:
    """
    Gives back the right adapter for this source.

    Raises ValueError for an adapter_type we do not know.
    """
    adapter_type = getattr(source, "adapter_type", "")
    if adapter_type not in _ADAPTERS:
        raise ValueError(f"Unknown adapter_type: {adapter_type!r}")
    return _ADAPTERS[adapter_type]()
