"""
Finds more employers' career boards, including small and niche ones, and keeps the ones with
jobs in Canada or US student roles. The owner runs it now and then, it is not part of start.py.

    python -m seed.discover_boards            (from backend/, takes 10 to 20 minutes)
    python -m seed.discover_boards --lists    (only the boards linked from the GitHub lists)

How it works
  1. Common Crawl is a free public copy of the web. Its URL index lists every Greenhouse,
     Lever, Ashby, SmartRecruiters,
     Recruitee, BambooHR, Rippling and Workday careers page it saw, which gives us thousands of company boards.
  2. For each board we ask that board's own public job API once, the same API the importer
     uses, and count the jobs we would keep (Canada, plus US co-op and intern roles).
     The apply links on public GitHub student lists (Simplify's and others) add the boards
     of employers that hire students, including Oracle career sites.
  3. Boards with at least one are written to seed/discovered_boards.json. seed/job_boards.py
     adds them as import sources next to the hand picked list.

Boards already in JOB_BOARDS are skipped. Re-running adds new boards to the file and keeps the ones found before.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx

from app.ingest.ats import RecruiteeAdapter
from app.ingest.base import BaseAdapter
from app.ingest.boards import AshbyAdapter, LeverAdapter, choose_location
from app.ingest.oracle import list_url as oracle_list_url
from app.ingest.oracle import parse_board as oracle_board
from app.ingest.oracle import places as oracle_places
from app.ingest.workday import parse_board
from seed.job_boards import JOB_BOARDS

OUT = Path(__file__).with_name("discovered_boards.json")
_INDEX = "https://index.commoncrawl.org"
_CRAWLS = 3  # how many of the newest monthly crawls to read
_CONCURRENCY = 8
_UA = {"User-Agent": BaseAdapter.user_agent}

# Host pattern in Common Crawl, adapter type, and how to read the board from a URL
_HOSTS: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("job-boards.greenhouse.io/", "prefix", "greenhouse",
     re.compile(r"^https?://job-boards\.greenhouse\.io/([a-z0-9_-]+)", re.I)),
    ("boards.greenhouse.io/", "prefix", "greenhouse",
     re.compile(r"^https?://boards\.greenhouse\.io/([a-z0-9_-]+)", re.I)),
    ("jobs.lever.co/", "prefix", "lever", re.compile(r"^https?://jobs\.lever\.co/([a-z0-9_.-]+)", re.I)),
    ("jobs.ashbyhq.com/", "prefix", "ashby",
     re.compile(r"^https?://jobs\.ashbyhq\.com/([a-z0-9_.%-]+)", re.I)),
    ("jobs.smartrecruiters.com/", "prefix", "smartrecruiters",
     re.compile(r"^https?://jobs\.smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I)),
    ("recruitee.com", "domain", "recruitee", re.compile(r"^https?://([a-z0-9-]+)\.recruitee\.com", re.I)),
    ("bamboohr.com", "domain", "bamboohr",
     re.compile(r"^https?://([a-z0-9-]+)\.bamboohr\.com/(?:careers|jobs)", re.I)),
    ("ats.rippling.com/", "prefix", "rippling",
     re.compile(r"^https?://ats\.rippling\.com/(?:[a-z]{2}-[A-Z]{2}/)?([a-z0-9_-]+)/jobs", re.I)),
    ("myworkdayjobs.com", "domain", "workday", re.compile(
        r"^https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)"
    )),
]
_NOT_BOARDS = {"embed", "v1", "api", "static", "robots.txt", "favicon.ico", "sitemap.xml", "wday",
               "job", "jobs", "login", "assets", "en-us", "www", "app", "careers", "help",
               "support", "status", "blog", "info", "mail", "demo", "partners", "marketplace"}


def _known() -> set[tuple[str, str]]:
    return {(adapter, board.lower()) for _, adapter, board, *_ in JOB_BOARDS}


async def _get_retrying(
    client: httpx.AsyncClient, url: str, params: dict[str, str]
) -> httpx.Response | None:
    """Common Crawl's index often answers 502 or 504 when busy, so try a few times."""
    for attempt in range(4):
        try:
            r = await client.get(url, params=params, timeout=180)
            if r.status_code == 200:
                return r
        except httpx.HTTPError:
            pass
        await asyncio.sleep(5 * (attempt + 1))
    return None


async def _index_urls(client: httpx.AsyncClient, crawl: str, url: str, match: str) -> list[str]:
    base = f"{_INDEX}/{crawl}-index"
    params = {"url": url, "matchType": match, "output": "json", "fl": "url"}
    first = await _get_retrying(client, base, {**params, "showNumPages": "true"})
    try:
        meta = first.json() if first is not None else {}
    except ValueError:
        return []
    urls: list[str] = []
    for page in range(int(meta.get("pages") or 0)):
        r = await _get_retrying(client, base, {**params, "page": str(page)})
        if r is None:
            continue
        for line in r.text.splitlines():
            try:
                urls.append(json.loads(line)["url"])
            except (ValueError, KeyError):
                continue
    return urls


