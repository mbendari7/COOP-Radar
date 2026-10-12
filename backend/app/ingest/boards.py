"""
Company career-board adapters: Greenhouse, Lever, Ashby and SmartRecruiters.

Hundreds of employers host their careers page on one of these applicant-tracking systems, and
each offers an official, public, key-free JSON API intended for showing a company's open jobs on
other sites. CoopRadar uses them to pull *real* postings and always links back to the employer's
own page to apply.

source.config:
  - board:    the company's board name in the URL, e.g. "stripe" (boards.greenhouse.io/stripe)
  - company:  display name, e.g. "Stripe"

Which jobs are kept:
  - Canada: every job whose location matches settings.ingest_location_filter (Canada, Canadian
    provinces and cities, "Remote - Canada").
  - United States: settings.ingest_us_jobs, by default only co-op / intern / student / new-grad
    roles (many Canadian students do a US co-op term). Set it to "all" or "none".
Anything else (Dublin, London UK, ...) is skipped.
"""

import asyncio
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

_US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "district of columbia": "DC",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA",
    "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
_US_CODES = set(_US_STATES.values())
_US_CITY_STATE = {
    "new york": "NY", "new york city": "NY", "nyc": "NY", "brooklyn": "NY",
    "san francisco": "CA", "sf": "CA", "bay area": "CA", "san francisco bay area": "CA",
    "los angeles": "CA", "mountain view": "CA", "palo alto": "CA", "menlo park": "CA",
    "sunnyvale": "CA", "san jose": "CA", "san mateo": "CA", "redwood city": "CA",
    "santa clara": "CA", "cupertino": "CA", "san diego": "CA", "irvine": "CA", "oakland": "CA",
    "seattle": "WA", "bellevue": "WA", "redmond": "WA", "boston": "MA",
    "chicago": "IL", "austin": "TX", "dallas": "TX", "houston": "TX", "denver": "CO",
    "boulder": "CO", "atlanta": "GA", "pittsburgh": "PA", "philadelphia": "PA",
    "washington dc": "DC", "washington, dc": "DC", "miami": "FL", "portland": "OR",
    "salt lake city": "UT", "phoenix": "AZ", "raleigh": "NC", "nashville": "TN",
    "detroit": "MI", "ann arbor": "MI", "minneapolis": "MN", "columbus": "OH",
    "hawthorne": "CA", "long beach": "CA", "el segundo": "CA", "huntsville": "AL",
}
_US_LOCATION = re.compile(
    r"(?i)united states|\busa\b|\bu\.s\.(a\.)?|\bus\b|remote[^,]*\bus\b|"
    + "|".join(re.escape(c) for c in sorted(_US_CITY_STATE, key=len, reverse=True) if len(c) > 2)
    + r"|(?-i:(?:^|,\s*)(?:" + "|".join(sorted(_US_CODES)) + r")\b)"
)
# A US state code after a comma ("Vancouver, WA") means the US, even for a Canadian-sounding city
_US_STATE_SUFFIX = re.compile(r"(?-i:,\s*(?:" + "|".join(sorted(_US_CODES - {"CA"})) + r")\b)")

# Python twin of STUDENT_TITLE_PATTERN in app/services/postings.py
STUDENT_TITLE = re.compile(
    r"(?i)\b(intern|interns|internship|co-?op|student|new grad(uate)?|apprentice|stagiaire)\b"
)

_DETAIL_CONCURRENCY = 6


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


_MODE_WORDS = re.compile(r"(?i)^(remote|hybrid|on-?site|in[- ]office|in[- ]person|flexible)$")


def _tokens(location: str) -> list[str]:
    """Location parts, without work-mode words ("Hybrid - New York" -> ["New York"])."""
    parts = [t.strip() for t in re.split(r"[,;/|()]| - | or ", location) if t.strip()]
    return [t for t in parts if not _MODE_WORDS.match(t)]


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
    tokens = _tokens(loc)
    if not tokens:
        return ("Remote", "") if "remote" in loc.lower() else ("", "")

    # "City, Province" — works for any city, known or not ("Lethbridge, AB")
    if len(tokens) >= 2 and _province(tokens[1]) and not _province(tokens[0]):
        city = _known_city(tokens[0]) or tokens[0]
        return city, _province(tokens[1])
    # A known Canadian city anywhere in a multi-city list
    for token in tokens:
        known = _known_city(token)
        if known:
            return known, _CITY_PROVINCE.get(known.lower(), "QC" if known == "Montréal" else "")
    # Just a province ("Ontario, Canada")
    for token in tokens:
        if _province(token):
            return "", _province(token)
    if "remote" in loc.lower():
        return "Remote", ""
    if "canada" in loc.lower():
        return "Canada", ""
    return tokens[0], ""


def _state(token: str) -> str:
    t = token.strip()
    if t in _US_CODES:  # codes are upper case on every board; "in" or "or" are not states
        return t
    return _US_STATES.get(t.lower(), "")


