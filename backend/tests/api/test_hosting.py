"""
Tests for public-hosting features: demo accounts, the daily AI limit, /api/config,
serving the built website, and DATABASE_URL normalization.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.main import create_app, mount_frontend
from app.models.posting import Posting, WorkMode
from app.models.user import User
from app.services.demo import DEMO_TTL, cleanup_expired_demo_users, skill_overlap_match


def _posting(title: str, skills: list[str]) -> Posting:
    return Posting(
        title=title, company="Acme", city="Toronto", province="ON", work_mode=WorkMode.hybrid,
        term="Summer 2027", duration_months=4, deadline=date.today() + timedelta(days=30),
        description="d", skills=skills,
    )


@pytest.fixture
async def postings(db_session: AsyncSession) -> list[Posting]:
    rows = [_posting(f"Role {i}", ["Python", "SQL"] if i % 2 else ["Go", "Rust"]) for i in range(8)]
    db_session.add_all(rows)
    await db_session.flush()
    return rows


# ── Demo accounts ─────────────────────────────────────────────────────────────

async def test_demo_login_creates_prefilled_account(client: AsyncClient, postings: list[Posting]) -> None:
    res = await client.post("/api/auth/demo")

    assert res.status_code == 201
    assert res.json()["is_demo"] is True
    assert (await client.get("/api/me")).json()["is_demo"] is True  # cookie session works

    saved = (await client.get("/api/saved")).json()
    assert saved["total"] == 6
    assert saved["status_counts"]["interview"] == 1

    matches = (await client.get("/api/resume/matches")).json()
    assert matches["resume"]["filename"] == "alex-rivera-resume.pdf"
    assert matches["items"], "demo should have matches without any AI call"
    assert all("Demo match" in m["reason"] for m in matches["items"])
    assert matches["items"][0]["score"] == 100  # Python+SQL postings fully covered


async def test_each_demo_login_gets_its_own_account(client: AsyncClient, postings: list[Posting]) -> None:
    first = (await client.post("/api/auth/demo")).json()["id"]
    second = (await client.post("/api/auth/demo")).json()["id"]
    assert first != second


async def test_demo_rate_limited_per_ip(client: AsyncClient) -> None:
    for _ in range(10):
        await client.post("/api/auth/demo", headers={"X-Forwarded-For": "203.0.113.7"})
    res = await client.post("/api/auth/demo", headers={"X-Forwarded-For": "203.0.113.7"})
    assert res.status_code == 429
    assert res.json()["code"] == "RATE_LIMITED"


async def test_demo_disabled_returns_404(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "demo_enabled", False)
    res = await client.post("/api/auth/demo")
    assert res.status_code == 404
    assert res.json()["code"] == "DEMO_DISABLED"


async def test_cleanup_removes_only_expired_demo_users(db_session: AsyncSession) -> None:
    old = datetime.now(UTC) - DEMO_TTL - timedelta(hours=1)
    db_session.add_all([
        User(email="old@demo.coopradar", hashed_password="x", is_demo=True, created_at=old),
        User(email="new@demo.coopradar", hashed_password="x", is_demo=True),
        User(email="real@example.com", hashed_password="x", created_at=old),
    ])
    await db_session.flush()

    assert await cleanup_expired_demo_users(db_session) == 1
    emails = set((await db_session.execute(select(User.email))).scalars())
    assert {"new@demo.coopradar", "real@example.com"} <= emails
    assert "old@demo.coopradar" not in emails


def test_skill_overlap_match_scores_and_explains() -> None:
    score, reason = skill_overlap_match(["Python", "Go", "SQL", "Rust"], ["python", "SQL"])
    assert score == 50
    assert "Python, SQL" in reason and "missing Go, Rust" in reason


# ── Daily AI limit ────────────────────────────────────────────────────────────

def _docx_bytes(text: str) -> bytes:
    import io

    from docx import Document

    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def test_ai_daily_limit_applies_to_the_site_owners_key(
    client: AsyncClient,
    mock_embedding: AsyncMock,
    mock_claude_create: Callable[[str], AsyncMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Visitors without their own key use the owner's key, limited per day; own keys are not."""
    monkeypatch.setattr(get_settings(), "ai_daily_limit", 1)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "sk-owner-key")
    mock_claude_create("[]")
    await client.post("/api/auth/register", json={"email": "quota@test.com", "password": "Password1!"})
    files = {"file": ("r.docx", _docx_bytes("Skills: Python, SQL"), "application/octet-stream")}
    no_key = {"X-AI-Provider": "", "X-AI-Key": "", "X-AI-Model": ""}

    assert (await client.post("/api/resume", files=files, headers=no_key)).status_code == 200
    second = await client.post("/api/resume", files=files, headers=no_key)
    assert second.status_code == 429
    assert second.json()["code"] == "AI_LIMIT_REACHED"

    # The visitor's own key is never limited
    assert (await client.post("/api/resume", files=files)).status_code == 200


# ── /api/config ───────────────────────────────────────────────────────────────

async def test_public_config_reports_flags_without_secrets(client: AsyncClient) -> None:
    body = (await client.get("/api/config")).json()
    assert set(body) == {"demo_enabled", "server_ai_enabled", "semantic_search_enabled", "ai_daily_limit"}
    assert body["demo_enabled"] is True


# ── Serving the built website ─────────────────────────────────────────────────

async def test_api_serves_spa_with_history_fallback(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "favicon.svg").write_text("<svg/>")

    app = create_app()
    mount_frontend(app, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.get("/")).text == "<html>app</html>"
        assert (await ac.get("/saved")).text == "<html>app</html>"        # client-side route
        assert (await ac.get("/assets/app.js")).text == "console.log(1)"
        assert (await ac.get("/favicon.svg")).text == "<svg/>"
        assert (await ac.get("/api/health")).json() == {"status": "ok"}   # API still wins
        missing = await ac.get("/api/does-not-exist")
        assert missing.status_code == 404 and missing.json()["code"] == "HTTP_404"
        assert (await ac.get("/../../etc/passwd")).text == "<html>app</html>"


# ── DATABASE_URL normalization ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
    ],
)
def test_database_url_normalized_for_hosting_providers(raw: str, expected: str) -> None:
    assert Settings(database_url=raw).database_url == expected
