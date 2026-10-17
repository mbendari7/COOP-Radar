"""
Tests for the Workday and Adzuna adapters. HTTP is faked with respx using trimmed copies of
real replies, so nothing goes over the network.
"""

import json

import pytest
import respx
from httpx import Response

from app.config import get_settings
from app.ingest.adzuna import AdzunaAdapter, posting_from_result
from app.ingest.base import AdapterError
from app.ingest.boards import tidy_place
from app.ingest.registry import adapter_for
from app.ingest.workday import WorkdayAdapter, parse_board, posting_from_detail, wanted_by_scope

API = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers"


def make_source(board: str = "acme.wd3/Careers", **extra: str) -> object:
    class FakeSource:
        adapter_type = "workday"
        config = {"board": board, "company": "Acme", **extra}

    return FakeSource()


def detail(title: str, location: str, nation: str, **extra: object) -> dict[str, object]:
    info = {
        "title": title,
        "location": location,
        "additionalLocations": [],
        "jobDescription": "<p><b>Work Term:</b></p>Summer<p>A 4 month co-op.</p>",
        "jobReqId": f"R_{title[:5]}",
        "startDate": "2026-10-01",
        "endDate": "2026-11-13",
        "remoteType": "Hybrid",
        "externalUrl": f"https://acme.wd3.myworkdayjobs.com/Careers/job/{title[:5]}",
        "country": {"descriptor": nation, "alpha2Code": "CA" if nation == "Canada" else "US"},
        **extra,
    }
    return {"jobPostingInfo": info}


def test_parse_board() -> None:
    host, api, public = parse_board("td.wd3/TD_Bank_Careers")
    assert host == "https://td.wd3.myworkdayjobs.com"
    assert api == "https://td.wd3.myworkdayjobs.com/wday/cxs/td/TD_Bank_Careers"
    assert public == "https://td.wd3.myworkdayjobs.com/TD_Bank_Careers"
    with pytest.raises(AdapterError):
        parse_board("not a board")


def test_registry_knows_workday_and_adzuna() -> None:
    assert isinstance(adapter_for(make_source()), WorkdayAdapter)

    class Adz:
        adapter_type = "adzuna"

    assert isinstance(adapter_for(Adz()), AdzunaAdapter)


def test_scope_keeps_student_and_campus_roles() -> None:
    assert wanted_by_scope({"title": "Summer Analyst Co-op"}, "students")
    assert wanted_by_scope({"title": "Analyst", "bulletFields": ["R_1", "Campus"]}, "students")
    assert not wanted_by_scope({"title": "Branch Manager", "bulletFields": ["R_2"]}, "students")
    assert wanted_by_scope({"title": "Branch Manager"}, "all")


def test_detail_gives_place_deadline_and_link() -> None:
    raw = posting_from_detail(
        detail("Audit Co-op", "OSHAWA", "Canada"), "Acme", "https://x/Careers", "/job/1"
    )
    assert raw is not None
    assert (raw.city, raw.province, raw.country) == ("Oshawa", "", "CA")
    assert raw.deadline is not None and raw.deadline.isoformat() == "2026-11-13"
    assert raw.work_mode == "hybrid"
    assert "Work Term:" in (raw.description or "")
    assert raw.source_url and raw.source_url.endswith("/Audit")


def test_detail_uses_home_city_for_building_names() -> None:
    raw = posting_from_detail(
        detail("Lab Assistant", "Bronfman Building", "Canada"), "McGill", "https://x/C", "/job/2",
        home=("Montréal", "QC"),
    )
    assert raw is not None
    assert (raw.city, raw.province) == ("Montréal", "QC")


def test_detail_skips_places_we_never_keep() -> None:
    assert posting_from_detail(
        detail("Analyst", "Dublin", "Ireland", country={"descriptor": "Ireland"}),
        "Acme", "https://x/C", "/job/3",
    ) is None


