"""
Tests for bring-your-own-key AI (app/ai.py, /api/ai/check) across Claude, OpenAI, and Gemini.
Every provider SDK is mocked — no network calls, no real keys.
"""

import json
from collections.abc import AsyncIterator, Callable
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import ai
from app.ai import AICredentials, credentials_from_headers, recommended_model
from app.config import get_settings
from app.models.posting import Posting, WorkMode
from app.services.resume import find_candidates, skills_in_text

OPENAI = AICredentials("openai", "sk-openai", "gpt-test", "user")
GEMINI = AICredentials("gemini", "g-key", "gemini-flash-latest", "user")


# ── Which key is used ─────────────────────────────────────────────────────────

def test_visitor_key_is_used_with_default_model() -> None:
    creds = credentials_from_headers("gemini", " g-key ", None, "chat")
    assert (creds.provider, creds.api_key, creds.model, creds.source) == (
        "gemini", "g-key", "gemini-flash-latest", "user",
    )


def test_key_never_appears_in_repr() -> None:
    assert "sk-secret" not in repr(AICredentials("openai", "sk-secret", "m", "user"))


@pytest.mark.parametrize(
    "provider,key,model,code",
    [
        (None, None, None, "AI_KEY_REQUIRED"),
        ("mistral", "abc12345", None, "AI_PROVIDER_INVALID"),
        ("openai", "sk-abc", None, "AI_MODEL_REQUIRED"),
        ("anthropic", "has spaces in it", None, "AI_KEY_INVALID"),
    ],
)
def test_missing_or_bad_key_is_400(provider: str | None, key: str | None, model: str | None, code: str) -> None:
    with pytest.raises(HTTPException) as exc:
        credentials_from_headers(provider, key, model, "rank")
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == code


def test_site_owner_key_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "sk-owner")
    creds = credentials_from_headers(None, None, None, "chat")
    assert creds.source == "server" and creds.model == get_settings().agent_model


NO_KEY = {"X-AI-Provider": "", "X-AI-Key": "", "X-AI-Model": ""}


def _docx(text_value: str) -> bytes:
    import io

    from docx import Document

    doc = Document()
    doc.add_paragraph(text_value)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def _seed_two_postings(db_session: AsyncSession) -> None:
    def posting(title: str, skills: list[str]) -> Posting:
        return Posting(
            title=title, company="Acme", city="Toronto", province="ON", work_mode=WorkMode.hybrid,
            term="Summer 2027", duration_months=4, deadline=date.today() + timedelta(days=30),
            description="d", skills=skills,
        )

    db_session.add_all([posting("Backend Co-op", ["Python", "SQL", "Go"]),
                        posting("iOS Intern", ["Swift"])])
    await db_session.flush()


async def test_upload_without_any_key_gives_free_skill_matches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """No AI key anywhere: the upload still works, ranked and explained by skill overlap."""
    await _seed_two_postings(db_session)
    await client.post("/api/auth/register", json={"email": "nokey@test.com", "password": "Password1!"})
    res = await client.post(
        "/api/resume",
        files={"file": ("r.docx", _docx("Skills: Python, SQL"), "application/octet-stream")},
        headers=NO_KEY,
    )
    assert res.status_code == 200
    top = res.json()["matches"][0]
    assert top["title"] == "Backend Co-op"
    assert top["score"] == 58  # 2 of 3 skills (67% of 65) + 15 for a co-op title
    assert top["reason"] == "You have Python, SQL; it also asks for Go."


async def test_rematch_needs_a_key_then_ranks_with_ai(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    await _seed_two_postings(db_session)
    await client.post("/api/auth/register", json={"email": "rematch@test.com", "password": "Password1!"})
    files = {"file": ("r.docx", _docx("Skills: Python, SQL"), "application/octet-stream")}
    first = await client.post("/api/resume", files=files, headers=NO_KEY)
    backend_id = first.json()["matches"][0]["posting_id"]

    no_key = await client.post("/api/resume/rematch", headers=NO_KEY)
    assert no_key.status_code == 400
    assert no_key.json()["code"] == "AI_KEY_REQUIRED"

    mock_claude_create(json.dumps([
        {"posting_id": backend_id, "score": 91, "reason": "Python and SQL APIs fit well."}
    ]))
    res = await client.post("/api/resume/rematch")  # client sends the test AI key headers
    assert res.status_code == 200
    assert [(m["score"], m["reason"]) for m in res.json()["matches"]] == [
        (91, "Python and SQL APIs fit well.")
    ]
    stored = (await client.get("/api/resume/matches")).json()["items"]
    assert [m["score"] for m in stored] == [91]


# ── Provider calls (mocked SDKs) ──────────────────────────────────────────────

async def test_complete_with_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="hi from gpt"))])
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=reply)
    monkeypatch.setattr("openai.AsyncOpenAI", MagicMock(return_value=client))

    assert await ai.complete(OPENAI, "sys", "user") == "hi from gpt"
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-test"
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}


