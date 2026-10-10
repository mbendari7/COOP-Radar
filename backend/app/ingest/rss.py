"""RssAdapter — fetches postings from an RSS/Atom feed using feedparser."""

import asyncio
from datetime import date
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser  # type: ignore[import-untyped]

from app.ingest.base import AdapterError, BaseAdapter, RawPosting


class RssAdapter(BaseAdapter):
    """
    Fetches postings from an RSS or Atom feed.

    source.config must contain:
      - url: str  — the feed URL
    """

    async def fetch(self, source: Any) -> list[RawPosting]:  # type: ignore[override]
        config = source.config
        url = config.get("url", "")

        # feedparser is synchronous — run it in a thread pool to avoid blocking
        feed = await asyncio.to_thread(feedparser.parse, url)

        if feed.bozo and not feed.entries:
            raise AdapterError(f"RssAdapter failed to parse feed: {url}")

        return [self._map(entry) for entry in feed.entries]

    def _map(self, entry: Any) -> RawPosting:
        title = getattr(entry, "title", "") or ""
        company = getattr(entry, "author", "") or ""
        link = getattr(entry, "link", None)
        summary = getattr(entry, "summary", None)

        # Try to parse deadline from published date
        deadline: date | None = None
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed:
            import time
            try:
                deadline = date.fromtimestamp(time.mktime(published_parsed))
            except (ValueError, OverflowError):
                deadline = None

        # Source ref is the entry id or link
        source_ref = getattr(entry, "id", None) or link or title

        return RawPosting(
            title=title,
            company=company,
            city="",  # RSS feeds typically don't provide city; extract_fields will fill
            term="",  # Same — will be extracted
            work_mode=None,
            deadline=deadline,
            description=summary,
            skills=[],
            source_ref=source_ref,
            source_url=link,
        )
