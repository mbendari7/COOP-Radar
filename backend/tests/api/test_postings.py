"""
Tests for GET /api/postings, GET /api/postings/{id}, GET /api/postings/meta/filters.

Each test seeds only the data it needs via the rolled-back db_session fixture,
so tests are fast and independent.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, WorkMode

# --- Helpers ------------------------------------------------------------------

def make_posting(**kwargs) -> Posting:
    """
    Build a Posting with sane defaults — override only the fields under test.
    This keeps test setup short without hiding what's actually being tested.
    """
    defaults = dict(
        title="Test Co-op",
        company="Acme Corp",
        city="Waterloo",
        province="ON",
        work_mode=WorkMode.hybrid,
        term="Summer 2027",
        duration_months=4,
        deadline=date.today() + timedelta(days=30),   # active by default
        posted_at=datetime.now(tz=UTC),
        description="A great co-op role.",
        skills=["Python", "SQL"],
        source_url=None,
    )
    defaults.update(kwargs)
    return Posting(**defaults)


async def add(session: AsyncSession, *postings: Posting) -> None:
    for p in postings:
        session.add(p)
    await session.flush()  # write to DB without committing (rolled back after test)


# --- US1: Browse postings -----------------------------------------------------

async def test_list_returns_200_and_page_shape(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(db_session, make_posting(title="Alpha"), make_posting(title="Beta"))

    response = await client.get("/api/postings")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert body["page"] == 1
    assert body["page_size"] == 25


async def test_total_reflects_active_postings(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="Active 1"),
        make_posting(title="Active 2"),
        # Expired posting — should be hidden by default
        make_posting(title="Expired", deadline=date(2020, 1, 1)),
    )

    body = (await client.get("/api/postings")).json()

    assert body["total"] == 2


async def test_show_expired_reveals_past_deadline_postings(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="Active"),
        make_posting(title="Expired", deadline=date(2020, 1, 1)),
    )

    hidden = (await client.get("/api/postings")).json()
    visible = (await client.get("/api/postings?show_expired=true")).json()

    assert hidden["total"] == 1
    assert visible["total"] == 2


async def test_page_size_limits_items_returned(client: AsyncClient, db_session: AsyncSession) -> None:
    for i in range(15):
        await add(db_session, make_posting(title=f"Job {i}"))

    body = (await client.get("/api/postings?page_size=10")).json()

    assert len(body["items"]) == 10
    assert body["total"] == 15
    assert body["page_size"] == 10


async def test_page_beyond_last_returns_empty_items(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(db_session, make_posting(title="Only One"))

    body = (await client.get("/api/postings?page=999")).json()

    assert body["items"] == []
    assert body["total"] == 1


# --- US2: Search & filter ------------------------------------------------------

async def test_keyword_search_filters_by_title(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="Python Developer"),
        # Override the default skills (which include Python) so only the title differs
        make_posting(title="Java Engineer", skills=["Java"]),
    )

    body = (await client.get("/api/postings?q=python")).json()

    titles = [item["title"] for item in body["items"]]
    assert "Python Developer" in titles
    assert "Java Engineer" not in titles


async def test_skills_filter_uses_and_logic(client: AsyncClient, db_session: AsyncSession) -> None:
    """Posting must have ALL selected skills — AND logic per FR-004."""
    await add(
        db_session,
        make_posting(title="Both", skills=["React", "TypeScript", "SQL"]),
        make_posting(title="Only React", skills=["React"]),
        make_posting(title="Only TypeScript", skills=["TypeScript"]),
    )

    body = (await client.get("/api/postings?skills=React&skills=TypeScript")).json()

    titles = [item["title"] for item in body["items"]]
    assert titles == ["Both"]


async def test_city_filter_keeps_remote_postings(client: AsyncClient, db_session: AsyncSession) -> None:
    """Remote postings always appear in city-filtered results (FR-004a)."""
    await add(
        db_session,
        make_posting(title="Waterloo Job", city="Waterloo", work_mode=WorkMode.onsite),
        make_posting(title="Remote Job", city="Remote", work_mode=WorkMode.remote),
        make_posting(title="Toronto Job", city="Toronto", work_mode=WorkMode.onsite),
    )

    body = (await client.get("/api/postings?city=Waterloo")).json()

    titles = {item["title"] for item in body["items"]}
    assert "Waterloo Job" in titles
    assert "Remote Job" in titles
    assert "Toronto Job" not in titles


async def test_duration_filter_uses_or_logic(client: AsyncClient, db_session: AsyncSession) -> None:
    """Multiple duration values are OR'd — show any matching duration."""
    await add(
        db_session,
        make_posting(title="4 Month", duration_months=4),
        make_posting(title="8 Month", duration_months=8),
        make_posting(title="12 Month", duration_months=12),
    )

    body = (await client.get("/api/postings?duration=4&duration=8")).json()

    titles = {item["title"] for item in body["items"]}
    assert "4 Month" in titles
    assert "8 Month" in titles
    assert "12 Month" not in titles


