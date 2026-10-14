"""
Tests for the Workable job search adapter and the list of boards seed/discover_boards.py found.
HTTP is faked with respx using trimmed copies of real replies.
"""

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.ingest.base import AdapterError
from app.ingest.registry import adapter_for
from app.ingest.workable import WorkableAdapter, posting_from_job
from seed import job_boards
from seed.discover_boards import _facet_count

URL = "https://jobs.workable.com/api/v1/jobs"


def job(title: str, city: str, region: str, country: str, **extra: object) -> dict[str, object]:
    return {
        "id": f"id-{title}-{city}",
        "title": title,
        "state": "published",
        "description": "<p>Join our small team.</p>",
        "requirementsSection": "<ul><li>Excel</li></ul>",
        "benefitsSection": "",
        "url": f"https://jobs.workable.com/view/abc/{title}",
        "location": {"city": city, "subregion": region, "countryName": country},
        "locations": [f"{city}, {region}, {country}"],
        "created": "2026-10-13T08:59:54.039Z",
        "company": {"title": "Maple Labs"},
        "workplace": "hybrid",
        **extra,
    }


def make_source(**config: str) -> object:
    class FakeSource:
        adapter_type = "workable"

    src = FakeSource()
    src.config = config  # type: ignore[attr-defined]
    return src


def test_registry_knows_workable() -> None:
    assert isinstance(adapter_for(make_source()), WorkableAdapter)


def test_job_becomes_a_posting() -> None:
    p = posting_from_job(job("Marketing Co-op", "Halifax", "Nova Scotia", "Canada"))
    assert p is not None
    assert (p.title, p.company, p.city, p.province, p.country) == (
        "Marketing Co-op", "Maple Labs", "Halifax", "NS", "CA"
    )
    assert p.work_mode == "hybrid"
    assert "Join our small team." in (p.description or "") and "Excel" in (p.description or "")
    assert p.source_url == "https://jobs.workable.com/view/abc/Marketing Co-op"


def test_us_keeps_only_student_roles() -> None:
    assert posting_from_job(job("Sales Manager", "Austin", "Texas", "United States")) is None
    intern = posting_from_job(job("Sales Intern", "Austin", "Texas", "United States"))
    assert intern is not None and intern.country == "US"


def test_skips_closed_and_nameless_jobs() -> None:
    assert posting_from_job(job("Analyst", "Toronto", "Ontario", "Canada", state="closed")) is None
    assert posting_from_job(job("Analyst", "Toronto", "Ontario", "Canada", company={})) is None


@respx.mock
async def test_fetch_follows_pages_and_skips_repeats() -> None:
    first = job("Analyst", "Toronto", "Ontario", "Canada")
    second = job("Designer", "Calgary", "Alberta", "Canada")
    route = respx.get(URL).mock(side_effect=[
        Response(200, json={"jobs": [first], "nextPageToken": "t2"}),
        Response(200, json={"jobs": [first, second], "nextPageToken": None}),
    ])
    out = await WorkableAdapter().fetch(make_source(location="Canada"))
    assert [p.title for p in out] == ["Analyst", "Designer"]
    assert route.calls[1].request.url.params["pageToken"] == "t2"


@respx.mock
async def test_fetch_error_is_an_adapter_error() -> None:
    respx.get(URL).mock(return_value=Response(503))
    with pytest.raises(AdapterError):
        await WorkableAdapter().fetch(make_source())


def test_workday_facet_count_finds_canada() -> None:
    facets = [
        {"facetParameter": "timeType", "values": [{"descriptor": "Full time", "count": 9}]},
        {"facetParameter": "locationMainGroup", "values": [
            {"facetParameter": "locationCountry", "values": [
                {"descriptor": "United States of America", "count": 40},
                {"descriptor": "Canada", "count": 7},
            ]},
        ]},
    ]
    assert _facet_count(facets, "canada") == 7
    assert _facet_count([], "canada") == 0


def test_discovered_boards_are_read_and_bad_rows_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "discovered_boards.json"
    file.write_text(json.dumps([
        {"company": "Tiny Co", "adapter_type": "ashby", "board": "tinyco", "jobs": 2},
        {"company": "Bad", "adapter_type": "rss", "board": "x"},
        {"adapter_type": "lever", "board": "noname"},
    ]))
    monkeypatch.setattr(job_boards, "_DISCOVERED", file)
    assert job_boards.discovered_boards() == [
        {"company": "Tiny Co", "adapter_type": "ashby", "board": "tinyco"}
    ]
    monkeypatch.setattr(job_boards, "_DISCOVERED", tmp_path / "missing.json")
    assert job_boards.discovered_boards() == []
