"""
Adzuna, a job search API that gathers postings from thousands of employer sites and job
boards in every field. Optional. It only runs when the owner sets ADZUNA_APP_ID and
ADZUNA_APP_KEY (free at developer.adzuna.com), and seed/job_boards.py only adds the
source when they are set.

Adzuna's terms ask sites to credit them, so these jobs say "via Adzuna" on the details panel
and the apply link goes through Adzuna to the employer's posting. Adzuna gives a short part
of the description, so the employer's page has the rest.

source.config
  country   "ca" (the default) or "us"
  what_or   words, any of which a job title or description has, like "co-op intern student"
  pages     how many pages of 50 to read, 10 by default
"""

from typing import Any

import httpx

from app.config import get_settings
from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import STUDENT_TITLE, _parse_dt, _work_mode, html_to_text

_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
_PROVINCES = {
    "ontario": "ON", "british columbia": "BC", "quebec": "QC", "québec": "QC", "alberta": "AB",
    "manitoba": "MB", "saskatchewan": "SK", "nova scotia": "NS", "new brunswick": "NB",
    "newfoundland and labrador": "NL", "prince edward island": "PE",
}
DEFAULT_WHAT_OR = "co-op coop intern internship student summer apprentice"


def adzuna_configured() -> bool:
    s = get_settings()
    return bool(s.adzuna_app_id and s.adzuna_app_key)


def posting_from_result(job: dict[str, Any], country: str) -> RawPosting | None:
    title = html_to_text(str(job.get("title") or "")).strip()
    if not title:
        return None
    if country == "us" and not STUDENT_TITLE.search(title):
        return None  # same rule as the career boards, US jobs are student roles only
    location = job.get("location") or {}
    area = [str(a) for a in location.get("area") or []]
    province = ""
    city = ""
    if country == "ca":
        province = _PROVINCES.get(area[1].lower(), "") if len(area) > 1 else ""
        city = area[-1] if len(area) > 2 else ""
    else:
        city = area[-1] if len(area) > 2 else ""
    display = str(location.get("display_name") or "")
    company = str((job.get("company") or {}).get("display_name") or "").strip()
    if not company:
        return None
    return RawPosting(
        title=title,
        company=company,
        city=city or ("Canada" if country == "ca" else "United States"),
        province=province,
        country="CA" if country == "ca" else "US",
        term="",
        work_mode=_work_mode(f"{display} {title}"),
        description=html_to_text(str(job.get("description") or "")),
        source_ref=str(job.get("id") or ""),
        source_url=job.get("redirect_url"),
        posted_at=_parse_dt(job.get("created")),
    )


class AdzunaAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        settings = get_settings()
        if not adzuna_configured():
            raise AdapterError("ADZUNA_APP_ID and ADZUNA_APP_KEY are not set")
        config = source.config or {}
        country = "us" if config.get("country") == "us" else "ca"
        what_or = str(config.get("what_or") or DEFAULT_WHAT_OR)
        pages = max(1, min(int(config.get("pages") or 10), 40))

        out: list[RawPosting] = []
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for page in range(1, pages + 1):
                params: dict[str, str | int] = {
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "results_per_page": 50,
                    "what_or": what_or,
                    "max_days_old": 45,
                    "content-type": "application/json",
                }
                try:
                    url = _URL.format(country=country, page=page)
                    response = await client.get(url, params=params)
                except httpx.HTTPError as exc:
                    raise AdapterError(f"Could not reach Adzuna: {exc}") from exc
                if response.status_code != 200:
                    # Never echo the URL, it has the key in it
                    raise AdapterError(f"HTTP {response.status_code} from Adzuna")
                results = (response.json() or {}).get("results") or []
                for job in results:
                    posting = posting_from_result(job, country)
                    if posting is not None:
                        out.append(posting)
                if len(results) < 50:
                    break
        return out