async def find_boards(client: httpx.AsyncClient) -> set[tuple[str, str]]:
    crawls = [c["id"] for c in (await client.get(f"{_INDEX}/collinfo.json")).json()[:_CRAWLS]]
    found: set[tuple[str, str]] = set()
    for crawl in crawls:
        for url, match, adapter, rx in _HOSTS:
            for u in await _index_urls(client, crawl, url, match):
                m = rx.match(u)
                if not m:
                    continue
                if adapter == "workday":
                    tenant, wd, site = m.groups()
                    if site.lower() in _NOT_BOARDS:
                        continue
                    found.add((adapter, f"{tenant.lower()}.{wd.lower()}/{site}"))
                elif (board := unquote(m.group(1)).lower()) not in _NOT_BOARDS:
                    found.add((adapter, board))
            print(f"  {crawl} {url}: {len(found)} boards so far", flush=True)
    return found


# Public student job lists on GitHub. Their apply links point at the boards of employers that
# hire students, closed roles too, so they are a good list of boards to check
_LISTS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/negarprh/Canadian-Tech-Internships-2027/main/README.md",
    "https://raw.githubusercontent.com/negarprh/Canadian-Tech-Internships-2026/main/README.md",
]
_ORACLE = re.compile(
    r"^https?://([a-z0-9.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-z_-]+/sites/([A-Za-z0-9_]+)",
    re.I,
)
_URL_IN_TEXT = re.compile(r"https?://[^\s|)\]\"'<>]+")


def board_from_url(url: str) -> tuple[str, str] | None:
    """The (adapter, board) a job link belongs to, or None for a site we can't read."""
    if m := _ORACLE.match(url):
        return "oracle", f"{m.group(1).lower()}/{m.group(2)}"
    for _, _, adapter, rx in _HOSTS:
        m = rx.match(url)
        if not m:
            continue
        if adapter == "workday":
            tenant, wd, site = m.groups()
            if site.lower() in _NOT_BOARDS:
                return None
            return adapter, f"{tenant.lower()}.{wd.lower()}/{site}"
        board = unquote(m.group(1)).lower()
        return None if board in _NOT_BOARDS else (adapter, board)
    return None


async def find_boards_in_lists(client: httpx.AsyncClient) -> dict[tuple[str, str], str]:
    """Boards behind the apply links on the GitHub student lists, with the company's name."""
    found: dict[tuple[str, str], str] = {}
    for url in _LISTS:
        try:
            r = await client.get(url, timeout=120)
        except httpx.HTTPError:
            continue
        if r.status_code != 200:
            continue
        pairs: list[tuple[str, str]] = []
        if url.endswith(".json"):
            try:
                pairs = [(str(i.get("url") or ""), str(i.get("company_name") or "")) for i in r.json()]
            except (ValueError, AttributeError):
                pairs = []
        else:
            for line in r.text.splitlines():
                if line.lstrip().startswith("|"):
                    company = re.sub(r"[*\[\]]|\(http[^)]*\)", "", line.strip().strip("|").split("|")[0])
                    pairs += [(u, company.strip()) for u in _URL_IN_TEXT.findall(line)]
        for link, company in pairs:
            key = board_from_url(link)
            if key and company and company not in ("↳",):
                found.setdefault(key, company)
        print(f"  {url.split('/')[4]}: {len(found)} boards so far", flush=True)
    return found


def _kept(title: str, *locations: str) -> bool:
    return choose_location(title, *locations) is not None


