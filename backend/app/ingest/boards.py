"""
Company career-board adapters: Greenhouse, Lever, and Ashby.

Hundreds of employers host their careers page on one of these three applicant-tracking
systems, and each offers an official, public, key-free JSON API intended for showing a
company's open jobs on other sites. CoopRadar uses them to pull *real* postings and always
links back to the employer's own page to apply.

source.config:
  - board:    the company's board name in the URL, e.g. "stripe" (boards.greenhouse.io/stripe)
  - company:  display name, e.g. "Stripe"

Only jobs whose location matches settings.ingest_location_filter (default: Canada or
Canada-remote) are kept, so a student in Guelph isn't shown jobs in Dublin.
"""

import html
import re
from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.config import get_settings
from app.ingest.base import AdapterError, BaseAdapter, RawPosting

_PROVINCES = {
    "ontario": "ON", "british columbia": "BC", "quebec": "QC", "québec": "QC", "alberta": "AB",
    "manitoba": "MB", "saskatchewan": "SK", "nova scotia": "NS", "new brunswick": "NB",
    "newfoundland": "NL", "prince edward island": "PE",
}
_PROVINCE_CODES = set(_PROVINCES.values())
# Major cities → province, for boards that only give a city ("Toronto")
_CITY_PROVINCE = {
    "toronto": "ON", "waterloo": "ON", "kitchener": "ON", "ottawa": "ON", "guelph": "ON",
    "hamilton": "ON", "mississauga": "ON", "markham": "ON", "oakville": "ON",
    "burlington": "ON", "vaughan": "ON", "brampton": "ON", "windsor": "ON", "kingston": "ON",
    "vancouver": "BC", "burnaby": "BC", "victoria": "BC", "surrey": "BC", "richmond": "BC",
    "montreal": "QC", "montréal": "QC", "quebec city": "QC", "laval": "QC",
    "calgary": "AB", "edmonton": "AB", "winnipeg": "MB", "regina": "SK", "saskatoon": "SK",
    "halifax": "NS", "fredericton": "NB", "moncton": "NB", "st. john's": "NL",
    "charlottetown": "PE",
}


def html_to_text(raw: str | None) -> str:
    """Turn (possibly entity-escaped) job-description HTML into readable plain text."""
    if not raw:
        return ""
    text = html.unescape(html.unescape(raw))  # Greenhouse double-escapes its HTML
    text = re.sub(r"(?i)<\s*(br|/p|/div|/li|/h\d)\s*/?>", "\n", text)
    text = re.sub(r"(?i)<\s*li[^>]*>", "• ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _province(token: str) -> str:
    t = token.strip()
    if t.upper() in _PROVINCE_CODES:
        return t.upper()
    return _PROVINCES.get(t.lower(), "")


def _known_city(token: str) -> str | None:
    """Canonical name if the token is a known Canadian city ("Toronto Canada" → "Toronto")."""
    name = re.sub(r"\bcanada\b", "", token, flags=re.IGNORECASE).strip(" ,").lower()
    if name.startswith("montr"):  # also catches a mis-encoded "Montréal"
        return "Montréal"
    return name.title() if name in _CITY_PROVINCE else None


def parse_location(location: str) -> tuple[str, str]:
    """
    Best-effort (city, province) from the free-text location boards publish, e.g.
      "Toronto, Ontario, Canada" → ("Toronto", "ON")    "Vancouver, BC" → ("Vancouver", "BC")
      "SEA, SF, NY, Toronto"     → ("Toronto", "ON")    "US / Canada"   → ("Canada", "")
      "Calgary, Canada; Vancouver, Canada" → ("Calgary", "AB")
      "Remote Canada"            → ("Remote", "")       "Ontario, Canada" → ("", "ON")
    """
    loc = (location or "").strip()
    if not loc:
        return "", ""
    tokens = [t.strip() for t in re.split(r"[,;/|]| - | or ", loc) if t.strip()]

    # "City, Province" — works for any city, known or not ("Lethbridge, AB")
    if len(tokens) >= 2 and _province(tokens[1]) and not _province(tokens[0]):
        city = _known_city(tokens[0]) or tokens[0]
        return city, _province(tokens[1])
    # A known Canadian city anywhere in a multi-city list
    for token in tokens:
        city = _known_city(token)
        if city:
            return city, _CITY_PROVINCE.get(city.lower(), "QC" if city == "Montréal" else "")
    # Just a province ("Ontario, Canada")
    for token in tokens:
        if _province(token):
            return "", _province(token)
    if "remote" in loc.lower():
        return "Remote", ""
    if "canada" in loc.lower():
        return "Canada", ""
    return tokens[0], ""


def _work_mode(location: str, workplace: str | None = None, is_remote: bool | None = None) -> str:
    hint = f"{workplace or ''} {location}".lower()
    if is_remote or "remote" in hint:
        return "remote"
    if "hybrid" in hint:
        return "hybrid"
    return "onsite"


def _location_allowed(*locations: str) -> bool:
    return _pick_location(*locations) is not None


def _pick_location(*locations: str) -> str | None:
    """
    The first of a job's locations that matches the location filter (the one to display),
    or None to skip the job. A role listed as "London" + "Remote, Canada" is shown as the
    Canadian option, never mislabelled as London, Ontario.
    """
    rx = re.compile(get_settings().ingest_location_filter, re.IGNORECASE)
    return next((loc for loc in locations if loc and rx.search(loc)), None)


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)  # Lever: epoch milliseconds
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class _BoardAdapter(BaseAdapter):
    """Shared HTTP + config handling for the three career-board APIs."""

    url_template: str = ""

    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        board = str(config.get("board", "")).strip()
        if not board:
            raise AdapterError("Board name missing from source config")
        company = str(config.get("company") or board)
        url = self.url_template.format(board=board)

        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            try:
                response = await client.get(url)
            except httpx.HTTPError as exc:
                raise AdapterError(f"Could not reach {url}: {exc}") from exc
        if response.status_code != 200:
            raise AdapterError(f"HTTP {response.status_code} from {url}")
        try:
            data = response.json()
        except ValueError as exc:
            raise AdapterError(f"Invalid JSON from {url}") from exc
        return [p for p in self.parse(data, company) if p is not None]

    def parse(self, data: Any, company: str) -> list[RawPosting | None]:
        raise NotImplementedError

    @staticmethod
    def _posting(
        *, title: str, company: str, location: str, work_mode: str, description: str,
        ref: str, url: str | None, posted_at: datetime | None, deadline: date | None = None,
    ) -> RawPosting:
        city, province = parse_location(location)
        if work_mode == "remote" and not city:
            city = "Remote"
        return RawPosting(
            title=title.strip(),
            company=company,
            city=city or "Canada",
            province=province,
            term="",  # filled from the title/description by extract_fields ("Winter 2027")
            work_mode=work_mode,
            deadline=deadline,
            description=description,
            source_ref=ref,
            source_url=url,
            posted_at=posted_at,
        )


