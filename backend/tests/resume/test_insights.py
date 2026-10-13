"""
Tests for resume insights (GET and POST /api/resume/insights) and the tailor and cover letter modes.
AI calls are faked so there are no live API calls.
"""

import json
from collections.abc import Callable
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode


def _posting(title: str, skills: list[str]) -> Posting:
    return Posting(
        title=title,
        company="Acme",
        city="Toronto",
        province="ON",
        work_mode=WorkMode.hybrid,
        term="Summer 2027",
        duration_months=4,
        deadline=date.today() + timedelta(days=30),
        description=f"Uses {', '.join(skills)}.",
        skills=skills,
    )


async def _upload(
    client: AsyncClient,
    db_session: AsyncSession,
    email: str,
    resume_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
) -> Posting:
    """Add jobs, sign up and upload a resume with Python, Django, PostgreSQL and Docker."""
    target = _posting("Python Developer Co-op", ["Python", "Kubernetes"])
    db_session.add_all([
        target,
        _posting("Platform Intern", ["Kubernetes", "Go", "Python"]),
        _posting("Infra Co-op", ["Kubernetes", "Terraform"]),
    ])
    await db_session.flush()
    mock_claude_create(json.dumps([
        {"posting_id": str(target.id), "score": 80, "reason": "Python match."}
    ]))
    await client.post("/api/auth/register", json={"email": email, "password": "Password1!"})
    upload = await client.post(
        "/api/resume", files={"file": ("resume.pdf", resume_bytes, "application/pdf")}
    )
    assert upload.status_code == 200
    return target


async def test_free_insights_show_found_and_missing_skills(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    await _upload(client, db_session, "ins_free@test.com", sample_pdf_bytes, mock_claude_create)

    res = await client.get("/api/resume/insights")
    assert res.status_code == 200
    body = res.json()
    assert "Python" in body["skills_found"]
    missing = {m["skill"]: m["postings"] for m in body["in_demand_missing"]}
    assert missing["Kubernetes"] == 3  # all three open jobs ask for it
    assert "Python" not in missing
    assert body["ai"] is None


async def test_ai_insights_are_generated_and_cached(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    await _upload(client, db_session, "ins_ai@test.com", sample_pdf_bytes, mock_claude_create)
    review = {
        "summary": "A backend-leaning student.",
        "strengths": ["Python APIs with FastAPI"],
        "improvements": ["Add metrics"],
        "tailoring_tips": ["Mirror the posting's wording"],
        "roles_to_search": ["Backend Developer Co-op"],
        "keywords_to_add": ["REST"],
    }
    create = mock_claude_create(f"```json\n{json.dumps(review)}\n```")

    res = await client.post("/api/resume/insights")
    assert res.status_code == 200
    assert res.json()["ai"]["strengths"] == ["Python APIs with FastAPI"]
    # What employers want, like the missing popular skills, gets sent to the model
    assert "Kubernetes" in create.call_args.kwargs["messages"][0]["content"]

    cached = (await client.get("/api/resume/insights")).json()
    assert cached["ai"]["roles_to_search"] == ["Backend Developer Co-op"]


async def test_ai_insights_unreadable_reply_returns_502(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    await _upload(client, db_session, "ins_bad@test.com", sample_pdf_bytes, mock_claude_create)
    mock_claude_create("Sorry, here are some thoughts without JSON.")

    res = await client.post("/api/resume/insights")
    assert res.status_code == 502
    assert res.json()["code"] == "AI_BAD_RESPONSE"


async def test_insights_without_resume_returns_404(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register", json={"email": "ins_none@test.com", "password": "Password1!"}
    )
    res = await client.get("/api/resume/insights")
    assert res.status_code == 404
    assert res.json()["code"] == "RESUME_NOT_FOUND"


async def test_insights_require_login(client: AsyncClient) -> None:
    assert (await client.get("/api/resume/insights")).status_code == 401


async def test_tailor_mode_needs_no_question_and_uses_tailor_prompt(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    target = await _upload(
        client, db_session, "tailor@test.com", sample_pdf_bytes, mock_claude_create
    )
    stream = mock_claude_stream("## Fit\nGood fit.")

    res = await client.post(f"/api/resume/matches/{target.id}/ask", json={"mode": "tailor"})
    assert res.status_code == 200
    assert "data: [DONE]" in res.text
    kwargs = stream.call_args.kwargs
    assert "tailor their resume" in kwargs["system"]
    assert "How should I tailor my resume" in kwargs["messages"][0]["content"]


async def test_cover_letter_mode_uses_cover_letter_prompt(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    target = await _upload(
        client, db_session, "cover@test.com", sample_pdf_bytes, mock_claude_create
    )
    stream = mock_claude_stream("Dear hiring team,")

    res = await client.post(
        f"/api/resume/matches/{target.id}/ask", json={"mode": "cover_letter"}
    )
    assert res.status_code == 200
    assert "cover-letter" in stream.call_args.kwargs["system"]


async def test_question_mode_still_requires_a_question(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_bytes: bytes,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    target = await _upload(
        client, db_session, "q_empty@test.com", sample_pdf_bytes, mock_claude_create
    )
    res = await client.post(f"/api/resume/matches/{target.id}/ask", json={"question": "  "})
    assert res.status_code == 422