# --- US3: Sort -----------------------------------------------------------------

async def test_sort_by_deadline_ascending(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="Later", deadline=date.today() + timedelta(days=60)),
        make_posting(title="Sooner", deadline=date.today() + timedelta(days=10)),
    )

    body = (await client.get("/api/postings?sort=deadline&order=asc")).json()

    assert body["items"][0]["title"] == "Sooner"
    assert body["items"][1]["title"] == "Later"


async def test_invalid_sort_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/postings?sort=invalid_column")
    assert response.status_code == 422


async def test_invalid_page_size_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/postings?page_size=99")
    assert response.status_code == 422


# --- US4: Posting detail -------------------------------------------------------

async def test_get_posting_returns_full_detail(client: AsyncClient, db_session: AsyncSession) -> None:
    posting = make_posting(
        title="Detail Test",
        description="Full description here.",
        skills=["Go", "Docker"],
        source_url="https://example.com/job/1",
    )
    await add(db_session, posting)

    response = await client.get(f"/api/postings/{posting.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Detail Test"
    assert body["description"] == "Full description here."
    assert "Go" in body["skills"]
    assert body["source_url"] == "https://example.com/job/1"


async def test_get_unknown_posting_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/postings/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "POSTING_NOT_FOUND"


# --- is_saved field (Feature 002) ---------------------------------------------

async def test_unauthenticated_list_has_no_is_saved(client: AsyncClient, db_session: AsyncSession) -> None:
    """Unauthenticated GET /api/postings: is_saved should be null/absent."""
    await add(db_session, make_posting(title="Anon Test"))
    body = (await client.get("/api/postings")).json()
    for item in body["items"]:
        assert item.get("is_saved") is None


# --- Filter meta ---------------------------------------------------------------

async def test_filter_meta_returns_sorted_distinct_values(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(city="Waterloo", province="ON", term="Summer 2027", skills=["Python", "SQL"]),
        make_posting(city="Toronto", province="ON", term="Winter 2027", skills=["React", "SQL"]),
    )

    body = (await client.get("/api/postings/meta/filters")).json()

    assert body["cities"] == ["Toronto", "Waterloo"]
    assert body["provinces"] == ["ON"]
    assert "SQL" in body["skills"]
    assert body["skills"] == sorted(body["skills"])


# --- Regression tests ------------------------------------------------------------

async def test_skills_filter_treats_input_as_data(client: AsyncClient, db_session: AsyncSession) -> None:
    """Quotes/brackets in a skill value are bound parameters, never SQL (was f-string SQL)."""
    await add(db_session, make_posting(title="Safe"))

    response = await client.get(
        "/api/postings", params={"skills": "x']::text[]); DROP TABLE postings; --"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert (await client.get("/api/postings")).json()["total"] == 1  # table still there


async def test_semantic_search_orders_by_similarity(
    client: AsyncClient, db_session: AsyncSession, mock_embedding
) -> None:
    from app.models.posting_embedding import PostingEmbedding

    near, far = make_posting(title="Near"), make_posting(title="Far")
    await add(db_session, near, far)
    db_session.add_all([
        PostingEmbedding(posting_id=near.id, embedding=[0.1] * 1536, model="test"),
        PostingEmbedding(posting_id=far.id, embedding=[0.1] * 768 + [-0.1] * 768, model="test"),
    ])
    await db_session.flush()

    body = (await client.get("/api/postings?q=anything&search_mode=semantic")).json()

    assert [item["title"] for item in body["items"]] == ["Near", "Far"]


async def test_semantic_search_falls_back_to_keyword(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        "app.ingest.embed.generate_embedding", AsyncMock(side_effect=RuntimeError("no key"))
    )
    await add(
        db_session,
        make_posting(title="Rust Developer", skills=["Rust"]),
        make_posting(title="Other", skills=["Go"]),
    )

    body = (await client.get("/api/postings?q=rust&search_mode=semantic")).json()

    assert [item["title"] for item in body["items"]] == ["Rust Developer"]


async def test_similar_postings_returns_nearest(client: AsyncClient, db_session: AsyncSession) -> None:
    from app.models.posting_embedding import PostingEmbedding

    target = make_posting(title="Target")
    twin = make_posting(title="Twin")
    closed = make_posting(title="Closed", closed_at=datetime.now(tz=UTC))
    await add(db_session, target, twin, closed)
    for p in (target, twin, closed):
        db_session.add(PostingEmbedding(posting_id=p.id, embedding=[0.2] * 1536, model="test"))
    await db_session.flush()

    body = (await client.get(f"/api/postings/{target.id}/similar")).json()

    assert [item["title"] for item in body["items"]] == ["Twin"]  # never itself, never closed
    assert body["items"][0]["similarity"] > 0.99


async def test_error_responses_have_flat_shape(client: AsyncClient) -> None:
    body = (await client.get(f"/api/postings/{uuid4()}")).json()
    assert body == {"detail": "Posting not found", "code": "POSTING_NOT_FOUND"}


# --- Job types, employers, recency --------------------------------------------

async def test_category_filter_matches_job_type_from_title(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="Software Developer Co-op"),
        make_posting(title="Data Analyst Intern"),
        make_posting(title="UX Designer Co-op"),
    )

    one = (await client.get("/api/postings?category=design")).json()
    two = (await client.get("/api/postings?category=software&category=data")).json()

    assert [p["title"] for p in one["items"]] == ["UX Designer Co-op"]
    assert {p["title"] for p in two["items"]} == {"Software Developer Co-op", "Data Analyst Intern"}
    assert (await client.get("/api/postings?category=astronaut")).status_code == 422


async def test_company_filter(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="A", company="Shopify"),
        make_posting(title="B", company="Wealthsimple"),
        make_posting(title="C", company="Lyft"),
    )

    body = (await client.get("/api/postings?company=Shopify&company=Lyft&sort=title&order=asc")).json()

    assert [p["title"] for p in body["items"]] == ["A", "C"]


async def test_posted_within_filter(client: AsyncClient, db_session: AsyncSession) -> None:
    now = datetime.now(tz=UTC)
    await add(
        db_session,
        make_posting(title="Today", posted_at=now),
        make_posting(title="Last week", posted_at=now - timedelta(days=5)),
        make_posting(title="Last month", posted_at=now - timedelta(days=20)),
    )

    day = (await client.get("/api/postings?posted_within=1")).json()
    week = (await client.get("/api/postings?posted_within=7")).json()

    assert [p["title"] for p in day["items"]] == ["Today"]
    assert {p["title"] for p in week["items"]} == {"Today", "Last week"}
    assert (await client.get("/api/postings?posted_within=2")).status_code == 422


async def test_filter_meta_lists_job_types_and_employers(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="Software Developer Co-op", company="Shopify"),
        make_posting(title="Backend Intern", company="Lyft"),
        make_posting(title="Closed role", company="Gone Inc", deadline=date.today() - timedelta(days=1)),
    )

    body = (await client.get("/api/postings/meta/filters")).json()

    assert body["companies"] == ["Lyft", "Shopify"]  # open postings only
    assert body["open_jobs"] == 2
    counts = {c["key"]: c["count"] for c in body["categories"]}
    assert counts["software"] == 2
    assert counts["design"] == 0
    assert body["categories"][0]["label"] == "Software & web"


