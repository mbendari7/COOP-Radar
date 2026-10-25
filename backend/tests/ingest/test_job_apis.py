"""
Tests for The Muse and Himalayas job API adapters.
HTTP is faked with respx using trimmed copies of real replies.
"""

from datetime import UTC, datetime, timedelta

import pytest
import respx
from httpx import Response

from app.ingest import himalayas, themuse
from app.ingest.base import AdapterError
from app.ingest.himalayas import HimalayasAdapter
from app.ingest.registry import adapter_for
from app.ingest.themuse import TheMuseAdapter
from seed import job_boards

MUSE_URL = "https://www.themuse.com/api/public/jobs"
HIMALAYAS_URL = "https://himalayas.app/jobs/api/search"


def make_source(adapter_type: str, **config: str) -> object:
    class FakeSource:
        pass

    src = FakeSource()
    src.adapter_type = adapter_type  # type: ignore[attr-defined]
    src.config = config  # type: ignore[attr-defined]
    return src


def muse_job(
    name: str, *places: str, level: str = "Internship", id: int = 1, age: int = 2
) -> dict[str, object]:
    return {
        "id": id,
        "name": name,
        "contents": "<p>Help our team ship.</p>",
        "publication_date": (datetime.now(UTC) - timedelta(days=age)).isoformat(),
        "locations": [{"name": p} for p in places],
        "levels": [{"name": level, "short_name": level.lower()}],
        "refs": {"landing_page": f"https://www.themuse.com/jobs/acme/{id}"},
        "company": {"id": 9, "name": "Acme"},
    }


def himalayas_job(title: str, countries: list[str], guid: str = "g1") -> dict[str, object]:
    return {
        "title": title,
        "companyName": "Remote Co",
        "description": "<p>Work from anywhere in Canada.</p>",
        "excerpt": "Short text",
        "locationRestrictions": countries,
        "pubDate": 1792932297,
        "applicationLink": f"https://himalayas.app/companies/remote-co/jobs/{guid}",
        "guid": f"https://himalayas.app/companies/remote-co/jobs/{guid}",
    }


def test_registry_knows_both() -> None:
    assert isinstance(adapter_for(make_source("themuse")), TheMuseAdapter)
    assert isinstance(adapter_for(make_source("himalayas")), HimalayasAdapter)


def test_muse_keeps_canada_and_us_internships() -> None:
    ca = themuse.posting_from_job(muse_job("Marketing Intern", "Toronto, Canada"))
    assert ca is not None and (ca.city, ca.country) == ("Toronto", "CA")
    assert ca.source_url == "https://www.themuse.com/jobs/acme/1"
    assert "Help our team ship." in (ca.description or "")
    # The Internship level counts as a student role even when the title does not say so
    us = themuse.posting_from_job(muse_job("Summer Analyst", "New York, NY"))
    assert us is not None and us.country == "US"


def test_muse_skips_senior_us_and_remote_only_jobs() -> None:
    assert themuse.posting_from_job(muse_job("Director", "New York, NY", level="Senior Level")) is None
    assert themuse.posting_from_job(muse_job("Intern", "Flexible / Remote")) is None


def test_muse_skips_jobs_posted_long_ago() -> None:
    # The Muse still lists internships from years back, like a Summer 2025 role
    assert themuse.posting_from_job(muse_job("Summer 2025 Intern", "Toronto, Canada", age=400)) is None
    assert themuse.posting_from_job(muse_job("Intern", "Toronto, Canada", age=60)) is not None
    assert themuse.posting_from_job(muse_job("Intern", "Toronto, Canada", age=60), max_age_days=30) is None


@respx.mock
async def test_muse_fetch_reads_pages_until_the_last() -> None:
    route = respx.get(MUSE_URL).mock(side_effect=[
        Response(200, json={"page_count": 2, "results": [muse_job("A Intern", "Ottawa, Canada", id=1)]}),
        Response(200, json={"page_count": 2, "results": [
            muse_job("A Intern", "Ottawa, Canada", id=1), muse_job("B Intern", "Calgary, Canada", id=2),
        ]}),
    ])
    out = await TheMuseAdapter().fetch(make_source("themuse", pages="5"))
    assert [p.title for p in out] == ["A Intern", "B Intern"]
    assert route.call_count == 2
    assert route.calls[0].request.url.params["level"] == "Internship"


@respx.mock
async def test_muse_rate_limit_keeps_what_it_has() -> None:
    respx.get(MUSE_URL).mock(side_effect=[
        Response(200, json={"page_count": 9, "results": [muse_job("A Intern", "Ottawa, Canada")]}),
        Response(429),
    ])
    out = await TheMuseAdapter().fetch(make_source("themuse"))
    assert [p.title for p in out] == ["A Intern"]


@respx.mock
async def test_muse_error_is_an_adapter_error() -> None:
    respx.get(MUSE_URL).mock(return_value=Response(503))
    with pytest.raises(AdapterError):
        await TheMuseAdapter().fetch(make_source("themuse"))


def test_himalayas_keeps_only_jobs_open_to_canada() -> None:
    p = himalayas.posting_from_job(himalayas_job("Data Analyst", ["Canada", "United States"]))
    assert p is not None
    assert (p.country, p.work_mode, p.city) == ("CA", "remote", "Remote")
    assert p.posted_at is not None and p.posted_at.year == 2026
    assert "anywhere in Canada" in (p.description or "")
    assert himalayas.posting_from_job(himalayas_job("Data Analyst", ["India"])) is None
    # Open to every country only when the source asks for it
    assert himalayas.posting_from_job(himalayas_job("Writer", [])) is None
    assert himalayas.posting_from_job(himalayas_job("Writer", []), worldwide=True) is not None


@respx.mock
async def test_himalayas_fetch_stops_on_a_short_page() -> None:
    full = [himalayas_job(f"Job {i}", ["Canada"], guid=f"g{i}") for i in range(20)]
    route = respx.get(HIMALAYAS_URL).mock(side_effect=[
        Response(200, json={"jobs": full}),
        Response(200, json={"jobs": [himalayas_job("Last", ["Canada"], guid="last")]}),
    ])
    out = await HimalayasAdapter().fetch(make_source("himalayas", query="intern"))
    assert len(out) == 21
    assert route.call_count == 2
    params = route.calls[1].request.url.params
    assert (params["page"], params["country"], params["q"]) == ("2", "Canada", "intern")


def test_both_are_seeded() -> None:
    assert any(cfg.get("levels") == "Internship" for _, cfg in job_boards.MUSE_SOURCES)
    assert job_boards.HIMALAYAS_SOURCES
