"""Term season and length on GET /api/postings: the season filter, sorting and the menu counts."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api.test_postings import add, make_posting


async def test_season_is_worked_out_from_the_term(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="Summer Job", term="Summer 2027"),
        make_posting(title="Fall Job", term="Fall"),
        make_posting(title="Open Job", term="Open"),
    )

    items = {i["title"]: i for i in (await client.get("/api/postings")).json()["items"]}

    assert items["Summer Job"]["season"] == "summer"
    assert items["Summer Job"]["term_start"] == "2027-05-01"
    assert items["Fall Job"]["season"] == "fall"
    assert items["Fall Job"]["term_start"] is None  # no year so no start day
    assert items["Open Job"]["season"] is None


async def test_season_filter_uses_or_logic(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="W", term="Winter 2027"),
        make_posting(title="S", term="Summer 2027"),
        make_posting(title="F", term="Fall 2027"),
    )

    body = (await client.get("/api/postings?season=winter&season=fall")).json()

    assert sorted(i["title"] for i in body["items"]) == ["F", "W"]


async def test_bad_season_returns_422(client: AsyncClient) -> None:
    assert (await client.get("/api/postings?season=monsoon")).status_code == 422


async def test_sort_by_length_puts_unknown_last(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="Eight", duration_months=8),
        make_posting(title="Unknown", duration_months=None),
        make_posting(title="Four", duration_months=4),
        make_posting(title="Twelve", duration_months=12),
    )

    asc = (await client.get("/api/postings?sort=duration_months&order=asc")).json()["items"]
    desc = (await client.get("/api/postings?sort=duration_months&order=desc")).json()["items"]

    assert [i["title"] for i in asc] == ["Four", "Eight", "Twelve", "Unknown"]
    assert [i["title"] for i in desc] == ["Twelve", "Eight", "Four", "Unknown"]
    assert asc[-1]["duration_months"] is None


async def test_sort_by_term_start(client: AsyncClient, db_session: AsyncSession) -> None:
    await add(
        db_session,
        make_posting(title="Fall 27", term="Fall 2027"),
        make_posting(title="Winter 27", term="Winter 2027"),
        make_posting(title="No term", term="Open"),
        make_posting(title="Summer 27", term="Summer 2027"),
    )

    items = (await client.get("/api/postings?sort=term_start&order=asc")).json()["items"]

    assert [i["title"] for i in items] == ["Winter 27", "Summer 27", "Fall 27", "No term"]


async def test_filter_meta_counts_seasons_and_lengths(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="A", term="Summer 2027", duration_months=4),
        make_posting(title="B", term="Summer", duration_months=8),
        make_posting(title="C", term="Open", duration_months=None),
    )

    body = (await client.get("/api/postings/meta/filters")).json()

    assert {s["key"]: s["count"] for s in body["seasons"]} == {
        "winter": 0, "spring": 0, "summer": 2, "fall": 0,
    }
    assert {d["months"]: d["count"] for d in body["durations"]} == {4: 1, 8: 1, 12: 0, 16: 0}


async def test_new_job_types_cover_other_fields(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add(
        db_session,
        make_posting(title="Registered Nurse Student"),
        make_posting(title="Policy Analyst Co-op"),
        make_posting(title="Electrician Apprentice"),
        make_posting(title="Civil Engineering Co-op"),
    )

    async def titles(category: str) -> list[str]:
        body = (await client.get(f"/api/postings?category={category}")).json()
        return [i["title"] for i in body["items"]]

    assert await titles("health") == ["Registered Nurse Student"]
    assert await titles("public") == ["Policy Analyst Co-op"]
    assert await titles("trades") == ["Electrician Apprentice"]
    assert "Civil Engineering Co-op" in await titles("hardware")