# --- Country, program of study, graduation year --------------------------------

async def test_country_filter_and_role(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="Data Co-op", city="Toronto", province="ON"),
        make_posting(title="Software Engineer Intern", city="Austin", province="TX", country="US"),
    )

    ca = (await client.get("/api/postings?country=CA")).json()
    both = (await client.get("/api/postings?country=CA&country=US")).json()

    assert [p["title"] for p in ca["items"]] == ["Data Co-op"]
    assert both["total"] == 2
    roles = {p["title"]: (p["role"], p["country"]) for p in both["items"]}
    assert roles == {"Data Co-op": ("coop", "CA"), "Software Engineer Intern": ("internship", "US")}
    assert (await client.get("/api/postings?country=FR")).status_code == 422


async def test_program_filter_uses_named_fields_or_job_types(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        # names Mechanical Engineering in the description
        make_posting(title="Operations Co-op", fields_of_study=["mechanical", "engineering"]),
        # a hardware title, nothing named
        make_posting(title="Embedded Firmware Intern"),
        make_posting(title="Account Executive"),
    )

    body = (await client.get("/api/postings?program=mechanical_engineering")).json()

    assert {p["title"] for p in body["items"]} == {"Operations Co-op", "Embedded Firmware Intern"}
    assert (await client.get("/api/postings?program=astrology")).status_code == 422


async def test_grad_year_filter_keeps_jobs_that_do_not_say(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="For 2027 grads", grad_years=[2027]),
        make_posting(title="For 2028 grads", grad_years=[2028, 2029]),
        make_posting(title="Not stated"),
    )

    body = (await client.get("/api/postings?grad_year=2028")).json()

    assert {p["title"] for p in body["items"]} == {"For 2028 grads", "Not stated"}


async def test_filter_meta_counts_countries_and_work_modes(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="A", work_mode=WorkMode.remote),
        make_posting(title="B Intern", country="US", province="CA", city="San Francisco"),
    )

    body = (await client.get("/api/postings/meta/filters")).json()

    assert {c["code"]: c["count"] for c in body["countries"]} == {"CA": 1, "US": 1}
    assert {m["key"]: m["count"] for m in body["work_modes"]} == {
        "onsite": 0, "hybrid": 1, "remote": 1,
    }
    assert {"key": "computer_science", "label": "Computer Science"} in body["programs"]
