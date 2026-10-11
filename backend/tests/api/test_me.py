"""
Tests for /api/me endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def me_client(client: AsyncClient) -> AsyncClient:
    """Client with a registered, logged-in user."""

    await client.post(
        "/api/auth/register",
        json={"email": "me_user@example.com", "password": "password1234"},
    )
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_get_me_returns_user(me_client: AsyncClient):
    """GET /api/me returns the current user's profile."""
    res = await me_client.get("/api/me")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me_user@example.com"
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data


async def test_get_me_unauthenticated_returns_401(client: AsyncClient):
    """GET /api/me without a session returns 401."""

    res = await client.get("/api/me")
    assert res.status_code == 401


async def test_change_password_returns_204(me_client: AsyncClient):
    """Changing password with correct current password returns 204."""
    res = await me_client.patch(
        "/api/me/password",
        json={"current_password": "password1234", "new_password": "newpassword5678"},
    )
    assert res.status_code == 204


async def test_change_password_wrong_current_returns_401(me_client: AsyncClient):
    """Wrong current password returns 401 WRONG_PASSWORD."""
    res = await me_client.patch(
        "/api/me/password",
        json={"current_password": "wrongpassword", "new_password": "newpassword5678"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "WRONG_PASSWORD"


async def test_change_password_short_new_returns_422(me_client: AsyncClient):
    """New password shorter than 10 chars returns 422."""
    res = await me_client.patch(
        "/api/me/password",
        json={"current_password": "password1234", "new_password": "short"},
    )
    assert res.status_code == 422


async def test_delete_account_returns_204(me_client: AsyncClient):
    """Deleting account with correct password returns 204."""
    res = await me_client.request("DELETE", "/api/me", json={"password": "password1234"})
    assert res.status_code == 204


async def test_delete_account_wrong_password_returns_401(me_client: AsyncClient):
    """Wrong password on account delete returns 401."""
    res = await me_client.request("DELETE", "/api/me", json={"password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["code"] == "WRONG_PASSWORD"


async def test_deleted_account_cannot_login(me_client: AsyncClient):
    """After deletion, login with old credentials returns 401."""
    await me_client.request("DELETE", "/api/me", json={"password": "password1234"})
    res = await me_client.post(
        "/api/auth/login",
        json={"email": "me_user@example.com", "password": "password1234"},
    )
    assert res.status_code == 401
