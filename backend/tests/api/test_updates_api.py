"""
Keeping up with new jobs: real lengths under the usual length filters, new since your last visit
(added_since), the Newly added sort and the RSS feed at GET /api/postings/feed.rss.
"""

from datetime import UTC, date, datetime, timedelta
from xml.etree import ElementTree

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api.test_postings import add, make_posting


async def test_real_lengths_show_under_the_usual_length(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Regression: a 6 month job used to be saved as 8 months. Now it keeps 6 and still shows
    # when someone picks "about 8 months"
    await add(
        db_session,
        make_posting(title="Six", duration_months=6),
        make_posting(title="Three", duration_months=3),
        make_posting(title="Twelve", duration_months=12),
    )

    body = (await client.get("/api/postings?duration=8")).json()
    assert [(i["title"], i["duration_months"]) for i in body["items"]] == [("Six", 6)]

    meta = (await client.get("/api/postings/meta/filters")).json()
    counts = {d["months"]: d["count"] for d in meta["durations"]}
    assert counts[4] >= 1 and counts[8] >= 1 and counts[12] >= 1


async def test_added_since_and_newly_added_sort(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    await add(
        db_session,
        make_posting(title="Old", first_seen_at=now - timedelta(days=5), posted_at=now),
        make_posting(title="Fresh", first_seen_at=now - timedelta(hours=1),
                     posted_at=now - timedelta(days=20)),
    )
    since = (now - timedelta(days=1)).isoformat()

    body = (await client.get("/api/postings", params={"added_since": since})).json()
    assert [i["title"] for i in body["items"]] == ["Fresh"]
    assert body["items"][0]["first_seen_at"] is not None

    newest = (await client.get("/api/postings?sort=first_seen_at&order=desc")).json()["items"]
    assert [i["title"] for i in newest][:2] == ["Fresh", "Old"]


async def test_feed_lists_newest_jobs_for_a_search(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    await add(
        db_session,
        make_posting(title="Data Co-op", company="Maple & Co", first_seen_at=now - timedelta(days=2)),
        make_posting(title="Design Co-op", first_seen_at=now - timedelta(hours=2), term="Fall 2027"),
        make_posting(title="Old Co-op", deadline=date.today() - timedelta(days=2)),  # expired
    )

    response = await client.get("/api/postings/feed.rss?q=co-op")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    channel = ElementTree.fromstring(response.text).find("channel")
    assert channel is not None
    titles = [item.findtext("title") for item in channel.findall("item")]
    assert titles == ["Design Co-op at Acme Corp", "Data Co-op at Maple & Co"]
    first = channel.findall("item")[0]
    assert "/postings/" in (first.findtext("link") or "")
    assert "Fall 2027 term" in (first.findtext("description") or "")


async def test_term_starting_soonest_puts_terms_that_are_over_last(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Regression: Summer 2025 came first under "Term starting soonest" in October 2026
    this_year = date.today().year
    await add(
        db_session,
        make_posting(title="Over", term=f"Summer {this_year - 1}"),
        make_posting(title="Later", term=f"Summer {this_year + 1}"),
        make_posting(title="Sooner", term=f"Winter {this_year + 1}"),
        make_posting(title="No term", term="Open"),
    )

    items = (await client.get("/api/postings?sort=term_start&order=asc")).json()["items"]

    assert [i["title"] for i in items] == ["Sooner", "Later", "No term", "Over"]


async def test_feed_rejects_bad_filters(client: AsyncClient) -> None:
    assert (await client.get("/api/postings/feed.rss?season=monsoon")).status_code == 422
