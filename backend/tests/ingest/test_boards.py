"""
Tests for the Greenhouse / Lever / Ashby career-board adapters.

HTTP is mocked with respx using trimmed copies of real API responses — no live network calls.
"""

from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from app.config import get_settings
from app.ingest.base import AdapterError
from app.ingest.boards import (
    AshbyAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
    _parse_dt,
    _pick_location,
    choose_location,
    html_to_text,
    parse_location,
    parse_us_location,
)
from app.ingest.dedup import titles_match
from app.ingest.registry import adapter_for


def make_source(board: str, company: str = "Acme") -> object:
    class FakeSource:
        config = {"board": board, "company": company}

    return FakeSource()


# ── Location parsing (real strings seen on live boards) ───────────────────────

@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Toronto, Ontario, Canada", ("Toronto", "ON")),
        ("Vancouver, BC", ("Vancouver", "BC")),
        ("Lethbridge, AB", ("Lethbridge", "AB")),
        ("SEA, SF, NY, Toronto", ("Toronto", "ON")),
        ("Calgary, Canada; Vancouver, Canada", ("Calgary", "AB")),
        ("Montréal, Quebec", ("Montréal", "QC")),
        ("Ontario, Canada", ("", "ON")),
        ("Remote Canada", ("Remote", "")),
        ("Hybrid - Toronto", ("Toronto", "ON")),
        ("US / Canada", ("Canada", "")),
        ("", ("", "")),
    ],
)
def test_parse_location(location: str, expected: tuple[str, str]) -> None:
    assert parse_location(location) == expected


def test_london_is_not_mistaken_for_london_ontario() -> None:
    """London (UK) is skipped; the role's Canadian location is the one shown."""
    assert _pick_location("London", "Remote, Canada") == "Remote, Canada"
    assert _pick_location("London", "New York") is None


def test_pick_location_uses_first_matching_location() -> None:
    assert _pick_location("Toronto, ON", "Remote, Canada") == "Toronto, ON"
    assert _pick_location("San Francisco", "Waterloo, Ontario") == "Waterloo, Ontario"


def test_vancouver_washington_is_not_canada() -> None:
    assert _pick_location("Vancouver, WA") is None
    assert _pick_location("Vancouver, BC") == "Vancouver, BC"


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("San Francisco, CA", ("San Francisco", "CA")),
        ("Seattle, Washington, USA", ("Seattle", "WA")),
        ("New York City", ("New York City", "NY")),
        ("NYC", ("New York", "NY")),
        ("Washington, D.C.", ("Washington", "DC")),
        ("Remote - US", ("Remote", "")),
        ("Hybrid - New York", ("New York", "NY")),
        ("United States", ("United States", "")),
    ],
)
def test_parse_us_location(location: str, expected: tuple[str, str]) -> None:
    assert parse_us_location(location) == expected


def test_us_jobs_are_kept_only_for_students_by_default() -> None:
    assert choose_location("Software Engineer Intern", "San Francisco, CA") == (
        "San Francisco, CA", "US"
    )
    assert choose_location("Co-op, Data", "Remote - US") == ("Remote - US", "US")
    assert choose_location("Senior Software Engineer", "San Francisco, CA") is None
    # Canada wins when a job lists both
    assert choose_location("Senior Engineer", "New York, NY", "Toronto, ON") == ("Toronto, ON", "CA")
    assert choose_location("Intern", "Dublin, Ireland") is None


def test_us_jobs_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "ingest_us_jobs", "all")
    assert choose_location("Senior Software Engineer", "Austin, TX") == ("Austin, TX", "US")
    monkeypatch.setattr(get_settings(), "ingest_us_jobs", "none")
    assert choose_location("Software Engineer Intern", "Austin, TX") is None


def test_html_to_text_unescapes_and_strips_tags() -> None:
    raw = "&lt;p&gt;Build &amp;amp; ship&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;"
    text = html_to_text(raw)
    assert "Build & ship" in text
    assert "• Python" in text
    assert "<" not in text


