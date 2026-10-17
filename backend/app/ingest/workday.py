"""
Workday career sites, used by most big employers outside tech. Banks, insurers, energy,
health care, pharma, aerospace, retail, consulting and universities.

Every Workday careers page like td.wd3.myworkdayjobs.com/TD_Bank_Careers loads its jobs from
a public JSON endpoint on the same site, with no login. robots.txt on these sites allows the
careers pages. We read the list, keep the jobs we want, then get each kept job's details,
which give the location with its country, the closing date and the full description.
Every job links back to the employer's own Workday page to apply.

source.config
  board     "<tenant>.<wdN>/<site>", like "td.wd3/TD_Bank_Careers"
  company   the name we show, like "TD"
  scope     Every job the list shows in Canada is always kept, whatever the scope.
            For jobs elsewhere, "students" keeps student, early career and campus roles and
            "all" checks every job against settings.ingest_us_jobs.
            "auto", the default, is all for sites with up to 300 jobs and students for bigger
            ones, since big employers list thousands of US branch and store jobs
  city, province   optional. Where Canadian jobs are when the site only names a building,
            like McGill listing "Bronfman Building". Used only when no province is found
"""

import asyncio
import re
from typing import Any

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import (
    EARLY_CAREER_TITLE,
    _BoardAdapter,
    _details,
    _is_canadian,
    _parse_dt,
    _work_mode,
    choose_location,
    html_to_text,
)

_PAGE = 20  # Workday will not send more than 20 at a time
_MAX_JOBS = 3000
_PAGE_CONCURRENCY = 4
_AUTO_ALL_UP_TO = 300
# Workday sorts jobs into groups like "Campus" or "Interns & Associates". These mean students
_CAMPUS = re.compile(
    r"(?i)\b(campus|intern\w*|co-?op|students?|early (career|talent)|university|graduate program"
    r"|summer)\b"
)
_BOARD = re.compile(r"^(?P<tenant>[\w-]+)\.(?P<wd>wd\d+)/(?P<site>[\w-]+)$")
_COUNTRY_WORDS = {"canada": "CA", "united states of america": "US", "united states": "US"}


def parse_board(board: str) -> tuple[str, str, str]:
    """"td.wd3/TD_Bank_Careers" gives the host, the API base and the public site base."""
    m = _BOARD.match(board.strip())
    if not m:
        raise AdapterError(f"Workday board must look like tenant.wd3/Site, got {board!r}")
    host = f"https://{m['tenant']}.{m['wd']}.myworkdayjobs.com"
    return host, f"{host}/wday/cxs/{m['tenant']}/{m['site']}", f"{host}/{m['site']}"


def wanted_by_scope(job: dict[str, Any], scope: str) -> bool:
    """True when the list entry is a role this source keeps."""
    if scope == "all":
        return True
    title = str(job.get("title") or "")
    groups = " ".join(str(b) for b in job.get("bulletFields") or [])
    return bool(EARLY_CAREER_TITLE.search(title) or _CAMPUS.search(f"{title} {groups}"))


def listed_in_canada(job: dict[str, Any]) -> bool:
    """The list entry already shows a Canadian place. These jobs are kept whatever the scope."""
    return _is_canadian(str(job.get("locationsText") or ""))


def _country(info: dict[str, Any]) -> str:
    for holder in (info.get("country"), (info.get("jobRequisitionLocation") or {}).get("country")):
        if isinstance(holder, dict):
            code = str(holder.get("alpha2Code") or "").upper()
            if code:
                return code
            word = _COUNTRY_WORDS.get(str(holder.get("descriptor") or "").lower())
            if word:
                return word
    return ""


