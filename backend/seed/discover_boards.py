"""
Finds more employers' career boards, including small and niche ones, and keeps the ones with
jobs in Canada or US student roles. The owner runs it now and then, it is not part of start.py.

    python -m seed.discover_boards            (from backend/, takes 10 to 20 minutes)

How it works
  1. Common Crawl is a free public copy of the web. Its URL index lists every Greenhouse,
     Lever, Ashby and Workday careers page it saw, which gives us thousands of company boards.
  2. For each board we ask that board's own public job API once, the same API the importer
     uses, and count the jobs we would keep (Canada, plus US co-op and intern roles).
  3. Boards with at least one are written to seed/discovered_boards.json. seed/job_boards.py
     adds them as import sources next to the hand picked list.

Boards already in JOB_BOARDS are skipped. Re-running replaces the file.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx

from app.ingest.base import BaseAdapter
from app.ingest.boards import AshbyAdapter, LeverAdapter, choose_location
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
    ("myworkdayjobs.com", "domain", "workday", re.compile(
        r"^https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)"
    )),
]
_NOT_BOARDS = {"embed", "v1", "api", "static", "robots.txt", "favicon.ico", "sitemap.xml", "wday",
               "job", "jobs", "login", "assets", "en-us"}


def _known() -> set[tuple[str, str]]:
    return {(adapter, board.lower()) for _, adapter, board, *_ in JOB_BOARDS}


async def _index_urls(client: httpx.AsyncClient, crawl: str, url: str, match: str) -> list[str]:
    base = f"{_INDEX}/{crawl}-index"
    params = {"url": url, "matchType": match, "output": "json", "fl": "url"}
    try:
        meta = (await client.get(base, params={**params, "showNumPages": "true"})).json()
    except (httpx.HTTPError, ValueError):
        return []
    urls: list[str] = []
    for page in range(int(meta.get("pages") or 0)):
        try:
            r = await client.get(base, params={**params, "page": str(page)}, timeout=180)
        except httpx.HTTPError:
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


def _title(slug: str) -> str:
    return re.sub(r"[-_.]+", " ", slug).strip().title()


async def main() -> None:
    known = _known()
    async with httpx.AsyncClient(timeout=30.0, headers=_UA, follow_redirects=True) as client:
        print("Reading Common Crawl's URL index...", flush=True)
        # Workday site names come in any case, like CircleKStoreJobs and circlekstorejobs, so
        # compare without case and keep one spelling of each board
        unique: dict[tuple[str, str], tuple[str, str]] = {}
        for adapter, board in sorted(await find_boards(client)):
            unique.setdefault((adapter, board.lower()), (adapter, board))
        boards = [b for key, b in unique.items() if key not in known]
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
            return (got[0], adapter, board, got[1]) if got else None

        results = [r for r in await asyncio.gather(*(one(a, b) for a, b in boards)) if r]

    results.sort(key=lambda r: (-r[3], r[0].lower()))
    rows = [{"company": c, "adapter_type": a, "board": b, "jobs": n} for c, a, b, n in results]
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Kept {len(rows)} boards with {sum(r['jobs'] for r in rows)} jobs. Wrote {OUT.name}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