def test_parse_dt_handles_iso_and_epoch_ms() -> None:
    assert _parse_dt("2026-09-01T12:00:00Z") == datetime(2026, 9, 1, 12, tzinfo=UTC)
    assert _parse_dt(1756728000000) == datetime(2025, 9, 1, 12, tzinfo=UTC)
    assert _parse_dt("not a date") is None
    assert _parse_dt(None) is None


def test_titles_match_is_case_insensitive_and_fuzzy() -> None:
    assert titles_match("Frontend React Developer", "frontend react develoer")
    assert not titles_match("Data Analyst Co-op", "Backend Developer Co-op")


def test_registry_knows_board_adapters() -> None:
    def src(kind: str) -> object:
        return type("S", (), {"adapter_type": kind})()

    assert isinstance(adapter_for(src("greenhouse")), GreenhouseAdapter)
    assert isinstance(adapter_for(src("lever")), LeverAdapter)
    assert isinstance(adapter_for(src("ashby")), AshbyAdapter)
    assert isinstance(adapter_for(src("smartrecruiters")), SmartRecruitersAdapter)


# ── Adapters ──────────────────────────────────────────────────────────────────

# The list has no descriptions; each kept job's description comes from its own URL
GREENHOUSE = {
    "jobs": [
        {
            "id": 101,
            "title": "Software Engineering Intern (Winter 2027)",
            "location": {"name": "Toronto, Ontario, Canada"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
            "first_published": "2026-09-20T10:00:00-04:00",
            "company_name": "Acme Inc.",
        },
        {
            "id": 102,
            "title": "Account Executive",
            "location": {"name": "Dublin, Ireland"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/102",
        },
        {
            "id": 103,
            "title": "Hardware Engineering Intern",
            "location": {"name": "Austin, TX"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/103",
        },
        {
            "id": 104,
            "title": "Staff Engineer",
            "location": {"name": "Austin, TX"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/104",
        },
    ]
}
GREENHOUSE_DETAIL = {"id": 101, "content": "&lt;p&gt;Write Python &amp;amp; Go.&lt;/p&gt;"}

LEVER = [
    {
        "id": "abc",
        "text": "Data Co-op",
        "categories": {"location": "Remote - Canada"},
        "country": "CA",
        "workplaceType": "remote",
        "descriptionPlain": "Work with SQL and dashboards.",
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "createdAt": 1756728000000,
    },
    {
        "id": "def",
        "text": "Designer",
        "categories": {"location": "Berlin"},
        "country": "DE",
        "descriptionPlain": "",
        "hostedUrl": "https://jobs.lever.co/acme/def",
    },
]

ASHBY = {
    "jobs": [
        {
            "id": "a1",
            "title": "Machine Learning Intern",
            "location": "London",
            "secondaryLocations": [{"location": "Toronto"}],
            "workplaceType": "Hybrid",
            "isRemote": False,
            "isListed": True,
            "descriptionPlain": "PyTorch and Python.",
            "jobUrl": "https://jobs.ashbyhq.com/acme/a1",
            "publishedAt": "2026-09-01T00:00:00Z",
        },
        {
            "id": "a2",
            "title": "Hidden Role",
            "location": "Toronto",
            "isListed": False,
        },
    ]
}


async def test_greenhouse_adapter_keeps_canadian_jobs_and_us_internships() -> None:
    with respx.mock() as mock:
        mock.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
            return_value=Response(200, json=GREENHOUSE)
        )
        mock.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs/101").mock(
            return_value=Response(200, json=GREENHOUSE_DETAIL)
        )
        # A failed description fetch keeps the job, without a description
        mock.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs/103").mock(
            return_value=Response(500)
        )
        postings = await GreenhouseAdapter().fetch(make_source("acme"))

    assert [p.source_ref for p in postings] == ["101", "103"]
    us = postings[1]
    assert (us.city, us.province, us.country, us.description) == ("Austin", "TX", "US", "")
    p = postings[0]
    assert p.country == "CA"
    assert (p.title, p.company, p.city, p.province) == (
        "Software Engineering Intern (Winter 2027)", "Acme Inc.", "Toronto", "ON"
    )
    assert p.work_mode == "onsite"
    assert "Python & Go." in p.description
    assert p.source_ref == "101"
    assert p.source_url == "https://boards.greenhouse.io/acme/jobs/101"
    assert p.posted_at is not None


async def test_lever_adapter_maps_remote_jobs() -> None:
    with respx.mock() as mock:
        mock.get("https://api.lever.co/v0/postings/acme?mode=json").mock(
            return_value=Response(200, json=LEVER)
        )
        postings = await LeverAdapter().fetch(make_source("acme"))

    assert [p.title for p in postings] == ["Data Co-op"]
    assert postings[0].work_mode == "remote"
    assert postings[0].city == "Remote"
    assert postings[0].description == "Work with SQL and dashboards."


async def test_ashby_adapter_uses_canadian_secondary_location_and_skips_unlisted() -> None:
    with respx.mock() as mock:
        mock.get("https://api.ashbyhq.com/posting-api/job-board/acme").mock(
            return_value=Response(200, json=ASHBY)
        )
        postings = await AshbyAdapter().fetch(make_source("acme"))

    assert len(postings) == 1
    assert (postings[0].city, postings[0].province) == ("Toronto", "ON")
    assert postings[0].work_mode == "hybrid"


SMART_LIST = {
    "totalFound": 3,
    "content": [
        {
            "id": "1", "name": "Software Developer Co-op",
            "location": {"city": "Montréal", "region": "QC", "country": "ca", "hybrid": True},
            "releasedDate": "2026-10-01T12:00:00Z",
        },
        {
            "id": "2", "name": "Game Designer",
            "location": {"city": "Paris", "region": "Île-de-France", "country": "fr"},
        },
        {
            "id": "3", "name": "Senior Producer",
            "location": {"city": "San Francisco", "region": "CA", "country": "us"},
        },
    ],
}
SMART_DETAIL = {
    "postingUrl": "https://jobs.smartrecruiters.com/Acme/1-software-developer-co-op",
    "jobAd": {"sections": {
        "jobDescription": {"text": "<p>Build tools in C++.</p>"},
        "qualifications": {"text": "<ul><li>Enrolled in Computer Science</li></ul>"},
    }},
}


async def test_smartrecruiters_adapter() -> None:
    with respx.mock() as mock:
        mock.get(
            "https://api.smartrecruiters.com/v1/companies/Acme/postings?limit=100&offset=0"
        ).mock(return_value=Response(200, json=SMART_LIST))
        mock.get("https://api.smartrecruiters.com/v1/companies/Acme/postings/1").mock(
            return_value=Response(200, json=SMART_DETAIL)
        )
        postings = await SmartRecruitersAdapter().fetch(make_source("Acme", "Acme Games"))

    assert len(postings) == 1
    p = postings[0]
    assert (p.title, p.company, p.city, p.province, p.country) == (
        "Software Developer Co-op", "Acme Games", "Montréal", "QC", "CA"
    )
    assert p.work_mode == "hybrid"
    assert "Build tools in C++." in (p.description or "")
    assert "• Enrolled in Computer Science" in (p.description or "")
    assert p.source_url == SMART_DETAIL["postingUrl"]


async def test_board_adapter_http_error_raises() -> None:
    with respx.mock() as mock:
        mock.get("https://api.ashbyhq.com/posting-api/job-board/gone").mock(
            return_value=Response(404)
        )
        with pytest.raises(AdapterError, match="HTTP 404"):
            await AshbyAdapter().fetch(make_source("gone"))


async def test_board_adapter_requires_board_name() -> None:
    with pytest.raises(AdapterError, match="Board name"):
        await LeverAdapter().fetch(make_source(""))