def parse_us_location(location: str) -> tuple[str, str]:
    """
    Best-effort (city, state) for a US location:
      "San Francisco, CA" → ("San Francisco", "CA")    "New York City" → ("New York City", "NY")
      "Seattle, Washington, USA" → ("Seattle", "WA")   "Remote - US" → ("Remote", "")
    """
    loc = (location or "").strip()
    if re.search(r"(?i)washington,?\s*d\.?\s?c\b", loc):
        return "Washington", "DC"
    tokens = _tokens(loc)
    if len(tokens) >= 2 and _state(tokens[1]) and not _state(tokens[0]):
        return tokens[0], _state(tokens[1])
    for token in tokens:
        key = token.lower()
        if key in _US_CITY_STATE:
            name = {"sf": "San Francisco", "nyc": "New York"}.get(key, token)
            return name, _US_CITY_STATE[key]
    for token in tokens:
        if _state(token):
            return "", _state(token)
    if "remote" in loc.lower():
        return "Remote", ""
    return "United States", ""


def _work_mode(location: str, workplace: str | None = None, is_remote: bool | None = None) -> str:
    hint = f"{workplace or ''} {location}".lower()
    if is_remote or "remote" in hint:
        return "remote"
    if "hybrid" in hint:
        return "hybrid"
    return "onsite"


def _is_canadian(location: str) -> bool:
    if not location:
        return False
    rx = re.compile(get_settings().ingest_location_filter, re.IGNORECASE)
    if not rx.search(location):
        return False
    # "Vancouver, WA" is in the United States
    return "canada" in location.lower() or not _US_STATE_SUFFIX.search(location)


def _pick_location(*locations: str) -> str | None:
    """
    The first of a job's locations in Canada (the one to display), or None. A role listed as
    "London" + "Remote, Canada" is shown as the Canadian option, never mislabelled as London, ON.
    """
    return next((loc for loc in locations if _is_canadian(loc)), None)


def choose_location(title: str, *locations: str) -> tuple[str, str] | None:
    """
    (location to display, country) for a job, or None to skip it. Canadian locations win; a US
    location is used only when settings.ingest_us_jobs allows this job ("students" = the title
    is a co-op / intern / student / new-grad role).
    """
    canadian = _pick_location(*locations)
    if canadian is not None:
        return canadian, "CA"
    us_policy = get_settings().ingest_us_jobs
    if us_policy == "none" or (us_policy == "students" and not STUDENT_TITLE.search(title or "")):
        return None
    us = next((loc for loc in locations if loc and _US_LOCATION.search(loc)), None)
    return (us, "US") if us is not None else None


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)  # Lever: epoch milliseconds
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def _get_json(client: httpx.AsyncClient, url: str) -> Any:
    try:
        response = await client.get(url)
    except httpx.HTTPError as exc:
        raise AdapterError(f"Could not reach {url}: {exc}") from exc
    if response.status_code != 200:
        raise AdapterError(f"HTTP {response.status_code} from {url}")
    try:
        return response.json()
    except ValueError as exc:
        raise AdapterError(f"Invalid JSON from {url}") from exc


class _BoardAdapter(BaseAdapter):
    """Shared HTTP + config handling for the career-board APIs."""

    url_template: str = ""

    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        board = str(config.get("board", "")).strip()
        if not board:
            raise AdapterError("Board name missing from source config")
        company = str(config.get("company") or board)

        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            postings = await self.collect(client, board, company)
        return [p for p in postings if p is not None]

    async def collect(
        self, client: httpx.AsyncClient, board: str, company: str
    ) -> list[RawPosting | None]:
        """Default: one request returns every job with its description."""
        data = await _get_json(client, self.url_template.format(board=board))
        return self.parse(data, company)

    def parse(self, data: Any, company: str) -> list[RawPosting | None]:
        raise NotImplementedError

    @staticmethod
    def _posting(
        *, title: str, company: str, picked: tuple[str, str], work_mode: str, description: str,
        ref: str, url: str | None, posted_at: datetime | None, deadline: date | None = None,
    ) -> RawPosting:
        location, country = picked
        if country == "US":
            city, province = parse_us_location(location)
        else:
            city, province = parse_location(location)
        if work_mode == "remote" and not city:
            city = "Remote"
        return RawPosting(
            title=title.strip(),
            company=company,
            city=city or ("United States" if country == "US" else "Canada"),
            province=province,
            country=country,
            term="",  # filled from the title/description by extract_fields ("Winter 2027")
            work_mode=work_mode,
            deadline=deadline,
            description=description,
            source_ref=ref,
            source_url=url,
            posted_at=posted_at,
        )


async def _details(
    client: httpx.AsyncClient, urls: list[str]
) -> list[Any]:
    """Fetch several detail pages a few at a time; a failed one comes back as None."""
    gate = asyncio.Semaphore(_DETAIL_CONCURRENCY)

    async def one(url: str) -> Any:
        async with gate:
            try:
                return await _get_json(client, url)
            except AdapterError:
                return None

    return await asyncio.gather(*(one(u) for u in urls))


