"""
Tests for Simplify's student lists on GitHub (app/ingest/simplify.py). HTTP is faked with respx
using entries shaped like the real listings.json.
"""

from datetime import date

import pytest
import respx
from httpx import Response

from app.ingest.base import AdapterError
from app.ingest.boards import choose_location
from app.ingest.registry import adapter_for
from app.ingest.simplify import SimplifyAdapter, posting_from_listing, repos_to_try, upcoming_terms
from seed import job_boards

RAW = "https://raw.githubusercontent.com/SimplifyJobs/{repo}/dev/.github/scripts/listings.json"


def listing(title: str, locations: list[str], **extra: object) -> dict[str, object]:
    return {
        "source": "Simplify",
        "category": "Software",
        "company_name": "Maple Labs",
        "id": f"id-{title}",
        "title": title,
        "active": True,
        "terms": ["Summer 2027"],
        "date_posted": 1771484864,
        "url": f"https://jobs.example.com/{title}",
        "locations": locations,
        "is_visible": True,
        "degrees": ["Bachelor's"],
        **extra,
    }


def make_source(**config: str) -> object:
    class FakeSource:
        adapter_type = "simplify"

    src = FakeSource()
    src.config = config  # type: ignore[attr-defined]
    return src


def test_registry_knows_simplify() -> None:
    assert isinstance(adapter_for(make_source()), SimplifyAdapter)


def test_listing_becomes_a_posting_with_its_term() -> None:
    p = posting_from_listing(listing("Software Engineer Intern", ["Toronto, ON, Canada"]))
    assert p is not None
    assert (p.title, p.company, p.city, p.province, p.country, p.term) == (
        "Software Engineer Intern", "Maple Labs", "Toronto", "ON", "CA", "Summer 2027"
    )
    assert p.source_url == "https://jobs.example.com/Software Engineer Intern"
    assert p.posted_at is not None and p.posted_at.year == 2026  # seconds, not milliseconds
    assert "Bachelor's" in (p.description or "")


def test_us_new_grad_roles_count_as_student_roles() -> None:
    # "Software Engineer" alone would be skipped in the US, but every role on the list is for
    # students or new grads
    p = posting_from_listing(listing("Software Engineer", ["Austin, TX"], terms=[]))
    assert p is not None and p.country == "US" and p.term == ""


@pytest.mark.parametrize(
    "entry",
    [
        listing("Closed Intern", ["Toronto, ON"], active=False),
        listing("Hidden Intern", ["Toronto, ON"], is_visible=False),
        listing("London Intern", ["London, UK"]),
        listing("", ["Toronto, ON"]),
    ],
)
def test_skipped_listings(entry: dict[str, object]) -> None:
    assert posting_from_listing(entry) is None


def test_upcoming_terms_skip_terms_that_are_over() -> None:
    today = date(2026, 10, 16)
    terms = ["Winter 2026", "Summer 2026", "Summer 2027", "Winter 2027"]
    assert upcoming_terms(terms, today) == ["Winter 2027", "Summer 2027"]
    assert upcoming_terms(["Fall 2026"], today) == []  # started over a month ago
    assert upcoming_terms(["N/A"], today) == []


def test_old_terms_stay_out_of_the_description() -> None:
    # Regression: "Terms: Summer 2025" in the text let the importer read the old term back out
    p = posting_from_listing(listing("Analyst Intern", ["Toronto, ON"], terms=["Summer 2025"]))
    assert p is not None and p.term == "" and "2025" not in (p.description or "")


def test_the_most_specific_canadian_place_wins() -> None:
    p = posting_from_listing(listing("Engineering Intern", ["Ontario, Canada", "Kanata, Ottawa, ON, Canada"]))
    assert p is not None and (p.city, p.province) == ("Ottawa", "ON")


def test_repo_year_follows_the_next_summer() -> None:
    repo = "SimplifyJobs/Summer{summer}-Internships"
    assert repos_to_try(repo, date(2026, 10, 16)) == [
        "SimplifyJobs/Summer2027-Internships", "SimplifyJobs/Summer2026-Internships"
    ]
    assert repos_to_try(repo, date(2027, 2, 1))[0] == "SimplifyJobs/Summer2027-Internships"
    assert repos_to_try("SimplifyJobs/New-Grad-Positions") == ["SimplifyJobs/New-Grad-Positions"]


@respx.mock
async def test_fetch_falls_back_to_last_years_list() -> None:
    upcoming, current = repos_to_try("SimplifyJobs/Summer{summer}-Internships")
    respx.get(RAW.format(repo=upcoming.split("/")[1])).mock(return_value=Response(404))
    respx.get(RAW.format(repo=current.split("/")[1])).mock(
        return_value=Response(200, json=[
            listing("Data Co-op", ["Waterloo, ON, Canada"]),
            listing("Ops Intern", ["Dublin, Ireland"]),
        ])
    )
    got = await SimplifyAdapter().fetch(make_source(repo="SimplifyJobs/Summer{summer}-Internships"))
    assert [p.title for p in got] == ["Data Co-op"]


@respx.mock
async def test_fetch_error_raises() -> None:
    respx.get(RAW.format(repo="New-Grad-Positions")).mock(return_value=Response(500))
    with pytest.raises(AdapterError):
        await SimplifyAdapter().fetch(make_source(repo="SimplifyJobs/New-Grad-Positions"))


async def test_fetch_needs_a_repo() -> None:
    with pytest.raises(AdapterError):
        await SimplifyAdapter().fetch(make_source())


def test_simplify_lists_are_seeded() -> None:
    repos = {config["repo"] for _, config in job_boards.SIMPLIFY_SOURCES}
    assert "SimplifyJobs/New-Grad-Positions" in repos


def test_us_early_career_titles_are_kept() -> None:
    # Any year, any level that is open to students or recent grads
    for title in ("Junior Developer", "Entry Level Analyst", "Software Engineer I", "Trainee Accountant"):
        assert choose_location(title, "Austin, TX") is not None, title
    assert choose_location("Staff Engineer", "Austin, TX") is None
