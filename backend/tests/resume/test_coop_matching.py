"""
Co-op matching by program and grad year, read from the resume or set by the student,
with why it fits notes on each match. No AI key, so this is the free skill overlap path.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from tests.resume.conftest import _build_minimal_pdf

RESUME = (
    "Sam Student\n"
    "Skills: Python, SQL, SolidWorks, MATLAB\n"
    "EDUCATION\n"
    "University of Waterloo\n"
    "Bachelor of Applied Science, Mechanical Engineering\n"
    "Expected graduation: April 2028\n"
)


@pytest.fixture(autouse=True)
def no_ai_key(client: AsyncClient) -> None:
    for header in ("X-AI-Provider", "X-AI-Key", "X-AI-Model"):
        client.headers.pop(header, None)


def _posting(title: str, **kwargs: object) -> Posting:
    values: dict[str, object] = dict(
        title=title, company="Acme", city="Toronto", province="ON", work_mode=WorkMode.onsite,
        term="Summer 2027", duration_months=4, deadline=date.today() + timedelta(days=30),
        description="A role.", skills=["Python", "SolidWorks"],
    )
    values.update(kwargs)
    return Posting(**values)


async def _seed(db: AsyncSession) -> None:
    db.add_all([
        _posting(
            "Mechanical Design Co-op", fields_of_study=["mechanical", "engineering"],
            grad_years=[2028], description="Must be returning to school after the term.",
        ),
        _posting("Robotics Intern", grad_years=[2026]),        # wrong grad year
        _posting("Hardware Test Intern", country="US", city="Austin", province="TX"),
        _posting("Account Executive", skills=["Python"]),     # not a mechanical job type
    ])
    await db.flush()


async def _upload(client: AsyncClient, email: str):
    await client.post("/api/auth/register", json={"email": email, "password": "Password1!"})
    return await client.post(
        "/api/resume",
        files={"file": ("resume.pdf", _build_minimal_pdf(RESUME), "application/pdf")},
    )


async def test_program_and_grad_year_come_from_the_resume(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed(db_session)

    res = await _upload(client, "coop_detect@test.com")

    assert res.status_code == 200
    body = res.json()
    assert body["education"] == {
        "program": "mechanical_engineering",
        "program_label": "Mechanical / Mechatronics Engineering",
        "degree": "bachelors",
        "grad_year": 2028,
    }
    # Matching is lenient. The job that suits the program and grad year comes first, the others
    # still show up lower, and only Canada is in by default
    titles = [m["title"] for m in body["matches"]]
    assert titles[0] == "Mechanical Design Co-op"
    assert set(titles) == {"Mechanical Design Co-op", "Robotics Intern", "Account Executive"}
    notes = body["matches"][0]["fit_notes"]
    assert "Co-op role" in notes
    assert "Asks for Mechanical / Mechatronics, which fits your program" in notes
    assert "For students graduating in 2028, like you" in notes
    assert "For students still in school" in notes
    assert "2 of 2 listed skills on your resume" in notes
    assert "4 months long" in notes
    # A job for other grad years stays in, with a fair warning, below the one that fits
    robotics = next(m for m in body["matches"] if m["title"] == "Robotics Intern")
    assert "Asks for 2026 grads. You finish in 2028, so check before you apply" in (
        robotics["fit_notes"]
    )
    assert robotics["score"] < body["matches"][0]["score"]

    stored = (await client.get("/api/resume/matches")).json()
    assert stored["items"][0]["fit_notes"] == notes
    assert stored["education"]["grad_year"] == 2028


async def test_student_choices_override_the_resume(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed(db_session)
    assert (await _upload(client, "coop_override@test.com")).status_code == 200

    res = await client.put(
        "/api/resume/preferences",
        json={"grad_year": 2026, "countries": ["CA", "US"], "term": "Summer 2027"},
    )

    assert res.status_code == 200
    matches = res.json()["matches"]
    titles = [m["title"] for m in matches]
    # The US job is in now, and the jobs for 2026 grads rank above the one for 2028 grads
    assert "Hardware Test Intern" in titles
    assert titles.index("Robotics Intern") < titles.index("Mechanical Design Co-op")
    robotics = next(m for m in matches if m["title"] == "Robotics Intern")
    assert "Summer 2027 term, the one you want" in robotics["fit_notes"]
    us = next(m for m in matches if m["title"] == "Hardware Test Intern")
    assert us["country"] == "US"


async def test_picked_job_types_still_filter(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Job types the student picks on purpose are a real filter, unlike the program guess."""
    await _seed(db_session)
    assert (await _upload(client, "coop_types@test.com")).status_code == 200

    res = await client.put("/api/resume/preferences", json={"categories": ["sales_marketing"]})

    assert [m["title"] for m in res.json()["matches"]] == ["Account Executive"]


async def test_wanted_length_ranks_higher(client: AsyncClient, db_session: AsyncSession) -> None:
    db_session.add_all([
        _posting("Design Co-op A", duration_months=4),
        _posting("Design Co-op B", duration_months=8),
    ])
    await db_session.flush()
    assert (await _upload(client, "coop_length@test.com")).status_code == 200

    res = await client.put("/api/resume/preferences", json={"durations": [8]})

    matches = res.json()["matches"]
    assert matches[0]["title"] == "Design Co-op B"
    assert "8 months long, the length you want" in matches[0]["fit_notes"]
    assert matches[0]["duration_months"] == 8


async def test_invalid_program_is_rejected(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register", json={"email": "coop_bad@test.com", "password": "Password1!"}
    )
    res = await client.put("/api/resume/preferences", json={"program": "astrology"})
    assert res.status_code == 422
