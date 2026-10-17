"""
Simplify's open internship and new grad lists on GitHub (github.com/SimplifyJobs). Students and
Simplify keep them up to date by hand, so they hold thousands of roles from big companies and
startups alike, found all over the web, each with its term (like "Summer 2027") and a link to
the employer's own posting. The lists are public files with no key and no login.

We read the list, keep the open roles in Canada plus the US ones settings.ingest_us_jobs allows,
and link each one to the employer's page to apply. Every role on these lists is for students or
new grads, so US roles count as student roles even when the title does not say intern.
The lists have no descriptions, only the title, category and degrees, so the details panel
points to the employer's page for the rest.

source.config
  repo     the GitHub repo, like "SimplifyJobs/New-Grad-Positions". "{summer}" in it stands for
           the year of the next summer, so "SimplifyJobs/Summer{summer}-Internships" moves on to
           next year's list by itself, falling back to this year's until that one exists
  branch   "dev" by default, where the list file lives
"""

from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import _BoardAdapter, _work_mode, choose_location
from app.ingest.terms import term_in_text, term_start_date

_URL = "https://raw.githubusercontent.com/{repo}/{branch}/.github/scripts/listings.json"
_LATE_DAYS = 31  # a term that started over a month ago is too late to apply for


def _posted(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)  # seconds, unlike Lever's milliseconds
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def upcoming_terms(terms: list[str], today: date | None = None) -> list[str]:
    """
    The terms still ahead, soonest first, like ["Winter 2027", "Summer 2027"]. Open roles on the
    list often still name a term that is over, like "Winter 2026", next to the coming ones.
    """
    today = today or date.today()
    found: set[tuple[date, str]] = set()
    for t in terms:
        term = term_in_text(t, today=today)
        start = term_start_date(term)
        if term and start and (today - start).days < _LATE_DAYS:
            found.add((start, term))
    return [term for _, term in sorted(found)]


def posting_from_listing(item: dict[str, Any]) -> RawPosting | None:
    """One list entry as a RawPosting, or None when it is closed, hidden or somewhere we skip."""
    if not item.get("active") or item.get("is_visible") is False:
        return None
    title = str(item.get("title") or "").strip()
    company = str(item.get("company_name") or "").strip()
    url = str(item.get("url") or "").strip()
    if not title or not company or not url:
        return None
    locations = [str(x) for x in item.get("locations") or [] if x]
    # The most specific place first, so "Kanata, Ottawa, ON, Canada" wins over "Ontario, Canada"
    by_detail = sorted(locations, key=lambda loc: -loc.count(","))
    picked = choose_location(title, *by_detail, early_career=True)
    if picked is None:
        return None
    # Only terms still ahead go in, here and in the description, or the importer would read an
    # old term like "Summer 2025" back out of the text
    terms = upcoming_terms([str(t) for t in item.get("terms") or [] if t and t != "N/A"])
    degrees = ", ".join(str(d) for d in item.get("degrees") or [])
    lines = [
        f"{title} at {company}.",
        f"Category: {item['category']}." if item.get("category") else "",
        f"Terms: {', '.join(terms)}." if terms else "",
        f"Degrees: {degrees}." if degrees else "",
        f"Locations: {'; '.join(locations)}." if locations else "",
        "Found on Simplify's public list of student roles. The full description is on the "
        "employer's page.",
    ]
    raw = _BoardAdapter._posting(
        title=title,
        company=company,
        picked=picked,
        work_mode=_work_mode(picked[0]),
        description="\n".join(line for line in lines if line),
        ref=str(item.get("id") or url),
        url=url,
        posted_at=_posted(item.get("date_posted")),
    )
    raw.term = terms[0] if terms else ""
    return raw


def repos_to_try(repo: str, today: date | None = None) -> list[str]:
    """The repo names to try in order. "{summer}" becomes next summer's year, then this one's."""
    if "{summer}" not in repo:
        return [repo]
    today = today or date.today()
    upcoming = today.year + 1 if today.month >= 6 else today.year
    return [repo.replace("{summer}", str(y)) for y in (upcoming, upcoming - 1)]


class SimplifyAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        repo = str(config.get("repo") or "").strip()
        if not repo or repo.count("/") != 1:
            raise AdapterError("Simplify source needs repo like SimplifyJobs/New-Grad-Positions")
        branch = str(config.get("branch") or "dev")
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=60.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            response = None
            for name in repos_to_try(repo):
                url = _URL.format(repo=name, branch=branch)
                try:
                    response = await client.get(url)
                except httpx.HTTPError as exc:
                    raise AdapterError(f"Could not reach {url}: {exc}") from exc
                if response.status_code != 404:
                    break
        if response is None or response.status_code != 200:
            code = response.status_code if response is not None else "no reply"
            raise AdapterError(f"HTTP {code} from {url}")
        try:
            items = response.json()
        except ValueError as exc:
            raise AdapterError(f"Invalid JSON from {url}") from exc
        if not isinstance(items, list):
            raise AdapterError(f"Unexpected reply from {url}")
        out = [posting_from_listing(i) for i in items if isinstance(i, dict)]
        return [p for p in out if p is not None]
