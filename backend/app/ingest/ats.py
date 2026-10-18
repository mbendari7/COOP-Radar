"""
More hiring systems with public job lists, used by thousands of small and mid size employers:

  Recruitee   https://<board>.recruitee.com/api/offers/            every job with its description
  BambooHR    https://<board>.bamboohr.com/careers/list            the list, then one detail per job
  Rippling    https://api.rippling.com/platform/api/ats/v1/board/<board>/jobs   same idea

All three are the same public lists the employer's own careers page reads, with no key and no
login, and their robots.txt files allow them. Like the other boards we keep every job in Canada
and the US ones settings.ingest_us_jobs allows.
"""

from typing import Any

import httpx

from app.ingest.base import RawPosting
from app.ingest.boards import (
    _BoardAdapter,
    _details,
    _get_json,
    _parse_dt,
    _work_mode,
    choose_location,
    html_to_text,
)

_COUNTRY_NAMES = {"CA": "Canada", "US": "United States"}


def _with_country(place: str, country: str | None) -> list[str]:
    """The place as is, plus the place with its country added so choose_location can tell."""
    name = _COUNTRY_NAMES.get((country or "").upper(), country or "")
    places = [place] if place else []
    if name and name.lower() not in place.lower():
        places.append(f"{place}, {name}" if place else name)
    return places


class RecruiteeAdapter(_BoardAdapter):
    url_template = "https://{board}.recruitee.com/api/offers/"

    def parse(self, data: Any, company: str) -> list[RawPosting | None]:
        out: list[RawPosting | None] = []
        for job in (data or {}).get("offers") or []:
            if job.get("status") not in (None, "published"):
                continue
            title = str(job.get("title") or "")
            place = ", ".join(str(v) for v in (job.get("city"), job.get("state_name")) if v)
            places = _with_country(place, job.get("country_code") or job.get("country"))
            for loc in job.get("locations") or []:
                keys = ("city", "state", "country")
                extra = ", ".join(str(loc.get(k)) for k in keys if loc.get(k))
                if extra:
                    places.append(extra)
            if job.get("remote") and job.get("country"):
                places.append(f"Remote, {job.get('country')}")
            picked = choose_location(title, *places)
            if picked is None:
                continue
            mode = "remote" if job.get("remote") else "hybrid" if job.get("hybrid") else None
            description = "\n\n".join(
                html_to_text(job.get(key))
                for key in ("description", "requirements")
                if job.get(key)
            )
            out.append(self._posting(
                title=title,
                company=company,
                picked=picked,
                work_mode=_work_mode(picked[0], mode),
                description=description,
                ref=str(job.get("id") or job.get("slug")),
                url=job.get("careers_url"),
                posted_at=_parse_dt(str(job.get("published_at") or "").replace(" UTC", "+00:00")),
            ))
        return out


class BambooHrAdapter(_BoardAdapter):
    url_template = "https://{board}.bamboohr.com/careers/list"
    detail_template = "https://{board}.bamboohr.com/careers/{id}/detail"

    async def collect(
        self, client: httpx.AsyncClient, board: str, company: str
    ) -> list[RawPosting | None]:
        data = await _get_json(client, self.url_template.format(board=board))
        kept: list[tuple[dict[str, Any], tuple[str, str]]] = []
        for job in (data or {}).get("result") or []:
            ats = job.get("atsLocation") or {}
            loc = job.get("location") or {}
            place = ", ".join(
                str(v) for v in (ats.get("city") or loc.get("city"),
                                 ats.get("state") or ats.get("province") or loc.get("state")) if v
            )
            picked = choose_location(
                str(job.get("jobOpeningName") or ""), *_with_country(place, ats.get("country"))
            )
            if picked is not None:
                kept.append((job, picked))
        details = await _details(
            client, [self.detail_template.format(board=board, id=job.get("id")) for job, _ in kept]
        )
        out: list[RawPosting | None] = []
        for (job, picked), detail in zip(kept, details, strict=True):
            opening = ((detail or {}).get("result") or {}).get("jobOpening") or {}
            remote = job.get("isRemote") or str(job.get("locationType")) == "2"
            out.append(self._posting(
                title=str(job.get("jobOpeningName") or ""),
                company=company,
                picked=picked,
                work_mode=_work_mode(picked[0], "remote" if remote else None),
                description=html_to_text(opening.get("description")),
                ref=str(job.get("id")),
                url=opening.get("jobOpeningShareUrl")
                or f"https://{board}.bamboohr.com/careers/{job.get('id')}",
                posted_at=_parse_dt(opening.get("datePosted")),
            ))
        return out


class RipplingAdapter(_BoardAdapter):
    url_template = "https://api.rippling.com/platform/api/ats/v1/board/{board}/jobs"
    detail_template = "https://api.rippling.com/platform/api/ats/v1/board/{board}/jobs/{id}"

    async def collect(
        self, client: httpx.AsyncClient, board: str, company: str
    ) -> list[RawPosting | None]:
        data = await _get_json(client, self.url_template.format(board=board))
        kept: list[tuple[dict[str, Any], tuple[str, str]]] = []
        for job in data if isinstance(data, list) else []:
            label = str((job.get("workLocation") or {}).get("label") or "")
            picked = choose_location(str(job.get("name") or ""), label)
            if picked is not None:
                kept.append((job, picked))
        details = await _details(
            client,
            [self.detail_template.format(board=board, id=job.get("uuid")) for job, _ in kept],
        )
        out: list[RawPosting | None] = []
        for (job, picked), detail in zip(kept, details, strict=True):
            parts = (detail or {}).get("description") or {}
            texts = parts.values() if isinstance(parts, dict) else [parts]
            description = "\n\n".join(html_to_text(v) for v in texts if v)
            out.append(self._posting(
                title=str(job.get("name") or "").strip(),
                company=company,
                picked=picked,
                work_mode=_work_mode(picked[0]),
                description=description,
                ref=str(job.get("uuid")),
                url=job.get("url"),
                posted_at=_parse_dt((detail or {}).get("createdOn")),
            ))
        return out
