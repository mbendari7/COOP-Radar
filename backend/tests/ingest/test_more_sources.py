"""
Tests for the newer job sources: Recruitee, BambooHR and Rippling boards (app/ingest/ats.py),
student kept GitHub tables (app/ingest/github_lists.py) and lists that give only a season.
HTTP is faked with respx using replies shaped like the real ones.
"""

import time
from datetime import date

import respx
from httpx import Response

from app.ingest.ats import BambooHrAdapter, RecruiteeAdapter, RipplingAdapter
from app.ingest.github_lists import GithubListAdapter, rows_from_markdown
from app.ingest.registry import adapter_for
from app.ingest.simplify import posting_from_listing, season_terms
from seed import job_boards


def make_source(adapter_type: str, **config: str) -> object:
    class FakeSource:
        pass

    src = FakeSource()
    src.adapter_type = adapter_type  # type: ignore[attr-defined]
    src.config = config  # type: ignore[attr-defined]
    return src


def test_registry_knows_the_new_sources() -> None:
    assert isinstance(adapter_for(make_source("recruitee")), RecruiteeAdapter)
    assert isinstance(adapter_for(make_source("bamboohr")), BambooHrAdapter)
    assert isinstance(adapter_for(make_source("rippling")), RipplingAdapter)
    assert isinstance(adapter_for(make_source("github_list")), GithubListAdapter)


@respx.mock
async def test_recruitee_keeps_canada_and_us_student_roles() -> None:
    offer = {
        "id": 1, "status": "published", "title": "Data Co-op", "city": "Toronto",
        "state_name": "Ontario", "country_code": "CA", "remote": False, "hybrid": True,
        "description": "<p>Work with data.</p>", "requirements": "<p>Python</p>",
        "careers_url": "https://maple.recruitee.com/o/data-coop",
        "published_at": "2026-10-15 15:00:38 UTC",
    }
    us_senior = {**offer, "id": 2, "title": "Senior Accountant", "city": "Chicago",
                 "state_name": "Illinois", "country_code": "US"}
    respx.get("https://maple.recruitee.com/api/offers/").mock(
        return_value=Response(200, json={"offers": [offer, us_senior]})
    )

    jobs = await RecruiteeAdapter().fetch(make_source("recruitee", board="maple", company="Maple"))

    assert [(j.title, j.city, j.province, j.country, j.work_mode) for j in jobs] == [
        ("Data Co-op", "Toronto", "ON", "CA", "hybrid")
    ]
    assert "Python" in jobs[0].description
    assert jobs[0].posted_at is not None and jobs[0].posted_at.day == 15


@respx.mock
async def test_bamboohr_reads_the_list_then_each_description() -> None:
    respx.get("https://maple.bamboohr.com/careers/list").mock(return_value=Response(200, json={
        "result": [
            {"id": "7", "jobOpeningName": "Field Technician", "location": {"city": None},
             "atsLocation": {"country": "Canada", "state": "British Columbia", "city": "Vancouver"}},
            {"id": "8", "jobOpeningName": "Account Manager",
             "location": {"city": "Denver", "state": "Colorado"}, "atsLocation": {}},
        ]
    }))
    respx.get("https://maple.bamboohr.com/careers/7/detail").mock(return_value=Response(200, json={
        "result": {"jobOpening": {
            "description": "<p>Fix things.</p>", "datePosted": "2026-10-01",
            "jobOpeningShareUrl": "https://maple.bamboohr.com/careers/7",
        }}
    }))

    jobs = await BambooHrAdapter().fetch(make_source("bamboohr", board="maple", company="Maple"))

    assert [(j.title, j.city, j.province) for j in jobs] == [("Field Technician", "Vancouver", "BC")]
    assert jobs[0].description == "Fix things."
    assert jobs[0].source_url == "https://maple.bamboohr.com/careers/7"


@respx.mock
async def test_rippling_reads_the_board_then_each_job() -> None:
    base = "https://api.rippling.com/platform/api/ats/v1/board/maple/jobs"
    respx.get(base).mock(return_value=Response(200, json=[
        {"uuid": "a", "name": " Software Intern ", "url": "https://ats.rippling.com/maple/jobs/a",
         "workLocation": {"label": "Toronto, ON, Canada"}},
        {"uuid": "b", "name": "Office Lead", "url": "https://ats.rippling.com/maple/jobs/b",
         "workLocation": {"label": "Berlin, Germany"}},
    ]))
    respx.get(f"{base}/a").mock(return_value=Response(200, json={
        "description": {"company": "<p>About us</p>", "role": "<p>Build apps</p>"},
        "createdOn": "2026-10-06T16:36:07.947000-07:00",
    }))

    jobs = await RipplingAdapter().fetch(make_source("rippling", board="maple", company="Maple"))

    assert [(j.title, j.city, j.country) for j in jobs] == [("Software Intern", "Toronto", "CA")]
    assert "Build apps" in jobs[0].description