@respx.mock
async def test_adapter_lists_pages_and_keeps_canadian_and_us_student_jobs() -> None:
    jobs = [
        {"title": "Audit Co-op", "externalPath": "/job/a", "locationsText": "Toronto, Ontario"},
        {"title": "Summer Intern", "externalPath": "/job/b", "locationsText": "New York, New York"},
        {"title": "Branch Manager", "externalPath": "/job/c", "locationsText": "Calgary, Alberta"},
    ]

    def search(request: object) -> Response:
        offset = json.loads(request.content)["offset"]  # type: ignore[attr-defined]
        page = jobs[offset:offset + 20]
        return Response(200, json={"total": 3, "jobPostings": page})

    respx.post(f"{API}/jobs").mock(side_effect=search)
    respx.get(f"{API}/job/a").mock(return_value=Response(200, json=detail("Audit Co-op", "Toronto, Ontario", "Canada")))
    respx.get(f"{API}/job/b").mock(return_value=Response(200, json=detail("Summer Intern", "New York, New York", "United States of America")))
    respx.get(f"{API}/job/c").mock(return_value=Response(200, json=detail("Branch Manager", "Calgary, Alberta", "Canada")))

    # Small sites keep every Canadian job
    out = await WorkdayAdapter().fetch(make_source())
    assert sorted((p.title, p.country) for p in out) == [
        ("Audit Co-op", "CA"), ("Branch Manager", "CA"), ("Summer Intern", "US"),
    ]

    # Canadian jobs are kept even in the students scope, which only narrows jobs elsewhere
    out = await WorkdayAdapter().fetch(make_source(scope="students"))
    assert sorted(p.title for p in out) == ["Audit Co-op", "Branch Manager", "Summer Intern"]


@respx.mock
async def test_students_scope_skips_us_jobs_that_are_not_for_students() -> None:
    jobs = [
        {"title": "Store Manager", "externalPath": "/job/d", "locationsText": "Austin, Texas"},
        {"title": "Junior Analyst", "externalPath": "/job/e", "locationsText": "Austin, Texas"},
    ]
    respx.post(f"{API}/jobs").mock(return_value=Response(200, json={"total": 2, "jobPostings": jobs}))
    respx.get(f"{API}/job/e").mock(
        return_value=Response(200, json=detail("Junior Analyst", "Austin, Texas", "United States of America"))
    )
    out = await WorkdayAdapter().fetch(make_source(scope="students"))
    assert [p.title for p in out] == ["Junior Analyst"]


@respx.mock
async def test_adapter_raises_when_the_site_is_down() -> None:
    respx.post(f"{API}/jobs").mock(return_value=Response(500))
    with pytest.raises(AdapterError):
        await WorkdayAdapter().fetch(make_source())


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("OSHAWA", "Oshawa"), ("st. john's", "St. John's"), ("6168 NO 3 RD:RICHMOND", "Richmond"),
     ("Toronto", "Toronto"), ("NEW TECUMSETH", "New Tecumseth")],
)
def test_tidy_place(raw: str, expected: str) -> None:
    assert tidy_place(raw) == expected


# Adzuna

ADZUNA_JOB = {
    "id": "4321",
    "title": "<strong>Summer Student</strong> - Parks",
    "description": "Help run city parks programs for the summer.",
    "created": "2026-10-10T12:00:00Z",
    "redirect_url": "https://www.adzuna.ca/land/ad/4321",
    "location": {"display_name": "Ottawa, Ontario", "area": ["Canada", "Ontario", "Ottawa"]},
    "company": {"display_name": "City of Ottawa"},
}


def test_adzuna_result_becomes_a_posting() -> None:
    raw = posting_from_result(ADZUNA_JOB, "ca")
    assert raw is not None
    assert (raw.title, raw.company, raw.city, raw.province, raw.country) == (
        "Summer Student - Parks", "City of Ottawa", "Ottawa", "ON", "CA",
    )
    assert raw.source_ref == "4321"


def test_adzuna_us_keeps_only_student_roles() -> None:
    job = {**ADZUNA_JOB, "title": "Park Manager"}
    assert posting_from_result(job, "us") is None


async def test_adzuna_needs_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "adzuna_app_id", "")
    with pytest.raises(AdapterError, match="ADZUNA"):
        await AdzunaAdapter().fetch(make_source())


@respx.mock
async def test_adzuna_reads_pages_and_never_echoes_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "adzuna_app_id", "id123")
    monkeypatch.setattr(get_settings(), "adzuna_app_key", "secret-key")
    route = respx.get(url__regex=r"https://api\.adzuna\.com/v1/api/jobs/ca/search/1.*").mock(
        return_value=Response(200, json={"results": [ADZUNA_JOB]})
    )

    class Src:
        config = {"country": "ca"}

    out = await AdzunaAdapter().fetch(Src())
    assert [p.company for p in out] == ["City of Ottawa"]
    assert route.called

    route.mock(return_value=Response(401))
    with pytest.raises(AdapterError) as err:
        await AdzunaAdapter().fetch(Src())
    assert "secret-key" not in str(err.value)
