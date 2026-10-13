"""Gets jobs from an RSS or Atom feed with feedparser."""

import asyncio
from datetime import date
from typing import Any

import feedparser

from app.ingest.base import AdapterError, BaseAdapter, RawPosting


class RssAdapter(BaseAdapter):
    """
    Gets jobs from an RSS or Atom feed.

    source.config needs
      url  the feed address
    """

    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config
        url = config.get("url", "")

        # feedparser is not async so run it in a thread to keep things moving
        feed = await asyncio.to_thread(feedparser.parse, url)

        if feed.bozo and not feed.entries:
            raise AdapterError(f"RssAdapter failed to parse feed: {url}")

        return [self._map(entry) for entry in feed.entries]

    def _map(self, entry: Any) -> RawPosting:
        title = getattr(entry, "title", "") or ""
        company = getattr(entry, "author", "") or ""
        link = getattr(entry, "link", None)
        summary = getattr(entry, "summary", None)

        # Try to read a deadline from the published date
        deadline: date | None = None
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed:
            import time
            try:
                deadline = date.fromtimestamp(time.mktime(published_parsed))
            except (ValueError, OverflowError):
                deadline = None

        # The source ref is the entry id or link
        source_ref = getattr(entry, "id", None) or link or title

        return RawPosting(
            title=title,
            company=company,
            city="",  # feeds rarely give a city so extract_fields fills it in
            term="",  # same here, it gets pulled out later
            work_mode=None,
            deadline=deadline,
            description=summary,
            skills=[],
            source_ref=source_ref,
            source_url=link,
        )
