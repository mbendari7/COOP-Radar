"""
Oracle Cloud career sites, used by many big employers and public bodies, like Nokia, pension
plans, utilities, hospitals and universities. Their pages look like
fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/41311.

Every one of these pages loads its jobs from a public JSON endpoint on the same site with no
key and no login (recruitingCEJobRequisitions). We read the list 200 at a time, keep the jobs in
Canada and the US ones settings.ingest_us_jobs allows, then get each kept job's description.
Every job links back to the employer's own page to apply.

source.config
  board     "<host>/<site number>", like "fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/CX_1"
  company   the name we show, like "Nokia"
"""

import re
from typing import Any
from urllib.parse import quote

import httpx

from app.ingest.base import AdapterError, RawPosting
from app.ingest.boards import (
    _BoardAdapter,
    _details,
    _get_json,
    _parse_dt,
    _work_mode,
    choose_location,
    html_to_text,
)

_PAGE = 200
_MAX_JOBS = 3000
_BOARD = re.compile(r"^(?P<host>[a-z0-9.-]+\.oraclecloud\.com)/(?P<site>[A-Za-z0-9_]+)$")
_COUNTRIES = {"CA": "Canada", "US": "United States"}


def parse_board(board: str) -> tuple[str, str]:
    """'host/CX_1' gives the host and the site number."""
    m = _BOARD.match(board.strip())
    if not m:
        raise AdapterError(f"Oracle board must look like host.oraclecloud.com/CX_1, got {board!r}")
    return m["host"], m["site"]


def list_url(host: str, site: str, offset: int) -> str:
    return (
        f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
        f"&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber={site},"
        f"limit={_PAGE},offset={offset},sortBy=POSTING_DATES_DESC"
    )


def detail_url(host: str, site: str, job_id: str) -> str:
    finder = quote(f'ById;Id="{job_id}",siteNumber={site}', safe=";=,")
    return (
        f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
        f"?expand=all&onlyData=true&finder={finder}"
    )


def places(job: dict[str, Any]) -> list[str]:
    """The job's place with its country spelled out, then its other places."""
    primary = str(job.get("PrimaryLocation") or "")
    country = _COUNTRIES.get(str(job.get("PrimaryLocationCountry") or "").upper())
    out = [primary]
    if country and country.lower() not in primary.lower():
        out.append(f"{primary}, {country}" if primary else country)
    for loc in job.get("secondaryLocations") or []:
        name = str(loc.get("Name") or "")
        code = _COUNTRIES.get(str(loc.get("CountryCode") or "").upper())
        if name:
            out.append(f"{name}, {code}" if code and code.lower() not in name.lower() else name)
    return [p for p in out if p]


class OracleAdapter(_BoardAdapter):
    async def collect(
        self, client: httpx.AsyncClient, board: str, company: str
    ) -> list[RawPosting | None]:
        host, site = parse_board(board)
        jobs: list[dict[str, Any]] = []
        offset = 0
        while offset < _MAX_JOBS:
            data = await _get_json(client, list_url(host, site, offset))
            found = ((data.get("items") or [{}])[0]) if isinstance(data, dict) else {}
            page = found.get("requisitionList") or []
            jobs.extend(page)
            offset += _PAGE
            if not page or offset >= int(found.get("TotalJobsCount") or 0):
                break

        kept: list[tuple[dict[str, Any], tuple[str, str]]] = []
        for job in jobs:
            picked = choose_location(str(job.get("Title") or ""), *places(job))
            if picked is not None:
                kept.append((job, picked))

        details = await _details(
            client, [detail_url(host, site, str(j.get("Id"))) for j, _ in kept]
        )
        out: list[RawPosting | None] = []
        for (job, picked), detail in zip(kept, details, strict=True):
            info = ((detail or {}).get("items") or [{}])[0] if isinstance(detail, dict) else {}
            description = "\n\n".join(
                html_to_text(info.get(key))
                for key in ("ExternalDescriptionStr", "ExternalResponsibilitiesStr",
                            "ExternalQualificationsStr")
                if info.get(key)
            ) or str(job.get("ShortDescriptionStr") or "")
            # The list often names only the country. The details have the city and province
            for loc in info.get("workLocation") or []:
                town, region = loc.get("TownOrCity"), loc.get("Region2") or loc.get("Region1")
                country = _COUNTRIES.get(str(loc.get("Country") or "").upper())
                if town and country:
                    better = choose_location(
                        str(job.get("Title") or ""),
                        ", ".join(str(v) for v in (town, region, country) if v),
                    )
                    if better is not None and better[1] == picked[1]:
                        picked = better
                    break
            end = _parse_dt(job.get("PostingEndDate"))
            out.append(self._posting(
                title=str(job.get("Title") or ""),
                company=company,
                picked=picked,
                work_mode=_work_mode(picked[0], str(job.get("WorkplaceType") or "")),
                description=description,
                ref=str(job.get("Id")),
                url=f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{job.get('Id')}",
                posted_at=_parse_dt(info.get("ExternalPostedStartDate") or job.get("PostedDate")),
                deadline=end.date() if end else None,
            ))
        return out
