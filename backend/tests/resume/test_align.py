"""Make your resume fit one job (app/services/align.py and GET /api/resume/align/{id}). No AI."""

from datetime import date, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode
from app.services.align import align, job_keywords
from tests.resume.conftest import _build_minimal_pdf

DESCRIPTION = (
    "Financial Analyst Co-op, Summer 2027.\n"
    "You will build financial models and reconcile accounts in Excel.\n"
    "Prepare variance analysis for the finance team. Financial models feed monthly reporting.\n"
    "Requirements: enrolled in a Bachelor of Commerce or Finance program, graduating in 2028.\n"
    "Bilingual in English and French is an asset. Variance analysis experience is a plus."
)

RESUME = (
    "Jordan Lee\njordan@example.com\n"
    "EDUCATION\nUniversity of Ottawa\nBachelor of Commerce, Finance\n"
    "Expected graduation: April 2028\n"
    "Skills: Excel, SQL\n"
    "Built a budget tracker for a student club.\n"
)


def _posting(**kwargs: object) -> Posting:
    values: dict[str, object] = dict(
        id=uuid4(), title="Financial Analyst Co-op", company="Maple Bank", city="Ottawa",
        province="ON", work_mode=WorkMode.hybrid, term="Summer 2027", duration_months=4,
        deadline=date.today() + timedelta(days=30), description=DESCRIPTION,
        skills=["Excel", "Financial Modelling", "Financial Analysis"],
        fields_of_study=["finance", "business"], grad_years=[2028],
    )
    values.update(kwargs)
    return Posting(**values)


def test_job_keywords_finds_repeated_words_and_skips_filler() -> None:
    words = job_keywords("Financial Analyst Co-op", DESCRIPTION, "Maple Bank")
    assert "financial models" in words
    assert "variance analysis" in words
    assert not {"the", "you", "co-op", "summer"} & {w.lower() for w in words}


def test_align_checks_and_tips() -> None:
    result = align(_posting(), RESUME)

    assert result.matched_skills == ["Excel"]
    assert result.missing_skills == ["Financial Modelling", "Financial Analysis"]
    checks = {c.text: c.ok for c in result.checks}
    assert checks["Your program is one it asks for"] is True
    assert checks["Your graduation year 2028 is one it asks for"] is True
    assert checks["Your resume does not say you are free for Summer 2027"] is False
    assert checks["It mentions French or bilingual"] is False
    assert checks["Few of your bullets show results with numbers"] is False
    tips = " ".join(result.tips)
    assert "Available for a 4 month Summer 2027 co-op term" in tips
    assert "French" in tips
    assert "Financial Modelling" in tips
    assert "variance analysis" in result.keywords_missing


def test_align_gives_credit_for_what_is_there() -> None:
    resume = RESUME + (
        "Available for a Summer 2027 co-op term. Languages: French (fluent)\n"
        "Cut month end close time by 30% and reviewed 120 accounts for 15 clients.\n"
        "Built financial models and variance analysis for 3 projects.\n"
    )
    result = align(_posting(), resume)

    checks = {c.text: c.ok for c in result.checks}
    assert checks["Your resume says you are free for this term"] is True
    assert checks["Your resume mentions French"] is True
    assert checks["Your bullets show results with numbers"] is True
    assert "financial models" in result.keywords_found


async def test_align_endpoint(client: AsyncClient, db_session: AsyncSession) -> None:
    posting = _posting()
    db_session.add(posting)
    await db_session.flush()
    for header in ("X-AI-Provider", "X-AI-Key", "X-AI-Model"):
        client.headers.pop(header, None)

    # No resume yet
    await client.post(
        "/api/auth/register", json={"email": "align@test.com", "password": "Password1!"}
    )
    res = await client.get(f"/api/resume/align/{posting.id}")
    assert res.status_code == 404
    assert res.json()["code"] == "RESUME_NOT_FOUND"

    up = await client.post(
        "/api/resume", files={"file": ("r.pdf", _build_minimal_pdf(RESUME), "application/pdf")}
    )
    assert up.status_code == 200

    res = await client.get(f"/api/resume/align/{posting.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["company"] == "Maple Bank"
    assert body["matched_skills"] == ["Excel"]
    assert body["tips"]

    missing = await client.get(f"/api/resume/align/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "POSTING_NOT_FOUND"


async def test_align_needs_sign_in(client: AsyncClient) -> None:
    res = await client.get(f"/api/resume/align/{uuid4()}")
    assert res.status_code == 401
