"""
Tests for job preferences. What a student is looking for limits and orders their matches.
Covers the upload `preferences` field, PUT /api/resume/preferences and the skill split on
each match. No AI key is used so matching takes the free skill overlap path.
"""

import json
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode


@pytest.fixture(autouse=True)
def no_ai_key(client: AsyncClient) -> None:
    """A visitor with no AI key. Matching uses the free skill overlap ranking."""
    for header in ("X-AI-Provider", "X-AI-Key", "X-AI-Model"):
        client.headers.pop(header, None)


def _posting(title: str, city: str, province: str, mode: WorkMode, skills: list[str]) -> Posting:
    return Posting(
        title=title,
        company="Acme",
        city=city,
        province=province,
        work_mode=mode,
        term="Summer 2027",
        duration_months=4,
        deadline=date.today() + timedelta(days=30),
        description=f"Uses {', '.join(skills)}.",
        skills=skills,
    )


async def _seed(db_session: AsyncSession) -> None:
    db_session.add_all([
        _posting("Software Developer Co-op", "Toronto", "ON", WorkMode.hybrid, ["Python", "Django"]),
        _posting("Data Analyst Intern", "Vancouver", "BC", WorkMode.onsite, ["Python", "SQL"]),
        _posting("Senior Software Engineer", "Toronto", "ON", WorkMode.onsite, ["Python"]),
        _posting("Marketing Coordinator", "Montreal", "QC", WorkMode.remote, ["Excel"]),
    ])
    await db_session.flush()


async def _register(client: AsyncClient, email: str) -> None:
    await client.post("/api/auth/register", json={"email": email, "password": "Password1!"})


async def _upload(client: AsyncClient, pdf: bytes, preferences: dict | None = None):
    data = {"preferences": json.dumps(preferences)} if preferences is not None else None
    return await client.post(
        "/api/resume", files={"file": ("resume.pdf", pdf, "application/pdf")}, data=data
    )


def _titles(matches: list[dict]) -> set[str]:
    return {m["title"] for m in matches}


async def test_upload_with_job_type_only_matches_that_type(
    client: AsyncClient, db_session: AsyncSession, sample_pdf_bytes: bytes
) -> None:
    await _seed(db_session)
    await _register(client, "prefs_type@test.com")

    res = await _upload(client, sample_pdf_bytes, {"categories": ["data"]})

    assert res.status_code == 200
    assert _titles(res.json()["matches"]) == {"Data Analyst Intern"}

    stored = (await client.get("/api/resume/matches")).json()
    assert stored["preferences"]["categories"] == ["data"]
    match = stored["items"][0]
    assert match["matched_skills"] == ["Python"]  # the resume lists Python but not SQL
    assert match["missing_skills"] == ["SQL"]
    assert match["work_mode"] == "onsite"


async def test_update_preferences_rematches_by_location_and_level(
    client: AsyncClient, db_session: AsyncSession, sample_pdf_bytes: bytes
) -> None:
    await _seed(db_session)
    await _register(client, "prefs_loc@test.com")
    assert (await _upload(client, sample_pdf_bytes)).status_code == 200

    res = await client.put("/api/resume/preferences", json={"province": "ON", "level": "entry"})

    assert res.status_code == 200
    # Ontario jobs without senior titles plus remote jobs, which you can do from Ontario
    assert _titles(res.json()["matches"]) == {"Software Developer Co-op", "Marketing Coordinator"}
    stored = (await client.get("/api/resume/matches")).json()
    assert _titles(stored["items"]) == {"Software Developer Co-op", "Marketing Coordinator"}

    res = await client.put("/api/resume/preferences", json={"level": "students"})
    assert _titles(res.json()["matches"]) == {"Software Developer Co-op", "Data Analyst Intern"}


async def test_work_mode_preference(
    client: AsyncClient, db_session: AsyncSession, sample_pdf_bytes: bytes
) -> None:
    await _seed(db_session)
    await _register(client, "prefs_mode@test.com")
    await _upload(client, sample_pdf_bytes)

    res = await client.put("/api/resume/preferences", json={"work_modes": ["remote"], "level": "all"})

    assert _titles(res.json()["matches"]) == {"Marketing Coordinator"}


async def test_keywords_rank_matching_jobs_higher(
    client: AsyncClient, db_session: AsyncSession, sample_pdf_bytes: bytes
) -> None:
    await _seed(db_session)
    await _register(client, "prefs_kw@test.com")
    await _upload(client, sample_pdf_bytes, {"level": "all"})

    def score(matches: list[dict], title: str) -> int:
        return next(m["score"] for m in matches if m["title"] == title)

    before = (await client.get("/api/resume/matches")).json()["items"]
    res = await client.put("/api/resume/preferences", json={"level": "all", "keywords": "marketing"})
    after = res.json()["matches"]

    assert score(before, "Marketing Coordinator") == 0  # none of its skills are on the resume
    assert score(after, "Marketing Coordinator") == 20


async def test_new_resume_version_keeps_preferences(
    client: AsyncClient, db_session: AsyncSession, sample_pdf_bytes: bytes
) -> None:
    await _seed(db_session)
    await _register(client, "prefs_keep@test.com")
    await _upload(client, sample_pdf_bytes, {"categories": ["data"]})

    res = await _upload(client, sample_pdf_bytes)

    assert _titles(res.json()["matches"]) == {"Data Analyst Intern"}
    stored = (await client.get("/api/resume/matches")).json()
    assert stored["preferences"]["categories"] == ["data"]


async def test_invalid_preferences_are_rejected(
    client: AsyncClient, db_session: AsyncSession, sample_pdf_bytes: bytes
) -> None:
    await _register(client, "prefs_bad@test.com")

    res = await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")},
        data={"preferences": '{"categories": ["astronaut"]}'},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "INVALID_PREFERENCES"

    await _upload(client, sample_pdf_bytes)
    res = await client.put("/api/resume/preferences", json={"level": "wizard"})
    assert res.status_code == 422


async def test_update_preferences_needs_a_resume(client: AsyncClient) -> None:
    await _register(client, "prefs_none@test.com")

    res = await client.put("/api/resume/preferences", json={"categories": ["software"]})

    assert res.status_code == 404
    assert res.json()["code"] == "RESUME_NOT_FOUND"