def posting_from_detail(
    detail: Any, company: str, public_base: str, path: str,
    home: tuple[str, str] | None = None,
) -> RawPosting | None:
    """One RawPosting from a Workday job detail reply, or None when it is not in a place we keep."""
    info = (detail or {}).get("jobPostingInfo") if isinstance(detail, dict) else None
    if not isinstance(info, dict):
        return None
    title = str(info.get("title") or "").strip()
    primary = str(info.get("location") or "")
    extra = [str(x) for x in info.get("additionalLocations") or []]
    country = _country(info)
    hinted = [f"{primary}, Canada"] if country == "CA" else (
        [f"{primary}, United States"] if country == "US" else []
    )
    picked = choose_location(title, *hinted, primary, *extra)
    if picked is None:
        return None
    # Show the plain place, not our hint, and keep the country we were told when there is one
    place = primary if hinted and picked[0] == hinted[0] else picked[0]
    deadline = _parse_dt(info.get("endDate"))
    raw = _BoardAdapter._posting(
        title=title,
        company=company,
        picked=(place, picked[1]),
        work_mode=_work_mode(place, str(info.get("remoteType") or "")),
        description=html_to_text(info.get("jobDescription")),
        ref=str(info.get("jobReqId") or info.get("id") or path),
        url=info.get("externalUrl") or f"{public_base}{path}",
        posted_at=_parse_dt(info.get("startDate")),
        deadline=deadline.date() if deadline else None,
    )
    if home and raw.country == "CA" and not raw.province and raw.city != "Remote":
        raw.city, raw.province = home
    return raw


class WorkdayAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        _host, api, public = parse_board(str(config.get("board") or ""))
        company = str(config.get("company") or "")
        scope = str(config.get("scope") or "auto")
        home = None
        if config.get("city"):
            home = (str(config["city"]), str(config.get("province") or ""))

        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            transport=transport,
        ) as client:
            jobs, total = await self._list(client, api)
            if scope not in ("all", "students"):
                scope = "all" if total <= _AUTO_ALL_UP_TO else "students"
            kept = [
                j for j in jobs
                if j.get("externalPath") and (wanted_by_scope(j, scope) or listed_in_canada(j))
            ]
            if scope == "all":
                kept = [j for j in kept if _maybe_ours(str(j.get("title") or ""),
                                                       str(j.get("locationsText") or ""))]
            paths = [str(j["externalPath"]) for j in kept]
            details = await _details(client, [f"{api}{p}" for p in paths])

        out = [
            posting_from_detail(d, company, public, p, home)
            for d, p in zip(details, paths, strict=True)
        ]
        return [p for p in out if p is not None]

    async def _list(
        self, client: httpx.AsyncClient, api: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Every job summary on the site, up to _MAX_JOBS, and how many the site says it has."""
        first = await _search(client, api, 0)
        reported = int(first.get("total") or 0)
        total = min(reported, _MAX_JOBS)
        jobs = list(first.get("jobPostings") or [])
        gate = asyncio.Semaphore(_PAGE_CONCURRENCY)

        async def page(offset: int) -> list[dict[str, Any]]:
            async with gate:
                try:
                    return list((await _search(client, api, offset)).get("jobPostings") or [])
                except AdapterError:
                    return []

        for chunk in await asyncio.gather(*(page(o) for o in range(_PAGE, total, _PAGE))):
            jobs.extend(chunk)
        return jobs, reported


async def _search(client: httpx.AsyncClient, api: str, offset: int) -> dict[str, Any]:
    body = {"appliedFacets": {}, "limit": _PAGE, "offset": offset, "searchText": ""}
    try:
        response = await client.post(f"{api}/jobs", json=body)
    except httpx.HTTPError as exc:
        raise AdapterError(f"Could not reach {api}: {exc}") from exc
    if response.status_code != 200:
        raise AdapterError(f"HTTP {response.status_code} from {api}/jobs")
    try:
        data = response.json()
    except ValueError as exc:
        raise AdapterError(f"Invalid JSON from {api}/jobs") from exc
    if not isinstance(data, dict):
        raise AdapterError(f"Unexpected reply from {api}/jobs")
    return data


def _maybe_ours(title: str, locations_text: str) -> bool:
    """
    Before getting details for every job on a big site, skip the ones the list already shows
    are somewhere we never keep. "3 Locations" could be anywhere so those stay.
    """
    if re.search(r"(?i)\d+\s+locations", locations_text) or not locations_text:
        return True
    return choose_location(title, locations_text) is not None
