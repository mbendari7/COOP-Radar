"""
Job Bank, the Government of Canada's job site at jobbank.gc.ca. Every search there has a public
Atom feed, and robots.txt allows it with a 5 second pause between calls. It brings jobs in
every field and every province, from farms and daycares to hospitals and engineering firms,
which no career board list covers. Its "student jobs" and "apprentice jobs" filters are made
for people still in school or in a trade program.

Each feed gives the newest 100 jobs posted in about the last two days: title, employer,
place and pay, no full description. So the source keeps its jobs open after they leave the
feed (rolling_window below) instead of closing them on the next run. Every job links to its
page on Job Bank, where people apply. All the searches run one after another in one source,
so Job Bank never gets two calls closer than 5 seconds apart.

source.config
  queries  feed searches split by "|", each a search word or Job Bank's own filter like
           fjsf=1 (student jobs) or fjap=1 (apprentice jobs). DEFAULT_QUERIES when missing
"""

import asyncio
import re
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl

import feedparser
import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import STUDENT_TITLE, _parse_dt, html_to_text

_FEED = "https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed"
_PAUSE = 5.0  # seconds between feeds, what Job Bank's robots.txt asks for
_MAX_QUERIES = 30

# Student and apprentice jobs first, then words that bring jobs for the college and university
# programs that have co-ops, from nursing and teaching to trades, hospitality and engineering.
# Each one was checked on 2026-10-29 to give jobs for that field and not just any job
DEFAULT_QUERIES = (
    "fjsf=1|fjap=1"
    # Health
    "|nurse|personal support worker|medical laboratory|pharmacy|dental|veterinary"
    "|occupational therapist|paramedic"
    # Education and community services
    "|early childhood educator|teacher|social worker"
    # Engineering, technology and science
    "|technologist|engineer|drafting|laboratory|environmental|agricultural|developer|analyst"
    # Business, law and media
    "|accounting technician|human resources|marketing|logistics|paralegal|graphic designer"
    # Trades and hospitality
    "|electrician|welder|millwright|chef"
)

_PLACE = re.compile(r"([^()<>]+?)\s*\(([A-Z]{2})\)")
_FIELD = re.compile(r"<strong>\s*([^<:]+):\s*</strong>\s*([^<]*)", re.IGNORECASE)


def _params(query: str) -> dict[str, str]:
    """A query like "fjsf=1" is a Job Bank filter, anything else is a search word."""
    if "=" in query:
        return dict(parse_qsl(query))
    return {"searchstring": query}


def _tidy_company(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    # Some employers type their name in capitals. Only fix the ones that are all capitals
    return name.title() if name.isupper() and len(name) > 4 else name


def _tidy_title(title: str, query: dict[str, str]) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    if title.isupper():
        title = title.capitalize()
    elif title[:1].islower():
        title = title[:1].upper() + title[1:]
    # Job Bank marks these as student or apprentice jobs but the title rarely says so.
    # Saying it in the title is how the rest of the site knows a job is open to students
    if not STUDENT_TITLE.search(title):
        if query.get("fjsf") == "1":
            title = f"{title} (student)"
        elif query.get("fjap") == "1":
            title = f"{title} (apprentice)"
    return title


def posting_from_entry(entry: Any, query: dict[str, str]) -> RawPosting | None:
    """One feed entry as a RawPosting, or None when it has no title, employer or job page."""
    link = str(getattr(entry, "link", "") or "")
    ref = re.search(r"jobposting/(\d+)", link)
    summary = str(entry.get("summary", ""))
    fields = {k.strip().lower(): v.strip() for k, v in _FIELD.findall(summary)}
    company = _tidy_company(html_to_text(fields.get("employer", "")))
    title = html_to_text(str(getattr(entry, "title", "") or ""))
    if not ref or not title or not company:
        return None

    place = _PLACE.search(fields.get("location", ""))
    city, province = (place.group(1).strip(), place.group(2)) if place else ("", None)
    salary = fields.get("salary", "")
    description = f"Salary: {salary}.\n\n" if salary else ""
    description += "Full details and how to apply are on the job's page on Job Bank."
    return RawPosting(
        title=_tidy_title(title, query),
        company=company,
        city=city,
        province=province,
        term="",
        work_mode="onsite" if city else None,
        description=description,
        source_ref=ref.group(1),
        source_url=link,
        posted_at=_parse_dt(getattr(entry, "updated", None)),
        country="CA",
    )


class JobBankAdapter(BaseAdapter):
    # Feeds only show the last couple of days, so a job that left the feed is most likely
    # still open. The runner closes it once it was posted this long ago
    rolling_window = timedelta(days=21)

    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        raw = str(config.get("queries") or DEFAULT_QUERIES).split("|")
        queries = [q.strip() for q in raw if q.strip()][:_MAX_QUERIES]

        seen: set[str] = set()
        out: list[RawPosting] = []
        failures = 0
        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": self.user_agent}, follow_redirects=True
        ) as client:
            for i, query in enumerate(queries):
                if i:
                    await asyncio.sleep(_PAUSE)
                params = {**_params(query), "sort": "D"}
                text = await self._get_feed(client, params)
                if text is None:
                    failures += 1
                    continue
                feed = feedparser.parse(text)
                for entry in feed.entries:
                    posting = posting_from_entry(entry, params)
                    if posting is None or posting.source_ref in seen:
                        continue
                    seen.add(posting.source_ref or "")
                    out.append(posting)
        if failures == len(queries):
            raise AdapterError("Job Bank did not answer any of its feeds")
        return out

    @staticmethod
    async def _get_feed(client: httpx.AsyncClient, params: dict[str, str]) -> str | None:
        """The feed's text, trying once more after a pause when Job Bank hiccups. None if not."""
        for attempt in range(2):
            if attempt:
                await asyncio.sleep(_PAUSE)
            try:
                response = await client.get(_FEED, params=params)
            except httpx.HTTPError:
                continue
            if response.status_code == 200:
                return response.text
        return None
