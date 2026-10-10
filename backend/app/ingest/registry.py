"""Adapter registry — maps adapter_type string to the appropriate adapter class."""

from app.ingest.base import BaseAdapter
from app.ingest.json_api import JsonApiAdapter
from app.ingest.rss import RssAdapter


def adapter_for(source: object) -> BaseAdapter:
    """
    Factory that returns the correct BaseAdapter instance for the given source.

    Raises ValueError for unknown adapter_type values.
    """
    adapter_type = getattr(source, "adapter_type", "")
    if adapter_type == "json_api":
        return JsonApiAdapter()
    if adapter_type == "rss":
        return RssAdapter()
    raise ValueError(f"Unknown adapter_type: {adapter_type!r}")
