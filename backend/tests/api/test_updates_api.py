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


async def test_include_unstated_keeps_jobs_that_do_not_say_their_term(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Regression: picking Winter showed about 30 jobs, since most employers never write the
    # term. With include_unstated the jobs that say Winter come first, then the ones that don't
    this_year = date.today().year
    now = datetime.now(UTC)
    await add(
        db_session,
        make_posting(title="Winter", term=f"Winter {this_year + 1}", posted_at=now - timedelta(days=3)),
        make_posting(title="Unstated", term="Open", duration_months=None, posted_at=now),
        make_posting(title="Summer", term=f"Summer {this_year + 1}", posted_at=now),
    )

    exact = (await client.get("/api/postings?season=winter")).json()
    assert [i["title"] for i in exact["items"]] == ["Winter"]

    loose = (await client.get("/api/postings?season=winter&include_unstated=true")).json()
    assert [i["title"] for i in loose["items"]] == ["Winter", "Unstated"]

    lengths = (await client.get("/api/postings?duration=4&include_unstated=true")).json()
    assert {i["title"] for i in lengths["items"]} == {"Winter", "Unstated", "Summer"}
    assert lengths["items"][-1]["title"] == "Unstated"


async def test_a_hundred_jobs_per_page(client: AsyncClient) -> None:
    assert (await client.get("/api/postings?page_size=100")).status_code == 200
    assert (await client.get("/api/postings?page_size=99")).status_code == 422


async def test_old_closed_jobs_are_deleted_unless_saved(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.models.ingest_source import IngestSource
    from app.models.posting import Posting
    from app.models.saved_posting import SavedPosting
    from app.models.user import User
    from app.services.postings import delete_old_closed

    source = IngestSource(name="Old jobs", adapter_type="json_api", config={"url": "https://x"})
    db_session.add(source)
    await db_session.flush()
    long_ago = datetime.now(UTC) - timedelta(days=60)
    gone = make_posting(title="Gone", source_id=source.id, closed_at=long_ago)
    kept_saved = make_posting(title="Saved", source_id=source.id, closed_at=long_ago)
    recent = make_posting(title="Recent", source_id=source.id,
                          closed_at=datetime.now(UTC) - timedelta(days=2))
    manual = make_posting(title="Manual", closed_at=long_ago)  # added by hand, kept
    await add(db_session, gone, kept_saved, recent, manual)
    user = User(email="saver@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    db_session.add(SavedPosting(user_id=user.id, posting_id=kept_saved.id))
    await db_session.flush()

    assert await delete_old_closed(db_session) == 1

    titles = set((await db_session.execute(select(Posting.title))).scalars())
    assert {"Saved", "Recent", "Manual"} <= titles and "Gone" not in titles


async def test_a_season_means_a_coming_term(client: AsyncClient, db_session: AsyncSession) -> None:
    # Regression: Winter showed "Winter 2026" jobs in October 2026, a term that already began
    this_year = date.today().year
    await add(
        db_session,
        make_posting(title="Past winter", term=f"Winter {this_year - 1}"),
        make_posting(title="Next winter", term=f"Winter {this_year + 1}"),
    )

    for extra in ("", "&include_unstated=true"):
        items = (await client.get(f"/api/postings?season=winter{extra}")).json()["items"]
        assert [i["title"] for i in items] == ["Next winter"]