async def test_complete_with_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=SimpleNamespace(text="hi from gemini"))
    monkeypatch.setattr("google.genai.Client", MagicMock(return_value=client))

    assert await ai.complete(GEMINI, "sys", "user") == "hi from gemini"
    assert client.aio.models.generate_content.call_args.kwargs["model"] == "gemini-flash-latest"


async def test_stream_with_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    async def chunks() -> AsyncIterator[SimpleNamespace]:
        for piece in ("Resume: ", "Python."):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))])

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=chunks())
    monkeypatch.setattr("openai.AsyncOpenAI", MagicMock(return_value=client))

    assert [c async for c in ai.stream(OPENAI, "sys", "user")] == ["Resume: ", "Python."]


async def test_stream_with_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    async def chunks() -> AsyncIterator[SimpleNamespace]:
        for piece in ("Posting: ", "needs SQL."):
            yield SimpleNamespace(text=piece)

    client = MagicMock()
    client.aio.models.generate_content_stream = AsyncMock(return_value=chunks())
    monkeypatch.setattr("google.genai.Client", MagicMock(return_value=client))

    assert [c async for c in ai.stream(GEMINI, "sys", "user")] == ["Posting: ", "needs SQL."]


@pytest.mark.parametrize(
    "status,code", [(401, "AI_KEY_INVALID"), (404, "AI_MODEL_INVALID"), (429, "AI_PROVIDER_RATE_LIMITED"), (500, "AI_PROVIDER_ERROR")]
)
async def test_provider_errors_become_clear_codes(
    monkeypatch: pytest.MonkeyPatch, status: int, code: str
) -> None:
    error = Exception("provider said no")
    error.status_code = status  # type: ignore[attr-defined]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=error)
    monkeypatch.setattr("openai.AsyncOpenAI", MagicMock(return_value=client))

    with pytest.raises(ai.AIProviderError) as exc:
        await ai.complete(OPENAI, "sys", "user")
    assert exc.value.code == code
    assert "sk-openai" not in exc.value.message