README = """
# Canadian Tech Internships

| Company | Role | Location | Apply | Date Posted |
|--------|------|----------|:-----:|--------------|
| **Maple Labs** | Software Co-op (Winter 2027) | Ottawa, ON | [![Apply](https://img.shields.io/badge/-Apply-blue)](https://jobs.example.com/1) | Oct 15, 2026 |
| ↳ | Data Co-op | Toronto, ON / Remote | [![Apply](https://img.shields.io/badge/-Apply-blue)](https://jobs.example.com/2) | Oct 14, 2026 |

| Varian | Test Co-op | Ottawa, ON | Closed🔒 | Oct 9, 2026 |
| Old Co | Developer Co-op (Winter 2026) | Montreal, QC | [Apply](https://jobs.example.com/3) | Oct 1, 2026 |
| Fresh Co | IT Co-op | Halifax, NS | [Apply](https://jobs.example.com/4) | 3d |
"""


def test_github_table_rows_become_postings() -> None:
    today = date(2026, 10, 17)
    rows = rows_from_markdown(README, source="someone/list", country="CA", today=today)

    assert [(r.title, r.company, r.city, r.province, r.country) for r in rows] == [
        ("Software Co-op (Winter 2027)", "Maple Labs", "Ottawa", "ON", "CA"),
        ("Data Co-op", "Maple Labs", "Toronto", "ON", "CA"),  # ↳ means the company above
        ("IT Co-op", "Fresh Co", "Halifax", "NS", "CA"),
    ]
    # The link to apply, never the picture of the Apply button
    assert rows[0].source_url == "https://jobs.example.com/1"
    assert rows[0].posted_at is not None and rows[0].posted_at.date() == date(2026, 10, 15)
    assert rows[2].posted_at is not None and rows[2].posted_at.date() == date(2026, 10, 14)
    assert "someone/list" in rows[0].description


@respx.mock
async def test_github_list_fetch_uses_next_summers_repo() -> None:
    respx.get(
        "https://raw.githubusercontent.com/someone/Interns-2027/main/README.md"
    ).mock(return_value=Response(200, text=README))
    src = make_source("github_list", repo="someone/Interns-{summer}", country="CA")
    jobs = await GithubListAdapter().fetch(src)
    assert len(jobs) >= 2


def test_a_season_with_no_year_means_the_next_one_after_posting() -> None:
    today = date(2026, 10, 17)
    assert season_terms("Winter", date(2026, 10, 1), today) == ["Winter 2027"]
    assert season_terms("Spring/Summer", date(2026, 10, 1), today) == ["Spring 2027", "Summer 2027"]
    # Posted in June 2025 for the winter, so Winter 2026, which is over
    assert season_terms("Winter", date(2025, 6, 7), today) == []


def test_list_entries_nobody_touched_in_months_are_skipped() -> None:
    now = int(time.time())
    entry = {
        "company_name": "Maple", "title": "Intern", "active": True, "is_visible": True,
        "url": "https://jobs.example.com/x", "locations": ["Toronto, ON"], "season": "Winter",
        "date_posted": now - 86400, "date_updated": now - 86400,
    }
    fresh = posting_from_listing(entry)
    assert fresh is not None and fresh.term.startswith("Winter")
    old = {**entry, "date_posted": now - 400 * 86400, "date_updated": now - 400 * 86400}
    assert posting_from_listing(old) is None


def test_new_lists_are_seeded() -> None:
    assert any("negarprh" in c["repo"] for _, c in job_boards.GITHUB_LIST_SOURCES)
    assert any("vanshb03" in c["repo"] for _, c in job_boards.SIMPLIFY_SOURCES)


@respx.mock
async def test_oracle_reads_the_list_then_the_city_from_the_details() -> None:
    from app.ingest.oracle import OracleAdapter
    from seed.discover_boards import board_from_url

    host = "fa-test-saasfaprod1.fa.ocs.oraclecloud.com"
    api = f"https://{host}/hcmRestApi/resources/latest"
    respx.get(url__startswith=f"{api}/recruitingCEJobRequisitions?").mock(
        return_value=Response(200, json={"items": [{"TotalJobsCount": 2, "requisitionList": [
            {"Id": "41311", "Title": "Embedded Developer Co-op", "PrimaryLocation": "Canada",
             "PrimaryLocationCountry": "CA", "PostedDate": "2026-10-15", "WorkplaceType": "Onsite"},
            {"Id": "9", "Title": "Counsel", "PrimaryLocation": "Finland",
             "PrimaryLocationCountry": "FI"},
        ]}]})
    )
    respx.get(url__startswith=f"{api}/recruitingCEJobRequisitionDetails").mock(
        return_value=Response(200, json={"items": [{
            "ExternalDescriptionStr": "<p>Write C++.</p>",
            "ExternalPostedStartDate": "2026-10-15T16:58:19+00:00",
            "workLocation": [{"TownOrCity": "Ottawa", "Region2": "Ontario", "Country": "CA"}],
        }]})
    )

    src = make_source("oracle", board=f"{host}/CX_1", company="Nokia")
    jobs = await OracleAdapter().fetch(src)

    assert [(j.title, j.city, j.province, j.country) for j in jobs] == [
        ("Embedded Developer Co-op", "Ottawa", "ON", "CA")
    ]
    assert jobs[0].description == "Write C++."
    assert jobs[0].source_url == f"https://{host}/hcmUI/CandidateExperience/en/sites/CX_1/job/41311"
    assert board_from_url(jobs[0].source_url or "") == ("oracle", f"{host}/CX_1")