class GreenhouseAdapter(_BoardAdapter):
    """
    Lists the board without descriptions (big boards are 30 MB with them), keeps the jobs in
    Canada / allowed US ones, then fetches only those jobs' descriptions.
    """

    url_template = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    detail_template = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{id}"

    async def collect(
        self, client: httpx.AsyncClient, board: str, company: str
    ) -> list[RawPosting | None]:
        data = await _get_json(client, self.url_template.format(board=board))
        kept: list[tuple[dict[str, Any], tuple[str, str]]] = []
        for job in data.get("jobs", []):
            location = (job.get("location") or {}).get("name", "")
            picked = choose_location(job.get("title", ""), location)
            if picked is not None:
                kept.append((job, picked))
        details = await _details(
            client, [self.detail_template.format(board=board, id=job.get("id")) for job, _ in kept]
        )
        out: list[RawPosting | None] = []
        for (job, picked), detail in zip(kept, details, strict=True):
            deadline = _parse_dt(job.get("application_deadline"))
            out.append(self._posting(
                title=job.get("title", ""),
                company=job.get("company_name") or company,
                picked=picked,
                work_mode=_work_mode(picked[0]),
                description=html_to_text((detail or {}).get("content")),
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
            country = job.get("country") or ""
            title = job.get("text", "")
            picked = choose_location(title, location, *(
                [f"{location}, Canada"] if country == "CA" else
                [f"{location}, United States"] if country == "US" else []
            ))
            if picked is None:
                continue
            out.append(self._posting(
                title=title,
                company=company,
                picked=(location or picked[0], picked[1]),
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
            title = job.get("title", "")
            picked = choose_location(title, job.get("location") or "", *secondary)
            if picked is None:
                continue
            out.append(self._posting(
                title=title,
                company=company,
                picked=picked,
                work_mode=_work_mode(picked[0], job.get("workplaceType"), job.get("isRemote")),
                description=(job.get("descriptionPlain") or "").strip()
                or html_to_text(job.get("descriptionHtml")),
                ref=str(job.get("id")),
                url=job.get("jobUrl"),
                posted_at=_parse_dt(job.get("publishedAt")),
            ))
        return out


class SmartRecruitersAdapter(_BoardAdapter):
    """
    SmartRecruiters' public Posting API: pages of 100 job summaries, then one request per kept
    job for its description. Board = the company identifier (jobs.smartrecruiters.com/<board>).
    """

    url_template = "https://api.smartrecruiters.com/v1/companies/{board}/postings?limit=100&offset={offset}"
    detail_template = "https://api.smartrecruiters.com/v1/companies/{board}/postings/{id}"
    max_jobs = 2000

    async def collect(
        self, client: httpx.AsyncClient, board: str, company: str
    ) -> list[RawPosting | None]:
        jobs: list[dict[str, Any]] = []
        offset = 0
        while offset < self.max_jobs:
            page = await _get_json(client, self.url_template.format(board=board, offset=offset))
            content = page.get("content") or []
            jobs.extend(content)
            offset += 100
            if not content or offset >= int(page.get("totalFound") or 0):
                break

        kept: list[tuple[dict[str, Any], tuple[str, str], str]] = []
        for job in jobs:
            loc = job.get("location") or {}
            code = str(loc.get("country") or "").lower()
            place = ", ".join(str(v) for v in (loc.get("city"), loc.get("region")) if v)
            full = loc.get("fullLocation") or place
            hint = "remote" if loc.get("remote") else "hybrid" if loc.get("hybrid") else ""
            if code == "ca":
                picked = choose_location(job.get("name", ""), f"{place}, Canada")
            elif code == "us":
                picked = choose_location(job.get("name", ""), f"{place}, United States")
            else:
                picked = None
            if picked is not None:
                kept.append((job, (place or full, picked[1]), hint))

        details = await _details(
            client,
            [self.detail_template.format(board=board, id=job.get("id")) for job, _, _ in kept],
        )
        out: list[RawPosting | None] = []
        for (job, picked, hint), detail in zip(kept, details, strict=True):
            sections = ((detail or {}).get("jobAd") or {}).get("sections") or {}
            description = "\n\n".join(
                html_to_text((sections.get(key) or {}).get("text"))
                for key in ("jobDescription", "qualifications", "additionalInformation")
                if (sections.get(key) or {}).get("text")
            )
            out.append(self._posting(
                title=job.get("name", ""),
                company=company,  # the API's name can be a parent company ("General Dynamics UK")
                picked=picked,
                work_mode=_work_mode(picked[0], hint),
                description=description,
                ref=str(job.get("id")),
                url=(detail or {}).get("postingUrl")
                or f"https://jobs.smartrecruiters.com/{board}/{job.get('id')}",
                posted_at=_parse_dt(job.get("releasedDate")),
            ))
        return out