async def test_gemini_bad_key_is_reported_as_invalid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Google returns 400 + reason API_KEY_INVALID for a bad key (seen against the live API)."""
    error = Exception("API key not valid. Please pass a valid API key.")
    error.code = 400  # type: ignore[attr-defined]
    error.details = {"error": {"code": 400, "status": "INVALID_ARGUMENT", "details": [  # type: ignore[attr-defined]
        {"reason": "API_KEY_INVALID", "domain": "googleapis.com"}]}}
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(side_effect=error)
    monkeypatch.setattr("google.genai.Client", MagicMock(return_value=client))

    with pytest.raises(ai.AIProviderError) as exc:
        await ai.complete(GEMINI, "sys", "user")
    assert exc.value.code == "AI_KEY_INVALID"


async def test_qa_streams_through_the_visitors_openai_key(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mock_claude_create: Callable[[str], AsyncMock],
) -> None:
    """End to end: a ChatGPT key answers the resume Q&A."""
    posting = Posting(
        title="Data Co-op", company="Acme", city="Toronto", province="ON", work_mode=WorkMode.remote,
        term="Summer 2027", duration_months=4, deadline=date.today() + timedelta(days=20),
        description="Needs SQL", skills=["SQL"],
    )
    db_session.add(posting)
    await db_session.flush()
    await client.post("/api/auth/demo")  # demo account already has resume + matches
    matches = (await client.get("/api/resume/matches")).json()["items"]
    assert any(m["posting_id"] == str(posting.id) for m in matches)

    async def chunks() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Resume: SQL listed."))])

    oa = MagicMock()
    oa.chat.completions.create = AsyncMock(return_value=chunks())
    monkeypatch.setattr("openai.AsyncOpenAI", MagicMock(return_value=oa))

    res = await client.post(
        f"/api/resume/matches/{posting.id}/ask",
        json={"question": "Do I have SQL?"},
        headers={"X-AI-Provider": "openai", "X-AI-Key": "sk-visitor", "X-AI-Model": "gpt-test"},
    )
    assert res.status_code == 200
    deltas = [json.loads(line[6:]).get("delta", "") for line in res.text.splitlines()
              if line.startswith("data: ") and "[DONE]" not in line]
    assert "".join(deltas) == "Resume: SQL listed."


# ── "Check key" endpoint ──────────────────────────────────────────────────────

async def test_check_key_lists_models_and_recommends_one(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.ai.list_models",
        AsyncMock(return_value=[
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
            {"id": "gemini-flash-latest", "label": "Gemini Flash Latest"},
        ]),
    )
    res = await client.post("/api/ai/check", json={"provider": "gemini", "api_key": "g-key-12345"})

    assert res.status_code == 200
    body = res.json()
    assert body["recommended"] == "gemini-flash-latest"
    assert [m["id"] for m in body["models"]] == ["gemini-2.5-pro", "gemini-flash-latest"]


async def test_check_key_rejected(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.ai.list_models",
        AsyncMock(side_effect=ai.AIProviderError(400, "AI_KEY_INVALID", "OpenAI rejected the API key.")),
    )
    res = await client.post("/api/ai/check", json={"provider": "openai", "api_key": "sk-wrong-123"})
    assert res.status_code == 400
    assert res.json()["code"] == "AI_KEY_INVALID"


async def test_check_key_is_rate_limited(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ai.list_models", AsyncMock(return_value=[]))
    body = {"provider": "anthropic", "api_key": "sk-ant-12345"}
    for _ in range(30):
        await client.post("/api/ai/check", json=body)
    res = await client.post("/api/ai/check", json=body)
    assert res.status_code == 429


def test_recommended_model_prefers_known_good_defaults() -> None:
    assert recommended_model("anthropic", ["claude-haiku-5-5", "claude-opus-5-5"]) == "claude-opus-5-5"
    assert recommended_model("openai", ["gpt-5-mini", "gpt-5", "o3"]) == "gpt-5"
    assert recommended_model("openai", ["o3"]) == "o3"
    assert recommended_model("gemini", []) is None


# ── Shortlist without any AI key ──────────────────────────────────────────────

def test_skills_in_text_matches_whole_skills_only() -> None:
    text = "Built APIs in Python and C++; some CSS. Familiar with Node.js."
    assert skills_in_text(["Python", "C", "C++", "CSS", "Node.js", "Go"], text) == [
        "Python", "C++", "CSS", "Node.js",
    ]


async def test_skill_shortlist_ranks_by_overlap(db_session: AsyncSession) -> None:
    def posting(title: str, skills: list[str]) -> Posting:
        return Posting(
            title=title, company="Acme", city="Toronto", province="ON", work_mode=WorkMode.hybrid,
            term="Summer 2027", duration_months=4, deadline=date.today() + timedelta(days=30),
            description="d", skills=skills,
        )

    db_session.add_all([
        posting("Full match", ["Python", "SQL", "Docker"]),
        posting("Half match", ["Python", "Rust", "Go", "SQL"]),
        posting("One-skill posting", ["Python"]),
        posting("No match", ["Haskell"]),
    ])
    await db_session.flush()

    rows = await find_candidates(db_session, "Skills: Python, SQL, Docker")
    sim = {r["title"]: round(float(r["similarity"]), 2) for r in rows}

    # Skills are worth 65 of the 100 points
    assert sim["Full match"] == pytest.approx(0.65, abs=0.01)
    assert sim["Half match"] == pytest.approx(0.65 / 2, abs=0.01)
    # Listing a single skill can't earn full marks from one match (counts as 1 of 3)
    assert sim["One-skill posting"] == pytest.approx(0.65 / 3, abs=0.01)
    assert sim["No match"] == 0.0


async def test_skill_shortlist_prefers_student_roles_over_senior_ones(
    db_session: AsyncSession,
) -> None:
    def posting(title: str) -> Posting:
        return Posting(
            title=title, company="Acme", city="Toronto", province="ON", work_mode=WorkMode.hybrid,
            term="Summer 2027", duration_months=4, deadline=date.today() + timedelta(days=30),
            description="d", skills=["Python", "SQL", "React", "Go"],
        )

    db_session.add_all([
        posting("Senior Software Engineer"),
        posting("Software Engineer"),
        posting("Software Engineering Intern"),
        posting("Staff Engineer II"),
    ])
    await db_session.flush()

    rows = await find_candidates(db_session, "Skills: Python, SQL")
    sim = {r["title"]: round(float(r["similarity"]), 2) for r in rows}

    half = 0.65 / 2  # 2 of 4 skills
    assert sim["Software Engineering Intern"] == pytest.approx(half + 0.15, abs=0.01)  # student role
    assert sim["Software Engineer"] == pytest.approx(half, abs=0.01)
    assert sim["Senior Software Engineer"] == pytest.approx(half / 2, abs=0.01)  # senior counts half
    assert sim["Staff Engineer II"] == pytest.approx(half / 2, abs=0.01)
