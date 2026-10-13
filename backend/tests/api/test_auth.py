"""
Tests for sign up, sign in and sign out.

They use the in memory store from conftest so no real Redis is needed.
"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_client(client: AsyncClient) -> AsyncClient:
    """The shared client already uses the in memory store from conftest."""
    return client


# Tests

async def test_register_returns_201_and_user(auth_client: AsyncClient):
    """A good sign up answers 201 with the user."""
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
    """Sign up has to set an HttpOnly session cookie."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "password1234"},
    )
    assert res.status_code == 201
    cookie = res.headers.get("set-cookie", "")
    assert "session=" in cookie
    assert "HttpOnly" in cookie or "httponly" in cookie.lower()


async def test_register_duplicate_email_returns_409(auth_client: AsyncClient):
    """Signing up with an email that is taken answers 409 EMAIL_TAKEN."""
    payload = {"email": "dup@example.com", "password": "password1234"}
    await auth_client.post("/api/auth/register", json=payload)
    res = await auth_client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    assert res.json()["code"] == "EMAIL_TAKEN"


async def test_register_short_password_returns_422(auth_client: AsyncClient):
    """A password under 10 characters gets a 422."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert res.status_code == 422


async def test_register_email_normalised_to_lowercase(auth_client: AsyncClient):
    """The email is saved in lowercase."""
    res = await auth_client.post(
        "/api/auth/register",
        json={"email": "User@Example.COM", "password": "password1234"},
    )
    assert res.status_code == 201
    assert res.json()["email"] == "user@example.com"


async def test_login_valid_credentials_returns_200(auth_client: AsyncClient):
    """Signing in with the right details answers 200 and sets a cookie."""
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
    """A wrong password answers 401 INVALID_CREDENTIALS."""
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
    """An unknown email gets the very same 401 INVALID_CREDENTIALS as a wrong password."""
    res = await auth_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password1234"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_email_normalised(auth_client: AsyncClient):
    """Signing in works with a mixed case email since we lowercase it first."""
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
    """Opening /api/saved with no session cookie answers 401."""
    res = await auth_client.get("/api/saved")
    assert res.status_code == 401
    assert res.json()["code"] == "NOT_AUTHENTICATED"


async def test_logout_returns_204_and_clears_cookie(auth_client: AsyncClient):
    """Sign out answers 204 and clears the session cookie."""
    await auth_client.post(
        "/api/auth/register",
        json={"email": "frank@example.com", "password": "password1234"},
    )
    res = await auth_client.post("/api/auth/logout")
    assert res.status_code == 204
    # The cookie should be cleared with max-age=0
    cookie = res.headers.get("set-cookie", "")
    assert "Max-Age=0" in cookie or "max-age=0" in cookie.lower()


async def test_login_rate_limited_after_five_failures(auth_client: AsyncClient):
    """After 5 failed sign ins the 6th answers 429 RATE_LIMITED."""
    # Sign up first so the email is real and a wrong password bumps the counter
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
