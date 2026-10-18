"""
Public job lists on GitHub kept as a table in a README, like negarprh/Canadian-Tech-Internships,
where students add co-op roles they find all over the web (Workday, Oracle, company sites).
Each row has the company, the role, the place and a link to apply on the employer's own page.

We read the raw README (a public file, no key, no login), keep the rows in Canada plus the US
ones settings.ingest_us_jobs allows, and link each to the employer's page. Every row on these
lists is a student role, so US rows count as student roles. The term comes from the role when it
says one, like "Software Co-op (Winter 2027)".

source.config
  repo      the GitHub repo, like "negarprh/Canadian-Tech-Internships-{summer}". "{summer}" works
            like it does for Simplify: next summer's year, then this year's
  branch    "main" by default
  file      "README.md" by default
  country   "CA" when every row is in Canada, so "Surrey, BC" is read as Canada
"""

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.ingest.base import AdapterError, BaseAdapter, RawPosting
from app.ingest.boards import _BoardAdapter, _work_mode, choose_location
from app.ingest.simplify import repos_to_try, upcoming_terms
from app.ingest.terms import term_in_text

_URL = "https://raw.githubusercontent.com/{repo}/{branch}/{file}"
_LINK = re.compile(r"\]\((https?://[^)\s]+)\)|(https?://[^\s|)\"'>]+)")
_MD = re.compile(r"\*\*|__|`|<[^>]+>|!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_PICTURE = re.compile(r"(?i)shields\.io|\.(png|svg|gif|jpe?g|webp)(\?|$)|/images?/")
_AGE = re.compile(r"^(\d+)\s*([hdwm])\w*$", re.I)
_SAME_AS_ABOVE = {"↳", "&#8627;", "^", "\""}


def _clean(cell: str) -> str:
    """Markdown cell text without bold, links, images or a leading emoji."""
    text = _MD_LINK.sub(r"\1", _MD.sub("", cell))
    return re.sub(r"^[^\w(]+", "", text).strip()


def _posted(cell: str, today: date) -> datetime | None:
    """
    'Oct 16, 2026', 'Oct 16' (this year, or last year when that would be in the future) or '3d'.
    """
    text = _clean(cell)
    if m := _AGE.match(text):
        n, unit = int(m.group(1)), m.group(2).lower()
        days = {"h": 0, "d": n, "w": 7 * n, "m": 30 * n}[unit]
        return datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=UTC)
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%b %d", "%B %d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if "%Y" not in fmt:
            parsed = parsed.replace(year=today.year)
            if parsed.date() > today:
                parsed = parsed.replace(year=today.year - 1)
        return parsed.replace(tzinfo=UTC)
    return None


def _apply_link(cell: str) -> str | None:
    """The last link in the cell that is not a picture, since Apply buttons are images in links."""
    links = [m.group(1) or m.group(2) for m in _LINK.finditer(cell)]
    real = [u for u in links if not _PICTURE.search(u)]
    return real[-1] if real else None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _column(headers: list[str], *names: str) -> int | None:
    for i, h in enumerate(headers):
        if any(n in h for n in names):
            return i
    return None


def rows_from_markdown(
    text: str, *, source: str, country: str = "", today: date | None = None
) -> list[RawPosting]:
    """Every row of every job table in the README as a RawPosting we would keep."""
    today = today or date.today()
    out: list[RawPosting] = []
    headers: list[str] = []
    company = ""
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue  # tables can have blank or comment lines in them, so keep the headers
        cells = _cells(line)
        names = [_clean(c).lower() for c in cells]
        if "http" not in line and _column(names, "company", "employer") is not None:
            headers = names  # a header row starts a new table
            continue
        if not headers:
            continue
        if all(set(c) <= set(":- ") for c in cells):
            continue  # the |---|---| line under the headers
        col_company = _column(headers, "company", "employer")
        col_role = _column(headers, "role", "position", "title", "job")
        col_place = _column(headers, "location", "place", "city")
        col_link = _column(headers, "apply", "link", "application")
        col_date = _column(headers, "posted", "date", "age")
        if col_company is None or col_role is None or len(cells) < len(headers):
            continue
        name = _clean(cells[col_company])
        if name and name not in _SAME_AS_ABOVE:
            company = name
        title = _clean(cells[col_role])
        link_cell = cells[col_link] if col_link is not None else line
        url = _apply_link(link_cell) or _apply_link(cells[col_role])
        if not company or not title or not url:
            continue
        named = term_in_text(title, today=today)
        if named and not upcoming_terms([named], today):
            continue  # the role names a term that is already over, like "(Winter 2026)"
        place = _clean(cells[col_place].replace("<br>", " / ")) if col_place is not None else ""
        places = [p.strip() for p in re.split(r"\s*(?:/|;|<br>| or )\s*", place) if p.strip()]
        if country == "CA":
            places = [p if "canada" in p.lower() else f"{p}, Canada" for p in places] or ["Canada"]
        picked = choose_location(title, *places, early_career=True)
        if picked is None:
            continue
        raw = _BoardAdapter._posting(
            title=title,
            company=company,
            picked=picked,
            work_mode=_work_mode(place),
            description=(
                f"{title} at {company}.\nLocation: {place or picked[0]}.\n"
                f"Found on {source}, a public list of student roles on GitHub. The full "
                "description is on the employer's page."
            ),
            ref=url,
            url=url,
            posted_at=_posted(cells[col_date], today) if col_date is not None else None,
        )
        out.append(raw)
    return out


class GithubListAdapter(BaseAdapter):
    async def fetch(self, source: Any) -> list[RawPosting]:
        config = source.config or {}
        repo = str(config.get("repo") or "").strip()
        if not repo or repo.count("/") != 1:
            raise AdapterError("GitHub list source needs repo like owner/name")
        branch = str(config.get("branch") or "main")
        file = str(config.get("file") or "README.md")
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=60.0, headers={"User-Agent": self.user_agent}, transport=transport
        ) as client:
            response = None
            name = repo
            for name in repos_to_try(repo):
                url = _URL.format(repo=name, branch=branch, file=file)
                try:
                    response = await client.get(url)
                except httpx.HTTPError as exc:
                    raise AdapterError(f"Could not reach {url}: {exc}") from exc
                if response.status_code != 404:
                    break
        if response is None or response.status_code != 200:
            code = response.status_code if response is not None else "no reply"
            raise AdapterError(f"HTTP {code} from {repo}")
        return rows_from_markdown(
            response.text, source=name, country=str(config.get("country") or "").upper()
        )