class GreenhouseAdapter(_BoardAdapter):
    url_template = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    def parse(self, data: Any, company: str) -> list[RawPosting | None]:
        out: list[RawPosting | None] = []
        for job in data.get("jobs", []):
            location = (job.get("location") or {}).get("name", "")
            if not _location_allowed(location):
                continue
            deadline = _parse_dt(job.get("application_deadline"))
            out.append(self._posting(
                title=job.get("title", ""),
                company=job.get("company_name") or company,
                location=location,
                work_mode=_work_mode(location),
                description=html_to_text(job.get("content")),
                ref=str(job.get("id")),
                url=job.get("absolute_url"),
                posted_at=_parse_dt(job.get("first_published") or job.get("updated_at")),
                deadline=deadline.date() if deadline else None,
            ))
        return out


class LeverAdapter(_BoardAdapter):
    url_template = "https://api.lever.co/v0/postings/{board}?mode=json"

    def parse(self, data: Any, company: str) -> list[RawPosting | None]:
        out: list[RawPosting | None] = []
        for job in data if isinstance(data, list) else []:
            location = (job.get("categories") or {}).get("location") or ""
            if not _location_allowed(location, job.get("country") or ""):
                continue
            out.append(self._posting(
                title=job.get("text", ""),
                company=company,
                location=location,
                work_mode=_work_mode(location, job.get("workplaceType")),
                description=(job.get("descriptionPlain") or "").strip()
                or html_to_text(job.get("description")),
                ref=str(job.get("id")),
                url=job.get("hostedUrl"),
                posted_at=_parse_dt(job.get("createdAt")),
            ))
        return out


class AshbyAdapter(_BoardAdapter):
    url_template = "https://api.ashbyhq.com/posting-api/job-board/{board}"

    def parse(self, data: Any, company: str) -> list[RawPosting | None]:
        out: list[RawPosting | None] = []
        for job in data.get("jobs", []):
            if job.get("isListed") is False:
                continue
            secondary = [s.get("location", "") for s in job.get("secondaryLocations") or []]
            location = _pick_location(job.get("location") or "", *secondary)
            if location is None:
                continue
            out.append(self._posting(
                title=job.get("title", ""),
                company=company,
                location=location,
                work_mode=_work_mode(location, job.get("workplaceType"), job.get("isRemote")),
                description=(job.get("descriptionPlain") or "").strip()
                or html_to_text(job.get("descriptionHtml")),
                ref=str(job.get("id")),
                url=job.get("jobUrl"),
                posted_at=_parse_dt(job.get("publishedAt")),
            ))
        return out
