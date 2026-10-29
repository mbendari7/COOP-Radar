"""
Tests for the Job Bank feed adapter and for feeds with a rolling window in the runner.
HTTP is faked with respx using a trimmed copy of a real Job Bank feed.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest import jobbank
from app.ingest.base import AdapterError, RawPosting
from app.ingest.jobbank import JobBankAdapter
from app.ingest.registry import adapter_for
from app.ingest.runner import _execute_run
from app.models.ingest_source import IngestSource
from app.models.posting import Posting
from seed import job_boards

FEED_URL = "https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed"


def feed(*entries: tuple[str, str, str, str]) -> str:
    """An Atom feed like Job Bank's. Each entry is (title, job id, location, employer)."""
    body = "".join(
        f"""<entry>
  <title type="html"><![CDATA[{title}]]></title>
  <link rel="alternate" type="text/html" href="https://www.jobbank.gc.ca/jobsearch/jobposting/{ref}"/>
  <id>https://www.jobbank.gc.ca/jobsearch/jobSearchRSSfeed?id={ref}</id>
  <updated>2026-10-28T07:00:00Z</updated>
  <summary type="html"><![CDATA[<strong>Job number:</strong> 1<br /><strong>Location:</strong> {place}<br /><strong>Employer:</strong> {employer}<br /><strong>Salary:</strong> $22.00 hourly]]></summary>
</entry>"""
        for title, ref, place, employer in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">'
        f"<title>Job Bank</title>{body}</feed>"
    )


def make_source(**config: str) -> object:
    class FakeSource:
        adapter_type = "jobbank"

    src = FakeSource()
    src.config = config  # type: ignore[attr-defined]
    return src


@pytest.fixture(autouse=True)
def no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobbank, "_PAUSE", 0)


@pytest.mark.asyncio
@respx.mock
async def test_student_feed_marks_titles_and_reads_the_place() -> None:
    respx.get(FEED_URL, params={"fjsf": "1"}).mock(
        return_value=Response(200, text=feed(
            ("cook", "50595952", "Courtenay (BC)  ", "Whistle Stop Pub"),
            ("summer student - parks", "50595953", "Chambly (QC)", "Ville de Chambly"),
        ))
    )
    jobs = await JobBankAdapter().fetch(make_source(queries="fjsf=1"))

    assert [j.title for j in jobs] == ["Cook (student)", "Summer student - parks"]
    cook = jobs[0]
    assert (cook.company, cook.city, cook.province, cook.country) == (
        "Whistle Stop Pub", "Courtenay", "BC", "CA",
    )
    assert cook.source_ref == "50595952"
    assert cook.source_url == "https://www.jobbank.gc.ca/jobsearch/jobposting/50595952"
    assert cook.description is not None and "$22.00 hourly" in cook.description
    assert cook.posted_at == datetime(2026, 10, 28, 7, tzinfo=UTC)


@pytest.mark.asyncio
@respx.mock
async def test_search_words_tidy_capital_names_and_skip_repeats() -> None:
    same = ("CIVIL ENGINEERING TECHNOLOGIST", "1", "Delta (BC)", "CITY OF DELTA")
    respx.get(FEED_URL, params={"searchstring": "technologist"}).mock(
        return_value=Response(200, text=feed(same))
    )
    respx.get(FEED_URL, params={"searchstring": "engineer"}).mock(
        return_value=Response(200, text=feed(same, ("nurse", "2", "Not Available", "Clinic")))
    )
    jobs = await JobBankAdapter().fetch(make_source(queries="technologist|engineer"))

    assert [(j.title, j.company) for j in jobs] == [
        ("Civil engineering technologist", "City Of Delta"),
        ("Nurse", "Clinic"),
    ]
    assert jobs[1].city == ""  # no place given, extract_fields fills it in later


@pytest.mark.asyncio
@respx.mock
async def test_every_feed_failing_is_an_error() -> None:
    respx.get(FEED_URL).mock(return_value=Response(503))
    with pytest.raises(AdapterError):
        await JobBankAdapter().fetch(make_source(queries="fjsf=1|nurse"))


@pytest.mark.asyncio
@respx.mock
async def test_one_feed_failing_keeps_the_others() -> None:
    respx.get(FEED_URL, params={"searchstring": "nurse"}).mock(return_value=Response(500))
    respx.get(FEED_URL, params={"fjap": "1"}).mock(
        return_value=Response(200, text=feed(("electrician", "9", "Regina (SK)", "Sparks Ltd")))
    )
    jobs = await JobBankAdapter().fetch(make_source(queries="nurse|fjap=1"))
    assert [j.title for j in jobs] == ["Electrician (apprentice)"]


@pytest.mark.asyncio
@respx.mock
async def test_a_feed_that_hiccups_is_tried_once_more() -> None:
    respx.get(FEED_URL).mock(side_effect=[
        Response(502),
        Response(200, text=feed(("nurse", "5", "Kenora (ON)", "District Hospital"))),
    ])
    jobs = await JobBankAdapter().fetch(make_source(queries="nurse"))
    assert [j.title for j in jobs] == ["Nurse"]


def test_jobbank_is_registered_and_seeded() -> None:
    assert isinstance(adapter_for(make_source()), JobBankAdapter)
    assert [name for name, _ in job_boards.JOBBANK_SOURCES] == ["Job Bank jobs (Government of Canada)"]
    # Student and apprentice jobs come first so their titles get marked before any repeat
    assert jobbank.DEFAULT_QUERIES.startswith("fjsf=1|fjap=1|")


def _raw(ref: str, days_old: int) -> RawPosting:
    return RawPosting(
        title=f"Lab technologist {ref}",
        company="Clinic",
        city="Regina",
        province="SK",
        term="",
        description="Lab work.",
        source_ref=ref,
        posted_at=datetime.now(UTC) - timedelta(days=days_old),
    )


@pytest.mark.asyncio
async def test_rolling_feed_keeps_recent_jobs_open_after_they_leave(db_session: AsyncSession):
    """A job that left a rolling feed stays open until it is older than the window."""
    source = IngestSource(name="Job Bank test", adapter_type="jobbank", config={})
    db_session.add(source)
    await db_session.flush()

    adapter = AsyncMock()
    adapter.rolling_window = timedelta(days=21)
    adapter.fetch = AsyncMock(return_value=[_raw("new", 2), _raw("old", 40), _raw("stay", 1)])
    with patch("app.ingest.runner.adapter_for", return_value=adapter):
        await _execute_run(db_session, source.id)

    adapter.fetch = AsyncMock(return_value=[_raw("stay", 1)])
    with patch("app.ingest.runner.adapter_for", return_value=adapter):
        await _execute_run(db_session, source.id)

    rows = (await db_session.execute(select(Posting).where(Posting.source_id == source.id))).scalars()
    closed = {p.source_ref: p.closed_at is not None for p in rows}
    assert closed == {"new": False, "old": True, "stay": False}
