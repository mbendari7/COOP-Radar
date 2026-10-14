"""
Workable's public job search at jobs.workable.com. Thousands of small and mid size employers
in every field post on Workable, so one source brings in the niche companies that are not on
our list of career boards. No key and no login. robots.txt on jobs.workable.com allows it.

We page through the search for a country, keep the jobs in Canada and the US student roles
settings.ingest_us_jobs allows, and link each job to its own Workable page to apply.

source.config
  location   the country to search, "Canada" (the default) or "United States"
  queries    words to search for, split by "|", like "intern|co-op|student". Empty means every job
  pages      how many pages of 20 to read per query, 400 by default (Canada has about 7,500 jobs)
"""

import asyncio
from typing import Any

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import _BoardAdapter, _parse_dt, _work_mode, choose_location, html_to_text

_URL = "https://jobs.workable.com/api/v1/jobs"
_MAX_PAGES = 400
_PAUSE = 0.25  # seconds between pages, to be gentle


def posting_from_job(job: dict[str, Any]) -> RawPosting | None:
    """One search result as a RawPosting, or None when it is not a job we keep."""
    title = str(job.get("title") or "").strip()
    company = str((job.get("company") or {}).get("title") or "").strip()
    if not title or not company or job.get("state") not in (None, "published"):
        return None
    loc = job.get("location") or {}
    parts = [str(loc.get(k) or "") for k in ("city", "subregion", "countryName")]
    main = ", ".join(p for p in parts if p)
    picked = choose_location(title, main, *[str(x) for x in job.get("locations") or []])
    if picked is None:
        return None
    sections = [job.get("description"), job.get("requirementsSection"), job.get("benefitsSection")]
    description = "\n\n".join(html_to_text(s) for s in sections if s)
    return _BoardAdapter._posting(
        title=title,
        company=company,
        picked=(main, picked[1]) if main else picked,
        work_mode=_work_mode(main, str(job.get("workplace") or "").replace("_", "-")),
        description=description,
        ref=str(job.get("id") or ""),
        url=job.get("url"),
        posted_at=_parse_dt(job.get("created")),
    )


class WorkableAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        location = str(config.get("location") or "Canada")
        queries = [q.strip() for q in str(config.get("queries") or "").split("|")] or [""]
        pages = max(1, min(int(config.get("pages") or _MAX_PAGES), _MAX_PAGES))

        seen: set[str] = set()
        out: list[RawPosting] = []
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            for query in queries:
                token: str | None = None
                for _ in range(pages):
                    params = {"location": location, "query": query}
                    if token:
                        params["pageToken"] = token
                    try:
                        response = await client.get(_URL, params=params)
                    except httpx.HTTPError as exc:
                        raise AdapterError(f"Could not reach Workable: {exc}") from exc
                    if response.status_code != 200:
                        raise AdapterError(f"HTTP {response.status_code} from Workable")
                    data = response.json() or {}
                    for job in data.get("jobs") or []:
                        ref = str(job.get("id") or "")
                        if not ref or ref in seen:
                            continue
                        seen.add(ref)
                        posting = posting_from_job(job)
                        if posting is not None:
                            out.append(posting)
                    token = data.get("nextPageToken")
                    if not token or not data.get("jobs"):
                        break
                    await asyncio.sleep(_PAUSE)
        return out
