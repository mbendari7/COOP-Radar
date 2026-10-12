"""Tests for admin source management endpoints."""


import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _register_login(client: AsyncClient, email: str, password: str = "TestPass123!") -> str:
    await client.post("/api/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.cookies.get("session", "")


async def _make_admin(db: AsyncSession, email: str) -> None:
    await db.execute(text("UPDATE users SET is_admin = TRUE WHERE email = :email"), {"email": email})
    await db.flush()


async def _create_source(db: AsyncSession, name: str = "Test Source") -> str:
    result = await db.execute(
        text(
            "INSERT INTO ingest_sources (id, name, adapter_type, config) "
            "VALUES (gen_random_uuid(), :name, 'json_api', '{}') RETURNING id"
        ),
        {"name": name},
    )
    await db.flush()
    return str(result.scalar_one())


@pytest.mark.asyncio
async def test_non_admin_gets_403(client: AsyncClient, db_session: AsyncSession):
    """Non-admin user cannot access GET /api/admin/sources."""
    session = await _register_login(client, "student_admin_test@example.com")
    resp = await client.get("/api/admin/sources", cookies={"session": session})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_lists_sources(client: AsyncClient, db_session: AsyncSession):
    """Admin user receives list of sources."""
    await _register_login(client, "admin_list@example.com")
    await _make_admin(db_session, "admin_list@example.com")
    await _create_source(db_session, "Admin List Source")
    session = (
        await client.post(
            "/api/auth/login",
            json={"email": "admin_list@example.com", "password": "TestPass123!"},
        )
    ).cookies.get("session", "")

    resp = await client.get("/api/admin/sources", cookies={"session": session})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert any(s["name"] == "Admin List Source" for s in body)


@pytest.mark.asyncio
async def test_trigger_run_returns_202(client: AsyncClient, db_session: AsyncSession):
    """POST /api/admin/sources/{id}/run returns 202 ACCEPTED."""
    await _register_login(client, "admin_trigger@example.com")
    await _make_admin(db_session, "admin_trigger@example.com")
    source_id = await _create_source(db_session, "Trigger Source")
    session = (
        await client.post(
            "/api/auth/login",
            json={"email": "admin_trigger@example.com", "password": "TestPass123!"},
        )
    ).cookies.get("session", "")

    resp = await client.post(
        f"/api/admin/sources/{source_id}/run", cookies={"session": session}
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "run_id" in body


@pytest.mark.asyncio
async def test_trigger_already_running_409(client: AsyncClient, db_session: AsyncSession):
    """POST /api/admin/sources/{id}/run returns 409 when a run is already running."""
    await _register_login(client, "admin_running@example.com")
    await _make_admin(db_session, "admin_running@example.com")
    source_id = await _create_source(db_session, "Running Source")
    session = (
        await client.post(
            "/api/auth/login",
            json={"email": "admin_running@example.com", "password": "TestPass123!"},
        )
    ).cookies.get("session", "")

    # First run
    resp1 = await client.post(
        f"/api/admin/sources/{source_id}/run", cookies={"session": session}
    )
    assert resp1.status_code == 202

    # Second run while first is still "running"
    resp2 = await client.post(
        f"/api/admin/sources/{source_id}/run", cookies={"session": session}
    )
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "ALREADY_RUNNING"


@pytest.mark.asyncio
async def test_patch_source_re_enables(client: AsyncClient, db_session: AsyncSession):
    """PATCH auto_paused=false resets consecutive_failures to 0."""
    await _register_login(client, "admin_patch@example.com")
    await _make_admin(db_session, "admin_patch@example.com")

    # Create a paused source
    result = await db_session.execute(
        text(
            "INSERT INTO ingest_sources (id, name, adapter_type, config, auto_paused, consecutive_failures) "
            "VALUES (gen_random_uuid(), 'Paused Source', 'json_api', '{}', TRUE, 3) RETURNING id"
        )
    )
    await db_session.flush()
    source_id = str(result.scalar_one())

    session = (
        await client.post(
            "/api/auth/login",
            json={"email": "admin_patch@example.com", "password": "TestPass123!"},
        )
    ).cookies.get("session", "")

    resp = await client.patch(
        f"/api/admin/sources/{source_id}",
        json={"auto_paused": False},
        cookies={"session": session},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["auto_paused"] is False


@pytest.mark.asyncio
async def test_trigger_run_enqueues_job_with_run_id(
    client: AsyncClient, db_session: AsyncSession, fake_queue
):
    await _register_login(client, "admin_queue@example.com")
    await _make_admin(db_session, "admin_queue@example.com")
    source_id = await _create_source(db_session, "Queue Source")
    await client.post(
        "/api/auth/login", json={"email": "admin_queue@example.com", "password": "TestPass123!"}
    )

    resp = await client.post(f"/api/admin/sources/{source_id}/run")

    assert resp.status_code == 202
    fake_queue.enqueue.assert_called_once_with(
        "run_source", source_id, resp.json()["run_id"]
    )