async def probe(client: httpx.AsyncClient, adapter: str, board: str) -> tuple[str, int] | None:
    """The company name and how many jobs we would keep, or None when the board is not useful."""
    try:
        if adapter == "greenhouse":
            r = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
            if r.status_code != 200:
                return None
            jobs = r.json().get("jobs", [])
            n = sum(_kept(j.get("title", ""), (j.get("location") or {}).get("name", "")) for j in jobs)
            if not n:
                return None
            info = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{board}")
            name = (info.json().get("name") if info.status_code == 200 else None) or board
            return str(name), n
        if adapter == "lever":
            r = await client.get(f"https://api.lever.co/v0/postings/{board}?mode=json")
            if r.status_code != 200:
                return None
            n = len(LeverAdapter().parse(r.json(), board))
            return (_title(board), n) if n else None
        if adapter == "ashby":
            r = await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
            if r.status_code != 200:
                return None
            n = len(AshbyAdapter().parse(r.json(), board))
            return (_title(board), n) if n else None
        if adapter == "smartrecruiters":
            r = await client.get(
                f"https://api.smartrecruiters.com/v1/companies/{board}/postings?limit=100"
            )
            if r.status_code != 200:
                return None
            jobs = r.json().get("content") or []
            n = sum(_kept(j.get("name", ""), _sr_place(j)) for j in jobs)
            name = next(
                (str((j.get("company") or {}).get("name")) for j in jobs if j.get("company")), ""
            )
            return (name or _title(board), n) if n else None
        if adapter == "recruitee":
            r = await client.get(f"https://{board}.recruitee.com/api/offers/")
            if r.status_code != 200:
                return None
            offers = r.json().get("offers") or []
            n = len(RecruiteeAdapter().parse(r.json(), board))
            name = next((str(o["company_name"]) for o in offers if o.get("company_name")), "")
            return (name or _title(board), n) if n else None
        if adapter == "bamboohr":
            r = await client.get(f"https://{board}.bamboohr.com/careers/list")
            if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                return None
            n = 0
            for j in r.json().get("result") or []:
                ats = j.get("atsLocation") or {}
                loc = j.get("location") or {}
                place = ", ".join(str(v) for v in (
                    ats.get("city") or loc.get("city"), ats.get("state") or loc.get("state"),
                    ats.get("country"),
                ) if v)
                n += _kept(j.get("jobOpeningName", ""), place)
            return (_title(board), n) if n else None
        if adapter == "rippling":
            r = await client.get(f"https://api.rippling.com/platform/api/ats/v1/board/{board}/jobs")
            if r.status_code != 200:
                return None
            data = r.json()
            jobs = data if isinstance(data, list) else []
            n = sum(
                _kept(j.get("name", ""), (j.get("workLocation") or {}).get("label", "")) for j in jobs
            )
            return (_title(board), n) if n else None
        if adapter == "oracle":
            host, site = oracle_board(board)
            r = await client.get(oracle_list_url(host, site, 0))
            if r.status_code != 200:
                return None
            found = (r.json().get("items") or [{}])[0]
            jobs = found.get("requisitionList") or []
            n = sum(_kept(str(j.get("Title") or ""), *oracle_places(j)) for j in jobs)
            return (_title(host.split(".")[0]), n) if n else None
        if adapter == "workday":
            _, api, _ = parse_board(board)
            body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
            r = await client.post(f"{api}/jobs", json=body)
            if r.status_code != 200:
                return None
            n = _facet_count(r.json().get("facets") or [], "canada")
            return (_title(board.split(".")[0]), n) if n else None
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return None
    return None


def _sr_place(job: dict[str, Any]) -> str:
    loc = job.get("location") or {}
    country = {"ca": "Canada", "us": "United States"}.get(str(loc.get("country") or "").lower(), "")
    return ", ".join(str(v) for v in (loc.get("city"), loc.get("region"), country) if v)


def _facet_count(facets: list[Any], name: str) -> int:
    """Workday's first page has location facets with a count per country. Finds Canada's."""
    for f in facets:
        if not isinstance(f, dict):
            continue
        if str(f.get("descriptor", "")).strip().lower() == name and isinstance(f.get("count"), int):
            return int(f["count"])
        n = _facet_count(f.get("values") or [], name)
        if n:
            return n
    return 0


def _previous() -> list[dict[str, Any]]:
    """The boards already in discovered_boards.json, so a new run adds to them."""
    try:
        rows = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [r for r in rows if isinstance(r, dict) and r.get("board") and r.get("adapter_type")]


def _title(slug: str) -> str:
    return re.sub(r"[-_.]+", " ", slug).strip().title()


async def main() -> None:
    known = _known()
    async with httpx.AsyncClient(timeout=30.0, headers=_UA, follow_redirects=True) as client:
        print("Reading Common Crawl's URL index...", flush=True)
        # Workday site names come in any case, like CircleKStoreJobs and circlekstorejobs, so
        # compare without case and keep one spelling of each board
        unique: dict[tuple[str, str], tuple[str, str]] = {}
        print("Reading the GitHub student lists...", flush=True)
        names = await find_boards_in_lists(client)
        crawled = set() if "--lists" in sys.argv else await find_boards(client)
        for adapter, board in sorted(crawled | set(names)):
            unique.setdefault((adapter, board.lower()), (adapter, board))
        names_by_key = {(a, b.lower()): n for (a, b), n in names.items()}
        already = {(r["adapter_type"], str(r["board"]).lower()) for r in _previous()}
        boards = [b for key, b in unique.items() if key not in known and key not in already]
        print(f"Checking {len(boards)} boards for jobs in Canada or US student roles...", flush=True)
        gate = asyncio.Semaphore(_CONCURRENCY)
        done = 0

        async def one(adapter: str, board: str) -> tuple[str, str, str, int] | None:
            nonlocal done
            async with gate:
                got = await probe(client, adapter, board)
            done += 1
            if done % 250 == 0:
                print(f"  checked {done}/{len(boards)}", flush=True)
            if not got:
                return None
            # A name from the student lists beats one made from the board's web address
            return (names_by_key.get((adapter, board.lower()), got[0]), adapter, board, got[1])

        results = [r for r in await asyncio.gather(*(one(a, b) for a, b in boards)) if r]

    # Keep boards earlier runs found that this run did not check again
    fresh = {(a, b.lower()) for _, a, b, _ in results}
    for row in _previous():
        if (row["adapter_type"], row["board"].lower()) not in fresh:
            results.append(
                (row["company"], row["adapter_type"], row["board"], int(row.get("jobs") or 0))
            )
    results.sort(key=lambda r: (-r[3], r[0].lower()))
    rows = [{"company": c, "adapter_type": a, "board": b, "jobs": n} for c, a, b, n in results]
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Kept {len(rows)} boards with {sum(r['jobs'] for r in rows)} jobs. Wrote {OUT.name}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
