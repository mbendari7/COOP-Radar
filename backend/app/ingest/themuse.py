"""
The Muse's public jobs API at themuse.com/api/public/jobs. It lists about 10,000 internships
from US and Canadian employers in every field, each one tagged with its level, so one source
brings in student roles from companies that are not on our list of career boards. No key is
needed for up to 500 calls an hour, and robots.txt allows /api/public.

Its location filter mostly gives back remote US jobs for Canadian cities, so we read the
internship level and let choose_location keep the Canadian places and the US student roles.
Each job links to its page on The Muse, which links to the employer to apply.

source.config
  levels        levels to read, split by "|", "Internship" by default
  pages         how many pages of 20 to read per level, 100 by default and 400 at most
  max_age_days  skip jobs posted longer ago than this, 90 by default
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import _BoardAdapter, _parse_dt, _work_mode, choose_location, html_to_text

_URL = "https://www.themuse.com/api/public/jobs"
_MAX_PAGES = 400
_PAUSE = 0.4  # seconds between pages, to stay well under 500 calls an hour


def posting_from_job(job: dict[str, Any], *, max_age_days: int = 90) -> RawPosting | None:
    """
    One result as a RawPosting, or None when it is not a job we keep. The Muse still lists
    some jobs from years back, so anything posted more than max_age_days ago is left out.
    """
    title = str(job.get("name") or "").strip()
    company = str((job.get("company") or {}).get("name") or "").strip()
    if not title or not company:
        return None
    posted = _parse_dt(job.get("publication_date"))
    if posted is None or posted < datetime.now(UTC) - timedelta(days=max_age_days):
        return None
    places = [str(loc.get("name") or "") for loc in job.get("locations") or []]
    remote = any("remote" in p.lower() for p in places)
    levels = {str(lv.get("name") or "").lower() for lv in job.get("levels") or []}
    picked = choose_location(title, *places, early_career="internship" in levels)
    if picked is None:
        return None
    return _BoardAdapter._posting(
        title=title,
        company=company,
        picked=picked,
        work_mode=_work_mode(picked[0], "remote" if remote and len(places) == 1 else None),
        description=html_to_text(job.get("contents")),
        ref=str(job.get("id") or ""),
        url=(job.get("refs") or {}).get("landing_page"),
        posted_at=posted,
    )


class TheMuseAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        raw_levels = str(config.get("levels") or "Internship").split("|")
        levels = [x.strip() for x in raw_levels if x.strip()]
        pages = max(1, min(int(config.get("pages") or 100), _MAX_PAGES))
        max_age = int(config.get("max_age_days") or 90)

        seen: set[str] = set()
        out: list[RawPosting] = []
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            for level in levels:
                for page in range(pages):
                    params: dict[str, str | int] = {
                        "page": page, "level": level, "descending": "true",
                    }
                    try:
                        response = await client.get(_URL, params=params)
                    except httpx.HTTPError as exc:
                        raise AdapterError(f"Could not reach The Muse: {exc}") from exc
                    if response.status_code == 429:
                        return out  # used up this hour's calls, keep what we have
                    if response.status_code != 200:
                        raise AdapterError(f"HTTP {response.status_code} from The Muse")
                    data = response.json() or {}
                    for job in data.get("results") or []:
                        ref = str(job.get("id") or "")
                        if not ref or ref in seen:
                            continue
                        seen.add(ref)
                        posting = posting_from_job(job, max_age_days=max_age)
                        if posting is not None:
                            out.append(posting)
                    if not data.get("results") or page + 1 >= int(data.get("page_count") or 0):
                        break
                    await asyncio.sleep(_PAUSE)
        return out
