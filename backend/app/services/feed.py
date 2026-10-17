"""
An RSS feed of jobs for any search, so students get new jobs without checking the site.

GET /api/postings/feed.rss takes the same filters as the job list and gives back the 50 jobs we
added most recently. People paste the link into a feed reader, or into a free feed to email
service, and new jobs show up there on their own. No account and nothing stored.
"""

from collections.abc import Sequence
from email.utils import format_datetime
from xml.sax.saxutils import escape

from app.schemas.posting import PostingListItem


def _summary(p: PostingListItem) -> str:
    where = f"{p.city}, {p.province}" if p.province else p.city
    parts = [where]
    if p.term and p.term != "Open":
        parts.append(f"{p.term} term")
    if p.duration_months:
        parts.append(f"{p.duration_months} months")
    parts.append(f"apply by {p.deadline:%b %d, %Y}")
    return " | ".join(parts)


def build_feed(items: Sequence[PostingListItem], site: str, title: str, link: str) -> str:
    """The RSS 2.0 text for these jobs. site is the website's address, like https://coopradar.ca"""
    site = site.rstrip("/")
    entries = []
    for p in items:
        url = f"{site}/postings/{p.id}"
        seen = p.first_seen_at or p.posted_at
        categories = [p.term] if p.term and p.term != "Open" else []
        if p.duration_months:
            categories.append(f"{p.duration_months} months")
        entries.append(
            "<item>"
            f"<title>{escape(f'{p.title} at {p.company}')}</title>"
            f"<link>{escape(url)}</link>"
            f'<guid isPermaLink="false">coopradar-{p.id}</guid>'
            f"<pubDate>{format_datetime(seen)}</pubDate>"
            f"<description>{escape(_summary(p))}</description>"
            + "".join(f"<category>{escape(c)}</category>" for c in categories)
            + "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        f"<title>{escape(title)}</title>"
        f"<link>{escape(link)}</link>"
        "<description>New jobs on CoopRadar for this search, newest first.</description>"
        "<ttl>360</ttl>"
        + "".join(entries)
        + "</channel></rss>"
    )
