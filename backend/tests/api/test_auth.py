"""
Tests for authentication endpoints.

These tests use the in-memory MockRedis from conftest, so no real Redis is needed.
"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_client(client: AsyncClient) -> AsyncClient:
    """The shared client already uses the in-memory Redis from conftest."""
    return client


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_register_returns_201_and_user(auth_client: AsyncClient):
    """Successful registration returns 201 with user data."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "password1234"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "alice@example.com"
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_sets_httponly_cookie(auth_client: AsyncClient):
    """Registration response must set an HttpOnly session cookie."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "password1234"},
    )
    assert res.status_code == 201
    cookie = res.headers.get("set-cookie", "")
    assert "session=" in cookie
    assert "HttpOnly" in cookie or "httponly" in cookie.lower()


async def test_register_duplicate_email_returns_409(auth_client: AsyncClient):
    """Registering with an already-registered email returns 409 EMAIL_TAKEN."""
    payload = {"email": "dup@example.com", "password": "password1234"}
    await auth_client.post("/api/auth/register", json=payload)
    res = await auth_client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    assert res.json()["code"] == "EMAIL_TAKEN"


async def test_register_short_password_returns_422(auth_client: AsyncClient):
    """Password shorter than 10 characters is rejected with 422."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert res.status_code == 422


async def test_register_email_normalised_to_lowercase(auth_client: AsyncClient):
    """Email is normalised to lowercase before storage."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "User@Example.COM", "password": "password1234"},
    )
    assert res.status_code == 201
    assert res.json()["email"] == "user@example.com"


async def test_login_valid_credentials_returns_200(auth_client: AsyncClient):
    """Login with correct credentials returns 200 and a cookie."""
    await auth_client.post(
        "/api/auth/register",
        json={"email": "carol@example.com", "password": "password1234"},
    )
    res = await auth_client.post(
        "/api/auth/login",
        json={"email": "carol@example.com", "password": "password1234"},
    )
    assert res.status_code == 200
    assert "session=" in res.headers.get("set-cookie", "")


async def test_login_wrong_password_returns_401(auth_client: AsyncClient):
    """Wrong password returns 401 INVALID_CREDENTIALS."""
    await auth_client.post(
        "/api/auth/register",
        json={"email": "dave@example.com", "password": "password1234"},
    )
    res = await auth_client.post(
        "/api/auth/login",
        json={"email": "dave@example.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_email_same_error_as_wrong_password(auth_client: AsyncClient):
    """Unknown email returns the same 401 INVALID_CREDENTIALS as wrong password (FR-014)."""
    res = await auth_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password1234"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_email_normalised(auth_client: AsyncClient):
    """Login works with mixed-case email because it's normalised before lookup."""
    await auth_client.post(
        "/api/auth/register",
        json={"email": "eve@example.com", "password": "password1234"},
    )
    res = await auth_client.post(
        "/api/auth/login",
        json={"email": "EVE@EXAMPLE.COM", "password": "password1234"},
    )
    assert res.status_code == 200


async def test_protected_endpoint_without_cookie_returns_401(auth_client: AsyncClient):
    """Accessing /api/saved without a session cookie returns 401."""
    res = await auth_client.get("/api/saved")
    assert res.status_code == 401
    assert res.json()["code"] == "NOT_AUTHENTICATED"


async def test_logout_returns_204_and_clears_cookie(auth_client: AsyncClient):
    """Logout returns 204 and clears the session cookie."""
    await auth_client.post(
        "/api/auth/register",
        json={"email": "frank@example.com", "password": "password1234"},
    )
    res = await auth_client.post("/api/auth/logout")
    assert res.status_code == 204
    # Cookie should be cleared (max-age=0)
    cookie = res.headers.get("set-cookie", "")
    assert "Max-Age=0" in cookie or "max-age=0" in cookie.lower()


async def test_login_rate_limited_after_five_failures(auth_client: AsyncClient):
    """After 5 failed login attempts, the 6th returns 429 RATE_LIMITED."""
    # Register so the email is valid — wrong password triggers the counter
    await auth_client.post(
        "/api/auth/register",
        json={"email": "ratelimit@example.com", "password": "password1234"},
    )
    for _ in range(5):
        await auth_client.post(
            "/api/auth/login",
            json={"email": "ratelimit@example.com", "password": "wrongpassword"},
        )
    res = await auth_client.post(
        "/api/auth/login",
        json={"email": "ratelimit@example.com", "password": "wrongpassword"},
    )
    assert res.status_code == 429
    assert res.json()["code"] == "RATE_LIMITED"
