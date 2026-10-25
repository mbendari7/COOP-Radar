"""
Himalayas' public remote jobs API at himalayas.app/jobs/api. Its search for Canada gives about
9,000 remote jobs people in Canada can take, from employers all over the world. No key and no
login, and robots.txt allows it. Each job links to its Himalayas page, which links to the
employer to apply.

We keep the jobs whose list of allowed countries names Canada. A job open to the whole world
names no country, and those are left out unless the source says worldwide, since many of them
are contract gig work and not real roles.

source.config
  query      words to search for, empty for every job
  pages      how many pages of 20 to read, 150 by default and 500 at most
  worldwide  "true" to also keep jobs open to every country
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import _BoardAdapter, html_to_text

_URL = "https://himalayas.app/jobs/api/search"
_MAX_PAGES = 500
_PAUSE = 0.5  # seconds between pages, to be gentle


def _epoch(value: Any) -> datetime | None:
    """Himalayas sends dates as seconds since 1970."""
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def posting_from_job(job: dict[str, Any], *, worldwide: bool = False) -> RawPosting | None:
    """One result as a RawPosting, or None when it is not open to people in Canada."""
    title = str(job.get("title") or "").strip()
    company = str(job.get("companyName") or "").strip()
    if not title or not company:
        return None
    countries = [str(c) for c in job.get("locationRestrictions") or []]
    if "Canada" not in countries and not (worldwide and not countries):
        return None
    description = html_to_text(job.get("description")) or str(job.get("excerpt") or "")
    return _BoardAdapter._posting(
        title=title,
        company=company,
        picked=("Remote, Canada", "CA"),
        work_mode="remote",
        description=description,
        ref=str(job.get("guid") or job.get("applicationLink") or ""),
        url=job.get("applicationLink") or job.get("guid"),
        posted_at=_epoch(job.get("pubDate")),
    )


class HimalayasAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        query = str(config.get("query") or "")
        pages = max(1, min(int(config.get("pages") or 150), _MAX_PAGES))
        worldwide = str(config.get("worldwide") or "").lower() == "true"

        seen: set[str] = set()
        out: list[RawPosting] = []
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            for page in range(1, pages + 1):
                params: dict[str, str | int] = {"country": "Canada", "page": page}
                if query:
                    params["q"] = query
                try:
                    response = await client.get(_URL, params=params)
                except httpx.HTTPError as exc:
                    raise AdapterError(f"Could not reach Himalayas: {exc}") from exc
                if response.status_code == 429:
                    return out  # asked to slow down, keep what we have
                if response.status_code != 200:
                    raise AdapterError(f"HTTP {response.status_code} from Himalayas")
                jobs = (response.json() or {}).get("jobs") or []
                for job in jobs:
                    ref = str(job.get("guid") or "")
                    if not ref or ref in seen:
                        continue
                    seen.add(ref)
                    posting = posting_from_job(job, worldwide=worldwide)
                    if posting is not None:
                        out.append(posting)
                if len(jobs) < 20:
                    break
                await asyncio.sleep(_PAUSE)
        return out
