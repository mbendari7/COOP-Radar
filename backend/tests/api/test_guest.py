"""
Tests for guest accounts (POST /api/auth/guest), keeping them (POST /api/me/claim),
and the students-only postings filter.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.posting import Posting, WorkMode


async def test_guest_gets_an_empty_temporary_account(client: AsyncClient) -> None:
    res = await client.post("/api/auth/guest")
    assert res.status_code == 201
    assert res.json()["is_demo"] is True

    me = await client.get("/api/me")
    assert me.status_code == 200
    # Unlike the demo, a guest starts with nothing saved and no resume
    assert (await client.get("/api/saved")).json()["total"] == 0
    assert (await client.get("/api/resume")).status_code == 404


async def test_guest_disabled_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "demo_enabled", False)
    res = await client.post("/api/auth/guest")
    assert res.status_code == 404
    assert res.json()["code"] == "DEMO_DISABLED"


async def test_claim_turns_guest_into_normal_account(client: AsyncClient) -> None:
    await client.post("/api/auth/guest")
    res = await client.post(
        "/api/me/claim", json={"email": "Kept@Test.com", "password": "Password1!"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == "kept@test.com"
    assert res.json()["is_demo"] is False

    # The new credentials work
    await client.post("/api/auth/logout")
    login = await client.post(
        "/api/auth/login", json={"email": "kept@test.com", "password": "Password1!"}
    )
    assert login.status_code == 200


async def test_claim_with_taken_email_returns_409(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register", json={"email": "taken@test.com", "password": "Password1!"}
    )
    await client.post("/api/auth/logout")
    await client.post("/api/auth/guest")
    res = await client.post(
        "/api/me/claim", json={"email": "taken@test.com", "password": "Password1!"}
    )
    assert res.status_code == 409
    assert res.json()["code"] == "EMAIL_TAKEN"


async def test_claim_normal_account_returns_400(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register", json={"email": "normal@test.com", "password": "Password1!"}
    )
    res = await client.post(
        "/api/me/claim", json={"email": "other@test.com", "password": "Password1!"}
    )
    assert res.status_code == 400
    assert res.json()["code"] == "ALREADY_CLAIMED"


async def test_claim_requires_login(client: AsyncClient) -> None:
    res = await client.post(
        "/api/me/claim", json={"email": "x@test.com", "password": "Password1!"}
    )
    assert res.status_code == 401


# ── Students-only filter ──────────────────────────────────────────────────────

def _posting(title: str) -> Posting:
    return Posting(
        title=title,
        company="Acme",
        city="Toronto",
        province="ON",
        work_mode=WorkMode.onsite,
        term="Open",
        duration_months=4,
        deadline=date.today() + timedelta(days=30),
        description="",
        skills=[],
    )


async def test_students_only_keeps_intern_coop_and_new_grad_roles(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add_all([
        _posting("Software Engineering Intern"),
        _posting("Data Co-op (Winter 2027)"),
        _posting("Coop Student, QA"),
        _posting("New Grad Backend Engineer"),
        _posting("Senior Staff Engineer"),
        _posting("Internal Tools Lead"),  # "Internal" must not match "intern"
    ])
    await db_session.flush()

    res = await client.get("/api/postings", params={"students_only": "true", "page_size": 50})
    assert res.status_code == 200
    titles = {item["title"] for item in res.json()["items"]}
    assert titles == {
        "Software Engineering Intern",
        "Data Co-op (Winter 2027)",
        "Coop Student, QA",
        "New Grad Backend Engineer",
    }

    everything = await client.get("/api/postings", params={"page_size": 50})
    assert everything.json()["total"] == 6
    assert "source_id" in everything.json()["items"][0]
